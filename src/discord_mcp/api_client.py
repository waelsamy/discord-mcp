"""Discord API client using HTTP requests instead of web scraping."""

import pathlib as pl
from datetime import datetime, timezone
from typing import Any
import dataclasses as dc

import httpx

from .logger import logger


@dc.dataclass(frozen=True)
class DiscordMessage:
    id: str
    content: str
    author_name: str
    author_id: str
    channel_id: str
    timestamp: datetime
    attachments: list[str]


@dc.dataclass(frozen=True)
class DiscordChannel:
    id: str
    name: str
    type: int
    guild_id: str | None


@dc.dataclass(frozen=True)
class DiscordGuild:
    id: str
    name: str
    icon: str | None = None


@dc.dataclass(frozen=True)
class DiscordDMConversation:
    """Represents a DM conversation (1-on-1 or group)"""

    id: str  # Conversation ID from URL
    name: str  # Display name (global_name for DMs, custom name for groups)
    username: str | None  # Username (for 1-on-1 DMs only, used as identifier)
    type: str  # "dm" or "group_dm"
    recipient_count: int  # Number of recipients (1 for DM, 2+ for group)
    last_message_timestamp: datetime | None  # Most recent message time
    avatar_url: str | None  # Avatar URL if available


@dc.dataclass(frozen=True)
class APIClientState:
    """Client state for Discord API access."""

    token: str | None = None
    email: str | None = None
    password: str | None = None
    headless: bool = True
    token_file: pl.Path = dc.field(
        default_factory=lambda: pl.Path.home() / ".discord_mcp_token"
    )
    http_client: httpx.AsyncClient | None = None


def create_api_client_state(
    token: str | None = None,
    email: str | None = None,
    password: str | None = None,
    headless: bool = True,
) -> APIClientState:
    """Create a new API client state.

    Args:
        token: Discord auth token (if provided, email/password are not needed)
        email: Discord email (required if token not provided)
        password: Discord password (required if token not provided)
        headless: Whether to run browser in headless mode (only used if login needed)
    """
    return APIClientState(
        token=token, email=email, password=password, headless=headless
    )


