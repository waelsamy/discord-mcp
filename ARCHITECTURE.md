# Discord MCP Server - Architecture Documentation

## Table of Contents
1. [Overview](#overview)
2. [Project Structure](#project-structure)
3. [Core Components](#core-components)
4. [Architecture & Design Patterns](#architecture--design-patterns)
5. [Authentication & Session Management](#authentication--session-management)
6. [Message Handling](#message-handling)
7. [MCP Tools](#mcp-tools)
8. [Testing Strategy](#testing-strategy)
9. [Development Workflow](#development-workflow)
10. [Configuration](#configuration)
11. [Dependencies](#dependencies)

---

## Overview

The Discord MCP Server is a Model Context Protocol implementation that enables LLMs to interact with Discord servers through web scraping. Unlike traditional Discord bots that require API tokens and bot permissions, this server uses Playwright browser automation to access Discord as a regular user.

**Key Capabilities**:
- Read messages from any Discord server/channel you have access to
- Send messages to Discord channels
- List available servers and channels
- Time-based message filtering
- Automatic message chunking for long content

**Why Web Scraping?**
- Discord's API only allows reading from servers where you have bot permissions
- Web scraping enables reading from any Discord server you can access as a user
- No need for bot creation, OAuth flows, or server administrator permissions

---

## Project Structure

```
discord-mcp/
├── main.py                          # Entry point - starts MCP server
├── pyproject.toml                   # UV package configuration
├── pytest.ini                       # Test configuration (sequential execution)
├── .env.example                     # Environment variable template
├── src/discord_mcp/
│   ├── __init__.py                  # Package initialization
│   ├── server.py                    # FastMCP server (4 tools)
│   ├── client.py                    # Playwright Discord client (516 lines)
│   ├── config.py                    # Configuration management
│   ├── messages.py                  # Message filtering logic
│   └── logger.py                    # Logging setup
└── tests/
    ├── conftest.py                  # Pytest fixtures
    └── test_integration.py          # Integration tests (4 tests)
```

---

## Core Components

### 1. server.py (202 lines)

The FastMCP server that exposes 4 MCP tools to LLMs.

**Key Features**:
- Lifespan management with `discord_lifespan()` context manager
- Fresh browser client for every tool call via `_execute_with_fresh_client()`
- Async lock for serialization to prevent race conditions
- Cookie persistence for login state

**Core Pattern**:
```python
async def _execute_with_fresh_client(operation):
    """Execute operation with fresh browser client"""
    async with DISCORD_CLIENT_LOCK:
        state = await create_client(CONFIG.email, CONFIG.password)
        try:
            result = await operation(state)
            return result
        finally:
            await close_client(state)
```

This pattern ensures:
- Complete browser state reset between calls
- No memory leaks or browser crashes
- Serialized execution prevents conflicts
- Reliability prioritized over speed (~2-3s overhead per call)

---

### 2. client.py (516 lines)

The Playwright-based Discord web scraping client implementing all Discord interactions.

**Data Models** (Immutable frozen dataclasses):

```python
@dataclass(frozen=True)
class ClientState:
    """Immutable client state - safe for concurrent access"""
    email: str
    password: str
    playwright: Optional[Playwright]
    browser: Optional[Browser]
    context: Optional[BrowserContext]
    page: Optional[Page]
    logged_in: bool
    cookies_file: str

@dataclass(frozen=True)
class DiscordMessage:
    id: str
    content: str
    author_name: str
    author_id: str
    channel_id: str
    timestamp: datetime
    attachments: list[str]

@dataclass(frozen=True)
class DiscordChannel:
    id: str
    name: str
    type: str
    guild_id: str

@dataclass(frozen=True)
class DiscordGuild:
    id: str
    name: str
    icon: Optional[str] = None
```

**Core Functions**:

1. **`create_client(email, password)`** - Main entry point
   - Creates initial ClientState with credentials
   - Initializes browser infrastructure
   - Handles login flow
   - Returns ready-to-use client state

2. **`_ensure_browser(state)`** - Browser initialization
   - Launches Chromium with Playwright
   - Creates browser context (viewport 1920x1080)
   - Loads saved cookies from `~/.discord_mcp_cookies.json`
   - Creates new page
   - Returns updated state

3. **`_check_logged_in(state)`** - Login verification
   - Navigates to `https://discord.com/channels/@me`
   - Checks URL for login/register pages
   - Verifies guild navigation tree is visible
   - Returns boolean login status

4. **`_login(state)`** - Authentication flow
   - Checks if already logged in via cookies
   - Navigates to login page if needed
   - Fills email and password forms
   - Handles 2FA verification redirects
   - Saves storage state (cookies) for future sessions
   - Timing: 2s initial wait, 3s post-login, 5s for verification

5. **`get_guilds(state)`** - Extract all Discord servers
   ```javascript
   // JavaScript DOM extraction
   const tree = document.querySelector('[data-list-id="guildsnav"]');
   const items = tree.querySelectorAll('[role="treeitem"]');
   // Extract guild IDs and names
   ```
   - Scrolls guild list (20 iterations, 100px each)
   - Filters numeric guild IDs
   - Returns list of DiscordGuild objects

6. **`get_guild_channels(state, guild_id)`** - Two-stage channel discovery
   - **Stage 1**: Extract channels user already has access to
   - **Stage 2**: Click "Browse Channels" to discover additional channels
   - Scrolls to load hidden channels
   - Deduplicates by channel ID
   - Returns list of DiscordChannel objects

7. **`get_channel_messages(state, server_id, channel_id, limit, before?, after?)`**
   - Navigates to channel URL
   - Scrolls chat to bottom (newest messages)
   - Iterates through message elements in reverse
   - Supports pagination with PageUp navigation
   - Extracts: id, content, author_name, author_id, timestamp, attachments
   - Returns messages sorted newest-first

8. **`_extract_message_data(element, channel_id, collected)`** - Message parsing
   - Multiple CSS selectors for robustness
   - Extracts content, author, timestamp, attachments
   - Filters out messages with no content or attachments
   - Handles ISO8601 timestamp conversion

9. **`send_message(state, server_id, channel_id, content)`** - Post messages
   - Navigates to channel
   - Finds slate editor input
   - Fills content and presses Enter
   - Returns message ID based on timestamp

10. **`close_client(state)`** - Resource cleanup
    - Closes in reverse order: page → context → browser → playwright
    - Forces garbage collection
    - Handles exceptions gracefully

---

### 3. config.py (45 lines)

Configuration management using NamedTuple for immutability.

```python
class DiscordConfig(NamedTuple):
    email: str
    password: str
    headless: bool
    default_guild_ids: list[str]
    max_messages_per_channel: int
    default_hours_back: int
```

**Environment Variables**:
- `DISCORD_EMAIL` (required) - Discord account email
- `DISCORD_PASSWORD` (required) - Discord password or app password for 2FA
- `DISCORD_HEADLESS` (default: "true") - Run browser in headless mode
- `DISCORD_GUILD_IDS` (optional) - Comma-separated guild IDs to monitor
- `MAX_MESSAGES_PER_CHANNEL` (default: 200) - Maximum messages per channel
- `DEFAULT_HOURS_BACK` (default: 24) - Default time window for messages

---

### 4. messages.py (38 lines)

Message filtering and time-based logic.

```python
async def read_recent_messages(
    state: ClientState,
    server_id: str,
    channel_id: str,
    hours_back: int = 24,
    max_messages: int = 1000
) -> list[DiscordMessage]:
    """Read recent messages with time-based filtering"""
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours_back)

    # Fetch up to max_messages
    messages = await get_channel_messages(state, server_id, channel_id, max_messages)

    # Filter to only messages newer than cutoff_time
    recent = [msg for msg in messages if msg.timestamp > cutoff_time]

    # Return in chronological order (newest first)
    return recent
```

**Logic**:
1. Calculate cutoff timestamp: `now - timedelta(hours=hours_back)`
2. Fetch up to `max_messages` from channel
3. Filter messages newer than cutoff
4. Return in chronological order (newest first)

---

### 5. logger.py (28 lines)

Centralized logging configuration.

```python
import logging

logger = logging.getLogger("discord_mcp")
logger.setLevel(logging.DEBUG)

handler = logging.StreamHandler()
formatter = logging.Formatter(
    "[%(asctime)s] - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s"
)
handler.setFormatter(formatter)
logger.addHandler(handler)
```

**Output Format**: `[time] - [name] - [level] - [function]:[line] - [message]`

---

## Architecture & Design Patterns

### 1. Functional Programming

**Immutable State Transformations**:
```python
# State is never mutated, always replaced
state = await _ensure_browser(state)
state = await _login(state)
```

**Benefits**:
- Thread-safe by design
- Predictable state transitions
- Easy to reason about
- No side effects

### 2. Context Manager Pattern

**Lifespan Management**:
```python
@asynccontextmanager
async def discord_lifespan(app: FastMCP):
    """Manage server lifecycle"""
    logger.info("Discord MCP Server starting...")
    yield
    logger.info("Discord MCP Server shutting down...")
```

### 3. Higher-Order Functions

**Operation Wrapping**:
```python
async def _execute_with_fresh_client(operation: Callable):
    """Higher-order function that wraps operations with client lifecycle"""
    async with DISCORD_CLIENT_LOCK:
        state = await create_client(CONFIG.email, CONFIG.password)
        try:
            return await operation(state)
        finally:
            await close_client(state)
```

### 4. Async/Await Pattern

**Fully Asynchronous**:
- All I/O operations are async
- Non-blocking browser automation
- Concurrent-safe with async locks
- Efficient resource utilization

### 5. Fresh State Per Operation

**Trade Speed for Reliability**:
```python
# Every MCP tool call gets fresh browser
@mcp.tool()
async def get_servers():
    return await _execute_with_fresh_client(_get_servers_impl)
```

**Benefits**:
- No browser crash accumulation
- No memory leaks
- Clean slate for each operation
- 100% test reliability

**Cost**: ~2-3 seconds overhead per call

---

## Authentication & Session Management

### Cookie Persistence

**Location**: `~/.discord_mcp_cookies.json`

**Flow**:
1. First run: Login with credentials → Save cookies
2. Subsequent runs: Load cookies → Skip login if valid
3. Invalid cookies: Re-authenticate → Update cookie file

**Storage State**:
```python
# Save cookies after successful login
await state.context.storage_state(path=state.cookies_file)

# Load cookies on browser creation
context = await browser.new_context(storage_state=state.cookies_file)
```

### Browser Lifecycle

```
┌─────────────────────────────────────────┐
│ 1. Create ClientState with credentials │
└──────────────────┬──────────────────────┘
                   ▼
┌─────────────────────────────────────────┐
│ 2. Launch Playwright + Chromium        │
└──────────────────┬──────────────────────┘
                   ▼
┌─────────────────────────────────────────┐
│ 3. Load cookies from disk (if exists)  │
└──────────────────┬──────────────────────┘
                   ▼
┌─────────────────────────────────────────┐
│ 4. Check if logged in (navigate to @me)│
└──────────────────┬──────────────────────┘
                   ▼
         ┌─────────┴─────────┐
         │                   │
    Not Logged In        Logged In
         │                   │
         ▼                   │
┌──────────────────┐         │
│ 5. Fill login    │         │
│    form          │         │
└────────┬─────────┘         │
         │                   │
         └─────────┬─────────┘
                   ▼
┌─────────────────────────────────────────┐
│ 6. Execute operation (get_guilds, etc) │
└──────────────────┬──────────────────────┘
                   ▼
┌─────────────────────────────────────────┐
│ 7. Close: page → context → browser     │
└──────────────────┬──────────────────────┘
                   ▼
┌─────────────────────────────────────────┐
│ 8. Force garbage collection             │
└─────────────────────────────────────────┘
```

### Headless Mode

**Controlled by**: `DISCORD_HEADLESS` environment variable

**Production**: `DISCORD_HEADLESS=true` (no GUI)
**Development**: `DISCORD_HEADLESS=false` (visible browser for debugging)

---

## Message Handling

### Chronological Ordering

**Rule**: Messages returned **newest-first** (reverse chronological)

```python
# max_messages: 1  → Most recent message
# max_messages: 20 → 20 most recent messages (going back in time)
```

### Extraction Strategy

1. **Navigate to channel**: `https://discord.com/channels/{server_id}/{channel_id}`
2. **Scroll to bottom**: JavaScript scroll to get newest messages
3. **Extract visible messages**: Iterate through DOM elements in reverse
4. **Paginate backward**: Use PageUp key for older messages
5. **Deduplicate**: Track message IDs in set
6. **Filter by time**: Apply `hours_back` cutoff
7. **Sort newest-first**: Return chronologically ordered list

### Message Structure

```python
@dataclass(frozen=True)
class DiscordMessage:
    id: str                    # Unique message ID
    content: str               # Message text content
    author_name: str           # Display name of author
    author_id: str             # Numeric user ID
    channel_id: str            # Channel where message was sent
    timestamp: datetime        # UTC timestamp (ISO8601)
    attachments: list[str]     # List of attachment URLs
```

### Time-Based Filtering

```python
# Calculate cutoff
cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours_back)

# Filter messages
recent = [msg for msg in messages if msg.timestamp > cutoff_time]
```

**Validation**:
- `hours_back`: 1-8760 (1 hour to 1 year)
- `max_messages`: 1-1000

### Message Splitting for Sending

**Discord Limit**: 2000 characters per message

**Algorithm**:
1. **Try newline splitting**: Preserve paragraphs
2. **Try word splitting**: Preserve words
3. **Character truncation**: Last resort

```python
def _split_message(content: str, max_length: int = 2000) -> list[str]:
    """Smart message chunking"""
    if len(content) <= max_length:
        return [content]

    chunks = []
    remaining = content

    while remaining:
        if len(remaining) <= max_length:
            chunks.append(remaining)
            break

        # Find last newline before max_length
        split_pos = remaining.rfind('\n', 0, max_length)
        if split_pos == -1:
            # Find last space before max_length
            split_pos = remaining.rfind(' ', 0, max_length)
        if split_pos == -1:
            # Character truncation
            split_pos = max_length

        chunks.append(remaining[:split_pos])
        remaining = remaining[split_pos:].lstrip()

    return chunks
```

**Rate Limiting**: 0.5 second delay between chunks

---

## MCP Tools

### 1. get_servers

**Description**: List all Discord servers/guilds you have access to

**Parameters**: None

**Returns**:
```json
[
  {"id": "123456789", "name": "My Server"},
  {"id": "987654321", "name": "Another Server"}
]
```

**Implementation**:
- Navigates to Discord home
- Scrolls guild navigation list
- Extracts guild IDs and names via JavaScript
- Returns list of {id, name} dicts

---

### 2. get_channels

**Description**: List all channels in a specific Discord server

**Parameters**:
- `server_id` (required, string): Discord server/guild ID

**Returns**:
```json
[
  {"id": "111", "name": "general", "type": "text"},
  {"id": "222", "name": "announcements", "type": "text"}
]
```

**Implementation**:
- Two-stage discovery process:
  1. Extract visible channels from guild sidebar
  2. Click "Browse Channels" to find hidden channels
- Scrolls to load all channels
- Deduplicates by channel ID
- Returns list of {id, name, type} dicts

---

### 3. read_messages

**Description**: Read recent messages from a specific channel in chronological order (newest first)

**Parameters**:
- `server_id` (required, string): Discord server/guild ID
- `channel_id` (required, string): Channel ID
- `max_messages` (required, integer): Maximum number of messages to return (1-1000)
- `hours_back` (optional, integer): How many hours back to look (default: 24, range: 1-8760)

**Returns**:
```json
[
  {
    "id": "msg123",
    "content": "Hello world",
    "author_name": "John Doe",
    "author_id": "456",
    "channel_id": "789",
    "timestamp": "2025-01-09T10:30:00Z",
    "attachments": ["https://cdn.discord.com/..."]
  }
]
```

**Implementation**:
- Navigates to channel
- Scrolls to bottom for newest messages
- Extracts messages with JavaScript DOM queries
- Filters by timestamp (hours_back)
- Returns up to max_messages, newest first

---

### 4. send_message

**Description**: Send a message to a specific Discord channel (automatically splits long messages)

**Parameters**:
- `server_id` (required, string): Discord server/guild ID
- `channel_id` (required, string): Channel ID
- `content` (required, string): Message content to send

**Returns**:
```json
{
  "message_ids": ["msg1", "msg2"],
  "status": "sent",
  "chunks_sent": 2,
  "total_length": 3500
}
```

**Implementation**:
- Splits content into chunks if >2000 characters
- Navigates to channel
- Finds message input (slate editor)
- Sends each chunk with 0.5s delay
- Returns message IDs and status

---

## Testing Strategy

### Test Configuration (pytest.ini)

```ini
[pytest]
asyncio_mode = auto
asyncio_default_fixture_loop_scope = function
addopts = -v -n 0  # Sequential execution, no parallelism
markers =
    integration: Integration tests
    slow: Slow tests
    browser: Tests requiring browser
```

**Key Setting**: `-n 0` enforces sequential execution to prevent browser conflicts

### Test Fixtures (conftest.py)

```python
@pytest.fixture(scope="session")
def event_loop():
    """Session-scoped event loop"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def real_config():
    """Load Discord credentials from environment"""
    return load_config()

@pytest.fixture
async def discord_client(real_config):
    """Provide fresh Discord client state"""
    state = await create_client(real_config.email, real_config.password)
    yield state
    await close_client(state)

@pytest.fixture(autouse=True, scope="session")
def setup_test_environment():
    """Set headless mode for CI"""
    os.environ.setdefault("DISCORD_HEADLESS", "true")
```

### Integration Tests (test_integration.py)

**4 Tests** covering all MCP tools:

1. **test_mcp_get_servers_tool**
   - Spawns MCP server via stdio
   - Calls get_servers tool
   - Validates response structure
   - Checks for non-empty server list

2. **test_mcp_get_channels_tool**
   - Uses first available server ID
   - Calls get_channels tool
   - Validates channel structure
   - Verifies channel names and IDs

3. **test_mcp_send_message_tool**
   - Sends test message to channel
   - Validates response with message_ids
   - Checks status and chunk count

4. **test_mcp_read_messages_tool**
   - Reads messages from channel
   - Validates message structure
   - Checks timestamp, author, content fields

**Test Execution**:
```bash
uv run pytest -v tests/
```

**Test Reliability**: 100% pass rate across multiple runs due to fresh browser state

---

## Development Workflow

### 1. Setup

```bash
# Clone repository
git clone <repo-url>
cd discord-mcp

# Install dependencies
uv sync

# Install Playwright browsers
uv run playwright install chromium

# Configure environment
cp .env.example .env
# Edit .env with your Discord credentials
```

### 2. Development Cycle

```bash
# Make code changes following functional programming patterns

# Type check
uv run pyright

# Format code
uvx ruff format .

# Lint and fix
uvx ruff check --fix --unsafe-fixes .

# Run tests
uv run pytest -v tests/

# Run specific test
uv run pytest -v tests/test_integration.py::test_mcp_get_servers_tool
```

### 3. Running the Server

```bash
# Development (visible browser)
export DISCORD_HEADLESS=false
uv run python main.py

# Production (headless)
export DISCORD_HEADLESS=true
uv run python main.py
```

### 4. Testing with MCP Inspector

```bash
# Install MCP Inspector
npm install -g @modelcontextprotocol/inspector

# Run inspector
mcp-inspector uv run python main.py
```

---

## Configuration

### Environment Variables

Create `.env` file:

```bash
# Required
DISCORD_EMAIL=your_email@example.com
DISCORD_PASSWORD=your_password_or_app_password

# Optional
DISCORD_HEADLESS=true                          # Run browser in headless mode
DISCORD_GUILD_IDS=123456789,987654321          # Specific guilds to monitor
MAX_MESSAGES_PER_CHANNEL=200                   # Max messages per channel
DEFAULT_HOURS_BACK=24                          # Default time window (hours)
```

### Cookie Storage

**Location**: `~/.discord_mcp_cookies.json`

**Contents**: Browser storage state including:
- Session cookies
- Local storage data
- Authentication tokens

**Security**: File permissions should be `600` (owner read/write only)

---

## Dependencies

### Core Dependencies

```toml
[project.dependencies]
mcp = ">=1.9.3"                    # Official MCP library
playwright = ">=1.52.0"            # Browser automation
python-dotenv = ">=1.1.0"          # Environment variables
typing-extensions = ">=4.14.0"     # Enhanced type hints
```

### Dev Dependencies

```toml
[project.optional-dependencies]
dev = [
    "pytest>=8.4.0",               # Testing framework
    "pytest-asyncio>=1.0.0",       # Async test support
    "pyright>=1.1.401",            # Static type checker
    "ruff>=0.11.13"                # Formatter and linter
]
```

### Package Manager

**UV**: Ultra-fast Python package manager

```bash
# Install dependencies
uv sync

# Add new dependency
uv add <package>

# Run Python
uv run python main.py

# Run pytest
uv run pytest

# Run pyright
uv run pyright
```

---

## Performance Characteristics

### Trade-offs

| Aspect | Choice | Trade-off |
|--------|--------|-----------|
| Browser State | Fresh per call | Speed for reliability (~2-3s overhead) |
| Authentication | Cookie persistence | Faster subsequent calls |
| Message Extraction | JavaScript DOM | Faster than clicking elements |
| Test Execution | Sequential | Slower but 100% reliable |
| Logging | DEBUG level | Verbose but helpful for debugging |

### Timing Breakdown

**First Call** (with login):
- Browser launch: ~1s
- Login flow: ~5s
- Operation: ~2-3s
- Total: ~8-9s

**Subsequent Calls** (cookies valid):
- Browser launch: ~1s
- Cookie load: ~0.5s
- Operation: ~2-3s
- Total: ~3.5-4.5s

### Optimizations

1. **Cookie Persistence**: Eliminates re-login overhead
2. **JavaScript Extraction**: Faster than UI automation
3. **Simplified Message Logic**: Reduced from ~130 to ~54 lines
4. **Async Lock**: Prevents concurrent browser conflicts

---

## Key Design Decisions

### 1. Web Scraping vs Discord API

**Choice**: Playwright web scraping

**Rationale**:
- Discord API requires bot tokens and server permissions
- Web scraping works with any server accessible to user
- No bot creation or OAuth flow needed
- User-level access to all visible content

### 2. Fresh Browser Per Call

**Choice**: Complete browser reset between operations

**Rationale**:
- Prevents memory leaks and browser crashes
- Ensures clean state for each operation
- Eliminates race conditions
- 100% test reliability achieved

**Trade-off**: ~2-3 seconds overhead per call

### 3. Immutable Dataclasses

**Choice**: Frozen dataclasses for all state

**Rationale**:
- Thread-safe by design
- Prevents accidental mutations
- Clear state transitions
- Predictable behavior

### 4. Async Lock Serialization

**Choice**: Single global async lock for client operations

**Rationale**:
- Prevents concurrent browser access
- Avoids resource conflicts
- Simple and effective
- Works well with fresh browser pattern

### 5. Intelligent Message Chunking

**Choice**: Multi-stage chunking algorithm

**Rationale**:
- Preserves readability (newlines → words → characters)
- Respects Discord 2000 character limit
- Automatic with no user intervention
- Rate limiting protection with delays

### 6. Cookie Persistence

**Choice**: Save browser storage state to disk

**Rationale**:
- Reduces login overhead on subsequent calls
- User-friendly (no repeated authentication)
- Standard browser behavior
- Secure local storage

### 7. Verbose Logging

**Choice**: DEBUG level logging throughout

**Rationale**:
- Helps diagnose issues in production
- Tracks browser operations
- Debugging complex web scraping
- Minimal performance impact

### 8. Sequential Testing

**Choice**: `-n 0` in pytest.ini (no parallelism)

**Rationale**:
- Prevents browser resource conflicts
- 100% test pass rate
- Clear test output
- Acceptable speed (~30s for 4 tests)

---

## Security & Compliance

### Authentication Security

**Credentials**:
- Stored in `.env` file (not committed to git)
- Supports app passwords for 2FA accounts
- Cookies stored locally with restricted permissions

**Best Practices**:
```bash
# Set proper permissions on .env
chmod 600 .env

# Set proper permissions on cookie file
chmod 600 ~/.discord_mcp_cookies.json
```

### Rate Limiting

**Built-in Protections**:
- 0.5s delays between message chunks
- Progressive PageUp navigation with timeouts
- Headless browser operation in production
- Respects Discord's client-side limits

### Terms of Service Compliance

**Legitimate Use Cases**:
- Personal content aggregation
- Community monitoring and research
- Trend analysis and insights
- Educational and research purposes

**Restrictions**:
- Only access servers user has normal access to
- No bot behavior or automation at scale
- No spam or abuse
- Respect Discord's rate limits

**Gray Area**: Web scraping Discord is technically against their ToS, but this tool:
- Operates as a normal user (no bot tokens)
- Doesn't abuse rate limits
- Used for personal/research purposes
- Doesn't compromise Discord infrastructure

---

## Future Enhancements

### Potential Improvements

1. **Persistent Browser Instance**
   - Keep browser alive between calls
   - Reduce overhead from ~3s to ~0.5s
   - Requires robust error recovery and leak detection

2. **Parallel Channel Reading**
   - Read from multiple channels concurrently
   - Respect rate limits
   - Aggregate results efficiently

3. **Message Caching**
   - Cache recently read messages
   - Reduce redundant Discord requests
   - Invalidation strategy needed

4. **Reaction Support**
   - Add reactions to messages
   - Read message reactions
   - Track reaction changes

5. **Thread Support**
   - Read thread messages
   - Create and reply to threads
   - Navigate thread hierarchy

6. **Rich Embeds**
   - Parse embed content
   - Extract embed fields
   - Handle embed images/videos

7. **File Attachments**
   - Upload files when sending messages
   - Download attachments from messages
   - Handle large files

8. **Voice Channel Metadata**
   - List voice channels
   - See who's in voice channels
   - Extract voice channel info

---

## Troubleshooting

### Common Issues

**1. Login Failures**

```
Symptom: "Login failed" or stuck on login page
Solution:
- Check credentials in .env
- Use app password for 2FA accounts
- Delete ~/.discord_mcp_cookies.json and retry
- Set DISCORD_HEADLESS=false to see browser
```

**2. Browser Crashes**

```
Symptom: "Browser closed unexpectedly"
Solution:
- Fresh browser per call prevents accumulation
- Check system resources (RAM, CPU)
- Ensure Playwright browsers are installed
```

**3. Message Extraction Fails**

```
Symptom: Empty message list or missing messages
Solution:
- Discord may have updated DOM structure
- Check browser console for errors
- Update CSS selectors in client.py
- Enable DEBUG logging to see extraction attempts
```

**4. Rate Limiting**

```
Symptom: "Rate limited" or slow responses
Solution:
- Reduce message fetch frequency
- Increase delays between chunks
- Avoid rapid successive calls
```

### Debug Mode

```bash
# Run with visible browser
export DISCORD_HEADLESS=false
uv run python main.py

# Check logs
# Logs output to stdout with DEBUG level

# Test specific functionality
uv run pytest -v -s tests/test_integration.py::test_mcp_read_messages_tool
```

---

## Contributing

### Code Style

**Follow existing patterns**:
- Functional programming with immutable state
- Frozen dataclasses for all data models
- Async/await for all I/O operations
- Type hints for all functions

**Before committing**:
```bash
# Type check
uv run pyright

# Format
uvx ruff format .

# Lint
uvx ruff check --fix --unsafe-fixes .

# Test
uv run pytest -v tests/
```

### Adding New Features

1. Update dataclasses in `client.py` if needed
2. Add core functionality to `client.py`
3. Expose as MCP tool in `server.py`
4. Add integration test in `test_integration.py`
5. Update this documentation
6. Update `CLAUDE.md` with concise summary

---

## License

[Specify license here]

---

## Contact

[Specify contact information or links]

---

**Document Version**: 1.0
**Last Updated**: 2025-01-09
**Codebase Version**: Compatible with commit 38be985
