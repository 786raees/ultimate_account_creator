"""
MultiLoginX Client
==================

Simple client for MultiLoginX quick profile management.
Creates one-time quick browser profiles and connects via CDP.
"""

import hashlib
import httpx
from dataclasses import dataclass
from typing import Optional

from src.utils.logger import LoggerMixin


@dataclass
class QuickProfileResult:
    """Result from creating a quick profile."""

    success: bool
    profile_id: Optional[str] = None
    port: Optional[int] = None
    error: Optional[str] = None

    @property
    def cdp_url(self) -> str:
        """Get the Chrome DevTools Protocol URL for Playwright connection."""
        if not self.port:
            raise ValueError("No port available - profile not started")
        return f"http://127.0.0.1:{self.port}"


class MultiLoginXClient(LoggerMixin):
    """
    Client for MultiLoginX quick profile API.

    Uses the /api/v3/profile/quick endpoint to create temporary browser
    profiles with anti-fingerprint protection.
    """

    def __init__(
        self,
        base_url: str = "https://launcher.mlx.yt:45001",
        api_url: str = "https://api.multilogin.com",
        email: str = "",
        password: str = "",
        timeout: int = 60,
    ) -> None:
        """
        Initialize the MLX client.

        Args:
            base_url: MultiLoginX launcher API URL.
            api_url: MultiLoginX main API URL for authentication.
            email: Account email for authentication.
            password: Account password (will be MD5 hashed if not already).
            timeout: Request timeout in seconds.
        """
        self.base_url = base_url.rstrip("/")
        self.api_url = api_url.rstrip("/")
        self.email = email
        self.password = password
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
        self._token: Optional[str] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                verify=False,  # MLX uses self-signed cert
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
        self._token = None

    def _hash_password(self, password: str) -> str:
        """
        Hash password with MD5 if not already hashed.

        MLX expects MD5 hashed passwords. If the password looks like
        an MD5 hash (32 hex chars), return as-is.
        """
        # Check if already MD5 hashed (32 hex characters)
        if len(password) == 32 and all(c in '0123456789abcdef' for c in password.lower()):
            return password.lower()
        # Hash it
        return hashlib.md5(password.encode()).hexdigest()

    async def authenticate(self) -> bool:
        """
        Authenticate with MultiLoginX to get a bearer token.

        Returns:
            True if authentication was successful.
        """
        if not self.email or not self.password:
            self.log.error("MLX credentials not configured (MLX_EMAIL and MLX_PASSWORD)")
            return False

        url = f"{self.api_url}/user/signin"

        # Hash password if needed
        hashed_password = self._hash_password(self.password)

        body = {
            "email": self.email,
            "password": hashed_password,
        }

        self.log.info(f"Authenticating with MLX as: {self.email}")

        try:
            client = await self._get_client()
            response = await client.post(
                url,
                json=body,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
            )

            data = response.json()

            if response.status_code == 200 and data.get("data", {}).get("token"):
                self._token = data["data"]["token"]
                self.log.info("MLX authentication successful!")
                return True
            else:
                error_msg = data.get("message", str(data))
                self.log.error(f"MLX authentication failed: {error_msg}")
                return False

        except Exception as e:
            self.log.error(f"MLX authentication error: {e}")
            return False

    async def _ensure_authenticated(self) -> bool:
        """Ensure we have a valid token, authenticating if needed."""
        if self._token:
            return True
        return await self.authenticate()

    async def create_quick_profile(
        self,
        browser_type: str = "mimic",
        os_type: str = "windows",
        core_version: int = 132,
        is_headless: bool = False,
        proxy: Optional[dict] = None,
        automation: str = "playwright",
    ) -> QuickProfileResult:
        """
        Create and start a quick browser profile.

        Args:
            browser_type: Browser type ("mimic" for Chromium, "stealthfox" for Firefox).
            os_type: Operating system ("windows", "linux", "macos").
            core_version: Browser core version.
            is_headless: Run browser in headless mode.
            proxy: Optional proxy configuration dict with keys:
                   host, type, port, username, password.
            automation: Automation type ("playwright" or "selenium").

        Returns:
            QuickProfileResult with profile_id and CDP port on success.
        """
        # Ensure we're authenticated
        if not await self._ensure_authenticated():
            return QuickProfileResult(
                success=False,
                error="Authentication failed - check MLX_EMAIL and MLX_PASSWORD"
            )

        url = f"{self.base_url}/api/v3/profile/quick"

        # Build the request body with mask flags (not custom)
        # Using mask avoids having to specify all fingerprint params
        body = {
            "browser_type": browser_type,
            "os_type": os_type,
            "automation": automation,
            "is_headless": is_headless,
            "core_version": core_version,
            "parameters": {
                "flags": {
                    "audio_masking": "natural",
                    "fonts_masking": "mask",
                    "geolocation_masking": "mask",
                    "geolocation_popup": "allow",
                    "graphics_masking": "mask",
                    "graphics_noise": "mask",
                    "localization_masking": "mask",
                    "media_devices_masking": "natural",
                    "navigator_masking": "mask",
                    "ports_masking": "mask",
                    "proxy_masking": "custom" if proxy else "disabled",
                    "screen_masking": "mask",
                    "timezone_masking": "mask",
                    "webrtc_masking": "mask",
                    "canvas_noise": "mask",
                },
                "fingerprint": {},
                "storage": {},
            }
        }

        # Add proxy if provided
        if proxy:
            body["parameters"]["proxy"] = {
                "host": proxy.get("host", ""),
                "type": proxy.get("type", "http"),
                "port": proxy.get("port", 0),
                "username": proxy.get("username", ""),
                "password": proxy.get("password", ""),
            }

        self.log.info(f"Creating quick profile: {browser_type}/{os_type}")
        if proxy:
            self.log.info(f"  Proxy: {proxy.get('host')}:{proxy.get('port')}")

        try:
            client = await self._get_client()
            response = await client.post(
                url,
                json=body,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "Authorization": f"Bearer {self._token}",
                },
            )

            data = response.json()
            self.log.info(f"MLX response status: {response.status_code}")
            self.log.info(f"MLX response data: {data}")

            # Handle different response formats from MLX API
            # The API can return data in various structures

            status = data.get("status", {})
            status_ok = status.get("ok", False)
            status_message = status.get("message", "")

            # Try multiple locations for profile data
            result_data = data.get("data", {})

            # Profile ID might be in different keys
            profile_id = (
                result_data.get("id") or
                result_data.get("profile_id") or
                result_data.get("profileId") or
                data.get("id") or
                data.get("profile_id")
            )

            # Port might be in different keys
            port = (
                result_data.get("port") or
                result_data.get("browserPort") or
                result_data.get("browser_port") or
                data.get("port")
            )

            # Check for success: either we have port, or status says ok with success message
            is_success = (
                port is not None or
                (status_ok and "success" in status_message.lower())
            )

            if is_success and port:
                self.log.info(f"Quick profile created successfully!")
                self.log.info(f"  Profile ID: {profile_id}")
                self.log.info(f"  CDP Port: {port}")

                return QuickProfileResult(
                    success=True,
                    profile_id=profile_id,
                    port=port,
                )
            elif is_success and not port:
                # Success message but no port - need to extract from response
                self.log.warning(f"Profile started but port not found in response")
                self.log.warning(f"Full response: {data}")
                error_msg = f"Port not found in response. Full data: {data}"
                return QuickProfileResult(success=False, error=error_msg)
            else:
                error_msg = status_message or str(data)
                self.log.error(f"Failed to create profile: {error_msg}")
                return QuickProfileResult(success=False, error=error_msg)

        except httpx.TimeoutException:
            self.log.error(f"Timeout creating profile (>{self.timeout}s)")
            return QuickProfileResult(success=False, error="Request timeout")
        except Exception as e:
            self.log.error(f"Error creating profile: {e}")
            return QuickProfileResult(success=False, error=str(e))

    async def stop_profile(self, profile_id: str) -> bool:
        """
        Stop a running profile.

        Args:
            profile_id: The profile ID to stop.

        Returns:
            True if stopped successfully, False otherwise.
        """
        url = f"{self.base_url}/api/v1/profile/stop"

        self.log.info(f"Stopping profile: {profile_id}")

        try:
            client = await self._get_client()

            headers = {"Accept": "application/json"}
            if self._token:
                headers["Authorization"] = f"Bearer {self._token}"

            response = await client.get(
                url,
                params={"profile_id": profile_id},
                headers=headers,
            )

            # Try to parse JSON, but handle non-JSON responses gracefully
            try:
                data = response.json()
            except Exception:
                # Some stop responses may not be JSON
                if response.status_code == 200:
                    self.log.info(f"Profile stopped successfully")
                    return True
                self.log.warning(f"Non-JSON response: {response.text[:200]}")
                return False

            if response.status_code == 200 and data.get("status", {}).get("ok"):
                self.log.info(f"Profile stopped successfully")
                return True
            else:
                error_msg = data.get("status", {}).get("message", str(data))
                self.log.warning(f"Failed to stop profile: {error_msg}")
                return False

        except Exception as e:
            self.log.warning(f"Error stopping profile: {e}")
            return False
