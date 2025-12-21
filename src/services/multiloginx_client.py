"""
MultiLoginX API Client
======================

Client for interacting with MultiLoginX API to manage browser profiles.
Supports quick profile creation, starting, and stopping profiles.

Authentication flow:
1. Sign in to https://api.multilogin.com/user/signin with MD5-hashed password
2. Use returned Bearer token for launcher API calls
"""

import asyncio
import hashlib
from dataclasses import dataclass
from typing import Optional

import aiohttp

from src.config import get_settings
from src.utils.logger import LoggerMixin
from src.utils.fingerprint import BrowserFingerprint


# MultiLoginX API endpoints
MLX_API_BASE = "https://api.multilogin.com"
MLX_LAUNCHER_BASE = "https://launcher.mlx.yt:45001"


@dataclass
class MultiLoginXProfile:
    """Represents a MultiLoginX browser profile."""

    id: str
    port: str
    browser_type: str
    core_version: int
    is_quick: bool = True

    @property
    def cdp_url(self) -> str:
        """Get the Chrome DevTools Protocol URL for this profile."""
        return f"http://127.0.0.1:{self.port}"

    @property
    def ws_endpoint(self) -> str:
        """Get the WebSocket endpoint for Playwright connection."""
        return f"ws://127.0.0.1:{self.port}"


