"""
Phone Number Manager
====================

Manages phone numbers for signup operations including:
- Loading phone lists from files
- Tracking used/available numbers via CSV
- Persisting usage state
"""

import csv
from datetime import datetime
from pathlib import Path

import aiofiles

from src.types.enums import Platform
from src.types.models import PhoneNumber
from src.utils.logger import LoggerMixin

# Hardcoded CSV path relative to project root
PROJECT_ROOT = Path(__file__).parent.parent.parent
USED_PHONES_CSV = PROJECT_ROOT / "data" / "state" / "used_phones.csv"


class PhoneManager(LoggerMixin):
    """
    Manages phone numbers for signup operations.

    Uses a simple CSV file to track used phone numbers.
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
            state_path: Ignored - uses hardcoded CSV path instead.
            platform: Platform these numbers are designated for.
        """
        self.phone_list_path = Path(phone_list_path)
        self.platform = platform
        self.csv_path = USED_PHONES_CSV

        self._all_phones: list[PhoneNumber] = []
        self._used_numbers: set[str] = set()
        self._loaded = False

    async def load(self) -> None:
        """
        Load phone numbers and check CSV for used ones.
        """
        # Load all phone numbers from file
        await self._load_phone_list()

        # Load used numbers from CSV
        self._load_used_from_csv()

        self._loaded = True
        available = len(self._all_phones) - len(self._used_numbers)
        self.log.info(
            f"Loaded {available} available phones "
            f"({len(self._used_numbers)} already used in CSV)"
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
                number = line.strip()
                if number:
                    try:
                        phone = PhoneNumber(number=number, platform=self.platform)
                        phones.append(phone)
                    except ValueError as e:
                        self.log.warning(f"Invalid phone number '{number}': {e}")

        self._all_phones = phones
        self.log.debug(f"Loaded {len(phones)} phone numbers from file")

    def _load_used_from_csv(self) -> None:
        """Load used phone numbers from CSV file."""
        self._used_numbers = set()

        if not self.csv_path.exists():
            self.log.debug(f"No CSV file found at {self.csv_path}, starting fresh")
            return

        try:
            with open(self.csv_path, "r", newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    phone = row.get("phone_number", "").strip()
                    if phone:
                        self._used_numbers.add(phone)
            self.log.info(f"Loaded {len(self._used_numbers)} used numbers from CSV: {self.csv_path}")
        except Exception as e:
            self.log.error(f"Error reading CSV: {e}")
            self._used_numbers = set()

    def _append_to_csv(self, phone: str, success: bool) -> None:
        """Append a used phone number to the CSV file."""
        # Ensure directory exists
        self.csv_path.parent.mkdir(parents=True, exist_ok=True)

        # Check if file exists to determine if we need header
        file_exists = self.csv_path.exists()

        try:
            with open(self.csv_path, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)

                # Write header if new file
                if not file_exists:
                    writer.writerow(["phone_number", "used_at", "platform", "success"])

                # Write the phone number
                writer.writerow([
                    phone,
                    datetime.now().isoformat(),
                    str(self.platform),
                    str(success)
                ])

            self.log.info(f"Added {phone} to CSV: {self.csv_path}")
        except Exception as e:
            self.log.error(f"Error writing to CSV: {e}")

    def _is_used(self, phone_number: str) -> bool:
        """Check if a phone number is already used (in CSV)."""
        return phone_number in self._used_numbers

    def get_next(self) -> PhoneNumber | None:
        """
        Get the next available phone number.

        Returns:
            The next available PhoneNumber, or None if exhausted.
        """
        if not self._loaded:
            raise RuntimeError("PhoneManager not loaded. Call load() first.")

        # Re-read CSV to get latest used numbers (in case of concurrent runs)
        self._load_used_from_csv()

        for phone in self._all_phones:
            if not self._is_used(phone.number):
                self.log.info(f"Next available phone: {phone.formatted}")
                return phone

        self.log.warning("No available phone numbers remaining")
        return None

    async def mark_used(self, phone: PhoneNumber, success: bool = True) -> None:
        """
        Mark a phone number as used by adding to CSV.

        Args:
            phone: The phone number to mark as used.
            success: Whether the signup was successful.
        """
        if not self._loaded:
            raise RuntimeError("PhoneManager not loaded. Call load() first.")

        # Add to in-memory set
        self._used_numbers.add(phone.number)

        # Append to CSV file
        self._append_to_csv(phone.number, success)

        available = len(self._all_phones) - len(self._used_numbers)
        self.log.info(
            f"Marked phone {phone.formatted} as used "
            f"(success={success}, {available} remaining)"
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
        return len(self._all_phones) - len(self._used_numbers)

    @property
    def used_count(self) -> int:
        """Get the count of used phone numbers."""
        return len(self._used_numbers)

    @property
    def total_count(self) -> int:
        """Get the total count of phone numbers."""
        return len(self._all_phones)

    def get_stats(self) -> dict:
        """Get usage statistics."""
        return {
            "platform": str(self.platform),
            "available": self.available_count,
            "used": self.used_count,
            "total": self.total_count,
            "csv_path": str(self.csv_path),
        }
