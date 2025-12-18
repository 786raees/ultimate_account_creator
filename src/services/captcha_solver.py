"""
CAPTCHA Solving Service Integration
====================================

Integrates with various CAPTCHA solving services to handle
challenges during automation. Supports multiple providers.

Recommended Services for Arkose Labs (Airbnb):
- 2Captcha: https://2captcha.com - ~$3/1000 solves
- CapSolver: https://capsolver.com - ~$2.5/1000 solves
"""

import asyncio
import aiohttp
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from enum import Enum

from src.utils.logger import get_logger


class CaptchaType(str, Enum):
    """Supported CAPTCHA types."""
    RECAPTCHA_V2 = "recaptcha_v2"
    RECAPTCHA_V3 = "recaptcha_v3"
    HCAPTCHA = "hcaptcha"
    FUNCAPTCHA = "funcaptcha"  # Arkose Labs
    IMAGE_TO_TEXT = "image_to_text"


class CaptchaSolverBase(ABC):
    """Abstract base class for CAPTCHA solvers."""

    def __init__(self, api_key: str):
        """
        Initialize the CAPTCHA solver.

        Args:
            api_key: API key for the service.
        """
        self.api_key = api_key
        self.log = get_logger(self.__class__.__name__)

    @abstractmethod
    async def solve_funcaptcha(
        self,
        public_key: str,
        service_url: str,
        page_url: str,
        **kwargs,
    ) -> Optional[str]:
        """
        Solve an Arkose Labs FunCaptcha.

        Args:
            public_key: The public key for the captcha.
            service_url: The Arkose service URL.
            page_url: URL of the page with the captcha.

        Returns:
            Solution token or None if failed.
        """
        pass

    @abstractmethod
    async def solve_recaptcha_v2(
        self,
        site_key: str,
        page_url: str,
        **kwargs,
    ) -> Optional[str]:
        """
        Solve a reCAPTCHA v2.

        Args:
            site_key: The site key for the captcha.
            page_url: URL of the page with the captcha.

        Returns:
            Solution token or None if failed.
        """
        pass

    @abstractmethod
    async def get_balance(self) -> float:
        """Get account balance."""
        pass


