"""
Browser Fingerprint Randomization
=================================

Generates randomized browser fingerprints to avoid detection.
Includes user agent, viewport, timezone, locale, and other browser properties.

Supports country-based fingerprint matching to ensure the fingerprint
matches the phone number's country for consistent profiles.
"""

import random
import re
from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING

from src.utils.logger import get_logger

if TYPE_CHECKING:
    from src.utils.country_profiles import CountryProfile


@dataclass
class BrowserFingerprint:
    """Represents a randomized browser fingerprint."""

    user_agent: str
    viewport_width: int
    viewport_height: int
    device_scale_factor: float
    timezone_id: str
    locale: str
    color_scheme: str
    reduced_motion: str
    has_touch: bool
    is_mobile: bool
    extra_http_headers: dict = field(default_factory=dict)

    # Country profile info (optional)
    country_code: Optional[str] = None
    country_name: Optional[str] = None

    @property
    def viewport(self) -> dict:
        """Get viewport configuration for Playwright."""
        return {
            "width": self.viewport_width,
            "height": self.viewport_height,
        }

    @property
    def context_options(self) -> dict:
        """Get full context options for Playwright."""
        return {
            "user_agent": self.user_agent,
            "viewport": self.viewport,
            "device_scale_factor": self.device_scale_factor,
            "timezone_id": self.timezone_id,
            "locale": self.locale,
            "color_scheme": self.color_scheme,
            "reduced_motion": self.reduced_motion,
            "has_touch": self.has_touch,
            "is_mobile": self.is_mobile,
            "extra_http_headers": self.extra_http_headers,
        }


