"""
Enumeration Definitions
=======================

Defines all enumerations used across the application for
type safety and consistency.
"""

from enum import Enum, auto


class Platform(str, Enum):
    """Supported signup platforms."""

    AIRBNB = "airbnb"
    # Future platforms can be added here
    # BOOKING = "booking"
    # UBER = "uber"
    # DOORDASH = "doordash"

    def __str__(self) -> str:
        return self.value


class SignupStep(str, Enum):
    """Steps in the signup flow."""

    INITIALIZED = "initialized"
    NAVIGATED_TO_SIGNUP = "navigated_to_signup"
    EMAIL_ENTERED = "email_entered"
    PHONE_ENTERED = "phone_entered"
    OTP_REQUESTED = "otp_requested"
    OTP_VERIFIED = "otp_verified"
    PROFILE_COMPLETED = "profile_completed"
    SIGNUP_COMPLETED = "signup_completed"
    FAILED = "failed"

    def __str__(self) -> str:
        return self.value


class AccountStatus(str, Enum):
    """Status of a created account."""

    PENDING = "pending"
    ACTIVE = "active"
    VERIFIED = "verified"
    SUSPENDED = "suspended"
    FAILED = "failed"

    def __str__(self) -> str:
        return self.value


class BrowserType(str, Enum):
    """Supported browser types for Playwright."""

    CHROMIUM = "chromium"
    FIREFOX = "firefox"
    WEBKIT = "webkit"

    def __str__(self) -> str:
        return self.value


class PhoneStatus(str, Enum):
    """Status of a phone number."""

    AVAILABLE = "available"
    IN_USE = "in_use"
    USED = "used"
    BLOCKED = "blocked"
    INVALID = "invalid"

    def __str__(self) -> str:
        return self.value


class LogLevel(str, Enum):
    """Logging levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

    def __str__(self) -> str:
        return self.value
