#!/usr/bin/env python3
"""Debug script to check MCP tool JSON output for potential issues."""

import asyncio
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import os


async def test_tool_output(tool_name: str, args: dict):
    """Test a specific MCP tool and inspect its raw output."""
    server_params = StdioServerParameters(
        command="uv",
        args=["run", "python", "main.py"],
        env={
            "DISCORD_EMAIL": os.getenv("DISCORD_EMAIL", ""),
            "DISCORD_PASSWORD": os.getenv("DISCORD_PASSWORD", ""),
            "DISCORD_HEADLESS": "true",
        },
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            print(f"\n{'=' * 60}")
            print(f"Testing tool: {tool_name}")
            print(f"Arguments: {args}")
            print(f"{'=' * 60}\n")

            result = await session.call_tool(tool_name, args)

            print(f"Has error: {result.isError}")
            print(f"Content items: {len(result.content) if result.content else 0}\n")

            if result.content:
                for i, content in enumerate(result.content):
                    print(f"\n--- Content Item {i + 1} ---")
                    print(f"Type: {content.type}")
                    print(f"Text length: {len(content.text)}")
                    print(f"First 200 chars: {content.text[:200]}")
                    print(f"Last 50 chars: {content.text[-50:]}")

                    # Check for JSON validity
                    try:
                        parsed = json.loads(content.text)
                        print("✓ Valid JSON")
                        print(f"  Parsed type: {type(parsed).__name__}")
                        if isinstance(parsed, dict):
                            print(f"  Keys: {list(parsed.keys())}")
                            # Check for problematic characters in values
                            for key, value in parsed.items():
                                if isinstance(value, str):
                                    # Check for control characters
                                    control_chars = [
                                        c
                                        for c in value
                                        if ord(c) < 32 and c not in "\n\r\t"
                                    ]
                                    if control_chars:
                                        print(
                                            f"  ⚠ Control characters in '{key}': {[hex(ord(c)) for c in control_chars]}"
                                        )
                                    # Check for problematic Unicode
                                    if any(ord(c) > 0xFFFF for c in value):
                                        print(f"  ⚠ High Unicode characters in '{key}'")
                    except json.JSONDecodeError as e:
                        print(f"✗ Invalid JSON: {e}")
                        print(f"  Error at position: {e.pos}")
                        if e.pos < len(content.text):
                            start = max(0, e.pos - 20)
                            end = min(len(content.text), e.pos + 20)
                            print(f"  Context: ...{content.text[start:end]}...")
                            print(f"  Problem char: {repr(content.text[e.pos])}")
                    except Exception as e:
                        print(f"✗ Unexpected error: {e}")


async def main():
    """Run diagnostics on various MCP tools."""

    # Test get_servers (most common tool)
    await test_tool_output("get_servers", {})

    # Test get_channels if we have a server ID
    # Uncomment and add your server ID to test:
    # await test_tool_output("get_channels", {"server_id": "YOUR_SERVER_ID"})

    # Test get_dm_conversations
    # await test_tool_output("get_dm_conversations", {})


if __name__ == "__main__":
    asyncio.run(main())