class TwoCaptchaSolver(CaptchaSolverBase):
    """
    2Captcha.com integration.

    Supports FunCaptcha (Arkose Labs), reCAPTCHA, hCaptcha, and more.
    Pricing: ~$3 per 1000 solves for FunCaptcha.

    Sign up: https://2captcha.com
    """

    BASE_URL = "https://2captcha.com"

    async def solve_funcaptcha(
        self,
        public_key: str,
        service_url: str,
        page_url: str,
        timeout: int = 120,
        **kwargs,
    ) -> Optional[str]:
        """
        Solve Arkose Labs FunCaptcha using 2Captcha.

        Args:
            public_key: Arkose public key (e.g., 2F0D6CB5-ACAC-4EA9-9B2A-A5F90A2DF15E).
            service_url: Arkose service URL (e.g., https://airbnb-api.arkoselabs.com).
            page_url: URL of the page with the captcha.
            timeout: Maximum time to wait for solution in seconds.

        Returns:
            Solution token or None if failed.
        """
        self.log.info(f"Solving FunCaptcha for {page_url}")

        try:
            async with aiohttp.ClientSession() as session:
                # Submit captcha task
                submit_data = {
                    "key": self.api_key,
                    "method": "funcaptcha",
                    "publickey": public_key,
                    "surl": service_url,
                    "pageurl": page_url,
                    "json": 1,
                }

                async with session.post(
                    f"{self.BASE_URL}/in.php",
                    data=submit_data,
                ) as resp:
                    result = await resp.json()

                if result.get("status") != 1:
                    self.log.error(f"Failed to submit captcha: {result}")
                    return None

                task_id = result["request"]
                self.log.debug(f"Captcha task submitted: {task_id}")

                # Poll for result
                start_time = asyncio.get_event_loop().time()
                while asyncio.get_event_loop().time() - start_time < timeout:
                    await asyncio.sleep(5)  # Poll every 5 seconds

                    async with session.get(
                        f"{self.BASE_URL}/res.php",
                        params={
                            "key": self.api_key,
                            "action": "get",
                            "id": task_id,
                            "json": 1,
                        },
                    ) as resp:
                        result = await resp.json()

                    if result.get("status") == 1:
                        token = result["request"]
                        self.log.info("FunCaptcha solved successfully")
                        return token
                    elif result.get("request") == "CAPCHA_NOT_READY":
                        continue
                    else:
                        self.log.error(f"Captcha solving failed: {result}")
                        return None

                self.log.error("Captcha solving timeout")
                return None

        except Exception as e:
            self.log.error(f"Error solving FunCaptcha: {e}")
            return None

    async def solve_recaptcha_v2(
        self,
        site_key: str,
        page_url: str,
        timeout: int = 120,
        **kwargs,
    ) -> Optional[str]:
        """Solve reCAPTCHA v2 using 2Captcha."""
        self.log.info(f"Solving reCAPTCHA v2 for {page_url}")

        try:
            async with aiohttp.ClientSession() as session:
                # Submit captcha task
                submit_data = {
                    "key": self.api_key,
                    "method": "userrecaptcha",
                    "googlekey": site_key,
                    "pageurl": page_url,
                    "json": 1,
                }

                async with session.post(
                    f"{self.BASE_URL}/in.php",
                    data=submit_data,
                ) as resp:
                    result = await resp.json()

                if result.get("status") != 1:
                    self.log.error(f"Failed to submit captcha: {result}")
                    return None

                task_id = result["request"]

                # Poll for result
                start_time = asyncio.get_event_loop().time()
                while asyncio.get_event_loop().time() - start_time < timeout:
                    await asyncio.sleep(5)

                    async with session.get(
                        f"{self.BASE_URL}/res.php",
                        params={
                            "key": self.api_key,
                            "action": "get",
                            "id": task_id,
                            "json": 1,
                        },
                    ) as resp:
                        result = await resp.json()

                    if result.get("status") == 1:
                        return result["request"]
                    elif result.get("request") == "CAPCHA_NOT_READY":
                        continue
                    else:
                        return None

                return None

        except Exception as e:
            self.log.error(f"Error solving reCAPTCHA: {e}")
            return None

    async def get_balance(self) -> float:
        """Get 2Captcha account balance."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.BASE_URL}/res.php",
                    params={
                        "key": self.api_key,
                        "action": "getbalance",
                        "json": 1,
                    },
                ) as resp:
                    result = await resp.json()
                    if result.get("status") == 1:
                        return float(result["request"])
                    return 0.0
        except Exception:
            return 0.0


class CapSolverSolver(CaptchaSolverBase):
    """
    CapSolver.com integration.

    Modern API with good Arkose Labs support.
    Pricing: ~$2.5 per 1000 solves for FunCaptcha.

    Sign up: https://capsolver.com
    """

    BASE_URL = "https://api.capsolver.com"

    async def solve_funcaptcha(
        self,
        public_key: str,
        service_url: str,
        page_url: str,
        timeout: int = 120,
        **kwargs,
    ) -> Optional[str]:
        """
        Solve Arkose Labs FunCaptcha using CapSolver.

        Args:
            public_key: Arkose public key.
            service_url: Arkose service URL.
            page_url: URL of the page with the captcha.
            timeout: Maximum time to wait for solution in seconds.

        Returns:
            Solution token or None if failed.
        """
        self.log.info(f"Solving FunCaptcha via CapSolver for {page_url}")

        try:
            async with aiohttp.ClientSession() as session:
                # Create task
                task_data = {
                    "clientKey": self.api_key,
                    "task": {
                        "type": "FunCaptchaTaskProxyLess",
                        "websiteURL": page_url,
                        "websitePublicKey": public_key,
                        "funcaptchaApiJSSubdomain": service_url.replace("https://", "").replace("http://", ""),
                    },
                }

                async with session.post(
                    f"{self.BASE_URL}/createTask",
                    json=task_data,
                ) as resp:
                    result = await resp.json()

                if result.get("errorId") != 0:
                    self.log.error(f"Failed to create task: {result}")
                    return None

                task_id = result["taskId"]
                self.log.debug(f"Task created: {task_id}")

                # Poll for result
                start_time = asyncio.get_event_loop().time()
                while asyncio.get_event_loop().time() - start_time < timeout:
                    await asyncio.sleep(3)

                    async with session.post(
                        f"{self.BASE_URL}/getTaskResult",
                        json={
                            "clientKey": self.api_key,
                            "taskId": task_id,
                        },
                    ) as resp:
                        result = await resp.json()

                    if result.get("status") == "ready":
                        token = result.get("solution", {}).get("token")
                        if token:
                            self.log.info("FunCaptcha solved successfully")
                            return token
                    elif result.get("status") == "processing":
                        continue
                    else:
                        self.log.error(f"Task failed: {result}")
                        return None

                self.log.error("Captcha solving timeout")
                return None

        except Exception as e:
            self.log.error(f"Error solving FunCaptcha: {e}")
            return None

    async def solve_recaptcha_v2(
        self,
        site_key: str,
        page_url: str,
        timeout: int = 120,
        **kwargs,
    ) -> Optional[str]:
        """Solve reCAPTCHA v2 using CapSolver."""
        self.log.info(f"Solving reCAPTCHA v2 via CapSolver")

        try:
            async with aiohttp.ClientSession() as session:
                task_data = {
                    "clientKey": self.api_key,
                    "task": {
                        "type": "ReCaptchaV2TaskProxyLess",
                        "websiteURL": page_url,
                        "websiteKey": site_key,
                    },
                }

                async with session.post(
                    f"{self.BASE_URL}/createTask",
                    json=task_data,
                ) as resp:
                    result = await resp.json()

                if result.get("errorId") != 0:
                    return None

                task_id = result["taskId"]

                start_time = asyncio.get_event_loop().time()
                while asyncio.get_event_loop().time() - start_time < timeout:
                    await asyncio.sleep(3)

                    async with session.post(
                        f"{self.BASE_URL}/getTaskResult",
                        json={
                            "clientKey": self.api_key,
                            "taskId": task_id,
                        },
                    ) as resp:
                        result = await resp.json()

                    if result.get("status") == "ready":
                        return result.get("solution", {}).get("gRecaptchaResponse")
                    elif result.get("status") == "processing":
                        continue
                    else:
                        return None

                return None

        except Exception as e:
            self.log.error(f"Error solving reCAPTCHA: {e}")
            return None

    async def get_balance(self) -> float:
        """Get CapSolver account balance."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.BASE_URL}/getBalance",
                    json={"clientKey": self.api_key},
                ) as resp:
                    result = await resp.json()
                    if result.get("errorId") == 0:
                        return float(result.get("balance", 0))
                    return 0.0
        except Exception:
            return 0.0


