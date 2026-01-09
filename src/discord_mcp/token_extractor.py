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
    logger.info(f"Starting token extraction (headless={headless}, email={email})")

    playwright = await async_playwright().start()
    logger.debug("Playwright started")

    browser = await playwright.chromium.launch(headless=headless)
    logger.debug(f"Browser launched (headless={headless})")

    captured_token = None

    try:
        context = await browser.new_context()
        page = await context.new_page()
        logger.debug("Browser context and page created")

        # Network interception to capture authorization header
        async def capture_auth(route, request):
            nonlocal captured_token
            if auth := request.headers.get("authorization"):
                if not captured_token:
                    captured_token = auth
                    logger.info("Captured token from network request!")
            await route.continue_()

        await page.route("**/*", capture_auth)
        logger.debug("Network interception set up")

        # Navigate to Discord login
        logger.info("Navigating to Discord login page...")
        await page.goto("https://discord.com/login")
        logger.debug("Login page loaded")
        await asyncio.sleep(2)

        # Auto-fill credentials if provided
        if email and password:
            logger.info(f"Auto-filling credentials for {email}")
            await page.fill('input[name="email"]', email)
            await page.fill('input[name="password"]', password)
            logger.debug("Credentials filled")
            await asyncio.sleep(1)
            await page.click('button[type="submit"]')
            logger.info("Login form submitted, waiting for response...")

        # Wait for login to complete or MFA to be required
        try:
            logger.debug("Waiting 3 seconds for login response...")
            await asyncio.sleep(3)

            # Log current URL for debugging
            logger.info(f"Current URL after login attempt: {page.url}")

            # Check for login errors on the page
            error_messages = await page.locator(
                '[class*="error"], [class*="Error"]'
            ).all_text_contents()
            if error_messages:
                logger.error(f"Login errors detected on page: {error_messages}")

            # Check for CAPTCHA
            captcha_present = (
                await page.locator('iframe[src*="captcha"], [class*="captcha"]').count()
                > 0
            )
            if captcha_present:
                logger.error("CAPTCHA detected! Cannot proceed in headless mode.")
                raise RuntimeError(
                    "CAPTCHA detected during login. Please run 'uv run python get_token.py' "
                    "interactively to complete the CAPTCHA."
                )

            # Check if we already captured token
            if captured_token:
                logger.info("Token already captured from login response!")
            else:
                logger.debug("No token captured yet, checking for MFA...")

            # Detect MFA/2FA requirement
            if await _check_mfa_required(page):
                logger.warning("MFA/2FA detected!")
                if headless:
                    raise RuntimeError(
                        "MFA/2FA is required but cannot be completed in headless mode. "
                        "Please run 'uv run python get_token.py' interactively to get your token, "
                        "then add it to .env as DISCORD_TOKEN=your_token"
                    )
                else:
                    logger.info("MFA/2FA detected - waiting for user input...")

            # Wait for successful login (redirect to /channels or /app)
            logger.info("Waiting for redirect to Discord app...")
            await page.wait_for_function(
                "() => window.location.href.includes('/channels') || window.location.href.includes('/app')",
                timeout=timeout,
            )
            logger.info(f"Login successful! Redirected to: {page.url}")
            await asyncio.sleep(3)

        except Exception as e:
            logger.error(f"Login failed with error: {e}")
            logger.error(f"Current URL: {page.url}")
            # Try to get page content for debugging
            try:
                page_text = await page.locator("body").text_content()
                if page_text:
                    # Log first 500 chars of page content
                    logger.error(f"Page content preview: {page_text[:500]}")
            except Exception:
                pass
            raise RuntimeError(f"Login failed: {e}")

        # Navigate to channels to trigger more API requests if needed
        if "/channels/" not in page.url:
            logger.debug("Navigating to channels to capture more requests...")
            await page.goto("https://discord.com/channels/@me")
            await asyncio.sleep(3)

        # Extract token using multiple methods (in priority order)
        token = captured_token  # Method 1: Network capture (most reliable)
        logger.debug(f"Token from network capture: {'Found' if token else 'Not found'}")

        if not token:
            logger.info("Network capture failed, trying localStorage...")
            token = await _extract_from_localstorage(page)  # Method 2
            logger.debug(
                f"Token from localStorage: {'Found' if token else 'Not found'}"
            )

        if not token:
            logger.info("localStorage failed, trying webpack modules...")
            token = await _extract_from_webpack(page)  # Method 3
            logger.debug(f"Token from webpack: {'Found' if token else 'Not found'}")

        if not token:
            raise RuntimeError(
                "Failed to extract token from browser using all methods. "
                "This may be due to browser security restrictions."
            )

        logger.info("Successfully extracted Discord token!")
        return token

    finally:
        logger.debug("Cleaning up browser...")
        await browser.close()
        await playwright.stop()
        logger.debug("Browser cleanup complete")


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
