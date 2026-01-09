import asyncio
import pathlib as pl
import typing as tp
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass

from mcp.server.fastmcp import FastMCP
from .logger import logger
from .api_client import (
    create_api_client_state,
    get_guilds,
    get_guild_channels,
    send_message as send_discord_message,
    close_api_client,
    get_dm_conversations as get_dm_conversations_client,
    DiscordDMConversation,
)
from .config import load_config
from .messages import read_recent_messages, read_recent_dm_messages


@dataclass
class DiscordContext:
    config: tp.Any
    client_lock: asyncio.Lock
    token: (
        str | None
    )  # Extracted/loaded token available to all tools (None = extract on first call)


def _save_token_to_file_sync(token: str, token_file: pl.Path) -> None:
    """Save token to file with secure permissions (synchronous)."""
    try:
        token_file.parent.mkdir(parents=True, exist_ok=True)
        token_file.write_text(token)
        token_file.chmod(0o600)
        logger.debug(f"Token cached to {token_file}")
    except Exception as e:
        logger.warning(f"Failed to cache token: {e}")


@asynccontextmanager
async def discord_lifespan(server: FastMCP) -> AsyncIterator[DiscordContext]:
    config = load_config()
    client_lock = asyncio.Lock()
    logger.info("Discord MCP server starting up")

    # Determine which token to use (priority order)
    token = None
    token_file = pl.Path.home() / ".discord_mcp_token"

    # Priority 1: DISCORD_TOKEN environment variable
    if config.token:
        logger.debug("Using token from DISCORD_TOKEN environment variable")
        token = config.token
        # Save to cache for future use
        _save_token_to_file_sync(token, token_file)

    # Priority 2: Load from cached token file
    elif token_file.exists():
        try:
            token = token_file.read_text().strip()
            if token:
                logger.info(f"Loaded token from {token_file}")
            else:
                logger.warning("Token file exists but is empty")
        except Exception as e:
            logger.warning(f"Failed to load token from file: {e}")

    # Priority 3: Leave as None - will extract on first tool call
    if not token:
        logger.info(
            "No cached token found - will extract on first tool call if email/password provided"
        )

    logger.info("Server startup complete - ready for tool calls")

    try:
        yield DiscordContext(config=config, client_lock=client_lock, token=token)
    finally:
        logger.info("Discord MCP server shutting down")


async def _execute_with_fresh_client[T](
    discord_ctx: DiscordContext,
    operation: Callable[[tp.Any], tp.Awaitable[tuple[tp.Any, T]]],
) -> T:
    """Execute Discord operation with fresh client state, extracting token if needed"""
    async with discord_ctx.client_lock:  # Serializes - only one tool runs at a time
        # Create client state with potentially None token
        client_state = create_api_client_state(
            token=discord_ctx.token,
            email=discord_ctx.config.email,
            password=discord_ctx.config.password,
            headless=True,
        )
        try:
            # This calls _ensure_http_client() which calls _load_or_refresh_token()
            # That function will extract token if needed using existing logic
            client_state, result = await operation(client_state)

            # If token was extracted, update context for future calls
            if client_state.token and not discord_ctx.token:
                discord_ctx.token = client_state.token
                logger.info("Token extracted and cached for future tool calls")

            return result
        finally:
            logger.debug("Cleaning up API client resources")
            await close_api_client(client_state)


mcp = FastMCP("discord-mcp", lifespan=discord_lifespan)


@mcp.tool()
async def get_servers() -> list[dict[str, str]]:
    """List all Discord servers (guilds) you have access to"""
    ctx = mcp.get_context()
    discord_ctx = tp.cast(DiscordContext, ctx.request_context.lifespan_context)

    guilds = await _execute_with_fresh_client(discord_ctx, get_guilds)
    result = [{"id": g.id, "name": g.name} for g in guilds]

    # Log result for debugging
    import json

    logger.debug(f"get_servers returning {len(result)} guilds")
    for guild in result:
        try:
            # Ensure each guild can be JSON serialized
            json.dumps(guild)
        except Exception as e:
            logger.error(f"Guild cannot be JSON serialized: {guild} - Error: {e}")

    return result


