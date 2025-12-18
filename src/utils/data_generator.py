"""
Data Generator
==============

Generates realistic fake user data for signup operations
using the Faker library.
"""

import random
import string
from datetime import datetime, timedelta

from faker import Faker

from src.types.models import UserProfile
from src.utils.logger import LoggerMixin


class DataGenerator(LoggerMixin):
    """
    Generates fake user data for signup operations.

    Uses Faker to create realistic-looking names, emails,
    and other profile data.

    Attributes:
        faker: Faker instance for generating fake data.
        email_domains: List of email domains to use.
    """

    # Common email domains for generated addresses
    DEFAULT_EMAIL_DOMAINS = [
        "gmail.com",
        "yahoo.com",
        "outlook.com",
        "hotmail.com",
        "protonmail.com",
        "icloud.com",
    ]

    def __init__(
        self,
        locale: str = "en_US",
        email_domains: list[str] | None = None,
        seed: int | None = None,
    ) -> None:
        """
        Initialize the data generator.

        Args:
            locale: Faker locale for generating localized data.
            email_domains: Custom list of email domains to use.
            seed: Optional seed for reproducible generation.
        """
        self.faker = Faker(locale)
        self.email_domains = email_domains or self.DEFAULT_EMAIL_DOMAINS

        if seed is not None:
            Faker.seed(seed)
            random.seed(seed)

        self.log.debug(f"DataGenerator initialized with locale={locale}")

    def generate_profile(self) -> UserProfile:
        """
        Generate a complete user profile.

        Returns:
            UserProfile with randomly generated data.
        """
        first_name = self.faker.first_name()
        last_name = self.faker.last_name()
        email = self._generate_email(first_name, last_name)
        password = self._generate_password()
        birth_date = self._generate_birth_date()

        profile = UserProfile(
            first_name=first_name,
            last_name=last_name,
            email=email,
            password=password,
            birth_date=birth_date,
        )

        self.log.debug(f"Generated profile: {profile.full_name} <{profile.email}>")
        return profile

    def _generate_email(self, first_name: str, last_name: str) -> str:
        """
        Generate a realistic email address.

        Args:
            first_name: User's first name.
            last_name: User's last name.

        Returns:
            Generated email address.
        """
        domain = random.choice(self.email_domains)

        # Different email patterns
        patterns = [
            f"{first_name.lower()}.{last_name.lower()}",
            f"{first_name.lower()}{last_name.lower()}",
            f"{first_name.lower()}.{last_name.lower()}{random.randint(1, 99)}",
            f"{first_name.lower()}{random.randint(100, 999)}",
            f"{first_name[0].lower()}{last_name.lower()}{random.randint(1, 99)}",
        ]

        local_part = random.choice(patterns)
        # Remove any non-alphanumeric characters except dots
        local_part = "".join(c for c in local_part if c.isalnum() or c == ".")

        return f"{local_part}@{domain}"

    def _generate_password(self, length: int = 12) -> str:
        """
        Generate a secure password.

        Args:
            length: Minimum length of the password.

        Returns:
            Generated password meeting common requirements.
        """
        # Ensure password meets common requirements
        lowercase = random.choices(string.ascii_lowercase, k=length // 3)
        uppercase = random.choices(string.ascii_uppercase, k=length // 4)
        digits = random.choices(string.digits, k=length // 4)
        special = random.choices("!@#$%&*", k=2)

        # Combine and shuffle
        all_chars = lowercase + uppercase + digits + special
        random.shuffle(all_chars)

        password = "".join(all_chars)

        # Ensure minimum length
        while len(password) < length:
            password += random.choice(string.ascii_letters + string.digits)

        return password

    def _generate_birth_date(
        self,
        min_age: int = 18,
        max_age: int = 65,
    ) -> datetime:
        """
        Generate a realistic birth date.

        Args:
            min_age: Minimum age in years.
            max_age: Maximum age in years.

        Returns:
            Generated birth date.
        """
        today = datetime.now()
        min_date = today - timedelta(days=max_age * 365)
        max_date = today - timedelta(days=min_age * 365)

        # Random date between min and max
        days_range = (max_date - min_date).days
        random_days = random.randint(0, days_range)

        return min_date + timedelta(days=random_days)

    def generate_first_name(self) -> str:
        """Generate a random first name."""
        return self.faker.first_name()

    def generate_last_name(self) -> str:
        """Generate a random last name."""
        return self.faker.last_name()

    def generate_email(self) -> str:
        """Generate a random email address."""
        return self._generate_email(
            self.faker.first_name(),
            self.faker.last_name(),
        )

    def generate_password(self) -> str:
        """Generate a random secure password."""
        return self._generate_password()

    def generate_username(self, first_name: str | None = None) -> str:
        """
        Generate a username.

        Args:
            first_name: Optional first name to base username on.

        Returns:
            Generated username.
        """
        if first_name:
            base = first_name.lower()
        else:
            base = self.faker.first_name().lower()

        suffix = random.randint(100, 9999)
        return f"{base}{suffix}"