class FingerprintGenerator:
    """
    Generates randomized browser fingerprints.

    Creates realistic browser fingerprints by combining various
    parameters like user agents, viewports, timezones, etc.
    """

    # Chrome user agents for Windows (most common)
    CHROME_USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    ]

    # Chrome user agents for macOS
    CHROME_MAC_USER_AGENTS = [
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    ]

    # Fixed 5K viewport for maximum resolution
    DESKTOP_VIEWPORTS = [
        (5120, 2880),  # 5K resolution - maximized display
    ]

    # Common timezones (weighted towards US/EU for Airbnb)
    TIMEZONES = [
        "America/New_York",
        "America/Chicago",
        "America/Denver",
        "America/Los_Angeles",
        "America/Phoenix",
        "America/Toronto",
        "Europe/London",
        "Europe/Paris",
        "Europe/Berlin",
        "Europe/Madrid",
        "Europe/Rome",
        "Europe/Amsterdam",
        "Australia/Sydney",
        "Asia/Tokyo",
        "Asia/Singapore",
    ]

    # Locales matching timezones
    LOCALES = [
        "en-US",
        "en-GB",
        "en-CA",
        "en-AU",
        "de-DE",
        "fr-FR",
        "es-ES",
        "it-IT",
        "nl-NL",
        "pt-BR",
    ]

    # Accept-Language headers
    ACCEPT_LANGUAGES = [
        "en-US,en;q=0.9",
        "en-GB,en;q=0.9,en-US;q=0.8",
        "en-US,en;q=0.9,es;q=0.8",
        "en-US,en;q=0.9,fr;q=0.8",
        "en-US,en;q=0.9,de;q=0.8",
        "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
        "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
        "es-ES,es;q=0.9,en-US;q=0.8,en;q=0.7",
    ]

    def __init__(self, seed: Optional[int] = None):
        """
        Initialize the fingerprint generator.

        Args:
            seed: Optional random seed for reproducibility.
        """
        self.log = get_logger("FingerprintGenerator")
        if seed is not None:
            random.seed(seed)

    def generate(self, platform: str = "windows") -> BrowserFingerprint:
        """
        Generate a randomized browser fingerprint.

        Args:
            platform: Target platform ('windows', 'mac', or 'random').

        Returns:
            BrowserFingerprint with randomized values.
        """
        # Select platform
        if platform == "random":
            platform = random.choice(["windows", "mac"])

        # Select user agent based on platform
        if platform == "mac":
            user_agent = random.choice(self.CHROME_MAC_USER_AGENTS)
        else:
            user_agent = random.choice(self.CHROME_USER_AGENTS)

        # Use fixed Full HD viewport (1920x1080)
        viewport = self.DESKTOP_VIEWPORTS[0]
        width = viewport[0]
        height = viewport[1]

        # Select timezone and matching locale
        timezone = random.choice(self.TIMEZONES)
        locale = self._get_locale_for_timezone(timezone)

        # Select accept-language header
        accept_language = random.choice(self.ACCEPT_LANGUAGES)

        # Device scale factor (most common is 1.0 or 1.25)
        device_scale_factor = random.choice([1.0, 1.0, 1.0, 1.25, 1.5])

        fingerprint = BrowserFingerprint(
            user_agent=user_agent,
            viewport_width=width,
            viewport_height=height,
            device_scale_factor=device_scale_factor,
            timezone_id=timezone,
            locale=locale,
            color_scheme=random.choice(["light", "light", "light", "dark"]),  # Most use light
            reduced_motion=random.choice(["no-preference", "no-preference", "reduce"]),
            has_touch=False,  # Desktop doesn't have touch
            is_mobile=False,
            extra_http_headers={
                "Accept-Language": accept_language,
                "sec-ch-ua": self._generate_sec_ch_ua(user_agent),
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"Windows"' if platform == "windows" else '"macOS"',
            },
        )

        self.log.debug(f"Generated fingerprint: {viewport[0]}x{viewport[1]}, {timezone}")
        return fingerprint

    def _get_locale_for_timezone(self, timezone: str) -> str:
        """Get an appropriate locale for a timezone."""
        timezone_locale_map = {
            "America/New_York": "en-US",
            "America/Chicago": "en-US",
            "America/Denver": "en-US",
            "America/Los_Angeles": "en-US",
            "America/Phoenix": "en-US",
            "America/Toronto": "en-CA",
            "Europe/London": "en-GB",
            "Europe/Paris": "fr-FR",
            "Europe/Berlin": "de-DE",
            "Europe/Madrid": "es-ES",
            "Europe/Rome": "it-IT",
            "Europe/Amsterdam": "nl-NL",
            "Australia/Sydney": "en-AU",
            "Asia/Tokyo": "en-US",  # Many English speakers
            "Asia/Singapore": "en-US",
        }
        return timezone_locale_map.get(timezone, "en-US")

    def _generate_sec_ch_ua(self, user_agent: str) -> str:
        """Generate sec-ch-ua header based on user agent."""
        # Extract Chrome version from user agent
        match = re.search(r"Chrome/(\d+)", user_agent)
        if match:
            version = match.group(1)
            return f'"Google Chrome";v="{version}", "Chromium";v="{version}", "Not_A Brand";v="24"'
        return '"Google Chrome";v="120", "Chromium";v="120", "Not_A Brand";v="24"'

    def generate_for_phone(self, phone_number: str, platform: str = "windows") -> BrowserFingerprint:
        """
        Generate a fingerprint matching a phone number's country.

        Args:
            phone_number: Phone number with country code (e.g., "+380969200145").
            platform: Target platform ('windows', 'mac', or 'random').

        Returns:
            BrowserFingerprint matching the phone's country.
        """
        from src.utils.country_profiles import get_profile_for_phone

        profile = get_profile_for_phone(phone_number)
        return self.generate_for_country_profile(profile, platform)

    def generate_for_country_profile(
        self,
        profile: "CountryProfile",
        platform: str = "windows",
    ) -> BrowserFingerprint:
        """
        Generate a fingerprint matching a specific country profile.

        Args:
            profile: CountryProfile to match.
            platform: Target platform ('windows', 'mac', or 'random').

        Returns:
            BrowserFingerprint matching the country.
        """
        self.log.info(f"Generating fingerprint for {profile.country_name} (+{profile.country_code})")

        # Select platform
        if platform == "random":
            platform = random.choice(["windows", "mac"])

        # Select user agent based on platform
        if platform == "mac":
            user_agent = random.choice(self.CHROME_MAC_USER_AGENTS)
        else:
            user_agent = random.choice(self.CHROME_USER_AGENTS)

        # Use fixed Full HD viewport (1920x1080)
        viewport = self.DESKTOP_VIEWPORTS[0]
        width = viewport[0]
        height = viewport[1]

        # Get country-specific values from profile
        timezone = profile.get_random_timezone()
        locale = profile.get_random_locale()
        accept_language = profile.get_random_accept_language()

        # Device scale factor
        device_scale_factor = random.choice([1.0, 1.0, 1.0, 1.25, 1.5])

        fingerprint = BrowserFingerprint(
            user_agent=user_agent,
            viewport_width=width,
            viewport_height=height,
            device_scale_factor=device_scale_factor,
            timezone_id=timezone,
            locale=locale,
            color_scheme=random.choice(["light", "light", "light", "dark"]),
            reduced_motion=random.choice(["no-preference", "no-preference", "reduce"]),
            has_touch=False,
            is_mobile=False,
            extra_http_headers={
                "Accept-Language": accept_language,
                "sec-ch-ua": self._generate_sec_ch_ua(user_agent),
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"Windows"' if platform == "windows" else '"macOS"',
            },
            country_code=profile.country_code,
            country_name=profile.country_name,
        )

        self.log.info(f"  Fingerprint: {width}x{height}, {timezone}, {locale}")
        return fingerprint


# Singleton instance for convenience
_generator: Optional[FingerprintGenerator] = None


def get_fingerprint_generator() -> FingerprintGenerator:
    """Get or create the fingerprint generator instance."""
    global _generator
    if _generator is None:
        _generator = FingerprintGenerator()
    return _generator


def generate_fingerprint(platform: str = "windows") -> BrowserFingerprint:
    """Generate a random browser fingerprint."""
    return get_fingerprint_generator().generate(platform)


def generate_fingerprint_for_phone(
    phone_number: str,
    platform: str = "windows",
) -> BrowserFingerprint:
    """
    Generate a browser fingerprint matching a phone number's country.

    Args:
        phone_number: Phone number with country code (e.g., "+380969200145").
        platform: Target platform ('windows', 'mac', or 'random').

    Returns:
        BrowserFingerprint matching the phone's country.
    """
    return get_fingerprint_generator().generate_for_phone(phone_number, platform)