@mcp.tool()
async def get_channels(server_id: str) -> list[dict[str, str]]:
    """List all channels in a specific Discord server"""
    ctx = mcp.get_context()
    discord_ctx = tp.cast(DiscordContext, ctx.request_context.lifespan_context)

    async def operation(state):
        return await get_guild_channels(state, server_id)

    channels = await _execute_with_fresh_client(discord_ctx, operation)
    return [{"id": c.id, "name": c.name, "type": str(c.type)} for c in channels]


@mcp.tool()
async def read_messages(
    server_id: str, channel_id: str, max_messages: int, hours_back: int | None = None
) -> list[dict[str, tp.Any]]:
    """Read recent messages from a specific channel"""
    if hours_back is not None and not (1 <= hours_back <= 8760):
        raise ValueError("hours_back must be between 1 and 8760 (1 year)")
    if not (1 <= max_messages <= 1000):
        raise ValueError("max_messages must be between 1 and 1000")

    ctx = mcp.get_context()
    discord_ctx = tp.cast(DiscordContext, ctx.request_context.lifespan_context)

    async def operation(state):
        # If hours_back is None, use a very large value to effectively disable time filtering
        effective_hours_back = (
            hours_back if hours_back is not None else 87600
        )  # 10 years
        return await read_recent_messages(
            state, server_id, channel_id, effective_hours_back, max_messages
        )

    messages = await _execute_with_fresh_client(discord_ctx, operation)
    return [
        {
            "id": m.id,
            "content": m.content,
            "author_name": m.author_name,
            "timestamp": m.timestamp.isoformat(),
            "attachments": m.attachments,
        }
        for m in messages
    ]


@mcp.tool()
async def send_message(
    server_id: str, channel_id: str, content: str
) -> dict[str, tp.Any]:
    """Send a message to a specific Discord channel. Long messages are automatically split."""
    if len(content) == 0:
        raise ValueError("Message content cannot be empty")

    # Split long messages into chunks of 2000 characters or less
    chunks = []
    if len(content) <= 2000:
        chunks = [content]
    else:
        # Split by newlines first to avoid breaking paragraphs
        lines = content.split("\n")
        current_chunk = ""

        for line in lines:
            # If single line is too long, split it by words
            if len(line) > 2000:
                words = line.split(" ")
                current_line = ""
                for word in words:
                    if len(current_line + " " + word) <= 2000:
                        current_line += (" " + word) if current_line else word
                    else:
                        if current_line:
                            if len(current_chunk + "\n" + current_line) <= 2000:
                                current_chunk += (
                                    ("\n" + current_line)
                                    if current_chunk
                                    else current_line
                                )
                            else:
                                chunks.append(current_chunk)
                                current_chunk = current_line
                            current_line = word
                        else:
                            # Single word too long, truncate it
                            current_line = word[:2000]
                if current_line:
                    if len(current_chunk + "\n" + current_line) <= 2000:
                        current_chunk += (
                            ("\n" + current_line) if current_chunk else current_line
                        )
                    else:
                        chunks.append(current_chunk)
                        current_chunk = current_line
            else:
                # Normal line length
                if len(current_chunk + "\n" + line) <= 2000:
                    current_chunk += ("\n" + line) if current_chunk else line
                else:
                    chunks.append(current_chunk)
                    current_chunk = line

        if current_chunk:
            chunks.append(current_chunk)

    ctx = mcp.get_context()
    discord_ctx = tp.cast(DiscordContext, ctx.request_context.lifespan_context)

    message_ids = []
    for i, chunk in enumerate(chunks):

        async def operation(state, chunk_content=chunk):
            return await send_discord_message(state, channel_id, chunk_content)

        message_id = await _execute_with_fresh_client(discord_ctx, operation)
        message_ids.append(message_id)

        # Small delay between messages to avoid rate limiting
        if i < len(chunks) - 1:
            await asyncio.sleep(0.5)

    return {
        "message_ids": message_ids,
        "status": "sent",
        "chunks": len(chunks),
        "total_length": len(content),
    }


