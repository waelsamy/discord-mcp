"""Unit tests with mocked Discord API responses - no credentials required."""

import dataclasses as dc
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from src.discord_mcp.api_client import (
    APIClientState,
    DiscordChannel,
    DiscordDMConversation,
    DiscordGuild,
    DiscordMessage,
    close_api_client,
    create_api_client_state,
    get_channel_messages,
    get_dm_conversations,
    get_guild_channels,
    get_guilds,
    send_message,
)
from src.discord_mcp.messages import read_recent_messages


@pytest.fixture
def mock_state():
    """Create a mock API client state with a fake token."""
    return APIClientState(
        token="fake_token_for_testing",
        email=None,
        password=None,
        headless=True,
        http_client=None,
    )


@pytest.fixture
def mock_http_client():
    """Create a mock HTTP client."""
    return AsyncMock(spec=httpx.AsyncClient)


class TestDataclasses:
    """Test dataclass creation and properties."""

    def test_discord_message_creation(self):
        msg = DiscordMessage(
            id="123",
            content="Hello world",
            author_name="TestUser",
            author_id="456",
            channel_id="789",
            timestamp=datetime.now(timezone.utc),
            attachments=["https://example.com/image.png"],
        )
        assert msg.id == "123"
        assert msg.content == "Hello world"
        assert msg.author_name == "TestUser"
        assert len(msg.attachments) == 1

    def test_discord_channel_creation(self):
        channel = DiscordChannel(
            id="123",
            name="general",
            type=0,
            guild_id="456",
        )
        assert channel.id == "123"
        assert channel.name == "general"
        assert channel.type == 0

    def test_discord_guild_creation(self):
        guild = DiscordGuild(
            id="123",
            name="Test Server",
            icon="abc123",
        )
        assert guild.id == "123"
        assert guild.name == "Test Server"
        assert guild.icon == "abc123"

    def test_discord_dm_conversation_creation(self):
        conv = DiscordDMConversation(
            id="123",
            name="Test User",
            username="testuser",
            type="dm",
            recipient_count=1,
            last_message_timestamp=datetime.now(timezone.utc),
            avatar_url=None,
        )
        assert conv.id == "123"
        assert conv.name == "Test User"
        assert conv.username == "testuser"
        assert conv.type == "dm"


class TestCreateApiClientState:
    """Test API client state creation."""

    def test_create_with_token(self):
        state = create_api_client_state(token="test_token")
        assert state.token == "test_token"
        assert state.email is None
        assert state.password is None
        assert state.headless is True

    def test_create_with_email_password(self):
        state = create_api_client_state(
            email="test@example.com",
            password="password123",
        )
        assert state.token is None
        assert state.email == "test@example.com"
        assert state.password == "password123"

    def test_create_with_headless_false(self):
        state = create_api_client_state(headless=False)
        assert state.headless is False


class TestGetGuilds:
    """Test get_guilds function with mocked responses."""

    @pytest.mark.asyncio
    async def test_get_guilds_success(self, mock_state):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"id": "123", "name": "Server 1", "icon": "abc"},
            {"id": "456", "name": "Server 2", "icon": None},
        ]

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.request = AsyncMock(return_value=mock_response)

        state_with_client = dc.replace(mock_state, http_client=mock_client)

        state, guilds = await get_guilds(state_with_client)

        assert len(guilds) == 2
        assert guilds[0].id == "123"
        assert guilds[0].name == "Server 1"
        assert guilds[1].id == "456"
        assert guilds[1].name == "Server 2"

    @pytest.mark.asyncio
    async def test_get_guilds_empty(self, mock_state):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = []

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.request = AsyncMock(return_value=mock_response)

        state_with_client = dc.replace(mock_state, http_client=mock_client)

        state, guilds = await get_guilds(state_with_client)

        assert len(guilds) == 0


class TestGetGuildChannels:
    """Test get_guild_channels function with mocked responses."""

    @pytest.mark.asyncio
    async def test_get_channels_success(self, mock_state):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"id": "111", "name": "general", "type": 0},
            {"id": "222", "name": "voice-chat", "type": 2},
            {"id": "333", "name": "category", "type": 4},  # Should be filtered out
        ]

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.request = AsyncMock(return_value=mock_response)

        state_with_client = dc.replace(mock_state, http_client=mock_client)

        state, channels = await get_guild_channels(state_with_client, "123")

        # Type 4 (category) should be filtered out
        assert len(channels) == 2
        assert channels[0].name == "general"
        assert channels[1].name == "voice-chat"


