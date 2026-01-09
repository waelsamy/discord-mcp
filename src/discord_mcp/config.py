import os
import typing as tp
from pathlib import Path
from dotenv import load_dotenv


class DiscordConfig(tp.NamedTuple):
    token: str | None
    email: str | None
    password: str | None
    headless: bool
    default_guild_ids: list[str]
    max_messages_per_channel: int
    default_hours_back: int


def load_config() -> DiscordConfig:
    env_file = Path(".env")
    if env_file.exists():
        load_dotenv(env_file)

    # Token takes priority - if provided, email/password are optional
    token = os.getenv("DISCORD_TOKEN")

    # Email and password are only required if token is not provided
    email = os.getenv("DISCORD_EMAIL")
    password = os.getenv("DISCORD_PASSWORD")

    if not token and not (email and password):
        raise ValueError(
            "Either DISCORD_TOKEN or both DISCORD_EMAIL and DISCORD_PASSWORD "
            "environment variables are required"
        )

    headless = os.getenv("DISCORD_HEADLESS", "true").lower() == "true"

    guild_ids_str = os.getenv("DISCORD_GUILD_IDS", "")
    guild_ids = [gid.strip() for gid in guild_ids_str.split(",") if gid.strip()]

    max_messages = int(os.getenv("MAX_MESSAGES_PER_CHANNEL", "200"))
    hours_back = int(os.getenv("DEFAULT_HOURS_BACK", "24"))

    return DiscordConfig(
        token=token,
        email=email,
        password=password,
        headless=headless,
        default_guild_ids=guild_ids,
        max_messages_per_channel=max_messages,
        default_hours_back=hours_back,
    )