@mcp.tool()
async def send_message_with_attachment(
    server_id: str,
    channel_id: str,
    content: str,
    file_path: str,
    filename: str | None = None,
) -> dict[str, tp.Any]:
    """Send a message with a file attachment to a Discord channel.

    Args:
        server_id: Discord server ID (for validation/logging)
        channel_id: Discord channel ID to send to
        content: Message text content (max 2000 chars)
        file_path: Absolute path to file to attach
        filename: Optional custom filename to display in Discord

    Returns:
        {
            "message_id": str,
            "status": "sent",
            "file_size": int,
            "filename": str
        }

    Raises:
        ValueError: If content exceeds 2000 characters
        FileNotFoundError: If file doesn't exist
        PermissionError: If file isn't readable
    """
    from pathlib import Path

    from .api_client import (
        send_message_with_attachment as send_discord_message_with_attachment,
    )

    # Validate content length (cannot split messages with attachments)
    if len(content) > 2000:
        raise ValueError(
            f"Message content exceeds Discord's 2000 character limit ({len(content)} chars). "
            "Messages with attachments cannot be split. Please shorten your message."
        )

    # Get file info for response
    file = Path(file_path).expanduser().resolve()
    file_size = file.stat().st_size if file.exists() else 0
    actual_filename = filename if filename else file.name

    ctx = mcp.get_context()
    discord_ctx = tp.cast(DiscordContext, ctx.request_context.lifespan_context)

    async def operation(state):
        return await send_discord_message_with_attachment(
            state, channel_id, content, file_path, filename
        )

    message_id = await _execute_with_fresh_client(discord_ctx, operation)

    return {
        "message_id": message_id,
        "status": "sent",
        "file_size": file_size,
        "filename": actual_filename,
    }


def _find_conversation_matches(
    search_name: str, conversations: list[DiscordDMConversation]
) -> list[DiscordDMConversation]:
    """Find DM conversations matching a search name or username.

    Matching strategy (case-insensitive), prioritizing username over display name:
    1. Exact username match
    2. Exact display name match
    3. Username starts with search
    4. Display name starts with search
    5. Display name contains search

    Returns all matches in order of match quality.
    """
    search_lower = search_name.strip().lower()

    # Separate buckets for username vs name matches to ensure username priority
    username_exact = []
    name_exact = []
    username_starts = []
    name_starts = []
    name_contains = []

    for conv in conversations:
        # Skip conversations with no name
        if not conv.name:
            continue

        conv_name_lower = conv.name.lower()
        conv_username_lower = conv.username.lower() if conv.username else None

        # Check username first (exact identifier)
        if conv_username_lower:
            if conv_username_lower == search_lower:
                username_exact.append(conv)
                continue
            elif conv_username_lower.startswith(search_lower):
                username_starts.append(conv)
                continue

        # Then check display name
        if conv_name_lower == search_lower:
            name_exact.append(conv)
        elif conv_name_lower.startswith(search_lower):
            name_starts.append(conv)
        elif search_lower in conv_name_lower:
            name_contains.append(conv)

    # Return in priority order: username matches before name matches
    return username_exact + name_exact + username_starts + name_starts + name_contains


