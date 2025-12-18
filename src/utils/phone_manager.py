"""
Phone Number Manager
====================

Manages phone numbers for signup operations including:
- Loading phone lists from files
- Tracking used/available numbers
- Persisting usage state
"""

import json
from datetime import datetime
from pathlib import Path

import aiofiles

from src.types.enums import Platform
from src.types.models import PhoneNumber
from src.utils.logger import LoggerMixin


class PhoneManager(LoggerMixin):
    """
    Manages phone numbers for signup operations.

    Handles loading phone lists, tracking usage, and persisting
    state to prevent reuse of phone numbers.

    Attributes:
        phone_list_path: Path to the phone numbers file.
        state_path: Path to the state persistence file.
        platform: The platform these numbers are for.
    """

    def __init__(
        self,
        phone_list_path: Path | str,
        state_path: Path | str,
        platform: Platform,
    ) -> None:
        """
        Initialize the phone manager.

        Args:
            phone_list_path: Path to file containing phone numbers.
            state_path: Path to JSON file for tracking used numbers.
            platform: Platform these numbers are designated for.
        """
        self.phone_list_path = Path(phone_list_path)
        self.state_path = Path(state_path)
        self.platform = platform

        self._available: list[PhoneNumber] = []
        self._used: dict[str, dict] = {}
        self._loaded = False

    async def load(self) -> None:
        """
        Load phone numbers and usage state.

        Reads the phone list file and existing usage state,
        then filters to only available numbers.
        """
        await self._load_phone_list()
        await self._load_state()
        self._filter_available()
        self._loaded = True
        self.log.info(
            f"Loaded {len(self._available)} available phones "
            f"({len(self._used)} already used)"
        )

    async def _load_phone_list(self) -> None:
        """Load phone numbers from the file."""
        if not self.phone_list_path.exists():
            self.log.error(f"Phone list not found: {self.phone_list_path}")
            raise FileNotFoundError(f"Phone list not found: {self.phone_list_path}")

        phones: list[PhoneNumber] = []

        async with aiofiles.open(self.phone_list_path, "r") as f:
            content = await f.read()
            for line in content.strip().split("\n"):
                # Handle format: "number" or just "number"
                number = line.strip()
                if number:
                    try:
                        phone = PhoneNumber(number=number, platform=self.platform)
                        phones.append(phone)
                    except ValueError as e:
                        self.log.warning(f"Invalid phone number '{number}': {e}")

        self._available = phones
        self.log.debug(f"Loaded {len(phones)} phone numbers from file")

    async def _load_state(self) -> None:
        """Load the usage state from file."""
        if not self.state_path.exists():
            self.log.debug("No existing state file, starting fresh")
            self._used = {}
            return

        try:
            async with aiofiles.open(self.state_path, "r") as f:
                content = await f.read()
                data = json.loads(content)
                # Filter to only this platform's used numbers
                platform_key = str(self.platform)
                self._used = data.get(platform_key, {})
                self.log.debug(f"Loaded {len(self._used)} used numbers from state")
        except json.JSONDecodeError as e:
            self.log.warning(f"Invalid state file, starting fresh: {e}")
            self._used = {}

    async def _save_state(self) -> None:
        """Persist the usage state to file."""
        # Ensure parent directory exists
        self.state_path.parent.mkdir(parents=True, exist_ok=True)

        # Load existing state to preserve other platforms
        existing_data: dict = {}
        if self.state_path.exists():
            try:
                async with aiofiles.open(self.state_path, "r") as f:
                    content = await f.read()
                    existing_data = json.loads(content)
            except (json.JSONDecodeError, FileNotFoundError):
                existing_data = {}

        # Update with current platform's used numbers
        existing_data[str(self.platform)] = self._used

        # Write back
        async with aiofiles.open(self.state_path, "w") as f:
            await f.write(json.dumps(existing_data, indent=2, default=str))

        self.log.debug(f"Saved state with {len(self._used)} used numbers")

    def _filter_available(self) -> None:
        """Filter out already used phone numbers."""
        self._available = [
            phone for phone in self._available if phone.number not in self._used
        ]

    def get_next(self) -> PhoneNumber | None:
        """
        Get the next available phone number.

        Returns:
            The next available PhoneNumber, or None if exhausted.
        """
        if not self._loaded:
            raise RuntimeError("PhoneManager not loaded. Call load() first.")

        if not self._available:
            self.log.warning("No available phone numbers remaining")
            return None

        return self._available[0]

    async def mark_used(self, phone: PhoneNumber, success: bool = True) -> None:
        """
        Mark a phone number as used.

        Args:
            phone: The phone number to mark as used.
            success: Whether the signup was successful.
        """
        if not self._loaded:
            raise RuntimeError("PhoneManager not loaded. Call load() first.")

        self._used[phone.number] = {
            "used_at": datetime.now().isoformat(),
            "success": success,
            "platform": str(self.platform),
        }

        # Remove from available list
        self._available = [p for p in self._available if p.number != phone.number]

        # Persist state
        await self._save_state()

        self.log.info(
            f"Marked phone {phone.formatted} as used "
            f"(success={success}, {len(self._available)} remaining)"
        )

    async def mark_failed(self, phone: PhoneNumber) -> None:
        """
        Mark a phone number as failed (but used).

        Args:
            phone: The phone number that failed.
        """
        await self.mark_used(phone, success=False)

    @property
    def available_count(self) -> int:
        """Get the count of available phone numbers."""
        return len(self._available)

    @property
    def used_count(self) -> int:
        """Get the count of used phone numbers."""
        return len(self._used)

    @property
    def total_count(self) -> int:
        """Get the total count of phone numbers."""
        return self.available_count + self.used_count

    def get_stats(self) -> dict:
        """Get usage statistics."""
        return {
            "platform": str(self.platform),
            "available": self.available_count,
            "used": self.used_count,
            "total": self.total_count,
            "success_rate": self._calculate_success_rate(),
        }

    def _calculate_success_rate(self) -> float:
        """Calculate the success rate of used numbers."""
        if not self._used:
            return 0.0
        successes = sum(1 for data in self._used.values() if data.get("success", False))
        return (successes / len(self._used)) * 100
