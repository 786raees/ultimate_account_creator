"""
Browser Manager
===============

Manages Playwright browser instances with proxy configuration,
fingerprint randomization, and context management.
Includes comprehensive logging for debugging.
"""

import os
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import AsyncGenerator, Optional

from playwright.async_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    async_playwright,
    ConsoleMessage,
    Request,
    Response,
)

from src.config import get_settings
from src.types.enums import BrowserType
from src.utils.logger import LoggerMixin
from src.utils.fingerprint import generate_fingerprint, generate_fingerprint_for_phone, BrowserFingerprint


class BrowserManager(LoggerMixin):
    """
    Manages Playwright browser lifecycle.

    Handles browser launching, context creation, proxy rotation,
    and fingerprint randomization for automation tasks.

    Attributes:
        browser_type: Type of browser to use (chromium, firefox, webkit).
        use_proxy: Whether to use proxy configuration.
        debug_mode: Enable comprehensive debug logging.
        rotate_proxy: Whether to rotate proxy for each session.
        randomize_fingerprint: Whether to randomize browser fingerprint.
    """

    def __init__(
        self,
        browser_type: BrowserType = BrowserType.CHROMIUM,
        use_proxy: bool = True,
        debug_mode: bool = True,
        rotate_proxy: bool = True,
        randomize_fingerprint: bool = True,
    ) -> None:
        """
        Initialize the browser manager.

        Args:
            browser_type: Type of browser to launch.
            use_proxy: Whether to configure proxy settings.
            debug_mode: Enable debug logging and screenshots.
            rotate_proxy: Whether to rotate proxy port each session.
            randomize_fingerprint: Whether to randomize browser fingerprint.
        """
        self.browser_type = browser_type
        self.use_proxy = use_proxy
        self.debug_mode = debug_mode
        self.rotate_proxy = rotate_proxy
        self.randomize_fingerprint = randomize_fingerprint
        self.settings = get_settings()

        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._current_fingerprint: Optional[BrowserFingerprint] = None
        self._current_proxy_port: Optional[int] = None
        self._phone_number: Optional[str] = None

        # Screenshot directory for debugging
        self.screenshot_dir = Path("./screenshots")
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)

    def set_phone_number(self, phone_number: str) -> None:
        """
        Set the phone number for country-based fingerprinting.

        Call this before start() to generate a fingerprint matching
        the phone's country.

        Args:
            phone_number: Phone number with country code (e.g., "+380969200145").
        """
        self._phone_number = phone_number
        self.log.info(f"Phone number set for fingerprint: {phone_number}")

    async def start(self) -> None:
        """
        Start Playwright and launch the browser.

        Initializes Playwright instance and launches the
        configured browser type with optional proxy rotation
        and fingerprint randomization.
        """
        self.log.info(f"{'='*60}")
        self.log.info(f"STARTING BROWSER: {self.browser_type}")
        self.log.info(f"{'='*60}")
        self.log.info(f"Headless: {self.settings.browser.headless}")
        self.log.info(f"Slow Mo: {self.settings.browser.slow_mo}ms")
        self.log.info(f"Use Proxy: {self.use_proxy}")
        self.log.info(f"Rotate Proxy: {self.rotate_proxy}")
        self.log.info(f"Randomize Fingerprint: {self.randomize_fingerprint}")

        # Generate fingerprint if enabled
        if self.randomize_fingerprint and self.settings.fingerprint.enabled:
            # Use phone-based fingerprint if phone number is set
            if self._phone_number:
                self._current_fingerprint = generate_fingerprint_for_phone(
                    phone_number=self._phone_number,
                    platform=self.settings.fingerprint.platform,
                )
                self.log.info(f"Generated fingerprint for {self._current_fingerprint.country_name} (+{self._current_fingerprint.country_code})")
            else:
                self._current_fingerprint = generate_fingerprint(
                    platform=self.settings.fingerprint.platform
                )
                self.log.info(f"Generated random fingerprint")

            self.log.info(f"  Viewport: {self._current_fingerprint.viewport_width}x{self._current_fingerprint.viewport_height}")
            self.log.info(f"  Timezone: {self._current_fingerprint.timezone_id}")
            self.log.info(f"  Locale: {self._current_fingerprint.locale}")

        # Get rotated proxy port if enabled
        if self.use_proxy and self.rotate_proxy and self.settings.proxy.rotate_per_request:
            self._current_proxy_port = self.settings.proxy.get_rotated_port()
            self.log.info(f"Proxy Host: {self.settings.proxy.host}:{self._current_proxy_port} (rotated)")
        elif self.use_proxy:
            self._current_proxy_port = self.settings.proxy.port
            self.log.info(f"Proxy Host: {self.settings.proxy.host}:{self._current_proxy_port}")

        if self.use_proxy:
            self.log.info(f"Proxy User: {self.settings.proxy.username}")

        self._playwright = await async_playwright().start()

        # Get the appropriate browser launcher
        browser_launcher = self._get_browser_launcher()

        # Build launch options
        launch_options = self._build_launch_options()
        self.log.debug(f"Launch options: {launch_options}")

        # Launch browser
        self._browser = await browser_launcher.launch(**launch_options)

        self.log.info("Browser launched successfully")

    async def stop(self) -> None:
        """
        Stop the browser and Playwright.

        Closes the browser and cleans up Playwright resources.
        """
        self.log.info("Stopping browser...")

        if self._browser:
            await self._browser.close()
            self._browser = None
            self.log.debug("Browser closed")

        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
            self.log.debug("Playwright stopped")

        self.log.info("Browser manager stopped")

    def _get_browser_launcher(self):
        """Get the browser launcher based on type."""
        if not self._playwright:
            raise RuntimeError("Playwright not started")

        launchers = {
            BrowserType.CHROMIUM: self._playwright.chromium,
            BrowserType.FIREFOX: self._playwright.firefox,
            BrowserType.WEBKIT: self._playwright.webkit,
        }

        return launchers[self.browser_type]

    def _build_launch_options(self) -> dict:
        """Build browser launch options with optional rotated proxy."""
        options = {
            "headless": self.settings.browser.headless,
            "slow_mo": self.settings.browser.slow_mo,
        }

        # Add proxy if enabled (use rotated port)
        if self.use_proxy and self.settings.proxy.username:
            proxy_config = {
                "server": f"http://{self.settings.proxy.host}:{self._current_proxy_port or self.settings.proxy.port}",
                "username": self.settings.proxy.username,
                "password": self.settings.proxy.password,
            }
            options["proxy"] = proxy_config
            self.log.info(f"Proxy configured: {self.settings.proxy.host}:{self._current_proxy_port}")

        return options

    def _build_context_options(self) -> dict:
        """Build browser context options with fingerprint if available."""
        # Use fingerprint if generated
        if self._current_fingerprint:
            options = {
                "viewport": self._current_fingerprint.viewport,
                "user_agent": self._current_fingerprint.user_agent,
                "locale": self._current_fingerprint.locale,
                "timezone_id": self._current_fingerprint.timezone_id,
                "color_scheme": self._current_fingerprint.color_scheme,
                "device_scale_factor": self._current_fingerprint.device_scale_factor,
                "has_touch": self._current_fingerprint.has_touch,
                "is_mobile": self._current_fingerprint.is_mobile,
                "extra_http_headers": self._current_fingerprint.extra_http_headers,
                "ignore_https_errors": True,
            }
        else:
            # Default options
            options = {
                "viewport": {"width": 1920, "height": 1080},
                "user_agent": self._get_user_agent(),
                "locale": "en-US",
                "timezone_id": "America/New_York",
                "ignore_https_errors": True,
            }

        # Add proxy authentication if needed (use rotated port)
        if self.use_proxy and self.settings.proxy.username:
            options["proxy"] = {
                "server": f"http://{self.settings.proxy.host}:{self._current_proxy_port or self.settings.proxy.port}",
                "username": self.settings.proxy.username,
                "password": self.settings.proxy.password,
            }

        return options

    def _get_user_agent(self) -> str:
        """Get a realistic user agent string (used when fingerprint not enabled)."""
        # Latest Chrome on Windows
        return (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/121.0.0.0 Safari/537.36"
        )

    @property
    def current_fingerprint(self) -> Optional[BrowserFingerprint]:
        """Get the current browser fingerprint."""
        return self._current_fingerprint

    @property
    def current_proxy_port(self) -> Optional[int]:
        """Get the current proxy port."""
        return self._current_proxy_port

    def _setup_page_logging(self, page: Page) -> None:
        """Set up comprehensive page event logging."""

        # Console message logging
        def on_console(msg: ConsoleMessage) -> None:
            if msg.type == "error":
                self.log.error(f"[CONSOLE ERROR] {msg.text}")
            elif msg.type == "warning":
                self.log.warning(f"[CONSOLE WARN] {msg.text}")
            elif self.debug_mode:
                self.log.debug(f"[CONSOLE {msg.type.upper()}] {msg.text}")

        page.on("console", on_console)

        # Page error logging
        def on_page_error(error: Exception) -> None:
            self.log.error(f"[PAGE ERROR] {error}")

        page.on("pageerror", on_page_error)

        # Request logging (for debugging network issues)
        def on_request(request: Request) -> None:
            if self.debug_mode and request.resource_type in ["document", "xhr", "fetch"]:
                self.log.debug(f"[REQUEST] {request.method} {request.url[:100]}")

        page.on("request", on_request)

        # Response logging
        def on_response(response: Response) -> None:
            if response.status >= 400:
                self.log.warning(f"[RESPONSE {response.status}] {response.url[:100]}")
            elif self.debug_mode and response.request.resource_type in ["document", "xhr", "fetch"]:
                self.log.debug(f"[RESPONSE {response.status}] {response.url[:100]}")

        page.on("response", on_response)

        # Dialog handling (alerts, confirms, prompts)
        async def on_dialog(dialog) -> None:
            self.log.warning(f"[DIALOG {dialog.type}] {dialog.message}")
            await dialog.dismiss()

        page.on("dialog", lambda d: page._loop.create_task(on_dialog(d)))

        self.log.debug("Page event logging configured")

    async def create_context(self) -> BrowserContext:
        """
        Create a new browser context.

        Returns:
            New BrowserContext with configured options.
        """
        if not self._browser:
            raise RuntimeError("Browser not started. Call start() first.")

        context_options = self._build_context_options()
        self.log.debug(f"Context options: viewport={context_options['viewport']}, locale={context_options['locale']}")

        context = await self._browser.new_context(**context_options)

        # Set default timeouts
        context.set_default_timeout(self.settings.browser.default_timeout)
        context.set_default_navigation_timeout(self.settings.browser.navigation_timeout)

        self.log.info(f"Created browser context (timeout={self.settings.browser.default_timeout}ms)")
        return context

    async def create_page(self, context: BrowserContext | None = None) -> Page:
        """
        Create a new page with logging enabled.

        Args:
            context: Optional context to use. Creates new if not provided.

        Returns:
            New Page instance with event logging.
        """
        if context is None:
            context = await self.create_context()

        page = await context.new_page()

        # Set up comprehensive logging
        self._setup_page_logging(page)

        self.log.info("Created new page with event logging")
        return page

    async def take_debug_screenshot(self, page: Page, name: str) -> str:
        """
        Take a debug screenshot.

        Args:
            page: Page to screenshot.
            name: Name for the screenshot file.

        Returns:
            Path to the saved screenshot.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{name}.png"
        filepath = self.screenshot_dir / filename

        await page.screenshot(path=str(filepath), full_page=False)
        self.log.info(f"Screenshot saved: {filepath}")

        return str(filepath)

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[Page, None]:
        """
        Context manager for a complete browser session.

        Yields:
            Page instance for automation.

        Example:
            async with browser_manager.session() as page:
                await page.goto("https://example.com")
        """
        context: BrowserContext | None = None
        page: Page | None = None

        try:
            await self.start()
            context = await self.create_context()
            page = await self.create_page(context)
            yield page
        except Exception as e:
            self.log.error(f"Session error: {e}")
            if page:
                try:
                    await self.take_debug_screenshot(page, "error")
                except Exception:
                    pass
            raise
        finally:
            if context:
                await context.close()
            await self.stop()

    @asynccontextmanager
    async def page_context(self) -> AsyncGenerator[Page, None]:
        """
        Context manager for a page within an existing browser.

        Use this when the browser is already started and you
        just need a new page/context.

        Yields:
            Page instance for automation.
        """
        if not self._browser:
            raise RuntimeError("Browser not started. Call start() first.")

        context = await self.create_context()
        page = await self.create_page(context)

        try:
            yield page
        finally:
            await context.close()

    @property
    def is_running(self) -> bool:
        """Check if the browser is running."""
        return self._browser is not None and self._browser.is_connected()
