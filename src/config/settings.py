"""
Settings Configuration
======================

Defines all application settings using Pydantic Settings.
Supports environment variables and .env file configuration.
"""

import random
from functools import lru_cache
from pathlib import Path
from typing import Literal, Optional, List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ProxySettings(BaseSettings):
    """Proxy server configuration with rotation support."""

    model_config = SettingsConfigDict(
        env_prefix="PROXY_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    host: str = Field(default="gate.decodo.com", description="Proxy server hostname")
    host_domain: str = Field(default="decodo.com", description="Base domain for country-specific hosts")
    port: int = Field(default=40001, description="Default proxy server port")
    username: str = Field(default="", description="Proxy authentication username")
    password: str = Field(default="", description="Proxy authentication password")

    # Rotating proxy configuration
    port_range_start: int = Field(default=40001, description="Start of rotating port range")
    port_range_end: int = Field(default=49999, description="End of rotating port range")
    rotate_per_request: bool = Field(default=True, description="Rotate proxy for each new session")

    # Country-specific proxy host mapping (ISO code -> subdomain prefix)
    # Override defaults where the subdomain doesn't match the ISO code
    COUNTRY_HOST_OVERRIDES: dict = {
        # Add any country-specific overrides here
        # e.g., "GB": "uk" if the provider uses "uk" instead of "gb"
    }

    def get_rotated_port(self) -> int:
        """Get a random port from the rotation range."""
        return random.randint(self.port_range_start, self.port_range_end)

    @property
    def server_url(self) -> str:
        """Get the full proxy server URL with current port."""
        return f"http://{self.host}:{self.port}"

    def get_rotated_server_url(self) -> str:
        """Get proxy URL with a rotated port."""
        rotated_port = self.get_rotated_port()
        return f"http://{self.host}:{rotated_port}"

    @property
    def auth_credentials(self) -> dict[str, str]:
        """Get proxy authentication credentials."""
        return {"username": self.username, "password": self.password}

    @property
    def playwright_proxy(self) -> dict[str, str]:
        """Get proxy configuration for Playwright."""
        return {
            "server": self.server_url,
            "username": self.username,
            "password": self.password,
        }

    def get_rotated_playwright_proxy(self) -> dict[str, str]:
        """Get proxy configuration with rotated port."""
        return {
            "server": self.get_rotated_server_url(),
            "username": self.username,
            "password": self.password,
        }

    def get_country_targeted_username(self, country_iso: str) -> str:
        """
        Get username with country targeting suffix.

        Smartproxy/Decodo format: user-USERNAME-country-XX
        where XX is 2-letter ISO country code.

        Args:
            country_iso: 2-letter ISO country code (e.g., "UA", "US", "GB")

        Returns:
            Username with country targeting suffix.
        """
        if not country_iso:
            return self.username
        return f"user-{self.username}-country-{country_iso.lower()}"

    def get_country_host(self, country_iso: str) -> str:
        """
        Get country-specific proxy host.

        Uses format: {country_code}.{domain} (e.g., ua.decodo.com for Ukraine)

        Args:
            country_iso: 2-letter ISO country code (e.g., "UA", "US", "GB")

        Returns:
            Country-specific proxy host.
        """
        if not country_iso:
            return self.host

        # Check for overrides first
        subdomain = self.COUNTRY_HOST_OVERRIDES.get(
            country_iso.upper(),
            country_iso.lower()  # Default: use ISO code as subdomain
        )

        return f"{subdomain}.{self.host_domain}"

    def get_country_targeted_playwright_proxy(self, country_iso: str) -> dict[str, str]:
        """
        Get proxy configuration with country targeting.

        Uses country-specific host and rotated port.

        Args:
            country_iso: 2-letter ISO country code (e.g., "UA", "US", "GB")

        Returns:
            Playwright proxy config with country-specific host.
        """
        rotated_port = self.get_rotated_port()
        country_host = self.get_country_host(country_iso)
        return {
            "server": f"http://{country_host}:{rotated_port}",
            "username": self.username,  # No username modification needed with country-specific host
            "password": self.password,
        }


class CaptchaSettings(BaseSettings):
    """CAPTCHA solving service configuration."""

    model_config = SettingsConfigDict(
        env_prefix="CAPTCHA_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    enabled: bool = Field(default=False, description="Enable CAPTCHA solving")
    provider: str = Field(default="2captcha", description="CAPTCHA service provider (2captcha, capsolver)")
    api_key: str = Field(default="", description="CAPTCHA service API key")
    timeout: int = Field(default=120, description="CAPTCHA solving timeout in seconds")


class FingerprintSettings(BaseSettings):
    """Browser fingerprint randomization configuration."""

    model_config = SettingsConfigDict(
        env_prefix="FINGERPRINT_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    enabled: bool = Field(default=True, description="Enable fingerprint randomization")
    platform: str = Field(default="random", description="Target platform (windows, mac, random)")
    randomize_viewport: bool = Field(default=True, description="Randomize viewport size")
    randomize_timezone: bool = Field(default=True, description="Randomize timezone")
    randomize_locale: bool = Field(default=True, description="Randomize locale")


class HumanBehaviorSettings(BaseSettings):
    """Human-like behavior simulation configuration."""

    model_config = SettingsConfigDict(
        env_prefix="HUMAN_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    enabled: bool = Field(default=True, description="Enable human-like behavior simulation")
    typing_speed_min: int = Field(default=50, description="Minimum typing delay in ms")
    typing_speed_max: int = Field(default=150, description="Maximum typing delay in ms")
    typo_probability: float = Field(default=0.02, description="Probability of making a typo (0-1)")
    mouse_movement: bool = Field(default=True, description="Enable natural mouse movement")
    random_delays: bool = Field(default=True, description="Enable random delays between actions")


class BrowserSettings(BaseSettings):
    """Browser configuration settings."""

    model_config = SettingsConfigDict(
        env_prefix="",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    headless: bool = Field(default=False, description="Run browser in headless mode")
    slow_mo: int = Field(default=50, description="Slow down operations by ms")
    default_timeout: int = Field(default=30000, description="Default timeout in ms")
    navigation_timeout: int = Field(default=60000, description="Navigation timeout in ms")

    @field_validator("slow_mo", "default_timeout", "navigation_timeout", mode="before")
    @classmethod
    def validate_positive_int(cls, v: int | str) -> int:
        """Ensure timeout values are positive integers."""
        value = int(v)
        if value < 0:
            raise ValueError("Timeout values must be non-negative")
        return value


class PathSettings(BaseSettings):
    """File and directory path configuration."""

    model_config = SettingsConfigDict(
        env_prefix="",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    phone_list_airbnb: Path = Field(
        default=Path("./data/phones/airbnb_phones.txt"),
        description="Path to Airbnb phone numbers list",
    )
    used_phones_path: Path = Field(
        default=Path("./data/state/used_phones.json"),
        description="Path to track used phone numbers",
    )
    accounts_output_path: Path = Field(
        default=Path("./data/accounts/"),
        description="Directory for saved account credentials",
    )

    @field_validator("phone_list_airbnb", "used_phones_path", "accounts_output_path", mode="before")
    @classmethod
    def validate_path(cls, v: str | Path) -> Path:
        """Convert string paths to Path objects and resolve relative to project root."""
        path = Path(v) if isinstance(v, str) else v
        if not path.is_absolute():
            # Resolve relative paths from project root (src/config/settings.py -> ../../)
            project_root = Path(__file__).parent.parent.parent
            path = project_root / path
        return path.resolve()


class LogSettings(BaseSettings):
    """Logging configuration settings."""

    model_config = SettingsConfigDict(
        env_prefix="LOG_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO", description="Logging level"
    )
    dir: Path = Field(default=Path("./logs"), description="Log files directory")
    rotation: str = Field(default="10 MB", description="Log file rotation size")
    retention: str = Field(default="7 days", description="Log file retention period")


class RetrySettings(BaseSettings):
    """Retry behavior configuration."""

    model_config = SettingsConfigDict(
        env_prefix="",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    max_retries: int = Field(default=3, description="Maximum retry attempts")
    retry_delay_seconds: int = Field(default=5, description="Delay between retries in seconds")


class MultiLoginXSettings(BaseSettings):
    """MultiLoginX integration configuration."""

    model_config = SettingsConfigDict(
        env_prefix="MLX_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    enabled: bool = Field(default=True, description="Enable MultiLoginX for browser profiles")
    base_url: str = Field(
        default="https://launcher.mlx.yt:45001",
        description="MultiLoginX launcher API URL"
    )
    api_url: str = Field(
        default="https://api.multilogin.com",
        description="MultiLoginX main API URL for authentication"
    )
    email: str = Field(default="", description="MultiLoginX account email")
    password: str = Field(default="", description="MultiLoginX account password (MD5 hashed)")
    timeout: int = Field(default=60, description="API request timeout in seconds")
    browser_type: str = Field(default="mimic", description="Browser type (mimic, stealthfox)")
    core_version: int = Field(default=132, description="Browser core version")
    os_type: str = Field(default="windows", description="OS type (windows, linux, macos)")


class Settings(BaseSettings):
    """
    Main application settings.

    Aggregates all configuration sections and provides
    a unified interface for accessing settings.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Sub-configurations
    proxy: ProxySettings = Field(default_factory=ProxySettings)
    browser: BrowserSettings = Field(default_factory=BrowserSettings)
    paths: PathSettings = Field(default_factory=PathSettings)
    log: LogSettings = Field(default_factory=LogSettings)
    retry: RetrySettings = Field(default_factory=RetrySettings)
    captcha: CaptchaSettings = Field(default_factory=CaptchaSettings)
    fingerprint: FingerprintSettings = Field(default_factory=FingerprintSettings)
    human_behavior: HumanBehaviorSettings = Field(default_factory=HumanBehaviorSettings)
    multiloginx: MultiLoginXSettings = Field(default_factory=MultiLoginXSettings)

    def __init__(self, **kwargs):
        """Initialize settings with nested configurations."""
        super().__init__(**kwargs)
        # Initialize nested settings from environment
        object.__setattr__(self, "proxy", ProxySettings())
        object.__setattr__(self, "browser", BrowserSettings())
        object.__setattr__(self, "paths", PathSettings())
        object.__setattr__(self, "log", LogSettings())
        object.__setattr__(self, "retry", RetrySettings())
        object.__setattr__(self, "captcha", CaptchaSettings())
        object.__setattr__(self, "fingerprint", FingerprintSettings())
        object.__setattr__(self, "human_behavior", HumanBehaviorSettings())
        object.__setattr__(self, "multiloginx", MultiLoginXSettings())


@lru_cache
def get_settings() -> Settings:
    """
    Get cached application settings instance.

    Uses LRU cache to ensure settings are loaded only once
    and reused throughout the application lifecycle.

    Returns:
        Settings: The application settings instance.
    """
    return Settings()