@mcp.tool()
async def get_dm_conversations() -> list[dict[str, tp.Any]]:
    """List all direct message conversations (1-on-1 and group DMs) with all available attributes.

    Returns:
        List of DM conversations with:
        - id: Conversation ID
        - name: Display name (global_name for 1-on-1 DMs, custom name for groups)
        - username: Username identifier (for 1-on-1 DMs only, None for groups)
        - type: "dm" or "group_dm"
        - recipient_count: Number of recipients
        - last_message_timestamp: ISO format timestamp of last message
        - avatar_url: Avatar URL if available
    """
    ctx = mcp.get_context()
    discord_ctx = tp.cast(DiscordContext, ctx.request_context.lifespan_context)

    async def operation(state):
        return await get_dm_conversations_client(state)

    conversations = await _execute_with_fresh_client(discord_ctx, operation)
    return [
        {
            "id": c.id,
            "name": c.name,
            "username": c.username,
            "type": c.type,
            "recipient_count": c.recipient_count,
            "last_message_timestamp": c.last_message_timestamp.isoformat()
            if c.last_message_timestamp
            else None,
            "avatar_url": c.avatar_url,
        }
        for c in conversations
    ]


@mcp.tool()
async def read_dm_messages(
    name: str, max_messages: int, hours_back: int | None = None
) -> list[dict[str, tp.Any]]:
    """Read recent messages from a DM conversation by username or display name.

    Searches for conversations by username (exact identifier) or display name (global_name).
    For best results, use the username from get_dm_conversations output.

    Args:
        name: Username (e.g., "johndoe123") or display name (e.g., "John Doe") to search for
        max_messages: Maximum number of messages to return (1-1000)
        hours_back: How many hours back to look (optional, default: no time limit, range: 1-8760)

    Returns:
        If single match found: List of messages from the conversation
        If multiple matches found: List with one object containing:
            - multiple_matches_found: True
            - search_term: The search term used
            - message: Helper message
            - options: List of matching conversations with their details and suggested search terms

    Raises:
        ValueError: If name not found or invalid parameters
    """
    # Validate parameters
    if hours_back is not None and not (1 <= hours_back <= 8760):
        raise ValueError("hours_back must be between 1 and 8760 (1 year)")
    if not (1 <= max_messages <= 1000):
        raise ValueError("max_messages must be between 1 and 1000")
    if not name or not name.strip():
        raise ValueError("name cannot be empty")

    ctx = mcp.get_context()
    discord_ctx = tp.cast(DiscordContext, ctx.request_context.lifespan_context)

    # Step 1: Get all DM conversations
    async def get_convs_operation(state):
        return await get_dm_conversations_client(state)

    conversations = await _execute_with_fresh_client(discord_ctx, get_convs_operation)

    # Step 2: Search for matching name or username
    matches = _find_conversation_matches(name, conversations)

    if len(matches) == 0:
        raise ValueError(
            f"No DM conversation found matching '{name}'. "
            f"Use get_dm_conversations to see available conversations."
        )
    elif len(matches) > 1:
        # Return a list of matching conversations for the user to choose from
        return [
            {
                "multiple_matches_found": True,
                "search_term": name,
                "message": f"Found {len(matches)} conversations matching '{name}'. Please use the exact username or full display name from the options below.",
                "options": [
                    {
                        "id": m.id,
                        "name": m.name,
                        "username": m.username,
                        "type": m.type,
                        "recipient_count": m.recipient_count,
                        "last_message_timestamp": m.last_message_timestamp.isoformat()
                        if m.last_message_timestamp
                        else None,
                        "suggestion": m.username if m.username else m.name,
                    }
                    for m in matches
                ],
            }
        ]

    # Step 3: Read messages from the matched conversation
    conversation = matches[0]

    async def read_msgs_operation(state):
        # If hours_back is None, use a very large value to effectively disable time filtering
        effective_hours_back = (
            hours_back if hours_back is not None else 87600
        )  # 10 years
        return await read_recent_dm_messages(
            state, conversation.id, effective_hours_back, max_messages
        )

    messages = await _execute_with_fresh_client(discord_ctx, read_msgs_operation)

    return [
        {
            "id": m.id,
            "content": m.content,
            "author_name": m.author_name,
            "timestamp": m.timestamp.isoformat(),
            "attachments": m.attachments,
            "conversation_name": conversation.name,  # Include context
        }
        for m in messages
    ]


def main():
    mcp.run()


if __name__ == "__main__":
    main()