async def _get_fingerprint() -> str:
    """Get Discord fingerprint by visiting the login page."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                "https://discord.com/api/v9/experiments",
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
                },
                timeout=30.0,
            )
            data = response.json()
            fingerprint = data.get("fingerprint")
            if fingerprint:
                logger.debug(f"Got fingerprint: {fingerprint}")
                return fingerprint
            raise RuntimeError("No fingerprint in response")
        except Exception as e:
            logger.warning(f"Failed to get fingerprint: {e}, using fallback")
            # Fallback fingerprint if we can't get one
            return "1459218773813760205.kdP1VW_xZM22wrtN0b64AJDO_Z0"


async def _extract_token_via_api(email: str, password: str) -> str:
    """Extract Discord auth token by logging in via API.

    DEPRECATED: This method uses Discord's /auth/login API endpoint which is against
    Discord's Terms of Service and may result in account bans. This function is kept
    for reference only and should NOT be called.

    Use headless browser extraction instead (token_extractor.py).
    """
    raise RuntimeError(
        "API-based login is deprecated and disabled. "
        "This method violates Discord's Terms of Service. "
        "Use headless browser extraction instead."
    )

    # Original implementation commented out to prevent accidental use
    """
    logger.debug("Extracting Discord token via API login")

    # Get fingerprint first
    fingerprint = await _get_fingerprint()

    # Updated x-super-properties with latest client build number
    super_properties = "eyJvcyI6Ik1hYyBPUyBYIiwiYnJvd3NlciI6IkNocm9tZSIsImRldmljZSI6IiIsInN5c3RlbV9sb2NhbGUiOiJlbi1VUyIsImhhc19jbGllbnRfbW9kcyI6ZmFsc2UsImJyb3dzZXJfdXNlcl9hZ2VudCI6Ik1vemlsbGEvNS4wIChNYWNpbnRvc2g7IEludGVsIE1hYyBPUyBYIDEwXzE1XzcpIEFwcGxlV2ViS2l0LzUzNy4zNiAoS0hUTUwsIGxpa2UgR2Vja28pIENocm9tZS8xNDMuMC4wLjAgU2FmYXJpLzUzNy4zNiIsImJyb3dzZXJfdmVyc2lvbiI6IjE0My4wLjAuMCIsIm9zX3ZlcnNpb24iOiIxMC4xNS43IiwicmVmZXJyZXIiOiIiLCJyZWZlcnJpbmdfZG9tYWluIjoiIiwicmVmZXJyZXJfY3VycmVudCI6IiIsInJlZmVycmluZ19kb21haW5fY3VycmVudCI6IiIsInJlbGVhc2VfY2hhbm5lbCI6InN0YWJsZSIsImNsaWVudF9idWlsZF9udW1iZXIiOjQ4NDIxMiwiY2xpZW50X2V2ZW50X3NvdXJjZSI6bnVsbH0="

    async with httpx.AsyncClient(follow_redirects=True) as client:
        try:
            # Call Discord's login API with browser-like headers matching the curl
            response = await client.post(
                "https://discord.com/api/v9/auth/login",
                json={
                    "login": email,
                    "password": password,
                    "undelete": False,
                    "login_source": None,
                    "gift_code_sku_id": None,
                },
                headers={
                    "Accept": "*/*",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept-Encoding": "gzip, deflate, br",
                    "Content-Type": "application/json",
                    "Origin": "https://discord.com",
                    "Referer": "https://discord.com/login",
                    "Sec-Ch-Ua": '"Google Chrome";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
                    "Sec-Ch-Ua-Mobile": "?0",
                    "Sec-Ch-Ua-Platform": '"macOS"',
                    "Sec-Fetch-Dest": "empty",
                    "Sec-Fetch-Mode": "cors",
                    "Sec-Fetch-Site": "same-origin",
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
                    "X-Debug-Options": "bugReporterEnabled",
                    "X-Discord-Locale": "en-US",
                    "X-Discord-Timezone": "America/New_York",
                    "X-Fingerprint": fingerprint,
                    "X-Super-Properties": super_properties,
                },
                timeout=30.0,
            )

            response.raise_for_status()
            data = response.json()

            # Check if MFA/2FA is required
            if "mfa" in data and data["mfa"]:
                raise RuntimeError(
                    "MFA/2FA is enabled on this account. Please disable it or use a different authentication method."
                )

            # Check if CAPTCHA is required
            if "captcha_key" in data and data["captcha_key"]:
                raise RuntimeError(
                    "CAPTCHA verification required. Discord has detected automated login. "
                    "Try logging in manually through a browser first, then retry."
                )

            # Get the token
            token = data.get("token")
            if not token:
                raise RuntimeError(f"No token in API response: {data}")

            logger.debug(f"Successfully extracted token via API (length: {len(token)})")
            return token

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 400:
                error_data = e.response.json()
                if "captcha_key" in error_data:
                    raise RuntimeError(
                        "CAPTCHA verification required. Please login manually through a browser first."
                    )
                raise RuntimeError(f"Login failed: {error_data}")
            raise RuntimeError(f"HTTP error during login: {e}")
        except Exception as e:
            raise RuntimeError(f"Failed to login to Discord via API: {e}")
    """


async def _load_or_refresh_token(state: APIClientState) -> tuple[APIClientState, str]:
    """Load or refresh Discord authentication token.

    Priority order:
    1. Use token from state (if already loaded) and save to file
    2. Load from ~/.discord_mcp_token file
    3. Extract via headless browser
    4. Raise error - require manual extraction
    """
    # Priority 1: Use provided token and save to file
    if state.token:
        logger.debug("Using provided token from env/config")
        _save_token_to_file(state.token, state.token_file)
        return state, state.token

    # Priority 2: Try to load from file
    if state.token_file.exists():
        try:
            token = state.token_file.read_text().strip()
            if token:
                logger.debug("Loaded token from file")
                return dc.replace(state, token=token), token
        except Exception as e:
            logger.warning(f"Failed to load token from file: {e}")

    # Priority 3: Extract via headless browser (NEW!)
    if state.email and state.password and state.headless:
        try:
            logger.info(
                f"Extracting token via headless browser... "
                f"(email={state.email}, headless={state.headless})"
            )
            from .token_extractor import extract_token_headless

            token = await extract_token_headless(
                email=state.email, password=state.password, headless=True
            )

            _save_token_to_file(token, state.token_file)
            logger.info("Token extracted and saved successfully")
            return dc.replace(state, token=token), token

        except Exception as e:
            logger.error(f"Headless browser extraction failed: {e}")
            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")
            # Fall through to Priority 4 error

    # Priority 4: No more fallbacks - require manual token extraction
    raise RuntimeError(
        "No token available and automated extraction failed. "
        "Please run 'uv run python get_token.py' to extract your token manually, "
        "then add it to .env as DISCORD_TOKEN=your_token"
    )


def _save_token_to_file(token: str, token_file: pl.Path) -> None:
    """Save token to file with secure permissions.

    Args:
        token: Discord authentication token
        token_file: Path to token file
    """
    try:
        token_file.parent.mkdir(parents=True, exist_ok=True)
        token_file.write_text(token)
        token_file.chmod(0o600)  # Owner read/write only
        logger.debug(f"Saved token to {token_file}")
    except Exception as e:
        logger.warning(f"Failed to save token to file: {e}")


async def _ensure_http_client(state: APIClientState) -> APIClientState:
    """Ensure HTTP client is initialized with auth headers."""
    if state.http_client:
        return state

    state, token = await _load_or_refresh_token(state)

    # Updated x-super-properties with latest client build number
    super_properties = "eyJvcyI6Ik1hYyBPUyBYIiwiYnJvd3NlciI6IkNocm9tZSIsImRldmljZSI6IiIsInN5c3RlbV9sb2NhbGUiOiJlbi1VUyIsImhhc19jbGllbnRfbW9kcyI6ZmFsc2UsImJyb3dzZXJfdXNlcl9hZ2VudCI6Ik1vemlsbGEvNS4wIChNYWNpbnRvc2g7IEludGVsIE1hYyBPUyBYIDEwXzE1XzcpIEFwcGxlV2ViS2l0LzUzNy4zNiAoS0hUTUwsIGxpa2UgR2Vja28pIENocm9tZS8xNDMuMC4wLjAgU2FmYXJpLzUzNy4zNiIsImJyb3dzZXJfdmVyc2lvbiI6IjE0My4wLjAuMCIsIm9zX3ZlcnNpb24iOiIxMC4xNS43IiwicmVmZXJyZXIiOiIiLCJyZWZlcnJpbmdfZG9tYWluIjoiIiwicmVmZXJyZXJfY3VycmVudCI6IiIsInJlZmVycmluZ19kb21haW5fY3VycmVudCI6IiIsInJlbGVhc2VfY2hhbm5lbCI6InN0YWJsZSIsImNsaWVudF9idWlsZF9udW1iZXIiOjQ4NDIxMiwiY2xpZW50X2V2ZW50X3NvdXJjZSI6bnVsbH0="

    # Don't set Content-Type in client headers - let it be set per-request
    # (application/json for JSON, multipart/form-data for file uploads)
    client = httpx.AsyncClient(
        headers={
            "Authorization": token,
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            # NOTE: Content-Type removed - will be set per-request
            "Origin": "https://discord.com",
            "Referer": "https://discord.com/channels/@me",
            "Sec-Ch-Ua": '"Google Chrome";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"macOS"',
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
            "X-Debug-Options": "bugReporterEnabled",
            "X-Discord-Locale": "en-US",
            "X-Discord-Timezone": "America/New_York",
            "X-Super-Properties": super_properties,
        },
        timeout=30.0,
    )

    return dc.replace(state, http_client=client)


async def _api_request(
    state: APIClientState, method: str, endpoint: str, **kwargs: Any
) -> tuple[APIClientState, Any]:
    """Make an API request to Discord."""
    state = await _ensure_http_client(state)
    if not state.http_client:
        raise RuntimeError("HTTP client not initialized")

    url = f"https://discord.com/api/v9{endpoint}"
    logger.debug(f"{method} {url}")

    # Handle Content-Type header per-request:
    # - For files (multipart/form-data): httpx will auto-set with boundary
    # - For JSON: explicitly set application/json
    request_kwargs = kwargs.copy()
    if "files" not in kwargs and "json" in kwargs:
        # JSON request - add Content-Type header
        request_kwargs.setdefault("headers", {})
        if isinstance(request_kwargs["headers"], dict):
            request_kwargs["headers"]["Content-Type"] = "application/json"
        logger.debug("Sending JSON request with Content-Type: application/json")
    elif "files" in kwargs:
        # File upload - httpx will set Content-Type with boundary
        logger.debug("Sending multipart/form-data (httpx will set Content-Type)")

    try:
        response = await state.http_client.request(method, url, **request_kwargs)

        # Handle token expiration
        if response.status_code == 401:
            logger.warning("Token expired, refreshing")
            # Close old client
            await state.http_client.aclose()

            # Delete token and refresh
            if state.token_file.exists():
                state.token_file.unlink()

            state = dc.replace(state, token=None, http_client=None)
            state, new_token = await _load_or_refresh_token(state)
            state = await _ensure_http_client(state)

            # Retry request - use the same request_kwargs we prepared earlier
            if not state.http_client:
                raise RuntimeError("HTTP client not initialized after refresh")
            response = await state.http_client.request(method, url, **request_kwargs)

        response.raise_for_status()
        return state, response.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"API request failed: {e.response.status_code} {e.response.text}")
        raise
    except Exception as e:
        logger.error(f"API request error: {e}")
        raise


async def close_api_client(state: APIClientState) -> None:
    """Close HTTP client."""
    if state.http_client:
        await state.http_client.aclose()


async def get_guilds(
    state: APIClientState,
) -> tuple[APIClientState, list[DiscordGuild]]:
    """Get all guilds (servers) the user is in."""
    state, guilds_data = await _api_request(state, "GET", "/users/@me/guilds")

    guilds = [
        DiscordGuild(
            id=g["id"],
            name=g["name"],
            icon=g.get("icon"),
        )
        for g in guilds_data
    ]

    logger.debug(f"Found {len(guilds)} guilds")
    return state, guilds


async def get_guild_channels(
    state: APIClientState, guild_id: str
) -> tuple[APIClientState, list[DiscordChannel]]:
    """Get all channels in a guild."""
    state, channels_data = await _api_request(
        state, "GET", f"/guilds/{guild_id}/channels"
    )

    channels = [
        DiscordChannel(
            id=c["id"],
            name=c["name"],
            type=c["type"],
            guild_id=guild_id,
        )
        for c in channels_data
        if c["type"] in [0, 2, 5, 11, 12, 13, 15, 16]  # Text-based channel types
    ]

    logger.debug(f"Found {len(channels)} channels in guild {guild_id}")
    return state, channels


async def get_channel_messages(
    state: APIClientState,
    channel_id: str,
    limit: int = 100,
    before: str | None = None,
    after: str | None = None,
) -> tuple[APIClientState, list[DiscordMessage]]:
    """Get messages from a channel."""
    params: dict[str, Any] = {"limit": min(limit, 100)}  # Discord API max is 100
    if before:
        params["before"] = before
    if after:
        params["after"] = after

    state, messages_data = await _api_request(
        state, "GET", f"/channels/{channel_id}/messages", params=params
    )

    messages = []
    for msg in messages_data:
        # Parse timestamp
        timestamp_str = msg.get("timestamp", "")
        timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))

        # Get author info
        author = msg.get("author", {})
        author_name = author.get("username", "Unknown")
        author_id = author.get("id", "unknown")

        # Get attachments
        attachments = [att["url"] for att in msg.get("attachments", [])]

        messages.append(
            DiscordMessage(
                id=msg["id"],
                content=msg.get("content", ""),
                author_name=author_name,
                author_id=author_id,
                channel_id=channel_id,
                timestamp=timestamp,
                attachments=attachments,
            )
        )

    logger.debug(f"Got {len(messages)} messages from channel {channel_id}")
    return state, messages


async def get_dm_conversations(
    state: APIClientState,
) -> tuple[APIClientState, list[DiscordDMConversation]]:
    """Get all DM conversations."""
    state, dm_data = await _api_request(state, "GET", "/users/@me/channels")

    conversations = []
    for dm in dm_data:
        dm_type = dm.get("type", 0)

        # Type 1 = DM, Type 3 = Group DM
        if dm_type not in [1, 3]:
            continue

        # For DMs, get recipient info
        recipients = dm.get("recipients", [])
        if dm_type == 1:
            # 1-on-1 DM
            if recipients:
                recipient = recipients[0]
                # Use global_name (display name) as the readable name
                name = (
                    recipient.get("global_name")
                    or recipient.get("username")
                    or "Unknown User"
                )
                # Keep username as identifier
                username = recipient.get("username")
            else:
                name = "Unknown User"
                username = None
            recipient_count = 1
            conv_type = "dm"
        else:
            # Group DM - Type 3
            # Group DMs can have a custom name or use recipient list
            name = dm.get("name")
            if not name and recipients:
                # Build name from first few recipients (prefer global_name)
                recipient_names = [
                    r.get("global_name") or r.get("username") or "Unknown"
                    for r in recipients[:3]
                ]
                name = ", ".join(recipient_names)
                if len(recipients) > 3:
                    name += f" +{len(recipients) - 3} more"
            if not name:
                name = "Unnamed Group"
            username = None  # Groups don't have a single username
            recipient_count = len(recipients)
            conv_type = "group_dm"

        # Get last message timestamp
        last_msg_ts = None
        if last_msg_id := dm.get("last_message_id"):
            try:
                # Discord snowflake IDs encode timestamp
                timestamp_ms = ((int(last_msg_id) >> 22) + 1420070400000) / 1000
                last_msg_ts = datetime.fromtimestamp(timestamp_ms, tz=timezone.utc)
            except Exception:
                pass

        conversations.append(
            DiscordDMConversation(
                id=dm["id"],
                name=name,
                username=username,
                type=conv_type,
                recipient_count=recipient_count,
                last_message_timestamp=last_msg_ts,
                avatar_url=dm.get("icon"),
            )
        )

    logger.debug(f"Found {len(conversations)} DM conversations")
    return state, conversations


async def get_dm_messages(
    state: APIClientState,
    conversation_id: str,
    limit: int = 100,
    before: str | None = None,
    after: str | None = None,
) -> tuple[APIClientState, list[DiscordMessage]]:
    """Get messages from a DM conversation.

    Same as get_channel_messages but for DMs.
    """
    return await get_channel_messages(state, conversation_id, limit, before, after)


async def send_message(
    state: APIClientState, channel_id: str, content: str
) -> tuple[APIClientState, str]:
    """Send a message to a channel or DM."""
    payload = {"content": content}

    state, response = await _api_request(
        state, "POST", f"/channels/{channel_id}/messages", json=payload
    )

    message_id = response.get("id", "unknown")
    logger.debug(f"Sent message {message_id} to channel {channel_id}")
    return state, message_id


async def send_message_with_attachment(
    state: APIClientState,
    channel_id: str,
    content: str,
    file_path: str,
    filename: str | None = None,
) -> tuple[APIClientState, str]:
    """Send a message with a file attachment to a channel or DM.

    Args:
        state: Current API client state
        channel_id: Discord channel ID
        content: Message text content
        file_path: Absolute path to file to attach
        filename: Optional custom filename (defaults to basename of file_path)

    Returns:
        Tuple of (updated state, message ID)

    Raises:
        FileNotFoundError: If the file doesn't exist
        PermissionError: If the file isn't readable
        RuntimeError: If HTTP client not initialized
    """
    import json
    from pathlib import Path

    # Validate file exists and is readable
    file = Path(file_path).expanduser().resolve()
    if not file.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    if not file.is_file():
        raise ValueError(f"Path is not a file: {file_path}")

    # Determine filename
    actual_filename = filename if filename else file.name

    # Read file content
    try:
        file_content = file.read_bytes()
    except PermissionError:
        raise PermissionError(f"Cannot read file: {file_path}")

    # Create multipart form data
    # Discord API requires:
    # - payload_json: form field with stringified JSON message content
    # - files[0]: file upload field with file content
    payload_json = json.dumps({"content": content})

    # httpx expects files parameter for file uploads
    # and data parameter for regular form fields
    files = {
        "files[0]": (actual_filename, file_content, "application/octet-stream"),
    }
    data = {
        "payload_json": payload_json,
    }

    logger.debug(
        f"Preparing multipart request: files={list(files.keys())}, data={list(data.keys())}, payload_json={payload_json[:100]}"
    )

    state, response = await _api_request(
        state,
        "POST",
        f"/channels/{channel_id}/messages",
        files=files,
        data=data,
    )

    message_id = response.get("id", "unknown")
    logger.debug(
        f"Sent message {message_id} with attachment '{actual_filename}' to channel {channel_id}"
    )
    return state, message_id
