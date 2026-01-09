# Discord MCP Server (Python)

## Task
Build a Discord MCP (Model Context Protocol) server that can:
- Read messages across multiple Discord servers and channels
- Send messages to Discord channels  
- List Discord servers and channels
- Provide efficient message reading with proper chronological ordering
- Handle authentication with Discord credentials using web scraping

## Use Cases
Enable an LLM to:
1. Monitor Discord servers and communities of interest
2. Read and summarize recent messages from channels
3. Send messages to Discord channels
4. Discover available servers and channels

This enables automated community monitoring, content aggregation, and interaction across Discord servers for purposes like community engagement, trend monitoring, and content curation.

## Implementation Approach
This implementation uses **Discord HTTP API** for reliable, fast access:
- Uses Discord's official API for reading messages and managing servers
- Token-based authentication (no bot permissions needed)
- Automatic headless browser token extraction for ease of setup

## Package Management
- Use `uv` package manager for all operations
- Use `uv run` prefix for all Python commands
- Use `uv add` for adding dependencies

## Code Quality
- Always run `uv run pyright` for Python type checking
- Always run `uvx ruff format .` for formatting
- Always run `uvx ruff check --fix --unsafe-fixes .` for linting

## Current Architecture

- **`main.py`** - Entry point that starts the MCP server
- **`src/discord_mcp/server.py`** - FastMCP server with 7 tool definitions
- **`src/discord_mcp/api_client.py`** - HTTP-based Discord client using Discord API
- **`src/discord_mcp/token_extractor.py`** - Headless browser token extraction
- **`src/discord_mcp/config.py`** - Configuration management for Discord credentials
- **`src/discord_mcp/messages.py`** - Message reading and time filtering logic
- **`src/discord_mcp/logger.py`** - Logging configuration (CRITICAL: uses stderr to avoid corrupting MCP stdio protocol)
- **`tests/test_integration.py`** - Integration tests for all MCP tools
- **`get_token.py`** - Interactive token extraction script (uses token_extractor module)

## MCP Tools Implemented
- **`get_servers`** - List all Discord servers you have access to
- **`get_channels(server_id)`** - List all channels in a specific Discord server
- **`read_messages(server_id, channel_id, max_messages, hours_back?)`** - Read recent messages in chronological order (newest first). `hours_back` is optional; if omitted, returns messages without time filtering.
- **`send_message(server_id, channel_id, content)`** - Send messages to specific Discord channels (automatically splits long messages)
- **`send_message_with_attachment(server_id, channel_id, content, file_path, filename?)`** - Send a message with a file attachment to a Discord channel. Content must be ≤2000 chars. Supports any file type.
- **`get_dm_conversations()`** - List all direct message conversations (1-on-1 and group DMs) with attributes: id, name (display name/global_name), username (identifier for 1-on-1 DMs), type, recipient_count, last_message_timestamp, and avatar_url
- **`read_dm_messages(name, max_messages, hours_back?)`** - Read messages from DM by username or display name. Returns messages if single match found, or a list of options if multiple matches found for easy selection. `hours_back` is optional; if omitted, returns messages without time filtering (useful for old conversations).

## Direct Message Support

The server supports reading from Discord direct messages:

- **Dual field search**: Search by username (e.g., "johndoe123") or display name (e.g., "John Doe")
- **Username priority**: Username matches are prioritized over display name matches
- **Both 1-on-1 and group DMs**: Automatically detects conversation type
- **Smart matching**: Exact match > starts-with > contains (username checked first, then display name)
- **Multiple match handling**: Returns a list of options with details when multiple conversations match, making it easy to choose the right one

Example workflow:

1. Call `get_dm_conversations()` to see all available DMs with their usernames and display names
2. Call `read_dm_messages(name="johndoe123", max_messages=20)` using username for exact match
3. Or use display name: `read_dm_messages(name="John Doe", max_messages=20)`
4. For old conversations, omit `hours_back` to read without time filtering: `read_dm_messages(name="johndoe123", max_messages=50)`
5. If multiple matches are found, the response includes a list of options with:
   - Full details (id, name, username, type, recipient_count, last_message_timestamp)
   - A suggested search term for each option
   - Simply use the suggested username or full display name to retry and get the exact match

## Dependencies
- **mcp** - Official MCP library via FastMCP
- **playwright** - Browser automation for Discord web scraping  
- **python-dotenv** - Environment variable management
- **pytest** - Testing framework

## Server Startup & Token Management

The MCP server uses **lazy token extraction** for instant startup while supporting automatic authentication:

1. **Instant Server Startup**: When the server starts, it:
   - Loads token from `DISCORD_TOKEN` env var (if provided) → saves to cache
   - Falls back to cached token at `~/.discord_mcp_token`
   - **Starts instantly even if no token found** (extracts on first tool call)

2. **Lazy Token Extraction** (Automatic on first tool call):
   - If email/password provided but no token cached
   - First tool call triggers headless browser extraction (10-15 seconds)
   - Token automatically saved to `~/.discord_mcp_token` (0o600 permissions)
   - All subsequent tool calls use cached token (instant)