class MultiLoginXClient(LoggerMixin):
    """
    Client for MultiLoginX API.

    Manages browser profiles through the MultiLoginX launcher API.
    Supports quick profile creation with custom fingerprints and proxy settings.

    Requires authentication via email/password to obtain Bearer token.
    """

    def __init__(
        self,
        base_url: str = "https://launcher.mlx.yt:45001",
        timeout: int = 60,
    ) -> None:
        """
        Initialize the MultiLoginX client.

        Args:
            base_url: Base URL for the MultiLoginX launcher API.
            timeout: Request timeout in seconds.
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.settings = get_settings()
        self._session: Optional[aiohttp.ClientSession] = None
        self._active_profiles: dict[str, MultiLoginXProfile] = {}
        self._token: Optional[str] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create an aiohttp session."""
        if self._session is None or self._session.closed:
            # Disable SSL verification for local launcher
            connector = aiohttp.TCPConnector(ssl=False)
            self._session = aiohttp.ClientSession(
                connector=connector,
                timeout=aiohttp.ClientTimeout(total=self.timeout),
            )
        return self._session

    async def close(self) -> None:
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    async def signin(self) -> str:
        """
        Sign in to MultiLoginX API and obtain Bearer token.

        Returns:
            Bearer token string.

        Raises:
            RuntimeError: If sign in fails.
        """
        session = await self._get_session()

        email = self.settings.multiloginx.email
        password = self.settings.multiloginx.password

        if not email or not password:
            raise RuntimeError(
                "MultiLoginX credentials not configured. "
                "Set MLX_EMAIL and MLX_PASSWORD in .env file."
            )

        # Password must be MD5 hashed
        password_hash = hashlib.md5(password.encode()).hexdigest()

        payload = {
            "email": email,
            "password": password_hash,
        }

        self.log.info(f"Signing in to MultiLoginX as {email}...")

        try:
            async with session.post(
                f"{MLX_API_BASE}/user/signin",
                json=payload,
                headers={"Accept": "application/json", "Content-Type": "application/json"},
            ) as response:
                data = await response.json()

                if response.status != 200:
                    error_msg = data.get("status", {}).get("message", data.get("message", "Unknown error"))
                    self.log.error(f"MultiLoginX signin failed: {error_msg}")
                    raise RuntimeError(f"MultiLoginX signin failed: {error_msg}")

                token = data.get("data", {}).get("token")
                if not token:
                    raise RuntimeError("No token received from MultiLoginX signin")

                self._token = token
                self.log.info("MultiLoginX signin successful, token obtained")
                return token

        except aiohttp.ClientError as e:
            self.log.error(f"Network error during signin: {e}")
            raise RuntimeError(f"Failed to connect to MultiLoginX API: {e}")

    async def _ensure_authenticated(self) -> None:
        """Ensure we have a valid authentication token."""
        if not self._token:
            await self.signin()

    def _get_auth_headers(self) -> dict:
        """Get headers with authentication token."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    async def create_quick_profile(
        self,
        fingerprint: Optional[BrowserFingerprint] = None,
        proxy_port: Optional[int] = None,
        country_iso: Optional[str] = None,
        start_url: Optional[str] = None,
        browser_type: str = "mimic",
        core_version: int = 132,
        os_type: str = "windows",
        is_headless: bool = False,
    ) -> MultiLoginXProfile:
        """
        Create and start a quick profile.

        Args:
            fingerprint: Browser fingerprint to use (optional).
            proxy_port: Proxy port to use (will use rotated port if not provided).
            country_iso: ISO country code for proxy targeting (e.g., "IL", "US").
            start_url: URL to open when profile starts.
            browser_type: Browser type ("mimic" for Chromium-based).
            core_version: Browser core version.
            os_type: Operating system type ("windows", "linux", "macos").
            is_headless: Whether to run in headless mode.

        Returns:
            MultiLoginXProfile with connection details.
        """
        # Ensure we have a valid authentication token
        await self._ensure_authenticated()

        session = await self._get_session()

        # Get proxy configuration
        proxy_settings = self.settings.proxy
        if proxy_port is None:
            proxy_port = proxy_settings.get_rotated_port()

        # Build the request payload
        payload = self._build_quick_profile_payload(
            fingerprint=fingerprint,
            proxy_port=proxy_port,
            country_iso=country_iso,
            start_url=start_url,
            browser_type=browser_type,
            core_version=core_version,
            os_type=os_type,
            is_headless=is_headless,
        )

        # Log proxy config for debugging (mask password)
        proxy_config = payload.get("parameters", {}).get("proxy", {})
        self.log.info(f"Creating quick profile with proxy:")
        self.log.info(f"  Host: {proxy_config.get('host')}")
        self.log.info(f"  Port: {proxy_config.get('port')}")
        self.log.info(f"  Type: {proxy_config.get('type')}")
        self.log.info(f"  Username: {proxy_config.get('username')}")
        pwd = proxy_config.get('password', '')
        self.log.info(f"  Password: {pwd[:3]}***{pwd[-3:] if len(pwd) > 3 else ''}")
        self.log.debug(f"Profile payload: {payload}")

        url = f"{self.base_url}/api/v3/profile/quick"

        try:
            async with session.post(
                url,
                json=payload,
                headers=self._get_auth_headers(),
            ) as response:
                response_text = await response.text()
                self.log.info(f"API Response status: {response.status}")
                self.log.info(f"API Response body: {response_text[:500]}")

                import json as json_lib
                try:
                    data = json_lib.loads(response_text)
                except Exception:
                    data = {"status": {"message": response_text}}

                if response.status != 200:
                    error_msg = data.get("status", {}).get("message", "Unknown error")
                    self.log.error(f"Failed to create profile: {error_msg}")
                    self.log.error(f"Full response: {data}")
                    raise RuntimeError(f"MultiLoginX error: {error_msg}")

                self.log.debug(f"Full API response data: {data}")

                profile_data = data.get("data", {})

                # Get the port - could be string or int
                port = profile_data.get("port", "")
                if not port:
                    self.log.error(f"No port in response! Profile data: {profile_data}")
                    raise RuntimeError("MultiLoginX did not return a port for the profile")

                profile = MultiLoginXProfile(
                    id=profile_data.get("id", ""),
                    port=str(port),  # Ensure it's a string
                    browser_type=profile_data.get("browser_type", browser_type),
                    core_version=profile_data.get("core_version", core_version) or 0,
                    is_quick=profile_data.get("is_quick", True),
                )

                self._active_profiles[profile.id] = profile

                self.log.info(f"Quick profile created: {profile.id}")
                self.log.info(f"  CDP Port: {profile.port}")
                self.log.info(f"  Browser: {profile.browser_type} v{profile.core_version}")

                return profile

        except aiohttp.ClientError as e:
            self.log.error(f"Network error creating profile: {e}")
            raise RuntimeError(f"Failed to connect to MultiLoginX: {e}")

    def _build_quick_profile_payload(
        self,
        fingerprint: Optional[BrowserFingerprint],
        proxy_port: int,
        country_iso: Optional[str],
        start_url: Optional[str],
        browser_type: str,
        core_version: int,
        os_type: str,
        is_headless: bool,
    ) -> dict:
        """Build the request payload for quick profile creation."""
        proxy_settings = self.settings.proxy

        # Get country-targeted username if country_iso is provided
        if country_iso:
            proxy_username = proxy_settings.get_country_targeted_username(country_iso)
        else:
            proxy_username = proxy_settings.username

        # Build payload with all required flags
        # Using "mask" for most flags so MultiLoginX generates fingerprint automatically
        payload = {
            "browser_type": browser_type,
            "os_type": os_type,
            "is_headless": is_headless,
            "automation": "playwright",
            "parameters": {
                "flags": {
                    # Required flags with default values
                    "audio_masking": "natural",
                    "fonts_masking": "mask",
                    "geolocation_masking": "mask",
                    "geolocation_popup": "prompt",
                    "graphics_masking": "mask",
                    "graphics_noise": "mask",
                    "localization_masking": "mask",
                    "media_devices_masking": "natural",
                    "navigator_masking": "mask",
                    "ports_masking": "mask",
                    "proxy_masking": "custom",  # custom because we provide proxy
                    "screen_masking": "mask",
                    "timezone_masking": "mask",
                    "webrtc_masking": "mask",
                },
                "fingerprint": {},  # Required but empty when using mask
                "storage": {},  # Required for parameters
                "proxy": {
                    "host": proxy_settings.host,
                    "type": "http",
                    "port": int(proxy_port),
                    "username": proxy_username,
                    "password": proxy_settings.password,
                },
            },
        }

        # Don't specify core_version - let MultiLoginX use latest automatically
        # API docs: "Defaults to latest. Cannot specify version older than 6 versions from current"
        # if core_version:
        #     payload["core_version"] = int(core_version)

        # Add custom fingerprint data if provided
        # Set corresponding flags to "custom" and provide all required fields
        if fingerprint:
            # Set flags to custom for the fields we're providing
            payload["parameters"]["flags"]["localization_masking"] = "custom"
            payload["parameters"]["flags"]["navigator_masking"] = "custom"
            payload["parameters"]["flags"]["screen_masking"] = "custom"
            payload["parameters"]["flags"]["timezone_masking"] = "custom"

            payload["parameters"]["fingerprint"] = {
                "navigator": {
                    "hardware_concurrency": 8,
                    "user_agent": fingerprint.user_agent,
                    "platform": "Win32" if "Windows" in fingerprint.user_agent else "MacIntel",
                    "os_cpu": "",
                },
                "localization": {
                    "languages": fingerprint.locale,
                    "locale": fingerprint.locale,
                    "accept_languages": fingerprint.extra_http_headers.get(
                        "Accept-Language", "en-US,en;q=0.9"
                    ),
                },
                "timezone": {
                    "zone": fingerprint.timezone_id,
                },
                "screen": {
                    "height": int(fingerprint.viewport_height),
                    "width": int(fingerprint.viewport_width),
                    "pixel_ratio": float(fingerprint.device_scale_factor),
                },
            }

        # Add start URLs if provided
        if start_url:
            payload["parameters"]["flags"]["startup_behavior"] = "custom"
            payload["parameters"]["custom_start_urls"] = [start_url]

        return payload

    async def stop_profile(self, profile_id: str) -> bool:
        """
        Stop a running profile.

        Args:
            profile_id: The profile ID to stop.

        Returns:
            True if successful, False otherwise.
        """
        await self._ensure_authenticated()
        session = await self._get_session()

        self.log.info(f"Stopping profile: {profile_id}")

        url = f"{self.base_url}/api/v1/profile/stop"

        try:
            async with session.get(
                url,
                params={"profile_id": profile_id},
                headers=self._get_auth_headers(),
            ) as response:
                # Handle non-JSON responses gracefully
                try:
                    data = await response.json()
                except Exception:
                    response_text = await response.text()
                    data = {"status": {"message": response_text}}

                if response.status == 200:
                    self.log.info(f"Profile stopped: {profile_id}")
                    if profile_id in self._active_profiles:
                        del self._active_profiles[profile_id]
                    return True
                else:
                    error_msg = data.get("status", {}).get("message", "Unknown error")
                    self.log.warning(f"Failed to stop profile {profile_id}: {error_msg}")
                    # Even if API returns error, the profile might already be stopped
                    if profile_id in self._active_profiles:
                        del self._active_profiles[profile_id]
                    return False

        except aiohttp.ClientError as e:
            self.log.error(f"Network error stopping profile: {e}")
            return False

    async def stop_all_profiles(self) -> None:
        """Stop all active profiles managed by this client."""
        profile_ids = list(self._active_profiles.keys())

        for profile_id in profile_ids:
            await self.stop_profile(profile_id)

        self.log.info(f"Stopped {len(profile_ids)} profiles")

    async def get_profile_status(self, profile_id: str) -> Optional[dict]:
        """
        Get the status of a profile.

        Args:
            profile_id: The profile ID to check.

        Returns:
            Status dict or None if not found.
        """
        session = await self._get_session()

        url = f"{self.base_url}/api/v1/profile/active"

        try:
            async with session.get(
                url,
                headers={"Accept": "application/json"},
            ) as response:
                data = await response.json()

                if response.status == 200:
                    profiles = data.get("data", [])
                    for profile in profiles:
                        if profile.get("uuid") == profile_id:
                            return profile
                return None

        except aiohttp.ClientError as e:
            self.log.error(f"Network error getting profile status: {e}")
            return None

    @property
    def active_profile_count(self) -> int:
        """Get the count of active profiles."""
        return len(self._active_profiles)

    def get_active_profile(self, profile_id: str) -> Optional[MultiLoginXProfile]:
        """Get an active profile by ID."""
        return self._active_profiles.get(profile_id)


# Singleton instance
_client: Optional[MultiLoginXClient] = None


def get_multiloginx_client() -> MultiLoginXClient:
    """Get or create the MultiLoginX client singleton."""
    global _client
    if _client is None:
        settings = get_settings()
        _client = MultiLoginXClient(
            base_url=settings.multiloginx.base_url,
            timeout=settings.multiloginx.timeout,
        )
    return _client


async def cleanup_multiloginx_client() -> None:
    """Cleanup the MultiLoginX client singleton."""
    global _client
    if _client is not None:
        await _client.stop_all_profiles()
        await _client.close()
        _client = None
