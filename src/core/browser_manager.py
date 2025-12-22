"""
Browser Manager
===============

Manages Playwright browser instances with proxy configuration,
fingerprint randomization, and context management.
Includes comprehensive logging for debugging.

Supports two modes:
1. Direct Playwright: Standard browser launch with fingerprinting
2. MultiLoginX: Quick profiles with anti-fingerprint protection
"""

import asyncio
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
)

from src.config import get_settings
from src.services.multiloginx_client import MultiLoginXClient, QuickProfileResult
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
        use_multiloginx: Optional[bool] = None,
    ) -> None:
        """
        Initialize the browser manager.

        Args:
            browser_type: Type of browser to launch.
            use_proxy: Whether to configure proxy settings.
            debug_mode: Enable debug logging and screenshots.
            rotate_proxy: Whether to rotate proxy port each session.
            randomize_fingerprint: Whether to randomize browser fingerprint.
            use_multiloginx: Use MultiLoginX for browser profiles.
                            If None, uses setting from config (MLX_ENABLED).
        """
        self.browser_type = browser_type
        self.use_proxy = use_proxy
        self.debug_mode = debug_mode
        self.rotate_proxy = rotate_proxy
        self.randomize_fingerprint = randomize_fingerprint
        self.settings = get_settings()

        # Use MLX if explicitly set, otherwise use config setting
        self.use_multiloginx = use_multiloginx if use_multiloginx is not None else self.settings.multiloginx.enabled

        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._current_fingerprint: Optional[BrowserFingerprint] = None
        self._current_proxy_port: Optional[int] = None
        self._phone_number: Optional[str] = None
        self._country_iso: Optional[str] = None  # ISO country code for proxy targeting

        # MultiLoginX client and state
        self._mlx_client: Optional[MultiLoginXClient] = None
        self._mlx_profile_id: Optional[str] = None

        # Screenshot directory for debugging
        self.screenshot_dir = Path("./screenshots")
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)

    def set_phone_number(self, phone_number: str) -> None:
        """
        Set the phone number for country-based fingerprinting and proxy targeting.

        Call this before start() to generate a fingerprint matching
        the phone's country and route proxy through the same country.

        Args:
            phone_number: Phone number with country code (e.g., "+380969200145").
        """
        from src.utils.country_profiles import get_profile_for_phone

        self._phone_number = phone_number

        # Extract country ISO code for proxy targeting
        try:
            profile = get_profile_for_phone(phone_number)
            self._country_iso = profile.iso_code
            self.log.info(f"Phone number set: {phone_number}")
            self.log.info(f"Country targeting: {profile.country_name} ({self._country_iso})")
        except Exception as e:
            self.log.warning(f"Could not determine country for phone {phone_number}: {e}")
            self._country_iso = None

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
            proxy_username = self._get_proxy_username()
            self.log.info(f"Proxy User: {proxy_username}")
            if self._country_iso:
                self.log.info(f"Proxy Country Target: {self._country_iso}")

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

    def _get_proxy_username(self) -> str:
        """
        Get the proxy username with optional country targeting.

        Returns country-targeted username if a phone country was set,
        otherwise returns the base username.
        """
        if self._country_iso:
            return self.settings.proxy.get_country_targeted_username(self._country_iso)
        return self.settings.proxy.username

    def _build_launch_options(self) -> dict:
        """Build browser launch options with optional rotated proxy and country targeting."""
        options = {
            "headless": self.settings.browser.headless,
            "slow_mo": self.settings.browser.slow_mo,
        }

        # Add proxy if enabled (use rotated port and country targeting)
        if self.use_proxy and self.settings.proxy.username:
            proxy_username = self._get_proxy_username()
            proxy_config = {
                "server": f"http://{self.settings.proxy.host}:{self._current_proxy_port or self.settings.proxy.port}",
                "username": proxy_username,
                "password": self.settings.proxy.password,
            }
            options["proxy"] = proxy_config
            self.log.info(f"Proxy configured: {self.settings.proxy.host}:{self._current_proxy_port} (user: {proxy_username})")

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
            # Default options - standard 1080p viewport
            options = {
                "viewport": {"width": 1920, "height": 1080},
                "user_agent": self._get_user_agent(),
                "locale": "en-US",
                "timezone_id": "America/New_York",
                "ignore_https_errors": True,
            }

        # Add proxy authentication if needed (use rotated port and country targeting)
        if self.use_proxy and self.settings.proxy.username:
            proxy_username = self._get_proxy_username()
            options["proxy"] = {
                "server": f"http://{self.settings.proxy.host}:{self._current_proxy_port or self.settings.proxy.port}",
                "username": proxy_username,
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
        """Set up minimal page event logging - only errors."""

        # Only log page errors
        def on_page_error(error: Exception) -> None:
            self.log.error(f"[PAGE ERROR] {error}")

        page.on("pageerror", on_page_error)

        # Only log console errors
        def on_console(msg: ConsoleMessage) -> None:
            if msg.type == "error":
                self.log.error(f"[CONSOLE] {msg.text[:200]}")

        page.on("console", on_console)

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

        Routes to either MultiLoginX or direct Playwright based on config.

        Yields:
            Page instance for automation.

        Example:
            async with browser_manager.session() as page:
                await page.goto("https://example.com")
        """
        if self.use_multiloginx:
            async with self._mlx_session() as page:
                yield page
        else:
            async with self._direct_session() as page:
                yield page

    @asynccontextmanager
    async def _direct_session(self) -> AsyncGenerator[Page, None]:
        """
        Context manager for a direct Playwright browser session.

        Uses standard Playwright browser launch with fingerprinting.
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
    async def _mlx_session(self) -> AsyncGenerator[Page, None]:
        """
        Context manager for a MultiLoginX browser session.

        Creates a quick profile, connects via CDP, runs automation,
        then stops the profile.
        """
        mlx_settings = self.settings.multiloginx
        self._mlx_client = MultiLoginXClient(
            base_url=mlx_settings.base_url,
            api_url=mlx_settings.api_url,
            email=mlx_settings.email,
            password=mlx_settings.password,
            timeout=mlx_settings.timeout,
        )

        profile_result: Optional[QuickProfileResult] = None
        page: Page | None = None

        try:
            # Get rotated proxy port if enabled
            if self.use_proxy and self.rotate_proxy and self.settings.proxy.rotate_per_request:
                self._current_proxy_port = self.settings.proxy.get_rotated_port()
            elif self.use_proxy:
                self._current_proxy_port = self.settings.proxy.port

            # Build proxy config for MLX
            # Note: Use base username for MLX - MLX handles geo-targeting via fingerprinting
            # Country-targeted username format may not work with MLX's proxy handling
            proxy_config = None
            if self.use_proxy and self.settings.proxy.username:
                proxy_port = self._current_proxy_port or self.settings.proxy.port
                proxy_config = {
                    "host": self.settings.proxy.host,
                    "type": "http",
                    "port": proxy_port,
                    "username": self.settings.proxy.username,
                    "password": self.settings.proxy.password,
                }

            # Create quick profile - let MLX auto-handle screen resolution
            profile_result = await self._mlx_client.create_quick_profile(
                browser_type=mlx_settings.browser_type,
                os_type=mlx_settings.os_type,
                core_version=mlx_settings.core_version,
                is_headless=self.settings.browser.headless,
                proxy=proxy_config,
                automation="playwright",
                # screen_width/height not set - MLX auto-handles
            )

            if not profile_result.success:
                raise RuntimeError(f"Failed to create MLX profile: {profile_result.error}")

            self._mlx_profile_id = profile_result.profile_id

            # Small delay to let browser fully initialize
            await asyncio.sleep(2)

            # Connect to the browser via CDP
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.connect_over_cdp(
                profile_result.cdp_url,
                timeout=30000,
            )

            # Get the existing context (MLX creates one)
            contexts = self._browser.contexts
            if contexts:
                context = contexts[0]
            else:
                context = await self._browser.new_context()

            # Set timeouts
            context.set_default_timeout(self.settings.browser.default_timeout)
            context.set_default_navigation_timeout(self.settings.browser.navigation_timeout)

            # Get existing page or create new one
            pages = context.pages
            if pages:
                page = pages[0]
            else:
                page = await context.new_page()

            # Set up page logging
            self._setup_page_logging(page)

            # Warm up proxy connection
            await page.goto("about:blank")
            await asyncio.sleep(1)

            yield page

        except Exception as e:
            self.log.error(f"MLX session error: {e}")
            if page:
                try:
                    await self.take_debug_screenshot(page, "mlx_error")
                except Exception:
                    pass
            raise

        finally:
            # Clean up

            if self._browser:
                try:
                    await self._browser.close()
                except Exception as e:
                    self.log.debug(f"Error closing browser: {e}")
                self._browser = None

            if self._playwright:
                try:
                    await self._playwright.stop()
                except Exception as e:
                    self.log.debug(f"Error stopping playwright: {e}")
                self._playwright = None

            # Stop the MLX profile
            if self._mlx_client and self._mlx_profile_id:
                await self._mlx_client.stop_profile(self._mlx_profile_id)
                self._mlx_profile_id = None

            if self._mlx_client:
                await self._mlx_client.close()
                self._mlx_client = None

            # Kill any remaining Chrome processes from MLX
            await self._kill_chrome_processes()

    async def _kill_chrome_processes(self) -> None:
        """Kill Chrome processes to ensure MLX profiles are fully stopped."""
        import subprocess
        import platform

        try:
            if platform.system() == "Windows":
                # Kill Chrome processes on Windows
                subprocess.run(
                    ["taskkill", "/F", "/IM", "chrome.exe"],
                    capture_output=True,
                    timeout=10,
                )
                self.log.debug("Killed Chrome processes")
            else:
                # Kill Chrome processes on Linux/Mac
                subprocess.run(
                    ["pkill", "-f", "chrome"],
                    capture_output=True,
                    timeout=10,
                )
                self.log.debug("Killed Chrome processes")
        except Exception as e:
            self.log.debug(f"Could not kill Chrome processes: {e}")

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
