"""
Batch Phone Number Tester
=========================

Tests multiple phone numbers to identify which ones are accepted
by Airbnb (OTP screen shown) vs rejected (HTTP 420 error).

This script runs quickly through all numbers without waiting for
actual OTP entry, just to identify working numbers.
"""

import asyncio
import csv
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from playwright.async_api import Page, Response

from src.config import get_settings
from src.core.browser_manager import BrowserManager
from src.pages.airbnb.home_page import AirbnbHomePage
from src.pages.airbnb.signup_page import AirbnbSignupPage
from src.types.enums import Platform
from src.types.models import PhoneNumber
from src.utils.data_generator import DataGenerator
from src.utils.logger import setup_logger, get_logger
from src.utils.phone_manager import PhoneManager


class PhoneTestResult:
    """Result of testing a single phone number."""

    def __init__(
        self,
        phone_number: str,
        country: str,
        accepted: bool,
        error_code: Optional[int] = None,
        error_message: Optional[str] = None,
        otp_screen_shown: bool = False,
        duration_seconds: float = 0.0,
    ):
        self.phone_number = phone_number
        self.country = country
        self.accepted = accepted
        self.error_code = error_code
        self.error_message = error_message
        self.otp_screen_shown = otp_screen_shown
        self.duration_seconds = duration_seconds
        self.timestamp = datetime.now().isoformat()


