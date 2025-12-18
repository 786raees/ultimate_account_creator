"""
Airbnb Home Page
================

Page object for the Airbnb home/landing page.
Handles navigation to signup flow.
"""

from playwright.async_api import Page, TimeoutError as PlaywrightTimeout

from src.config.constants import PlatformDomains
from src.core.base_page import BasePage
from src.pages.airbnb.selectors import HomePageSelectors


class AirbnbHomePage(BasePage):
    """
    Page object for Airbnb's home page.

    Provides methods to interact with the home page and
    initiate the signup flow. Supports both modal and direct URL flows.
    """

    # Platform configuration
    PLATFORM_CONFIG = PlatformDomains.AIRBNB

    def __init__(self, page: Page) -> None:
        """
        Initialize the home page.

        Args:
            page: Playwright Page instance.
        """
        super().__init__(page)
        self.selectors = HomePageSelectors

    @property
    def url(self) -> str:
        """Get the home page URL."""
        return self.PLATFORM_CONFIG.base_url

    @property
    def signup_url(self) -> str:
        """Get the direct signup URL."""
        return self.PLATFORM_CONFIG.signup_url

    @property
    def is_direct_signup(self) -> bool:
        """Check if using direct signup flow."""
        return self.PLATFORM_CONFIG.is_direct_signup

    async def navigate_to_signup(self) -> None:
        """
        Navigate to signup - either direct URL or via modal.

        Uses the flow configured in PLATFORM_CONFIG.
        """
        if self.is_direct_signup:
            self.log.info(f"Using direct signup URL: {self.signup_url}")
            await self.page.goto(self.signup_url)
            await self.page.wait_for_load_state("domcontentloaded")
        else:
            self.log.info("Using modal signup flow")
            await self.navigate()
            await self.accept_cookies()
            await self.dismiss_popups()
            await self.open_signup_modal()

    @property
    def page_identifier(self) -> str:
        """Get the page identifier selector."""
        return self.selectors.LOGO

    async def open_signup_modal(self) -> None:
        """
        Open the signup modal from the home page.

        Clicks on the profile menu and then the signup button
        to open the signup modal.
        """
        self.log.info("Opening signup modal")

        # Click on the profile/menu button
        await self._click_profile_menu()

        # Wait for dropdown and click signup
        await self._click_signup_in_menu()

        self.log.info("Signup modal opened")

    async def _click_profile_menu(self) -> None:
        """Click the profile menu to reveal options."""
        self.log.debug(f"Looking for profile menu: {self.selectors.PROFILE_MENU}")

        try:
            # Try the profile menu button - use .first to avoid strict mode issues
            profile_btn = self.page.locator(self.selectors.PROFILE_MENU).first

            # Count matching elements for debugging
            count = await self.page.locator(self.selectors.PROFILE_MENU).count()
            self.log.debug(f"Found {count} elements matching profile menu selector")

            await profile_btn.wait_for(state="visible", timeout=10000)
            await profile_btn.click()
            self.log.debug("Clicked profile menu button")
        except PlaywrightTimeout:
            self.log.warning("Profile menu not found, trying alternatives")
            # Try alternative selectors - include multi-language aria-labels
            alternatives = [
                'button[aria-label*="Menu"]',
                'button[aria-label*="navigation"]',
                'button[aria-label*="меню"]',  # Russian: menu
                'button[aria-label*="Главное навигационное меню"]',  # Russian: Main navigation menu
                'header button:last-child',  # Often the profile menu is the last button
            ]
            for alt_selector in alternatives:
                try:
                    alt_btn = self.page.locator(alt_selector).first
                    if await alt_btn.is_visible(timeout=2000):
                        await alt_btn.click()
                        self.log.debug(f"Clicked profile menu using alternative: {alt_selector}")
                        return
                except Exception:
                    continue
            raise RuntimeError("Could not find profile menu button")

    async def _click_signup_in_menu(self) -> None:
        """Click the signup option in the dropdown menu."""
        # Wait for the menu to appear
        await self.page.wait_for_timeout(500)

        # Try different signup button selectors
        # Include multiple languages: English, Ukrainian, Russian, German, etc.
        signup_selectors = [
            # Data-testid selectors (language-independent)
            '[data-testid="signup-button"]',
            '[data-testid="cypress-headernav-signup"]',
            # English
            'a:has-text("Sign up")',
            'div[role="menuitem"]:has-text("Sign up")',
            'button:has-text("Sign up")',
            # Ukrainian - various forms (Зареєструватися, Реєстрація, etc.)
            'a:has-text("Зареєструватися")',
            'div[role="menuitem"]:has-text("Зареєструватися")',
            'a:has-text("Реєстрація")',
            'a:has-text("Зареєструйтеся")',  # imperative form
            'a:has-text("Реєструватися")',   # infinitive
            'div:has-text("Зареєструватися")',
            # Russian (Зарегистрироваться = Sign up/Register)
            'a:has-text("Зарегистрироваться")',
            'div[role="menuitem"]:has-text("Зарегистрироваться")',
            'a:has-text("Регистрация")',
            # German
            'a:has-text("Registrieren")',
            # French
            'a:has-text("Inscription")',
            # Spanish
            'a:has-text("Regístrate")',
        ]

        self.log.debug("Searching for signup button in menu...")

        # First, dump the menu HTML to debug
        try:
            menu = self.page.locator('div[role="menu"], nav[role="menu"], div[aria-label*="menu"]').first
            if await menu.is_visible(timeout=1000):
                menu_text = await menu.inner_text()
                self.log.debug(f"Menu text found: {menu_text[:200]}...")
        except Exception as e:
            self.log.debug(f"Could not get menu text: {e}")

        for selector in signup_selectors:
            try:
                btn = self.page.locator(selector).first
                if await btn.is_visible(timeout=2000):
                    await btn.click()
                    self.log.debug(f"Clicked signup with selector: {selector}")
                    return
            except PlaywrightTimeout:
                continue

        raise RuntimeError("Could not find signup button in menu")

    async def is_logged_in(self) -> bool:
        """
        Check if a user is currently logged in.

        Returns:
            True if user appears to be logged in.
        """
        try:
            # Look for indicators of logged-in state
            await self._click_profile_menu()
            await self.page.wait_for_timeout(500)

            # If we see "Log out" option, user is logged in
            logout = self.page.locator('a:has-text("Log out"), button:has-text("Log out")')
            is_logged = await logout.is_visible(timeout=2000)

            # Close the menu
            await self.page.keyboard.press("Escape")

            return is_logged
        except PlaywrightTimeout:
            return False

    async def accept_cookies(self) -> None:
        """Accept cookie consent if present."""
        try:
            cookie_selectors = [
                'button:has-text("Accept")',
                'button:has-text("OK")',
                'button:has-text("I accept")',
                '[data-testid="accept-cookies"]',
            ]

            for selector in cookie_selectors:
                btn = self.page.locator(selector).first
                if await btn.is_visible(timeout=2000):
                    await btn.click()
                    self.log.debug("Accepted cookies")
                    return
        except PlaywrightTimeout:
            self.log.debug("No cookie banner found")

    async def dismiss_popups(self) -> None:
        """Dismiss any promotional popups that might appear."""
        try:
            close_selectors = [
                'button[aria-label="Close"]',
                'button[aria-label="Dismiss"]',
                '[data-testid="modal-close"]',
            ]

            for selector in close_selectors:
                btn = self.page.locator(selector).first
                if await btn.is_visible(timeout=1000):
                    await btn.click()
                    self.log.debug(f"Dismissed popup with: {selector}")
                    await self.page.wait_for_timeout(500)
        except PlaywrightTimeout:
            pass