class CaptchaSolverService:
    """
    High-level CAPTCHA solving service.

    Provides a unified interface for solving various CAPTCHA types
    using configurable backend services.
    """

    # Arkose Labs public key for Airbnb (extracted from their site)
    AIRBNB_ARKOSE_PUBLIC_KEY = "2F0D6CB5-ACAC-4EA9-9B2A-A5F90A2DF15E"
    AIRBNB_ARKOSE_SERVICE_URL = "https://airbnb-api.arkoselabs.com"

    def __init__(
        self,
        provider: str = "2captcha",
        api_key: Optional[str] = None,
    ):
        """
        Initialize the CAPTCHA solving service.

        Args:
            provider: Service provider ('2captcha' or 'capsolver').
            api_key: API key for the service.
        """
        self.log = get_logger("CaptchaSolverService")
        self.provider = provider
        self.api_key = api_key
        self._solver: Optional[CaptchaSolverBase] = None

        if api_key:
            self._init_solver()

    def _init_solver(self) -> None:
        """Initialize the appropriate solver backend."""
        if self.provider == "2captcha":
            self._solver = TwoCaptchaSolver(self.api_key)
        elif self.provider == "capsolver":
            self._solver = CapSolverSolver(self.api_key)
        else:
            raise ValueError(f"Unknown CAPTCHA provider: {self.provider}")

        self.log.info(f"Initialized {self.provider} CAPTCHA solver")

    def configure(self, provider: str, api_key: str) -> None:
        """
        Configure the CAPTCHA solver.

        Args:
            provider: Service provider.
            api_key: API key.
        """
        self.provider = provider
        self.api_key = api_key
        self._init_solver()

    @property
    def is_configured(self) -> bool:
        """Check if the solver is configured."""
        return self._solver is not None

    async def solve_airbnb_captcha(self, page_url: str) -> Optional[str]:
        """
        Solve Airbnb's Arkose Labs CAPTCHA.

        Args:
            page_url: Current page URL.

        Returns:
            Solution token or None if failed.
        """
        if not self._solver:
            self.log.error("CAPTCHA solver not configured")
            return None

        return await self._solver.solve_funcaptcha(
            public_key=self.AIRBNB_ARKOSE_PUBLIC_KEY,
            service_url=self.AIRBNB_ARKOSE_SERVICE_URL,
            page_url=page_url,
        )

    async def solve_funcaptcha(
        self,
        public_key: str,
        service_url: str,
        page_url: str,
    ) -> Optional[str]:
        """
        Solve a FunCaptcha/Arkose Labs challenge.

        Args:
            public_key: Arkose public key.
            service_url: Arkose service URL.
            page_url: Page URL with the captcha.

        Returns:
            Solution token or None.
        """
        if not self._solver:
            self.log.error("CAPTCHA solver not configured")
            return None

        return await self._solver.solve_funcaptcha(
            public_key=public_key,
            service_url=service_url,
            page_url=page_url,
        )

    async def solve_recaptcha_v2(
        self,
        site_key: str,
        page_url: str,
    ) -> Optional[str]:
        """
        Solve a reCAPTCHA v2 challenge.

        Args:
            site_key: reCAPTCHA site key.
            page_url: Page URL with the captcha.

        Returns:
            Solution token or None.
        """
        if not self._solver:
            self.log.error("CAPTCHA solver not configured")
            return None

        return await self._solver.solve_recaptcha_v2(
            site_key=site_key,
            page_url=page_url,
        )

    async def get_balance(self) -> float:
        """Get account balance from the service."""
        if not self._solver:
            return 0.0
        return await self._solver.get_balance()

    async def check_service(self) -> Dict[str, Any]:
        """
        Check if the CAPTCHA service is working.

        Returns:
            Dict with status and balance information.
        """
        if not self._solver:
            return {"status": "not_configured", "balance": 0.0}

        balance = await self.get_balance()
        return {
            "status": "ok" if balance > 0 else "low_balance",
            "provider": self.provider,
            "balance": balance,
        }


# Singleton instance
_captcha_service: Optional[CaptchaSolverService] = None


def get_captcha_service() -> CaptchaSolverService:
    """Get or create the CAPTCHA solver service instance."""
    global _captcha_service
    if _captcha_service is None:
        _captcha_service = CaptchaSolverService()
    return _captcha_service


def configure_captcha_service(provider: str, api_key: str) -> CaptchaSolverService:
    """
    Configure the CAPTCHA solver service.

    Args:
        provider: Service provider ('2captcha' or 'capsolver').
        api_key: API key for the service.

    Returns:
        Configured CaptchaSolverService instance.
    """
    service = get_captcha_service()
    service.configure(provider, api_key)
    return service
