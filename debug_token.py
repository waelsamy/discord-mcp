"""Debug script to check how Discord stores the token."""

import asyncio
import os
from dotenv import load_dotenv
from playwright.async_api import async_playwright

load_dotenv()


async def debug_token():
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(
        headless=False
    )  # Non-headless to see what's happening
    context = await browser.new_context()
    page = await context.new_page()

    # Login
    await page.goto("https://discord.com/login")
    await asyncio.sleep(2)

    email = os.getenv("DISCORD_EMAIL")
    password = os.getenv("DISCORD_PASSWORD")

    await page.fill('input[name="email"]', email)
    await page.fill('input[name="password"]', password)
    await page.click('button[type="submit"]')

    # Wait for login
    await page.wait_for_function(
        "() => !window.location.href.includes('/login')", timeout=60000
    )
    await asyncio.sleep(5)

    # Navigate to channels
    await page.goto("https://discord.com/channels/@me")
    await asyncio.sleep(3)

    # Try to extract token in various ways
    result = await page.evaluate("""
        () => {
            const results = {};

            // Check localStorage
            try {
                results.localStorageKeys = Object.keys(localStorage);
                results.token = localStorage.getItem('token');
            } catch (e) {
                results.localStorageError = e.toString();
            }

            // Check sessionStorage
            try {
                results.sessionStorageKeys = Object.keys(sessionStorage);
            } catch (e) {
                results.sessionStorageError = e.toString();
            }

            // Check cookies via document.cookie
            results.cookies = document.cookie;

            return results;
        }
    """)

    print("Debug results:")
    print(f"localStorage keys: {result.get('localStorageKeys')}")
    print(f"token value: {result.get('token')}")
    print(f"localStorage error: {result.get('localStorageError')}")
    print(f"sessionStorage keys: {result.get('sessionStorageKeys')}")
    print(
        f"cookies: {result.get('cookies')[:100] if result.get('cookies') else 'None'}..."
    )

    input("Press Enter to close browser...")

    await browser.close()
    await playwright.stop()


if __name__ == "__main__":
    asyncio.run(debug_token())