class TestGetChannelMessages:
    """Test get_channel_messages function with mocked responses."""

    @pytest.mark.asyncio
    async def test_get_messages_success(self, mock_state):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "id": "msg1",
                "content": "Hello",
                "author": {"id": "user1", "username": "Alice"},
                "timestamp": "2024-01-01T12:00:00+00:00",
                "attachments": [],
            },
            {
                "id": "msg2",
                "content": "World",
                "author": {"id": "user2", "username": "Bob"},
                "timestamp": "2024-01-01T12:01:00+00:00",
                "attachments": [{"url": "https://example.com/file.png"}],
            },
        ]

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.request = AsyncMock(return_value=mock_response)

        state_with_client = dc.replace(mock_state, http_client=mock_client)

        state, messages = await get_channel_messages(state_with_client, "channel123")

        assert len(messages) == 2
        assert messages[0].id == "msg1"
        assert messages[0].content == "Hello"
        assert messages[0].author_name == "Alice"
        assert messages[1].id == "msg2"
        assert len(messages[1].attachments) == 1


class TestGetDMConversations:
    """Test get_dm_conversations function with mocked responses."""

    @pytest.mark.asyncio
    async def test_get_dm_conversations_success(self, mock_state):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "id": "dm1",
                "type": 1,  # DM
                "recipients": [
                    {"id": "user1", "username": "alice", "global_name": "Alice Smith"}
                ],
                "last_message_id": "1234567890123456789",
            },
            {
                "id": "dm2",
                "type": 3,  # Group DM
                "name": "Project Team",
                "recipients": [
                    {"id": "user2", "username": "bob", "global_name": "Bob"},
                    {"id": "user3", "username": "charlie", "global_name": "Charlie"},
                ],
                "last_message_id": None,
            },
        ]

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.request = AsyncMock(return_value=mock_response)

        state_with_client = dc.replace(mock_state, http_client=mock_client)

        state, conversations = await get_dm_conversations(state_with_client)

        assert len(conversations) == 2
        assert conversations[0].type == "dm"
        assert conversations[0].name == "Alice Smith"
        assert conversations[0].username == "alice"
        assert conversations[1].type == "group_dm"
        assert conversations[1].name == "Project Team"
        assert conversations[1].username is None


class TestSendMessage:
    """Test send_message function with mocked responses."""

    @pytest.mark.asyncio
    async def test_send_message_success(self, mock_state):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "new_msg_123"}

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.request = AsyncMock(return_value=mock_response)

        state_with_client = dc.replace(mock_state, http_client=mock_client)

        state, message_id = await send_message(
            state_with_client, "channel123", "Test message"
        )

        assert message_id == "new_msg_123"
        mock_client.request.assert_called_once()


class TestReadRecentMessages:
    """Test read_recent_messages with time filtering."""

    @pytest.mark.asyncio
    async def test_filters_old_messages(self, mock_state):
        now = datetime.now(timezone.utc)
        old_time = datetime(2020, 1, 1, tzinfo=timezone.utc)
        recent_time = now

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "id": "old_msg",
                "content": "Old message",
                "author": {"id": "user1", "username": "Alice"},
                "timestamp": old_time.isoformat(),
                "attachments": [],
            },
            {
                "id": "new_msg",
                "content": "New message",
                "author": {"id": "user2", "username": "Bob"},
                "timestamp": recent_time.isoformat(),
                "attachments": [],
            },
        ]

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.request = AsyncMock(return_value=mock_response)

        state_with_client = dc.replace(mock_state, http_client=mock_client)

        state, messages = await read_recent_messages(
            state_with_client,
            server_id="server123",
            channel_id="channel123",
            hours_back=24,
            max_messages=100,
        )

        # Only the recent message should be returned
        assert len(messages) == 1
        assert messages[0].id == "new_msg"


class TestCloseApiClient:
    """Test closing the API client."""

    @pytest.mark.asyncio
    async def test_close_client_with_http_client(self, mock_state):
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        state_with_client = dc.replace(mock_state, http_client=mock_client)

        await close_api_client(state_with_client)

        mock_client.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_client_without_http_client(self, mock_state):
        # Should not raise
        await close_api_client(mock_state)
