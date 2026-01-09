import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def _build_server_env(config):
    """Build environment dict for MCP server, only including non-None values."""
    env = {"DISCORD_HEADLESS": "true"}
    if config.token:
        env["DISCORD_TOKEN"] = config.token
    if config.email:
        env["DISCORD_EMAIL"] = config.email
    if config.password:
        env["DISCORD_PASSWORD"] = config.password
    return env


@pytest.mark.integration
@pytest.mark.browser
@pytest.mark.slow
@pytest.mark.asyncio
async def test_mcp_get_servers_tool(real_config):
    """Test the get_servers MCP tool via proper MCP client."""
    # Create server parameters for stdio connection
    server_params = StdioServerParameters(
        command="uv",
        args=["run", "python", "main.py"],
        env=_build_server_env(real_config),
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize the connection
            await session.initialize()

            # Call get_servers tool
            result = await session.call_tool("get_servers", {})
            print(f"Servers response: {result}")

            assert hasattr(result, "content")
            assert result.content, "No content in result"

            # Check if this is an error response
            if result.isError:
                text_content = result.content[0] if result.content else None
                error_text = text_content.text if text_content else "Unknown error"
                print(f"Error in tool response: {error_text}")
                raise Exception(f"Tool failed: {error_text[:200]}...")

            # Parse the JSON from each text content object
            import json

            servers_data = []
            for text_content in result.content:
                server_data = json.loads(text_content.text)
                servers_data.append(server_data)

            assert isinstance(servers_data, list)
            assert len(servers_data) > 0
            print(f"MCP server found {len(servers_data)} guilds")

            # Print all servers found
            for i, server in enumerate(servers_data):
                print(f"Server {i + 1}: {server['name']} (ID: {server['id']})")

            # Should find some Discord server
            assert servers_data[0]["id"] is not None
            assert servers_data[0]["name"] is not None


@pytest.mark.integration
@pytest.mark.browser
@pytest.mark.slow
@pytest.mark.asyncio
async def test_mcp_get_channels_tool(real_config):
    """Test the get_channels MCP tool via proper MCP client."""
    # Create server parameters for stdio connection
    server_params = StdioServerParameters(
        command="uv",
        args=["run", "python", "main.py"],
        env=_build_server_env(real_config),
    )

    audiogen_server_id = "1353689257796960296"

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize the connection
            await session.initialize()

            # Test get_channels tool
            result = await session.call_tool(
                "get_channels", {"server_id": audiogen_server_id}
            )
            assert hasattr(result, "content")
            assert result.content, "No content in result"

            if result.isError:
                text_content = result.content[0] if result.content else None
                error_text = text_content.text if text_content else "Unknown error"
                print(f"Error in tool response: {error_text}")
                raise Exception(f"Tool failed: {error_text[:200]}...")

            import json

            channels_data = []
            for text_content in result.content:
                channel_data = json.loads(text_content.text)
                channels_data.append(channel_data)
            assert isinstance(channels_data, list)
            assert len(channels_data) > 0, (
                f"Expected to find channels in server {audiogen_server_id} via MCP, but found 0"
            )
            print(
                f"MCP found {len(channels_data)} channels in server {audiogen_server_id}"
            )

            for channel_info in channels_data:
                assert "id" in channel_info
                assert "name" in channel_info
                assert "type" in channel_info
                print(f"  {channel_info['name']} (ID: {channel_info['id']})")


@pytest.mark.integration
@pytest.mark.browser
@pytest.mark.slow
@pytest.mark.asyncio
async def test_mcp_send_message_tool(real_config):
    """Test the send_message MCP tool via proper MCP client."""
    # Create server parameters for stdio connection
    server_params = StdioServerParameters(
        command="uv",
        args=["run", "python", "main.py"],
        env=_build_server_env(real_config),
    )

    audiogen_server_id = "1353689257796960296"
    audiogen_channel_id = "1353694097696755766"
    test_message = "hi from discord mcp fastmcp test"

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize the connection
            await session.initialize()

            # Test send_message tool
            print(
                f"Testing MCP message sending to server {audiogen_server_id}, channel {audiogen_channel_id}"
            )
            result = await session.call_tool(
                "send_message",
                {
                    "server_id": audiogen_server_id,
                    "channel_id": audiogen_channel_id,
                    "content": test_message,
                },
            )
            assert hasattr(result, "content")
            assert result.content, "No content in result"

            if result.isError:
                text_content = result.content[0] if result.content else None
                error_text = text_content.text if text_content else "Unknown error"
                print(f"Error in tool response: {error_text}")
                raise Exception(f"Tool failed: {error_text[:200]}...")

            import json

            # send_message returns a single object, not a list
            text_content = result.content[0]
            response_data = json.loads(text_content.text)

            assert isinstance(response_data, dict)
            assert "message_ids" in response_data
            assert "status" in response_data
            assert "chunks" in response_data
            assert response_data["status"] == "sent"
            assert len(response_data["message_ids"]) >= 1
            print(
                f"MCP successfully sent {response_data['chunks']} message(s) with IDs: {response_data['message_ids']}"
            )


@pytest.mark.integration
@pytest.mark.browser
@pytest.mark.slow
@pytest.mark.asyncio
async def test_mcp_read_messages_tool(real_config):
    """Test the read_messages MCP tool via proper MCP client."""
    # Create server parameters for stdio connection
    server_params = StdioServerParameters(
        command="uv",
        args=["run", "python", "main.py"],
        env=_build_server_env(real_config),
    )

    audiogen_server_id = "1353689257796960296"
    test_channel_id = "1353694097696755766"

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize the connection
            await session.initialize()

            # Test read_messages tool
            print(
                f"Testing MCP message reading from server {audiogen_server_id}, channel {test_channel_id}"
            )
            result = await session.call_tool(
                "read_messages",
                {
                    "server_id": audiogen_server_id,
                    "channel_id": test_channel_id,
                    "hours_back": 8760,  # 1 year to handle Discord timestamp quirks
                    "max_messages": 20,  # Test with 20 messages to show chronological order
                },
            )
            assert hasattr(result, "content")

            if result.isError:
                text_content = result.content[0] if result.content else None
                error_text = text_content.text if text_content else "Unknown error"
                print(f"Error in tool response: {error_text}")
                raise Exception(f"Tool failed: {error_text[:200]}...")

            import json

            messages_data = []

            assert result.content, "No content in result - expected to find messages"

            for text_content in result.content:
                message_data = json.loads(text_content.text)
                messages_data.append(message_data)
            assert isinstance(messages_data, list)

            print(
                f"\n=== MCP read {len(messages_data)} messages from channel {test_channel_id} ==="
            )
            for i, msg in enumerate(messages_data, 1):
                print(f"\nMessage {i}:")
                print(f"  ID: {msg.get('id', 'Unknown')}")
                print(f"  Author: {msg.get('author_name', 'Unknown')}")
                print(f"  Timestamp: {msg.get('timestamp', 'Unknown')}")
                print(
                    f"  Content: {msg.get('content', '')[:100]}{'...' if len(msg.get('content', '')) > 100 else ''}"
                )
                print(f"  Attachments: {len(msg.get('attachments', []))} files")
            print("=" * 50)

            for message_info in messages_data:
                assert "id" in message_info
                assert "content" in message_info
                assert "author_name" in message_info
                assert "timestamp" in message_info
                assert "attachments" in message_info


@pytest.mark.integration
@pytest.mark.browser
@pytest.mark.slow
@pytest.mark.asyncio
async def test_mcp_get_dm_conversations_tool(real_config):
    """Test the get_dm_conversations MCP tool via proper MCP client."""
    server_params = StdioServerParameters(
        command="uv",
        args=["run", "python", "main.py"],
        env=_build_server_env(real_config),
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            result = await session.call_tool("get_dm_conversations", {})

            assert hasattr(result, "content")
            assert result.content, "No content in result"

            if result.isError:
                text_content = result.content[0] if result.content else None
                error_text = text_content.text if text_content else "Unknown error"
                raise Exception(f"Tool failed: {error_text[:200]}")

            import json

            conversations_data = []
            for text_content in result.content:
                conv_data = json.loads(text_content.text)
                conversations_data.append(conv_data)

            print(f"\nMCP found {len(conversations_data)} DM conversations")

            for conv in conversations_data:
                assert "id" in conv
                assert "name" in conv
                assert "type" in conv
                assert conv["type"] in ["dm", "group_dm"]
                assert "recipient_count" in conv
                print(f"  {conv['name']} (ID: {conv['id']}, type: {conv['type']})")


@pytest.mark.integration
@pytest.mark.browser
@pytest.mark.slow
@pytest.mark.asyncio
async def test_mcp_read_dm_messages_by_name_tool(real_config):
    """Test the read_dm_messages MCP tool with name-based lookup."""
    server_params = StdioServerParameters(
        command="uv",
        args=["run", "python", "main.py"],
        env=_build_server_env(real_config),
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # First, get available conversations
            convs_result = await session.call_tool("get_dm_conversations", {})
            if convs_result.isError or not convs_result.content:
                pytest.skip("No DM conversations available for testing")

            import json

            conversations_data = []
            for text_content in convs_result.content:
                conv_data = json.loads(text_content.text)
                conversations_data.append(conv_data)

            if len(conversations_data) == 0:
                pytest.skip("No DM conversations available for testing")

            # Use first available conversation
            test_dm_name = conversations_data[0]["name"]
            print(f"\nTesting with DM conversation: {test_dm_name}")

            # Test reading messages by name
            result = await session.call_tool(
                "read_dm_messages",
                {
                    "name": test_dm_name,
                    "max_messages": 10,
                    "hours_back": 8760,  # 1 year to maximize chance of messages
                },
            )

            assert hasattr(result, "content")

            if result.isError:
                text_content = result.content[0] if result.content else None
                error_text = text_content.text if text_content else "Unknown error"
                # May have no messages, which is acceptable
                if "No messages found" not in error_text:
                    print(f"Error: {error_text}")
                    raise Exception(f"Tool failed: {error_text[:200]}")
                return

            messages_data = []
            for text_content in result.content:
                message_data = json.loads(text_content.text)
                messages_data.append(message_data)

            print(f"\nRead {len(messages_data)} messages from DM '{test_dm_name}'")

            for message_info in messages_data[:3]:  # Show first 3
                assert "id" in message_info
                assert "content" in message_info
                assert "author_name" in message_info
                assert "timestamp" in message_info
                assert "conversation_name" in message_info
                print(
                    f"  {message_info['author_name']}: {message_info['content'][:50]}"
                )


@pytest.mark.integration
@pytest.mark.browser
@pytest.mark.slow
@pytest.mark.asyncio
async def test_dm_name_not_found_error(real_config):
    """Test that read_dm_messages returns helpful error for non-existent name."""
    server_params = StdioServerParameters(
        command="uv",
        args=["run", "python", "main.py"],
        env=_build_server_env(real_config),
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Try to read from non-existent conversation
            result = await session.call_tool(
                "read_dm_messages",
                {
                    "name": "ThisUserDefinitelyDoesNotExist123456",
                    "max_messages": 10,
                },
            )

            assert result.isError, "Expected error for non-existent DM name"
            text_content = result.content[0] if result.content else None
            error_text = text_content.text if text_content else ""
            assert "No DM conversation found" in error_text
            assert "get_dm_conversations" in error_text  # Should suggest tool
            print(f"\nCorrectly returned error: {error_text}")


@pytest.mark.integration
@pytest.mark.browser
@pytest.mark.slow
@pytest.mark.asyncio
async def test_mcp_send_message_with_attachment_tool(real_config):
    """Test the send_message_with_attachment MCP tool via proper MCP client."""
    import json
    import tempfile
    from pathlib import Path

    # Create server parameters for stdio connection
    server_params = StdioServerParameters(
        command="uv",
        args=["run", "python", "main.py"],
        env=_build_server_env(real_config),
    )

    audiogen_server_id = "1353689257796960296"
    audiogen_channel_id = "1353694097696755766"
    test_message = "Test message with attachment from discord-mcp integration test"

    # Create a temporary test file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("This is a test attachment file.\n")
        f.write("Testing Discord MCP attachment feature.\n")
        f.write("Timestamp: 2026-01-09\n")
        temp_file_path = f.name

    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                # Initialize the connection
                await session.initialize()

                # Test send_message_with_attachment tool
                print(
                    f"Testing MCP message with attachment to server {audiogen_server_id}, channel {audiogen_channel_id}"
                )
                print(f"Attaching file: {temp_file_path}")

                result = await session.call_tool(
                    "send_message_with_attachment",
                    {
                        "server_id": audiogen_server_id,
                        "channel_id": audiogen_channel_id,
                        "content": test_message,
                        "file_path": temp_file_path,
                    },
                )
                assert hasattr(result, "content")
                assert result.content, "No content in result"

                if result.isError:
                    text_content = result.content[0] if result.content else None
                    error_text = text_content.text if text_content else "Unknown error"
                    print(f"Error in tool response: {error_text}")
                    raise Exception(f"Tool failed: {error_text[:200]}...")

                # Parse response
                text_content = result.content[0]
                response_data = json.loads(text_content.text)

                assert isinstance(response_data, dict)
                assert "message_id" in response_data
                assert "status" in response_data
                assert "file_size" in response_data
                assert "filename" in response_data
                assert response_data["status"] == "sent"
                assert response_data["file_size"] > 0

                print(
                    f"MCP successfully sent message with attachment. Message ID: {response_data['message_id']}"
                )
                print(
                    f"File: {response_data['filename']} ({response_data['file_size']} bytes)"
                )

    finally:
        # Clean up temporary file
        Path(temp_file_path).unlink(missing_ok=True)


@pytest.mark.integration
@pytest.mark.browser
@pytest.mark.slow
@pytest.mark.asyncio
async def test_mcp_send_message_with_attachment_file_not_found(real_config):
    """Test that send_message_with_attachment returns error for non-existent file."""

    server_params = StdioServerParameters(
        command="uv",
        args=["run", "python", "main.py"],
        env=_build_server_env(real_config),
    )

    audiogen_server_id = "1353689257796960296"
    audiogen_channel_id = "1353694097696755766"

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Try to send with non-existent file
            result = await session.call_tool(
                "send_message_with_attachment",
                {
                    "server_id": audiogen_server_id,
                    "channel_id": audiogen_channel_id,
                    "content": "This should fail",
                    "file_path": "/tmp/this_file_does_not_exist_12345.txt",
                },
            )

            assert result.isError, "Expected error for non-existent file"
            text_content = result.content[0] if result.content else None
            error_text = text_content.text if text_content else ""
            assert (
                "FileNotFoundError" in error_text or "not found" in error_text.lower()
            )
            print(f"\nCorrectly returned error: {error_text[:200]}...")
