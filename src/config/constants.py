"""
Platform Constants
==================

Centralized constants for platform URLs and configuration.
"""

from dataclasses import dataclass
from enum import Enum


class SignupFlow(Enum):
    """Type of signup flow for a platform."""
    MODAL = "modal"      # Open home page → Click menu → Signup modal
    DIRECT = "direct"    # Go directly to signup URL


@dataclass
class PlatformConfig:
    """Configuration for a platform."""
    name: str
    base_url: str
    signup_url: str
    signup_flow: SignupFlow

    @property
    def is_direct_signup(self) -> bool:
        """Check if platform uses direct signup URL."""
        return self.signup_flow == SignupFlow.DIRECT


class PlatformDomains:
    """Platform configurations."""

    # Airbnb configuration
    AIRBNB = PlatformConfig(
        name="airbnb",
        base_url="https://www.airbnb.com",
        signup_url="https://www.airbnb.com/signup_login",
        signup_flow=SignupFlow.DIRECT,  # Use direct URL flow
    )

    # Add more platforms as needed:
    # BOOKING = PlatformConfig(
    #     name="booking",
    #     base_url="https://www.booking.com",
    #     signup_url="https://www.booking.com/register",
    #     signup_flow=SignupFlow.DIRECT,
    # )

    @classmethod
    def get_config(cls, platform: str) -> PlatformConfig:
        """
        Get configuration for a platform.

        Args:
            platform: Platform name (e.g., 'airbnb', 'AIRBNB')

        Returns:
            PlatformConfig for the platform.

        Raises:
            ValueError: If platform is not supported.
        """
        platform_upper = platform.upper()

        configs = {
            "AIRBNB": cls.AIRBNB,
            # "BOOKING": cls.BOOKING,
        }

        if platform_upper not in configs:
            raise ValueError(f"Unsupported platform: {platform}")

        return configs[platform_upper]

    @classmethod
    def get_domain(cls, platform: str) -> str:
        """Get base domain URL for a platform."""
        return cls.get_config(platform).base_url

    @classmethod
    def get_signup_url(cls, platform: str) -> str:
        """Get signup URL for a platform."""
        return cls.get_config(platform).signup_url

    @classmethod
    def is_direct_signup(cls, platform: str) -> bool:
        """Check if platform uses direct signup flow."""
        return cls.get_config(platform).is_direct_signup
