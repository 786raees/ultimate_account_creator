"""
Browser Manager
===============

Manages Playwright browser instances with proxy configuration,
fingerprint randomization, and context management.
Includes comprehensive logging for debugging.

Supports two modes:
1. Direct Playwright: Launch browser directly via Playwright
2. MultiLoginX: Connect to browser via MultiLoginX CDP endpoint
"""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional, TYPE_CHECKING

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

if TYPE_CHECKING:
    from src.services.multiloginx_client import MultiLoginXProfile


class BrowserManager(LoggerMixin):
    """
    Manages Playwright browser lifecycle.

    Handles browser launching, context creation, proxy rotation,
    and fingerprint randomization for automation tasks.

    Supports two modes:
    1. Direct mode: Launch browser directly via Playwright
    2. MultiLoginX mode: Connect to browser via MultiLoginX CDP endpoint

    Attributes:
        browser_type: Type of browser to use (chromium, firefox, webkit).
        use_proxy: Whether to use proxy configuration.
        debug_mode: Enable comprehensive debug logging.
        rotate_proxy: Whether to rotate proxy for each session.
        randomize_fingerprint: Whether to randomize browser fingerprint.
        use_multiloginx: Whether to use MultiLoginX for browser profiles.
    """

    def __init__(
        self,
        browser_type: BrowserType = BrowserType.CHROMIUM,
        use_proxy: bool = True,
        debug_mode: bool = True,
        rotate_proxy: bool = True,
        randomize_fingerprint: bool = True,
        use_multiloginx: bool = True,
    ) -> None:
        """
        Initialize the browser manager.

        Args:
            browser_type: Type of browser to launch.
            use_proxy: Whether to configure proxy settings.
            debug_mode: Enable debug logging and screenshots.
            rotate_proxy: Whether to rotate proxy port each session.
            randomize_fingerprint: Whether to randomize browser fingerprint.
            use_multiloginx: Whether to use MultiLoginX for browser profiles.
        """
        self.browser_type = browser_type
        self.use_proxy = use_proxy
        self.debug_mode = debug_mode
        self.rotate_proxy = rotate_proxy
        self.randomize_fingerprint = randomize_fingerprint
        self.settings = get_settings()

        # Check if MultiLoginX is enabled in settings
        self.use_multiloginx = use_multiloginx and self.settings.multiloginx.enabled

        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None
        self._current_fingerprint: Optional[BrowserFingerprint] = None
        self._current_proxy_port: Optional[int] = None
        self._phone_number: Optional[str] = None
        self._country_iso: Optional[str] = None  # ISO country code for proxy targeting
        self._mlx_profile: Optional["MultiLoginXProfile"] = None  # MultiLoginX profile

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
        Start Playwright and launch/connect to the browser.

        Initializes Playwright instance and either:
        1. Creates a MultiLoginX profile and connects via CDP
        2. Launches browser directly via Playwright

        Uses optional proxy rotation and fingerprint randomization.
        """
        self.log.info(f"{'='*60}")
        self.log.info(f"STARTING BROWSER: {self.browser_type}")
        self.log.info(f"{'='*60}")
        self.log.info(f"Mode: {'MultiLoginX' if self.use_multiloginx else 'Direct Playwright'}")
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

        if self.use_multiloginx:
            # Use MultiLoginX to create profile and connect via CDP
            await self._start_multiloginx()
        else:
            # Launch browser directly via Playwright
            await self._start_direct()

        self.log.info("Browser started successfully")

    async def _start_multiloginx(self) -> None:
        """Start browser via MultiLoginX profile."""
        from src.services.multiloginx_client import MultiLoginXClient

        self.log.info("Creating MultiLoginX profile...")

        # Create MultiLoginX client
        mlx_client = MultiLoginXClient(
            base_url=self.settings.multiloginx.base_url,
            timeout=self.settings.multiloginx.timeout,
        )

        try:
            # Create quick profile with fingerprint and proxy
            self._mlx_profile = await mlx_client.create_quick_profile(
                fingerprint=self._current_fingerprint,
                proxy_port=self._current_proxy_port,
                country_iso=self._country_iso,
                browser_type=self.settings.multiloginx.browser_type,
                core_version=self.settings.multiloginx.core_version,
                os_type=self.settings.multiloginx.os_type,
                is_headless=self.settings.browser.headless,
            )

            self.log.info(f"MultiLoginX profile created: {self._mlx_profile.id}")
            self.log.info(f"Connecting to CDP at port {self._mlx_profile.port}...")

            # Connect to the browser via CDP
            cdp_url = f"http://127.0.0.1:{self._mlx_profile.port}"
            self._browser = await self._playwright.chromium.connect_over_cdp(cdp_url)

            self.log.info(f"Connected to MultiLoginX browser via CDP")

            # Get the existing context and page from MLX
            contexts = self._browser.contexts
            if contexts:
                self._context = contexts[0]
                pages = self._context.pages
                if pages:
                    self._page = pages[0]
                    self.log.info("Using existing MLX page")
                else:
                    self._page = await self._context.new_page()
                    self.log.info("Created new page in MLX context")
            else:
                raise RuntimeError("No context found in MLX browser")

            # Setup page logging and timeouts
            self._setup_page_logging(self._page)
            self._context.set_default_timeout(self.settings.browser.default_timeout)
            self._context.set_default_navigation_timeout(self.settings.browser.navigation_timeout)

            # Wait for proxy to fully initialize
            await asyncio.sleep(2)

        except Exception as e:
            raise RuntimeError(f"Failed to start MultiLoginX profile: {e}")
        finally:
            # Always close the client session to prevent leaks
            await mlx_client.close()

    async def _start_direct(self) -> None:
        """Start browser directly via Playwright."""
        # Get the appropriate browser launcher
        browser_launcher = self._get_browser_launcher()

        # Build launch options
        launch_options = self._build_launch_options()
        self.log.debug(f"Launch options: {launch_options}")

        # Launch browser
        self._browser = await browser_launcher.launch(**launch_options)

        # Create context and page
        context_options = self._build_context_options()
        self._context = await self._browser.new_context(**context_options)
        self._context.set_default_timeout(self.settings.browser.default_timeout)
        self._context.set_default_navigation_timeout(self.settings.browser.navigation_timeout)

        self._page = await self._context.new_page()
        self._setup_page_logging(self._page)

        self.log.info("Browser launched directly via Playwright")

    @property
    def page(self) -> Page:
        """Get the current page. Raises if not started."""
        if not self._page:
            raise RuntimeError("Browser not started. Call start() first.")
        return self._page

    async def stop(self) -> None:
        """
        Stop the browser and Playwright.

        Closes the browser and cleans up Playwright resources.
        If using MultiLoginX, also stops the profile.
        """
        self.log.info("Stopping browser...")

        # Clear page and context references
        self._page = None
        self._context = None

        if self._browser:
            await self._browser.close()
            self._browser = None
            self.log.debug("Browser closed")

        # Stop MultiLoginX profile if active
        if self._mlx_profile:
            await self._stop_multiloginx_profile()

        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
            self.log.debug("Playwright stopped")

        self.log.info("Browser manager stopped")

    async def _stop_multiloginx_profile(self) -> None:
        """Stop the active MultiLoginX profile."""
        if not self._mlx_profile:
            return

        from src.services.multiloginx_client import MultiLoginXClient

        self.log.info(f"Stopping MultiLoginX profile: {self._mlx_profile.id}")

        mlx_client = MultiLoginXClient(
            base_url=self.settings.multiloginx.base_url,
            timeout=self.settings.multiloginx.timeout,
        )

        try:
            await mlx_client.stop_profile(self._mlx_profile.id)
            self.log.info(f"MultiLoginX profile stopped: {self._mlx_profile.id}")
        except Exception as e:
            self.log.warning(f"Failed to stop MultiLoginX profile: {e}")
        finally:
            await mlx_client.close()
            self._mlx_profile = None

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
        # When using MultiLoginX, fingerprint is configured in the profile
        # We only need minimal options here
        if self.use_multiloginx and self._mlx_profile:
            return {
                "ignore_https_errors": True,
            }

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

        # Add proxy authentication if needed (use rotated port and country targeting)
        # Skip if using MultiLoginX since proxy is configured in the profile
        if self.use_proxy and self.settings.proxy.username and not self.use_multiloginx:
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

    @property
    def mlx_profile_id(self) -> Optional[str]:
        """Get the MultiLoginX profile ID if using MultiLoginX."""
        return self._mlx_profile.id if self._mlx_profile else None

    def _setup_page_logging(self, page: Page) -> None:
        """Set up comprehensive page event logging."""

        # API endpoints to log in detail
        api_keywords = [
            "phone_one_time_passwords",
            "api/v2",
            "api/v3",
            "authentications",
            "signup",
            "login",
            "register",
        ]

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

        # Request logging with POST data for API calls
        def on_request(request: Request) -> None:
            url = request.url
            is_api_call = any(kw in url for kw in api_keywords)

            if is_api_call:
                self.log.info(f"[API REQUEST] {request.method} {url}")

                # Log POST data if available
                if request.method == "POST":
                    try:
                        post_data = request.post_data
                        if post_data:
                            self.log.info(f"[API REQUEST BODY] {post_data[:2000]}")
                    except Exception as e:
                        self.log.debug(f"Could not get POST data: {e}")

                # Log headers for API calls
                try:
                    headers = request.headers
                    important_headers = {k: v for k, v in headers.items()
                                        if k.lower() in ['content-type', 'x-airbnb-api-key', 'authorization', 'x-csrf-token']}
                    if important_headers:
                        self.log.info(f"[API REQUEST HEADERS] {important_headers}")
                except Exception:
                    pass

            elif self.debug_mode and request.resource_type in ["document", "xhr", "fetch"]:
                self.log.debug(f"[REQUEST] {request.method} {url[:100]}")

        page.on("request", on_request)

        # Response logging with body for API calls
        async def on_response_async(response: Response) -> None:
            url = response.url
            status = response.status
            is_api_call = any(kw in url for kw in api_keywords)

            if is_api_call:
                self.log.info(f"[API RESPONSE] {status} {url}")

                # Log response body for API calls
                try:
                    body = await response.text()
                    if body:
                        # Truncate long responses
                        body_preview = body[:3000] + "..." if len(body) > 3000 else body
                        self.log.info(f"[API RESPONSE BODY] {body_preview}")
                except Exception as e:
                    self.log.debug(f"Could not get response body: {e}")

            elif status >= 400:
                self.log.warning(f"[RESPONSE {status}] {url[:100]}")
            elif self.debug_mode and response.request.resource_type in ["document", "xhr", "fetch"]:
                self.log.debug(f"[RESPONSE {status}] {url[:100]}")

        def on_response(response: Response) -> None:
            # Schedule async response handling
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                loop.create_task(on_response_async(response))
            except RuntimeError:
                pass  # No event loop running

        page.on("response", on_response)

        # Dialog handling (alerts, confirms, prompts)
        async def on_dialog(dialog) -> None:
            self.log.warning(f"[DIALOG {dialog.type}] {dialog.message}")
            await dialog.dismiss()

        page.on("dialog", lambda d: page._loop.create_task(on_dialog(d)))

        self.log.debug("Page event logging configured (API logging enabled)")

    async def take_debug_screenshot(self, name: str) -> str:
        """
        Take a debug screenshot.

        Args:
            name: Name for the screenshot file.

        Returns:
            Path to the saved screenshot.
        """
        if not self._page:
            self.log.warning("Cannot take screenshot - no page available")
            return ""

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{name}.png"
        filepath = self.screenshot_dir / filename

        await self._page.screenshot(path=str(filepath), full_page=False)
        self.log.info(f"Screenshot saved: {filepath}")

        return str(filepath)

    @property
    def is_running(self) -> bool:
        """Check if the browser is running."""
        return self._browser is not None and self._browser.is_connected()
