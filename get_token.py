"""Helper script to extract Discord token from browser.

This script opens a browser, automatically logs in using credentials from .env,
then extracts and displays your authentication token.

Usage:
    uv run python get_token.py

The token will be displayed and automatically copied to your clipboard (if available).
Add it to your .env file as: DISCORD_TOKEN=your_token_here
"""

import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Import the shared token extraction module
from src.discord_mcp.token_extractor import extract_token_headless


async def get_discord_token():
    print("=" * 70)
    print("Discord Token Extractor")
    print("=" * 70)
    print()

    # Load credentials from .env
    env_file = Path(".env")
    if env_file.exists():
        load_dotenv(env_file)
        print("✅ Loaded credentials from .env file")
    else:
        print("⚠️  No .env file found - you'll need to log in manually")

    email = os.getenv("DISCORD_EMAIL", "")
    password = os.getenv("DISCORD_PASSWORD", "")

    print()
    print("This script will:")
    print("1. Open a browser window")
    print("2. Navigate to Discord login page")
    if email and password:
        print("3. Automatically fill in your credentials from .env")
        print("4. Submit the login form")
        print("5. Handle MFA/2FA if required (you'll complete it in the browser)")
        print("6. Extract your authentication token")
    else:
        print("3. Wait for you to log in manually")
        print("4. Extract your authentication token")
    print()

    try:
        # Use shared extractor with headless=False for interactive mode
        print("Opening browser...")
        token = await extract_token_headless(
            email=email,
            password=password,
            headless=False,  # Allow MFA/2FA interaction
        )

        print()
        print("✅ Successfully extracted Discord token!")
        print()
        print("=" * 70)
        print("Your Discord Token:")
        print("=" * 70)
        print(token)
        print("=" * 70)
        print()
        print("Add this to your .env file:")
        print(f"DISCORD_TOKEN={token}")
        print()

        # Try to copy to clipboard
        try:
            import pyperclip

            pyperclip.copy(token)
            print("✅ Token copied to clipboard!")
        except ImportError:
            print("💡 Tip: Install pyperclip to auto-copy token: uv add pyperclip")
        except Exception as e:
            print(f"⚠️  Could not copy to clipboard: {e}")

    except Exception as e:
        print()
        print(f"❌ Failed to extract token: {e}")
        print()
        print("Alternative method:")
        print("1. Press F12 to open Developer Tools")
        print("2. Go to 'Application' tab")
        print("3. Click 'Local Storage' > 'https://discord.com'")
        print("4. Find the 'token' key and copy its value")

    print()
    input("Press Enter to exit...")


if __name__ == "__main__":
    try:
        asyncio.run(get_discord_token())
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
        sys.exit(0)
