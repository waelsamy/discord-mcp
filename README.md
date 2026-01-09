# Discord MCP Server

A Model Context Protocol (MCP) server that lets LLMs read messages, discover channels, send messages, and monitor Discord communities using the Discord HTTP API.

## Features

- List Discord servers and channels you have access to
- Read recent messages with time filtering (newest first)
- Send messages to Discord channels (automatically splits long messages)
- Send messages with file attachments
- Read direct messages (1-on-1 and group DMs)
- Token-based authentication (automatic extraction supported)
- Fast API-based approach - no browser automation needed at runtime

## Quick Start with Claude Code

```bash
# Add Discord MCP server (with token)
claude mcp add discord-mcp -s user -e DISCORD_TOKEN=your_token -- uvx --from git+https://github.com/waelsamy/discord-mcp.git discord-mcp

# Or with email/password (auto-extracts token on first use)
claude mcp add discord-mcp -s user -e DISCORD_EMAIL=your_email@example.com -e DISCORD_PASSWORD=your_password -- uvx --from git+https://github.com/waelsamy/discord-mcp.git discord-mcp

# Start Claude Code
claude
```

### Usage Examples

```bash
# List your Discord servers
> use get_servers to show me all my Discord servers

# Read recent messages (max_messages is required)
> read the last 20 messages from channel ID 123 in server ID 456

# Send a message (long messages automatically split)
> send "Hello!" to channel 123 in server 456

# Send a message with attachment
> send a file /path/to/image.png to channel 123 in server 456

# List DM conversations
> show me my direct message conversations

# Read DMs from a user
> read the last 10 messages from my DM with johndoe123

# Monitor communities
> summarize discussions from the last 24 hours across my Discord servers
```

## Available Tools

- **`get_servers`** - List all Discord servers you have access to
- **`get_channels(server_id)`** - List channels in a specific server
- **`read_messages(server_id, channel_id, max_messages, hours_back?)`** - Read recent messages (newest first)
- **`send_message(server_id, channel_id, content)`** - Send messages to channels (automatically splits long messages)
- **`send_message_with_attachment(server_id, channel_id, content, file_path, filename?)`** - Send a message with a file attachment
- **`get_dm_conversations()`** - List all direct message conversations
- **`read_dm_messages(name, max_messages, hours_back?)`** - Read messages from a DM by username or display name

## Manual Setup

### Prerequisites
- Python 3.10+ with `uv` package manager
- Discord token or account credentials

### Installation
```bash
git clone https://github.com/waelsamy/discord-mcp.git
cd discord-mcp
uv sync
uv run playwright install  # Only needed for token extraction
```

### Configuration

#### Option 1: Using Discord Token (Recommended)

```env
DISCORD_TOKEN=your_discord_token_here
```

To extract your token, run:
```bash
uv run python get_token.py
```

#### Option 2: Using Email/Password

```env
DISCORD_EMAIL=your_email@example.com
DISCORD_PASSWORD=your_password
```

The server will automatically extract and cache your token on first use.

### Run Server
```bash
uv run python main.py
```

## Claude Desktop Integration

Add to `~/.claude/claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "discord": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/waelsamy/discord-mcp.git", "discord-mcp"],
      "env": {
        "DISCORD_TOKEN": "your_token_here"
      }
    }
  }
}
```

Or with email/password:
```json
{
  "mcpServers": {
    "discord": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/waelsamy/discord-mcp.git", "discord-mcp"],
      "env": {
        "DISCORD_EMAIL": "your_email@example.com",
        "DISCORD_PASSWORD": "your_password"
      }
    }
  }
}
```

## Development

```bash
# Type checking
uv run pyright

# Formatting
uvx ruff format .

# Linting
uvx ruff check --fix --unsafe-fixes .

# Testing
uv run pytest -v tests/
```

## Security Notes

- Token is cached securely at `~/.discord_mcp_token` with 0o600 permissions
- Never commit your token or `.env` file to git
- Consider using a dedicated Discord account for automation
- Server includes delays to avoid rate limiting (0.5s between split messages)
- If your token is exposed, change your Discord password to invalidate it

## Troubleshooting

- **Token extraction fails**: Run `uv run python get_token.py` interactively
- **MFA/2FA enabled**: Use `get_token.py` to complete authentication manually
- **Rate limits**: Reduce `max_messages`, monitor for Discord warnings
- **Token expired**: Server automatically detects 401 errors; re-run token extraction if needed
- **Browser errors**: Run `uv run playwright install --force`

## Legal Notice

Ensure compliance with Discord's Terms of Service. Only access information you would normally have access to as a user. Use for legitimate monitoring and research purposes.

## Author

[waelsamy](https://github.com/waelsamy)
