"""
Base Component Class
====================

Base class for reusable UI components that can be composed
within page objects.
"""

from abc import ABC, abstractmethod

from playwright.async_api import Locator, Page

from src.utils.logger import LoggerMixin


class BaseComponent(ABC, LoggerMixin):
    """
    Abstract base class for UI components.

    Components are reusable UI elements that appear across
    multiple pages (e.g., navigation bars, modals, forms).

    Attributes:
        page: Playwright Page instance.
        root_selector: CSS selector for the component root element.
    """

    def __init__(self, page: Page, root_selector: str | None = None) -> None:
        """
        Initialize the component.

        Args:
            page: Playwright Page instance.
            root_selector: Optional root selector to scope queries.
        """
        self.page = page
        self._root_selector = root_selector

    @property
    @abstractmethod
    def root_selector(self) -> str:
        """
        Get the root selector for this component.

        Returns:
            CSS selector for the component root element.
        """
        pass

    @property
    def root(self) -> Locator:
        """Get the root locator for this component."""
        selector = self._root_selector or self.root_selector
        return self.page.locator(selector)

    def locator(self, selector: str) -> Locator:
        """
        Get a locator scoped to this component.

        Args:
            selector: CSS selector relative to component root.

        Returns:
            Locator scoped to the component.
        """
        return self.root.locator(selector)

    async def is_visible(self, timeout: int = 5000) -> bool:
        """
        Check if the component is visible.

        Args:
            timeout: Time to wait for visibility.

        Returns:
            True if component is visible.
        """
        return await self.root.is_visible(timeout=timeout)

    async def wait_for_visible(self, timeout: int = 30000) -> None:
        """
        Wait for the component to be visible.

        Args:
            timeout: Maximum time to wait.
        """
        await self.root.wait_for(state="visible", timeout=timeout)

    async def wait_for_hidden(self, timeout: int = 30000) -> None:
        """
        Wait for the component to be hidden.

        Args:
            timeout: Maximum time to wait.
        """
        await self.root.wait_for(state="hidden", timeout=timeout)


class Modal(BaseComponent):
    """
    Base class for modal dialog components.

    Provides common functionality for modal interactions
    like opening, closing, and content verification.
    """

    @property
    @abstractmethod
    def close_button_selector(self) -> str:
        """Selector for the modal close button."""
        pass

    async def close(self) -> None:
        """Close the modal."""
        close_btn = self.locator(self.close_button_selector)
        await close_btn.click()
        await self.wait_for_hidden()

    async def is_open(self) -> bool:
        """Check if the modal is open."""
        return await self.is_visible()


class Form(BaseComponent):
    """
    Base class for form components.

    Provides common functionality for form interactions
    like filling fields, validation, and submission.
    """

    @property
    @abstractmethod
    def submit_button_selector(self) -> str:
        """Selector for the form submit button."""
        pass

    async def submit(self) -> None:
        """Submit the form."""
        submit_btn = self.locator(self.submit_button_selector)
        await submit_btn.click()

    async def fill_field(
        self,
        field_selector: str,
        value: str,
        clear_first: bool = True,
    ) -> None:
        """
        Fill a form field.

        Args:
            field_selector: Selector for the field.
            value: Value to enter.
            clear_first: Clear existing value first.
        """
        field = self.locator(field_selector)
        if clear_first:
            await field.fill("")
        await field.fill(value)

    async def get_field_value(self, field_selector: str) -> str:
        """Get the value of a form field."""
        field = self.locator(field_selector)
        return await field.input_value()

    async def has_error(self, error_selector: str = ".error") -> bool:
        """Check if the form has validation errors."""
        error = self.locator(error_selector)
        return await error.is_visible(timeout=1000)

    async def get_error_message(self, error_selector: str = ".error") -> str:
        """Get the form error message."""
        error = self.locator(error_selector)
        return await error.text_content() or ""
