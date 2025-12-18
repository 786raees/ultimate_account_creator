"""
Core Module
===========

Core components including browser management and base page classes.
"""

from src.core.base_page import BasePage
from src.core.browser_manager import BrowserManager
from src.core.base_component import BaseComponent

__all__ = [
    "BasePage",
    "BrowserManager",
    "BaseComponent",
]
