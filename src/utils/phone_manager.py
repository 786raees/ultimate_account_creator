"""
Phone Number Manager
====================

Manages phone numbers for signup operations including:
- Loading phone lists from files
- Tracking used/available numbers
- Separate files for success and failed numbers
- Persisting usage state
"""

from pathlib import Path

import aiofiles

from src.types.enums import Platform
from src.types.models import PhoneNumber
from src.utils.logger import LoggerMixin

# File paths relative to project root
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
SUCCESS_FILE = DATA_DIR / "success.txt"
FAILED_FILE = DATA_DIR / "failed.txt"


class PhoneManager(LoggerMixin):
    """
    Manages phone numbers for signup operations.

    Uses separate text files for success and failed numbers.
    """

    def __init__(
        self,
        phone_list_path: Path | str,
        state_path: Path | str,  # Kept for compatibility but not used
        platform: Platform,
    ) -> None:
        """
        Initialize the phone manager.

        Args:
            phone_list_path: Path to file containing phone numbers.
            state_path: Ignored - uses hardcoded paths instead.
            platform: Platform these numbers are designated for.
        """
        self.phone_list_path = Path(phone_list_path)
        self.platform = platform

        self._all_phones: list[PhoneNumber] = []
        self._success_numbers: set[str] = set()
        self._failed_numbers: set[str] = set()
        self._loaded = False

    async def load(self) -> None:
        """
        Load phone numbers and check processed files.
        """
        # Ensure data directory exists
        DATA_DIR.mkdir(parents=True, exist_ok=True)

        # Load all phone numbers from file
        await self._load_phone_list()

        # Load processed numbers
        self._success_numbers = self._load_numbers_from_file(SUCCESS_FILE)
        self._failed_numbers = self._load_numbers_from_file(FAILED_FILE)

        self._loaded = True

        processed = len(self._success_numbers) + len(self._failed_numbers)
        available = len(self._all_phones) - processed

        self.log.info(f"Phone stats:")
        self.log.info(f"  Total: {len(self._all_phones)}")
        self.log.info(f"  Success: {len(self._success_numbers)}")
        self.log.info(f"  Failed: {len(self._failed_numbers)}")
        self.log.info(f"  Available: {available}")

    async def _load_phone_list(self) -> None:
        """Load phone numbers from the file."""
        if not self.phone_list_path.exists():
            self.log.error(f"Phone list not found: {self.phone_list_path}")
            raise FileNotFoundError(f"Phone list not found: {self.phone_list_path}")

        phones: list[PhoneNumber] = []

        async with aiofiles.open(self.phone_list_path, "r") as f:
            content = await f.read()
            for line in content.strip().split("\n"):
                number = line.strip()
                if number:
                    try:
                        phone = PhoneNumber(number=number, platform=self.platform)
                        phones.append(phone)
                    except ValueError as e:
                        self.log.warning(f"Invalid phone number '{number}': {e}")

        self._all_phones = phones
        self.log.debug(f"Loaded {len(phones)} phone numbers from file")

    def _load_numbers_from_file(self, filepath: Path) -> set[str]:
        """Load phone numbers from a text file (one per line)."""
        numbers = set()

        if not filepath.exists():
            return numbers

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                for line in f:
                    number = line.strip()
                    if number:
                        numbers.add(number)
            self.log.debug(f"Loaded {len(numbers)} numbers from {filepath.name}")
        except Exception as e:
            self.log.error(f"Error reading {filepath}: {e}")

        return numbers

    def _append_to_file(self, filepath: Path, phone: str) -> None:
        """Append a phone number to a file."""
        try:
            with open(filepath, "a", encoding="utf-8") as f:
                f.write(f"{phone}\n")
            self.log.debug(f"Added {phone} to {filepath.name}")
        except Exception as e:
            self.log.error(f"Error writing to {filepath}: {e}")

    def _is_processed(self, phone_number: str) -> bool:
        """Check if a phone number is already processed (success or failed)."""
        return phone_number in self._success_numbers or phone_number in self._failed_numbers

    def get_next(self) -> PhoneNumber | None:
        """
        Get the next available phone number.

        Returns:
            The next available PhoneNumber, or None if exhausted.
        """
        if not self._loaded:
            raise RuntimeError("PhoneManager not loaded. Call load() first.")

        # Re-read files to get latest processed numbers (in case of concurrent runs)
        self._success_numbers = self._load_numbers_from_file(SUCCESS_FILE)
        self._failed_numbers = self._load_numbers_from_file(FAILED_FILE)

        for phone in self._all_phones:
            if not self._is_processed(phone.number):
                self.log.info(f"Next available phone: {phone.formatted}")
                return phone

        self.log.warning("No available phone numbers remaining")
        return None

    async def mark_success(self, phone: PhoneNumber) -> None:
        """
        Mark a phone number as successful.

        Args:
            phone: The phone number that succeeded.
        """
        if not self._loaded:
            raise RuntimeError("PhoneManager not loaded. Call load() first.")

        # Add to success file
        self._success_numbers.add(phone.number)
        self._append_to_file(SUCCESS_FILE, phone.number)

        available = self.available_count
        self.log.info(f"SUCCESS: {phone.formatted} ({available} remaining)")

    async def mark_failed(self, phone: PhoneNumber) -> None:
        """
        Mark a phone number as failed.

        Args:
            phone: The phone number that failed.
        """
        if not self._loaded:
            raise RuntimeError("PhoneManager not loaded. Call load() first.")

        # Add to failed file
        self._failed_numbers.add(phone.number)
        self._append_to_file(FAILED_FILE, phone.number)

        available = self.available_count
        self.log.info(f"FAILED: {phone.formatted} ({available} remaining)")

    async def mark_used(self, phone: PhoneNumber, success: bool = True) -> None:
        """
        Mark a phone number as used.

        Args:
            phone: The phone number to mark.
            success: Whether the signup was successful.
        """
        if success:
            await self.mark_success(phone)
        else:
            await self.mark_failed(phone)

    @property
    def available_count(self) -> int:
        """Get the count of available phone numbers."""
        # Re-read files to get latest
        self._success_numbers = self._load_numbers_from_file(SUCCESS_FILE)
        self._failed_numbers = self._load_numbers_from_file(FAILED_FILE)
        processed = len(self._success_numbers) + len(self._failed_numbers)
        return len(self._all_phones) - processed

    @property
    def success_count(self) -> int:
        """Get the count of successful phone numbers."""
        return len(self._success_numbers)

    @property
    def failed_count(self) -> int:
        """Get the count of failed phone numbers."""
        return len(self._failed_numbers)

    @property
    def total_count(self) -> int:
        """Get the total count of phone numbers."""
        return len(self._all_phones)

    # Kept for compatibility
    @property
    def used_count(self) -> int:
        """Get the count of processed phone numbers."""
        return self.success_count + self.failed_count

    def get_stats(self) -> dict:
        """Get usage statistics."""
        return {
            "platform": str(self.platform),
            "total": self.total_count,
            "success": self.success_count,
            "failed": self.failed_count,
            "available": self.available_count,
            "success_file": str(SUCCESS_FILE),
            "failed_file": str(FAILED_FILE),
        }