class BatchPhoneTester:
    """Tests multiple phone numbers for Airbnb acceptance."""

    def __init__(
        self,
        phone_list_path: Path,
        results_path: Path,
        max_numbers: int = 0,  # 0 = test all
        delay_between: float = 3.0,
    ):
        self.log = get_logger("BatchPhoneTester")
        self.phone_list_path = phone_list_path
        self.results_path = results_path
        self.max_numbers = max_numbers
        self.delay_between = delay_between
        self.settings = get_settings()

        self.results: List[PhoneTestResult] = []
        self._http_response_code: Optional[int] = None

    def _load_phone_numbers(self) -> List[str]:
        """Load phone numbers from file."""
        with open(self.phone_list_path, 'r') as f:
            numbers = [line.strip() for line in f if line.strip()]

        if self.max_numbers > 0:
            numbers = numbers[:self.max_numbers]

        self.log.info(f"Loaded {len(numbers)} phone numbers to test")
        return numbers

    def _get_country_for_phone(self, phone: str) -> str:
        """Get country name for a phone number."""
        from src.utils.country_profiles import get_profile_for_phone
        try:
            profile = get_profile_for_phone(f"+{phone}")
            return profile.country_name
        except Exception:
            return "Unknown"

    async def _test_single_phone(
        self,
        phone_number: str,
        browser_manager: BrowserManager,
    ) -> PhoneTestResult:
        """Test a single phone number."""
        start_time = datetime.now()
        country = self._get_country_for_phone(phone_number)

        self.log.info(f"\n{'='*60}")
        self.log.info(f"Testing: +{phone_number} ({country})")
        self.log.info(f"{'='*60}")

        self._http_response_code = None

        try:
            # Set phone for country targeting
            browser_manager.set_phone_number(f"+{phone_number}")

            # Start browser with fresh fingerprint
            await browser_manager.start()

            async with browser_manager.page_context() as page:
                # Track API responses
                async def on_response(response: Response):
                    if "phone_one_time_passwords" in response.url:
                        self._http_response_code = response.status
                        self.log.info(f"OTP API Response: {response.status}")

                page.on("response", on_response)

                # Navigate to signup
                home_page = AirbnbHomePage(page)
                await home_page.navigate_to_signup()

                # Handle signup modal
                signup_page = AirbnbSignupPage(page)
                await signup_page.wait_for_signup_modal()
                await signup_page.select_phone_signup()

                # Create PhoneNumber object and enter it
                phone_obj = PhoneNumber(number=phone_number)
                await signup_page.enter_phone_number(phone_obj)
                await signup_page.click_continue()

                # Wait for response (max 10 seconds)
                for _ in range(20):  # 20 * 0.5s = 10 seconds
                    await page.wait_for_timeout(500)
                    if self._http_response_code is not None:
                        break

                # Check result
                duration = (datetime.now() - start_time).total_seconds()

                if self._http_response_code == 420:
                    self.log.warning(f"REJECTED: HTTP 420 for +{phone_number}")
                    return PhoneTestResult(
                        phone_number=phone_number,
                        country=country,
                        accepted=False,
                        error_code=420,
                        error_message="Phone number rejected",
                        duration_seconds=duration,
                    )
                elif self._http_response_code == 200:
                    # Check for OTP screen
                    otp_visible = await signup_page.wait_for_otp_screen(timeout=5000)

                    if otp_visible:
                        self.log.info(f"ACCEPTED: OTP screen shown for +{phone_number}")
                        return PhoneTestResult(
                            phone_number=phone_number,
                            country=country,
                            accepted=True,
                            otp_screen_shown=True,
                            duration_seconds=duration,
                        )
                    else:
                        self.log.info(f"ACCEPTED: HTTP 200 but no OTP screen for +{phone_number}")
                        return PhoneTestResult(
                            phone_number=phone_number,
                            country=country,
                            accepted=True,
                            otp_screen_shown=False,
                            duration_seconds=duration,
                        )
                else:
                    # Check for error on page
                    error_msg = await signup_page.get_error_message()
                    self.log.warning(f"UNKNOWN: Code={self._http_response_code} for +{phone_number}")
                    return PhoneTestResult(
                        phone_number=phone_number,
                        country=country,
                        accepted=False,
                        error_code=self._http_response_code,
                        error_message=error_msg or "Unknown error",
                        duration_seconds=duration,
                    )

        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            self.log.error(f"ERROR testing +{phone_number}: {e}")
            return PhoneTestResult(
                phone_number=phone_number,
                country=country,
                accepted=False,
                error_message=str(e),
                duration_seconds=duration,
            )
        finally:
            await browser_manager.stop()

    def _save_results(self) -> None:
        """Save results to CSV file."""
        self.results_path.parent.mkdir(parents=True, exist_ok=True)

        with open(self.results_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'phone_number', 'country', 'accepted', 'otp_screen_shown',
                'error_code', 'error_message', 'duration_seconds', 'timestamp'
            ])

            for r in self.results:
                writer.writerow([
                    r.phone_number,
                    r.country,
                    r.accepted,
                    r.otp_screen_shown,
                    r.error_code or '',
                    r.error_message or '',
                    f"{r.duration_seconds:.2f}",
                    r.timestamp,
                ])

        self.log.info(f"Results saved to: {self.results_path}")

    def _print_summary(self) -> None:
        """Print test summary."""
        total = len(self.results)
        accepted = sum(1 for r in self.results if r.accepted)
        rejected = total - accepted
        otp_shown = sum(1 for r in self.results if r.otp_screen_shown)

        # Group by country
        by_country: Dict[str, Dict[str, int]] = {}
        for r in self.results:
            if r.country not in by_country:
                by_country[r.country] = {'total': 0, 'accepted': 0, 'rejected': 0}
            by_country[r.country]['total'] += 1
            if r.accepted:
                by_country[r.country]['accepted'] += 1
            else:
                by_country[r.country]['rejected'] += 1

        print(f"\n{'='*60}")
        print("BATCH PHONE TEST SUMMARY")
        print(f"{'='*60}")
        print(f"Total Tested: {total}")
        print(f"Accepted: {accepted} ({accepted/total*100:.1f}%)")
        print(f"Rejected: {rejected} ({rejected/total*100:.1f}%)")
        print(f"OTP Screens Shown: {otp_shown}")

        print(f"\nResults by Country:")
        for country, stats in sorted(by_country.items()):
            print(f"  {country}: {stats['accepted']}/{stats['total']} accepted "
                  f"({stats['accepted']/stats['total']*100:.0f}%)")

        if accepted > 0:
            print(f"\nWorking Phone Numbers:")
            for r in self.results:
                if r.accepted:
                    print(f"  +{r.phone_number} ({r.country})")

        print(f"{'='*60}\n")

    async def run(self) -> List[PhoneTestResult]:
        """Run the batch phone test."""
        self.log.info("Starting batch phone test")

        phone_numbers = self._load_phone_numbers()

        for i, phone in enumerate(phone_numbers, 1):
            self.log.info(f"\n[{i}/{len(phone_numbers)}] Testing phone...")

            browser_manager = BrowserManager(
                use_proxy=True,
                rotate_proxy=True,
                randomize_fingerprint=True,
                debug_mode=False,
            )

            result = await self._test_single_phone(phone, browser_manager)
            self.results.append(result)

            # Save results after each test (in case of crash)
            self._save_results()

            # Delay between tests
            if i < len(phone_numbers):
                self.log.info(f"Waiting {self.delay_between}s before next test...")
                await asyncio.sleep(self.delay_between)

        self._print_summary()
        return self.results


async def main():
    """Run the batch phone tester."""
    setup_logger()

    settings = get_settings()
    results_path = Path("./data/results/phone_test_results.csv")

    tester = BatchPhoneTester(
        phone_list_path=settings.paths.phone_list_airbnb,
        results_path=results_path,
        max_numbers=0,  # Test all
        delay_between=3.0,  # 3 seconds between tests
    )

    await tester.run()


if __name__ == "__main__":
    asyncio.run(main())
