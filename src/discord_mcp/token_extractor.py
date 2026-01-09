"""Discord token extraction via Playwright browser automation."""

import asyncio
from playwright.async_api import async_playwright, Page
from .logger import logger


async def extract_token_headless(
    email: str,
    password: str,
    headless: bool = True,
    timeout: int = 120000,
) -> str:
    """Extract Discord token using browser automation.

    Args:
        email: Discord email address
        password: Discord password
        headless: Run browser in headless mode (default: True)
        timeout: Maximum time to wait for login (default: 120000ms / 2 minutes)

    Returns:
        Discord authentication token

    Raises:
        RuntimeError: If MFA/2FA is required in headless mode or login fails
    """
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=headless)
    captured_token = None

    try:
        context = await browser.new_context()
        page = await context.new_page()

        # Network interception to capture authorization header
        async def capture_auth(route, request):
            nonlocal captured_token
            if auth := request.headers.get("authorization"):
                if not captured_token:
                    captured_token = auth
                    logger.debug("Captured token from network request")
            await route.continue_()

        await page.route("**/*", capture_auth)

        # Navigate to Discord login
        logger.debug("Navigating to Discord login page")
        await page.goto("https://discord.com/login")
        await asyncio.sleep(2)

        # Auto-fill credentials if provided
        if email and password:
            logger.debug(f"Auto-filling credentials for {email}")
            await page.fill('input[name="email"]', email)
            await page.fill('input[name="password"]', password)
            await asyncio.sleep(1)
            await page.click('button[type="submit"]')
            logger.debug("Login form submitted")

        # Wait for login to complete or MFA to be required
        try:
            await asyncio.sleep(3)

            # Detect MFA/2FA requirement
            if await _check_mfa_required(page):
                if headless:
                    raise RuntimeError(
                        "MFA/2FA is required but cannot be completed in headless mode. "
                        "Please run 'uv run python get_token.py' interactively to get your token, "
                        "then add it to .env as DISCORD_TOKEN=your_token"
                    )
                else:
                    logger.info("MFA/2FA detected - waiting for user input...")

            # Wait for successful login
            logger.debug("Waiting for login to complete...")
            await page.wait_for_function(
                "() => window.location.href.includes('/channels') || window.location.href.includes('/app')",
                timeout=timeout,
            )
            await asyncio.sleep(3)
            logger.debug("Login successful")

        except Exception as e:
            raise RuntimeError(f"Login failed: {e}")

        # Navigate to channels to trigger more API requests
        if "/channels/" not in page.url:
            logger.debug("Navigating to channels to capture token")
            await page.goto("https://discord.com/channels/@me")
            await asyncio.sleep(3)

        # Extract token using multiple methods (in priority order)
        token = captured_token  # Method 1: Network capture (most reliable)

        if not token:
            logger.debug("Network capture failed, trying localStorage")
            token = await _extract_from_localstorage(page)  # Method 2

        if not token:
            logger.debug("localStorage failed, trying webpack modules")
            token = await _extract_from_webpack(page)  # Method 3

        if not token:
            raise RuntimeError(
                "Failed to extract token from browser using all methods. "
                "This may be due to browser security restrictions."
            )

        logger.info("Successfully extracted Discord token")
        return token

    finally:
        await browser.close()
        await playwright.stop()


async def _check_mfa_required(page: Page) -> bool:
    """Check if MFA/2FA is required.

    Args:
        page: Playwright page object

    Returns:
        True if MFA/2FA is required, False otherwise
    """
    return (
        "/verify" in page.url
        or await page.locator('text="Check your email"').count() > 0
        or await page.locator('text="Two-Factor"').count() > 0
        or await page.locator('text="Enter Code"').count() > 0
    )


async def _extract_from_localstorage(page: Page) -> str | None:
    """Extract token from localStorage.

    Args:
        page: Playwright page object

    Returns:
        Token string if found, None otherwise
    """
    return await page.evaluate("""
        () => {
            try {
                // Try direct localStorage access
                let token = localStorage.getItem('token');
                if (token) return token.replace(/^"(.*)"$/, '$1');

                // Search all localStorage keys for token-like values
                for (let i = 0; i < localStorage.length; i++) {
                    const key = localStorage.key(i);
                    if (key?.includes('token')) {
                        const val = localStorage.getItem(key);
                        if (val && val.length > 50) {
                            return val.replace(/^"(.*)"$/, '$1');
                        }
                    }
                }
            } catch {}
            return null;
        }
    """)


async def _extract_from_webpack(page: Page) -> str | None:
    """Extract token from webpack modules.

    Args:
        page: Playwright page object

    Returns:
        Token string if found, None otherwise
    """
    return await page.evaluate("""
        () => {
            try {
                if (window.webpackChunkdiscord_app) {
                    const modules = window.webpackChunkdiscord_app.push(
                        [[Symbol()], {}, e => e.c]
                    );
                    for (const m in modules) {
                        try {
                            const mod = modules[m].exports;
                            if (mod?.default?.getToken) {
                                return mod.default.getToken();
                            }
                        } catch {}
                    }
                }
            } catch {}
            return null;
        }
    """)
