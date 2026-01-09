import asyncio
import os

import pytest
from dotenv import load_dotenv

from src.discord_mcp.config import DiscordConfig

load_dotenv()


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def real_config():
    """Provide real Discord configuration from environment."""
    token = os.getenv("DISCORD_TOKEN")
    email = os.getenv("DISCORD_EMAIL")
    password = os.getenv("DISCORD_PASSWORD")

    if not token and not (email and password):
        pytest.skip(
            "Discord credentials not available. Set DISCORD_TOKEN or both DISCORD_EMAIL and DISCORD_PASSWORD environment variables."
        )

    return DiscordConfig(
        token=token,
        email=email,
        password=password,
        headless=True,  # Use headless for testing in CI environment
        default_guild_ids=["780179350682599445"],
        max_messages_per_channel=50,
        default_hours_back=24,
    )


@pytest.fixture(autouse=True)
def setup_test_environment():
    """Setup test environment before each test."""
    # Ensure we're in headless mode for CI testing
    os.environ["DISCORD_HEADLESS"] = "true"
    yield