3. **Manual Token Extraction** (For MFA/2FA accounts):
   - Run `uv run python get_token.py` to extract interactively
   - Token is automatically saved and used by server
   - Or manually set `DISCORD_TOKEN` in your `.env` file

4. **Shared Token Context**: Token stored in `DiscordContext` and shared across all MCP tools:
   - No repeated authentication per tool call
   - Fast tool execution after initial extraction
   - Single token for entire server session

5. **Token Priority**:
   - Priority 1: `DISCORD_TOKEN` environment variable → saves to cache
   - Priority 2: Cached token from `~/.discord_mcp_token`
   - Priority 3: Extract on first tool call (if email/password provided)
   - Priority 4: Error with instructions to run `get_token.py`

**Key Benefits**:

- **Instant startup**: Server starts in <1 second even without cached token
- **Automatic extraction**: Headless browser extraction on first tool call (non-MFA accounts)
- **No hanging**: MFA/extraction errors occur during tool call, not at startup

## Test Strategy & Reliability

The implementation prioritizes **reliability over speed** through:

### Token & State Management

- Token loaded at server startup if available (env var or cached file)
- Lazy extraction on first tool call if email/password provided
- Token shared across all tools via `DiscordContext`
- Async lock serialization to prevent race conditions
- Secure token storage at `~/.discord_mcp_token` with 0o600 permissions

### Message Extraction
- **Chronological ordering**: Messages returned newest-first
- **Simplified extraction**: Streamlined from ~130 lines to ~54 lines
- **Robust scrolling**: JavaScript-based scroll to bottom for newest messages
- **Proper filtering**: Time-based and count-based message limiting

### Test Execution
- Sequential test execution (`-n 0` in pytest.ini) to avoid resource conflicts
- Comprehensive integration tests covering all 6 MCP tools
- 100% test reliability across multiple runs

## Performance Characteristics
- **Cookie persistence** eliminates re-login overhead  
- **JavaScript extraction** faster than clicking through UI elements
- **Fresh browser state** adds ~2-3 seconds per tool call but ensures reliability
- **Simplified message logic** improved performance while maintaining functionality

## Development Workflow
1. Make changes following functional programming patterns
2. Run `uv run pyright` for type checking
3. Run `uvx ruff format .` and `uvx ruff check --fix --unsafe-fixes .` for code quality
4. Run `uv run pytest -v tests/` for integration testing
5. Verify all 4 MCP tools work correctly

## Configuration

### Option 1: Using Discord Token (Recommended)

Set environment variables:

```env
DISCORD_TOKEN=your_discord_token_here
DISCORD_HEADLESS=true  # For production
```

To get your Discord token, run:

```bash
uv run python get_token.py
```

This will open a browser where you can log in to Discord, then automatically extract and display your token.

### Option 2: Using Email/Password (Legacy)

Set environment variables:
```env
DISCORD_EMAIL=your_email@example.com
DISCORD_PASSWORD=your_password
DISCORD_HEADLESS=true  # For production
```

**Note:** Token authentication is preferred as it's more secure and doesn't require storing passwords.

### Option 3: Automatic Headless Token Extraction (NEW!)

The server now automatically extracts tokens in headless mode when you provide email/password:

```env
DISCORD_EMAIL=your_email@example.com
DISCORD_PASSWORD=your_password
DISCORD_HEADLESS=true  # Default
```

**How it works:**
1. Server starts without a token
2. Headless browser launches automatically (invisible)
3. Credentials auto-filled and login submitted
4. Token extracted via network capture
5. Token saved to `~/.discord_mcp_token` with secure permissions (0o600)
6. Future runs use the cached token

**Requirements:**
- MFA/2FA must be **disabled** on your Discord account
- If MFA is enabled, the server will provide an error message directing you to use `get_token.py` interactively

**Token Storage:**
- Primary: `DISCORD_TOKEN` environment variable
- Secondary: `~/.discord_mcp_token` file (auto-created)
- Tokens are automatically saved when provided via env var
- Cached tokens are reused on subsequent runs

## Message Ordering Behavior
Messages are returned in **chronological order (newest first)**:
- `max_messages: 1` returns the most recent message
- `max_messages: 20` returns the 20 most recent messages
- More messages means going further back in time chronologically

This ordering was fixed from previous counterintuitive behavior and now works correctly and consistently.

## Critical Bug Fix: Logging Must Use stderr

**Problem:** The MCP protocol uses stdio (stdin/stdout) for JSON-RPC communication between client and server. Any output to stdout corrupts the protocol messages, causing `SyntaxError: Unexpected non-whitespace character after JSON at position 4`.

**Solution:** All logging MUST use `sys.stderr` instead of `sys.stdout`. This is implemented in `logger.py:19`.

**Why This Matters:**

- MCP clients (Claude Desktop, VSCode) communicate via stdio
- Log messages on stdout get mixed with JSON-RPC messages
- This causes JSON parse errors at the protocol layer
- The error appears before tool responses are even processed

**Never:**

- Use `print()` statements (they write to stdout)
- Use `logging.StreamHandler(sys.stdout)`
- Write to stdout directly in any way

**Always:**

- Use the configured logger from `logger.py`
- Ensure all logging goes to stderr
- Test with MCP clients, not just pytest
