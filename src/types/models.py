"""
Data Models
============

Pydantic models for data validation and serialization.
These models ensure type safety and data integrity throughout
the application.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, EmailStr, Field, field_validator

from src.types.enums import AccountStatus, Platform, SignupStep


class PhoneNumber(BaseModel):
    """
    Represents a phone number with metadata.

    Attributes:
        number: The full phone number including country code.
        country_code: The country dialing code (e.g., "380" for Ukraine).
        local_number: The local portion of the phone number.
        platform: The platform this number is designated for.
        is_used: Whether this number has been used for signup.
        used_at: Timestamp when the number was used.
    """

    number: str = Field(..., description="Full phone number with country code")
    country_code: str = Field(default="", description="Country dialing code")
    local_number: str = Field(default="", description="Local phone number portion")
    platform: Platform | None = Field(default=None, description="Designated platform")
    is_used: bool = Field(default=False, description="Whether number has been used")
    used_at: datetime | None = Field(default=None, description="When the number was used")

    @field_validator("number", mode="before")
    @classmethod
    def clean_number(cls, v: str) -> str:
        """Remove any non-digit characters except leading +."""
        if not v:
            raise ValueError("Phone number cannot be empty")
        # Keep only digits
        cleaned = "".join(c for c in v if c.isdigit())
        return cleaned

    def model_post_init(self, __context: Any) -> None:
        """Extract country code and local number after initialization."""
        if self.number and not self.country_code:
            # Common country codes mapping (first 1-3 digits)
            if self.number.startswith("380"):  # Ukraine
                object.__setattr__(self, "country_code", "380")
                object.__setattr__(self, "local_number", self.number[3:])
            elif self.number.startswith("375"):  # Belarus
                object.__setattr__(self, "country_code", "375")
                object.__setattr__(self, "local_number", self.number[3:])
            elif self.number.startswith("261"):  # Madagascar
                object.__setattr__(self, "country_code", "261")
                object.__setattr__(self, "local_number", self.number[3:])
            elif self.number.startswith("962"):  # Jordan
                object.__setattr__(self, "country_code", "962")
                object.__setattr__(self, "local_number", self.number[3:])
            elif self.number.startswith("1"):  # US/Canada
                object.__setattr__(self, "country_code", "1")
                object.__setattr__(self, "local_number", self.number[1:])

    @property
    def formatted(self) -> str:
        """Get formatted phone number with + prefix."""
        return f"+{self.number}"

    @property
    def display(self) -> str:
        """Get display-friendly format."""
        if self.country_code and self.local_number:
            return f"+{self.country_code} {self.local_number}"
        return f"+{self.number}"


class UserProfile(BaseModel):
    """
    User profile data for signup.

    Attributes:
        first_name: User's first name.
        last_name: User's last name.
        email: User's email address.
        password: Account password.
        birth_date: User's date of birth.
    """

    first_name: str = Field(..., min_length=2, max_length=50, description="First name")
    last_name: str = Field(..., min_length=2, max_length=50, description="Last name")
    email: EmailStr = Field(..., description="Email address")
    password: str = Field(..., min_length=8, description="Account password")
    birth_date: datetime | None = Field(default=None, description="Date of birth")

    @property
    def full_name(self) -> str:
        """Get the user's full name."""
        return f"{self.first_name} {self.last_name}"

    @property
    def birth_year(self) -> int | None:
        """Get birth year if birth_date is set."""
        return self.birth_date.year if self.birth_date else None

    @property
    def birth_month(self) -> int | None:
        """Get birth month if birth_date is set."""
        return self.birth_date.month if self.birth_date else None

    @property
    def birth_day(self) -> int | None:
        """Get birth day if birth_date is set."""
        return self.birth_date.day if self.birth_date else None


class ProxyConfig(BaseModel):
    """
    Proxy server configuration.

    Attributes:
        host: Proxy server hostname.
        port: Proxy server port.
        username: Authentication username.
        password: Authentication password.
    """

    host: str = Field(..., description="Proxy server hostname")
    port: int = Field(..., ge=1, le=65535, description="Proxy server port")
    username: str = Field(default="", description="Proxy username")
    password: str = Field(default="", description="Proxy password")

    @property
    def server_url(self) -> str:
        """Get the full proxy server URL."""
        return f"http://{self.host}:{self.port}"

    @property
    def has_auth(self) -> bool:
        """Check if proxy requires authentication."""
        return bool(self.username and self.password)

    def to_playwright_config(self) -> dict[str, str]:
        """Convert to Playwright proxy configuration format."""
        config = {"server": self.server_url}
        if self.has_auth:
            config["username"] = self.username
            config["password"] = self.password
        return config


class AccountCredentials(BaseModel):
    """
    Saved account credentials.

    Attributes:
        platform: The platform the account was created on.
        email: Account email address.
        password: Account password.
        phone: Phone number used for verification.
        profile: User profile information.
        created_at: When the account was created.
        status: Current account status.
    """

    platform: Platform = Field(..., description="Platform name")
    email: EmailStr = Field(..., description="Account email")
    password: str = Field(..., description="Account password")
    phone: str = Field(..., description="Verification phone number")
    profile: UserProfile = Field(..., description="User profile data")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")
    status: AccountStatus = Field(default=AccountStatus.PENDING, description="Account status")

    def to_export_dict(self) -> dict[str, Any]:
        """Convert to dictionary for export/saving."""
        return {
            "platform": str(self.platform),
            "email": self.email,
            "password": self.password,
            "phone": self.phone,
            "first_name": self.profile.first_name,
            "last_name": self.profile.last_name,
            "created_at": self.created_at.isoformat(),
            "status": str(self.status),
        }


class SignupResult(BaseModel):
    """
    Result of a signup attempt.

    Attributes:
        success: Whether the signup was successful.
        platform: The platform attempted.
        step_reached: The last step reached in the signup flow.
        account: Created account credentials (if successful).
        error_message: Error message (if failed).
        duration_seconds: How long the signup took.
        timestamp: When the attempt was made.
    """

    success: bool = Field(..., description="Whether signup succeeded")
    platform: Platform = Field(..., description="Target platform")
    step_reached: SignupStep = Field(..., description="Last successful step")
    account: AccountCredentials | None = Field(default=None, description="Created account")
    error_message: str | None = Field(default=None, description="Error if failed")
    duration_seconds: float = Field(default=0.0, description="Signup duration")
    timestamp: datetime = Field(default_factory=datetime.now, description="Attempt timestamp")

    @property
    def summary(self) -> str:
        """Get a summary of the signup result."""
        status = "SUCCESS" if self.success else "FAILED"
        msg = f"[{status}] {self.platform} - Step: {self.step_reached}"
        if self.error_message:
            msg += f" - Error: {self.error_message}"
        return msg
