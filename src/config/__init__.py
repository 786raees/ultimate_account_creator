"""
Configuration Module
====================

Centralized configuration management using Pydantic Settings.
Loads configuration from environment variables and .env files.
"""

from src.config.settings import Settings, get_settings

__all__ = ["Settings", "get_settings"]
