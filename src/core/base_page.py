"""
Base Page Class
===============

Abstract base class for all Page Object Model implementations.
Provides common functionality for page interactions.
"""

from abc import ABC, abstractmethod
from typing import Any

from playwright.async_api import Locator, Page, TimeoutError as PlaywrightTimeout

from src.config import get_settings
from src.utils.logger import LoggerMixin


class BasePage(ABC, LoggerMixin):
    """
    Abstract base class for page objects.

    Provides common methods for page interactions following
    the Page Object Model pattern.

    Attributes:
        page: Playwright Page instance.
        settings: Application settings.
    """

    def __init__(self, page: Page) -> None:
        """
        Initialize the base page.

        Args:
            page: Playwright Page instance to wrap.
        """
        self.page = page
        self.settings = get_settings()

    @property
    @abstractmethod
    def url(self) -> str:
        """
        Get the page URL.

        Returns:
            The URL of this page.
        """
        pass

    @property
    @abstractmethod
    def page_identifier(self) -> str:
        """
        Get a unique identifier/selector to verify the page.

        Returns:
            CSS selector or text that identifies this page.
        """
        pass

    async def navigate(self) -> None:
        """Navigate to this page's URL."""
        self.log.info(f"Navigating to: {self.url}")
        await self.page.goto(self.url, wait_until="domcontentloaded")
        await self.wait_for_page_load()

    async def wait_for_page_load(self) -> None:
        """Wait for the page to be fully loaded."""
        try:
            await self.page.wait_for_load_state("networkidle", timeout=10000)
        except PlaywrightTimeout:
            self.log.debug("Network idle timeout - continuing")

    async def is_current_page(self) -> bool:
        """
        Check if this is the current page.

        Returns:
            True if the page identifier is present.
        """
        try:
            locator = self.page.locator(self.page_identifier)
            return await locator.is_visible(timeout=5000)
        except PlaywrightTimeout:
            return False

    # -------------------------------------------------------------------------
    # Element Interaction Methods
    # -------------------------------------------------------------------------

    async def click(
        self,
        selector: str,
        timeout: int | None = None,
        force: bool = False,
    ) -> None:
        """
        Click an element.

        Args:
            selector: CSS selector for the element.
            timeout: Optional timeout override.
            force: Force click even if element is not actionable.
        """
        timeout = timeout or self.settings.browser.default_timeout
        self.log.debug(f"Clicking: {selector}")
        await self.page.click(selector, timeout=timeout, force=force)

    async def fill(
        self,
        selector: str,
        value: str,
        timeout: int | None = None,
        clear_first: bool = True,
    ) -> None:
        """
        Fill a text input field.

        Args:
            selector: CSS selector for the input.
            value: Value to enter.
            timeout: Optional timeout override.
            clear_first: Clear existing value before filling.
        """
        timeout = timeout or self.settings.browser.default_timeout
        self.log.debug(f"Filling '{selector}' with '{value[:20]}...'")

        if clear_first:
            await self.page.fill(selector, "", timeout=timeout)

        await self.page.fill(selector, value, timeout=timeout)

    async def type_text(
        self,
        selector: str,
        value: str,
        delay: int = 50,
        timeout: int | None = None,
    ) -> None:
        """
        Type text character by character (more human-like).

        Args:
            selector: CSS selector for the input.
            value: Value to type.
            delay: Delay between keystrokes in ms.
            timeout: Optional timeout override.
        """
        timeout = timeout or self.settings.browser.default_timeout
        self.log.debug(f"Typing in '{selector}'")

        await self.page.click(selector, timeout=timeout)
        await self.page.type(selector, value, delay=delay)

    async def select_option(
        self,
        selector: str,
        value: str | None = None,
        label: str | None = None,
        index: int | None = None,
    ) -> None:
        """
        Select an option from a dropdown.

        Args:
            selector: CSS selector for the select element.
            value: Option value to select.
            label: Option label to select.
            index: Option index to select.
        """
        self.log.debug(f"Selecting option in '{selector}'")

        if value:
            await self.page.select_option(selector, value=value)
        elif label:
            await self.page.select_option(selector, label=label)
        elif index is not None:
            await self.page.select_option(selector, index=index)

    async def check(self, selector: str) -> None:
        """Check a checkbox."""
        self.log.debug(f"Checking: {selector}")
        await self.page.check(selector)

    async def uncheck(self, selector: str) -> None:
        """Uncheck a checkbox."""
        self.log.debug(f"Unchecking: {selector}")
        await self.page.uncheck(selector)

    # -------------------------------------------------------------------------
    # Wait Methods
    # -------------------------------------------------------------------------

    async def wait_for_selector(
        self,
        selector: str,
        state: str = "visible",
        timeout: int | None = None,
    ) -> Locator:
        """
        Wait for an element to appear.

        Args:
            selector: CSS selector to wait for.
            state: Element state to wait for.
            timeout: Optional timeout override.

        Returns:
            Locator for the found element.
        """
        timeout = timeout or self.settings.browser.default_timeout
        self.log.debug(f"Waiting for: {selector} (state={state})")
        await self.page.wait_for_selector(selector, state=state, timeout=timeout)
        return self.page.locator(selector)

    async def wait_for_navigation(self, timeout: int | None = None) -> None:
        """Wait for navigation to complete."""
        timeout = timeout or self.settings.browser.navigation_timeout
        await self.page.wait_for_load_state("networkidle", timeout=timeout)

    async def wait_for_url(
        self,
        url_pattern: str,
        timeout: int | None = None,
    ) -> None:
        """
        Wait for URL to match a pattern.

        Args:
            url_pattern: URL pattern (can be regex or glob).
            timeout: Optional timeout override.
        """
        timeout = timeout or self.settings.browser.navigation_timeout
        await self.page.wait_for_url(url_pattern, timeout=timeout)

    # -------------------------------------------------------------------------
    # Element State Methods
    # -------------------------------------------------------------------------

    async def is_visible(self, selector: str, timeout: int = 5000) -> bool:
        """
        Check if an element is visible.

        Args:
            selector: CSS selector for the element.
            timeout: Time to wait for visibility.

        Returns:
            True if element is visible.
        """
        try:
            locator = self.page.locator(selector)
            return await locator.is_visible(timeout=timeout)
        except PlaywrightTimeout:
            return False

    async def is_enabled(self, selector: str) -> bool:
        """Check if an element is enabled."""
        locator = self.page.locator(selector)
        return await locator.is_enabled()

    async def get_text(self, selector: str) -> str:
        """Get the text content of an element."""
        locator = self.page.locator(selector)
        return await locator.text_content() or ""

    async def get_value(self, selector: str) -> str:
        """Get the value of an input element."""
        locator = self.page.locator(selector)
        return await locator.input_value()

    async def get_attribute(self, selector: str, attribute: str) -> str | None:
        """Get an attribute value from an element."""
        locator = self.page.locator(selector)
        return await locator.get_attribute(attribute)

    # -------------------------------------------------------------------------
    # Screenshot and Debug Methods
    # -------------------------------------------------------------------------

    async def screenshot(self, path: str, full_page: bool = False) -> None:
        """
        Take a screenshot of the page.

        Args:
            path: Path to save the screenshot.
            full_page: Capture the full scrollable page.
        """
        await self.page.screenshot(path=path, full_page=full_page)
        self.log.debug(f"Screenshot saved: {path}")

    async def get_page_source(self) -> str:
        """Get the page HTML source."""
        return await self.page.content()

    def locator(self, selector: str) -> Locator:
        """
        Get a locator for an element.

        Args:
            selector: CSS selector.

        Returns:
            Playwright Locator instance.
        """
        return self.page.locator(selector)
