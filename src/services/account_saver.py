"""
Account Saver Service
=====================

Handles saving and managing created account credentials.
"""

import json
from datetime import datetime
from pathlib import Path

import aiofiles

from src.types.enums import Platform
from src.types.models import AccountCredentials
from src.utils.logger import LoggerMixin


class AccountSaver(LoggerMixin):
    """
    Saves and manages created account credentials.

    Persists account information to JSON files organized
    by platform and date.

    Attributes:
        output_dir: Directory for saving account files.
    """

    def __init__(self, output_dir: Path | str) -> None:
        """
        Initialize the account saver.

        Args:
            output_dir: Directory for saving account files.
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _get_output_file(self, platform: Platform) -> Path:
        """
        Get the output file path for a platform.

        Args:
            platform: The platform to get file for.

        Returns:
            Path to the output file.
        """
        date_str = datetime.now().strftime("%Y-%m-%d")
        filename = f"{platform.value}_accounts_{date_str}.json"
        return self.output_dir / filename

    async def save(self, account: AccountCredentials) -> None:
        """
        Save an account to the appropriate file.

        Args:
            account: Account credentials to save.
        """
        output_file = self._get_output_file(account.platform)

        # Load existing accounts
        accounts = await self._load_existing(output_file)

        # Add new account
        accounts.append(account.to_export_dict())

        # Save back
        await self._save_to_file(output_file, accounts)

        self.log.info(f"Saved account to {output_file}")

    async def _load_existing(self, file_path: Path) -> list[dict]:
        """Load existing accounts from file."""
        if not file_path.exists():
            return []

        try:
            async with aiofiles.open(file_path, "r") as f:
                content = await f.read()
                return json.loads(content)
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    async def _save_to_file(self, file_path: Path, accounts: list[dict]) -> None:
        """Save accounts to file."""
        async with aiofiles.open(file_path, "w") as f:
            await f.write(json.dumps(accounts, indent=2))

    async def get_accounts(self, platform: Platform) -> list[dict]:
        """
        Get all saved accounts for a platform.

        Args:
            platform: The platform to get accounts for.

        Returns:
            List of account dictionaries.
        """
        output_file = self._get_output_file(platform)
        return await self._load_existing(output_file)

    async def get_account_count(self, platform: Platform) -> int:
        """
        Get the count of accounts for a platform today.

        Args:
            platform: The platform to count accounts for.

        Returns:
            Number of accounts saved today.
        """
        accounts = await self.get_accounts(platform)
        return len(accounts)
