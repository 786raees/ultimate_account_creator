"""
Signup Orchestrator
===================

Orchestrates the complete signup flow for various platforms.
Handles retry logic, error recovery, and progress tracking.
Includes comprehensive debug logging and screenshot capture.
"""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Callable

from playwright.async_api import Page, TimeoutError as PlaywrightTimeout
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from src.config import get_settings
from src.core.browser_manager import BrowserManager
from src.pages.airbnb import AirbnbHomePage, AirbnbSignupPage
from src.services.account_saver import AccountSaver
from src.types.enums import AccountStatus, Platform, SignupStep
from src.types.models import (
    AccountCredentials,
    PhoneNumber,
    SignupResult,
    UserProfile,
)
from src.utils.data_generator import DataGenerator
from src.utils.logger import LoggerMixin
from src.utils.phone_manager import PhoneManager


class SignupOrchestrator(LoggerMixin):
    """
    Orchestrates platform signup flows.

    Manages the complete signup process including:
    - Browser lifecycle
    - Phone number management
    - Profile generation
    - Error handling and retries
    - Account persistence
    - Debug logging and screenshots

    Attributes:
        platform: Target platform for signups.
        phone_manager: Manager for phone numbers.
        data_generator: Generator for fake user data.
        account_saver: Service for saving accounts.
    """

    def __init__(
        self,
        platform: Platform,
        phone_manager: PhoneManager,
        data_generator: DataGenerator | None = None,
        account_saver: AccountSaver | None = None,
    ) -> None:
        """
        Initialize the signup orchestrator.

        Args:
            platform: Target platform for signups.
            phone_manager: Manager for phone numbers.
            data_generator: Optional data generator (creates default if None).
            account_saver: Optional account saver (creates default if None).
        """
        self.platform = platform
        self.phone_manager = phone_manager
        self.data_generator = data_generator or DataGenerator()

        settings = get_settings()
        self.account_saver = account_saver or AccountSaver(
            settings.paths.accounts_output_path
        )

        self._browser_manager: BrowserManager | None = None
        self._current_step = SignupStep.INITIALIZED
        self._current_phone: str | None = None

        # Base screenshot directory
        self.screenshot_base_dir = Path("./screenshots")
        self.screenshot_base_dir.mkdir(parents=True, exist_ok=True)
        self.screenshot_dir = self.screenshot_base_dir

    async def _take_screenshot(self, page: Page, step_name: str) -> None:
        """Take a debug screenshot for the current step."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}_{step_name}.png"
            filepath = self.screenshot_dir / filename
            await page.screenshot(path=str(filepath), full_page=False)
            self.log.info(f"[SCREENSHOT] {filepath}")
        except Exception as e:
            self.log.warning(f"Failed to take screenshot: {e}")

    async def _log_page_state(self, page: Page, description: str) -> None:
        """Log the current page state for debugging."""
        try:
            url = page.url
            title = await page.title()
            self.log.info(f"[PAGE STATE] {description}")
            self.log.info(f"  URL: {url}")
            self.log.info(f"  Title: {title}")
        except Exception as e:
            self.log.warning(f"Failed to log page state: {e}")

    async def run_single_signup(
        self,
        otp_callback: Callable | None = None,
    ) -> SignupResult:
        """
        Run a single signup attempt.

        Args:
            otp_callback: Optional async callback to get OTP code.
                         Signature: async (phone: str) -> str

        Returns:
            SignupResult with the outcome of the attempt.
        """
        start_time = datetime.now()
        phone: PhoneNumber | None = None
        profile: UserProfile | None = None

        self.log.info("=" * 70)
        self.log.info("STARTING NEW SIGNUP ATTEMPT")
        self.log.info("=" * 70)

        try:
            # Get phone number
            phone = self.phone_manager.get_next()
            if not phone:
                self.log.error("No available phone numbers!")
                return self._create_result(
                    success=False,
                    step=SignupStep.INITIALIZED,
                    error="No available phone numbers",
                    start_time=start_time,
                )

            self.log.info(f"Phone selected: {phone.formatted}")
            self.log.info(f"  Country code: {phone.country_code}")
            self.log.info(f"  Local number: {phone.local_number}")

            # Create phone-specific screenshot directory
            self._current_phone = phone.number
            self.screenshot_dir = self.screenshot_base_dir / phone.number
            self.screenshot_dir.mkdir(parents=True, exist_ok=True)
            self.log.info(f"  Screenshots: {self.screenshot_dir}")

            # Generate profile
            profile = self.data_generator.generate_profile()
            self.log.info(f"Profile generated:")
            self.log.info(f"  Name: {profile.full_name}")
            self.log.info(f"  Email: {profile.email}")
            self.log.info(f"  Password: {'*' * len(profile.password)}")
            if profile.birth_date:
                self.log.info(f"  Birth date: {profile.birth_date.strftime('%Y-%m-%d')}")

            # Run the platform-specific signup
            if self.platform == Platform.AIRBNB:
                result = await self._run_airbnb_signup(
                    phone=phone,
                    profile=profile,
                    otp_callback=otp_callback,
                    start_time=start_time,
                )
            else:
                return self._create_result(
                    success=False,
                    step=SignupStep.INITIALIZED,
                    error=f"Unsupported platform: {self.platform}",
                    start_time=start_time,
                )

            # Handle result
            if result.success:
                self.log.info("Signup SUCCESSFUL - marking phone as used")
                await self.phone_manager.mark_used(phone, success=True)
                if result.account:
                    await self.account_saver.save(result.account)
            else:
                self.log.warning("Signup FAILED - marking phone as failed")
                await self.phone_manager.mark_failed(phone)

            return result

        except Exception as e:
            self.log.exception(f"Signup failed with exception: {e}")
            if phone:
                await self.phone_manager.mark_failed(phone)
            return self._create_result(
                success=False,
                step=self._current_step,
                error=str(e),
                start_time=start_time,
            )

    async def _run_airbnb_signup(
        self,
        phone: PhoneNumber,
        profile: UserProfile,
        otp_callback: Callable | None,
        start_time: datetime,
    ) -> SignupResult:
        """
        Run the Airbnb-specific signup flow.

        Uses MultiLoginX for browser profile management when enabled.
        Each signup gets a fresh profile with rotated proxy.

        Args:
            phone: Phone number for verification.
            profile: User profile data.
            otp_callback: Callback to get OTP code.
            start_time: When the signup started.

        Returns:
            SignupResult with the outcome.
        """
        settings = get_settings()

        # Create browser manager with MultiLoginX support
        # MultiLoginX is enabled by default in settings
        browser_manager = BrowserManager(
            use_proxy=True,
            debug_mode=True,
            use_multiloginx=settings.multiloginx.enabled,
        )

        # Set phone number for country-based fingerprint matching
        # This ensures browser fingerprint (timezone, locale, etc.) matches the phone's country
        browser_manager.set_phone_number(phone.formatted)

        if settings.multiloginx.enabled:
            self.log.info("Using MultiLoginX for browser profile management")

        try:
            # Start browser and get page
            await browser_manager.start()
            page = browser_manager.page

            # Initialize pages
            home_page = AirbnbHomePage(page)
            signup_page = AirbnbSignupPage(page)

            # ============================================================
            # STEP 1: Navigate to Signup
            # ============================================================
            self.log.info("-" * 60)
            self.log.info("STEP 1: Navigating to Signup")
            self.log.info("-" * 60)
            self._current_step = SignupStep.INITIALIZED

            # Uses direct URL or modal flow based on config
            await home_page.navigate_to_signup()
            await self._log_page_state(page, "After navigation to signup")
            await self._take_screenshot(page, "01_signup_page")

            # Handle cookies and popups (may appear on direct URL too)
            self.log.info("Handling cookies and popups...")
            # await home_page.accept_cookies()
            # await home_page.dismiss_popups()
            await page.wait_for_timeout(2000)
            await self._take_screenshot(page, "02_after_popups")

            self._current_step = SignupStep.NAVIGATED_TO_SIGNUP

            # ============================================================
            # STEP 2: Wait for signup form and select phone method
            # ============================================================
            self.log.info("-" * 60)
            self.log.info("STEP 2: Waiting for signup form")
            self.log.info("-" * 60)

            # Wait for signup form (works for both modal and direct page)
            try:
                await signup_page.wait_for_signup_modal()
                self.log.info("Signup form is visible!")
            except PlaywrightTimeout:
                self.log.error("Signup form did not appear!")
                await self._take_screenshot(page, "02_ERROR_no_form")
                await self._log_page_state(page, "Form not found")
                return self._create_result(
                    success=False,
                    step=self._current_step,
                    error="Signup form did not appear",
                    start_time=start_time,
                )

            await self._take_screenshot(page, "03_signup_form_visible")

            # Select phone signup method
            self.log.info("Selecting phone signup method...")
            await signup_page.select_phone_signup()
            await page.wait_for_timeout(1500)
            await self._take_screenshot(page, "04_phone_method_selected")

            # ============================================================
            # STEP 3: Enter phone number
            # ============================================================
            self.log.info("-" * 60)
            self.log.info("STEP 3: Entering phone number")
            self.log.info("-" * 60)
            self._current_step = SignupStep.PHONE_ENTERED

            self.log.info(f"Entering phone: {phone.formatted}")
            await signup_page.enter_phone_number(phone)
            await page.wait_for_timeout(1000)
            await self._take_screenshot(page, "06_phone_entered")

            # Click continue
            self.log.info("Clicking continue button...")
            await signup_page.click_continue()
            await page.wait_for_timeout(3000)
            await self._take_screenshot(page, "07_after_continue")

            # Check for errors
            if await signup_page.has_error():
                error_msg = await signup_page.get_error_message()
                self.log.error(f"Error after phone entry: {error_msg}")
                await self._take_screenshot(page, "07_ERROR_phone_rejected")
                return self._create_result(
                    success=False,
                    step=self._current_step,
                    error=error_msg or "Phone number rejected",
                    start_time=start_time,
                )

            # ============================================================
            # STEP 4: Wait for OTP screen
            # ============================================================
            self.log.info("-" * 60)
            self.log.info("STEP 4: Waiting for OTP verification screen")
            self.log.info("-" * 60)
            self._current_step = SignupStep.OTP_REQUESTED

            otp_received = await signup_page.wait_for_otp_screen()
            await self._take_screenshot(page, "08_otp_screen")

            if not otp_received:
                error_msg = await signup_page.get_error_message()
                self.log.error(f"OTP screen not shown. Error: {error_msg}")
                await self._log_page_state(page, "No OTP screen")
                return self._create_result(
                    success=False,
                    step=self._current_step,
                    error=error_msg or "OTP screen not shown",
                    start_time=start_time,
                )

            self.log.info("OTP screen detected!")

            # ============================================================
            # STEP 5: Handle OTP entry
            # ============================================================
            self.log.info("-" * 60)
            self.log.info("STEP 5: Handling OTP entry")
            self.log.info("-" * 60)

            if otp_callback:
                self.log.info("Waiting for OTP code from callback...")
                otp_code = await otp_callback(phone.formatted)

                if otp_code:
                    self.log.info(f"OTP received: {otp_code}")
                    await signup_page.enter_otp(otp_code)
                    await self._take_screenshot(page, "09_otp_entered")
                    await signup_page.click_verify()
                    self._current_step = SignupStep.OTP_VERIFIED
                    await page.wait_for_timeout(3000)
                    await self._take_screenshot(page, "10_after_otp_verify")
                else:
                    self.log.error("OTP not received from callback")
                    return self._create_result(
                        success=False,
                        step=self._current_step,
                        error="OTP not received",
                        start_time=start_time,
                    )
            else:
                # Manual OTP entry
                self.log.warning("=" * 50)
                self.log.warning("MANUAL OTP ENTRY REQUIRED")
                self.log.warning(f"Phone: {phone.formatted}")
                self.log.warning("Waiting for profile form (2 min timeout)...")
                self.log.warning("=" * 50)

                # Wait for profile form (indicates OTP was entered)
                if not await signup_page.wait_for_profile_form(timeout=120000):
                    self.log.error("Timeout waiting for manual OTP")
                    await self._take_screenshot(page, "09_ERROR_otp_timeout")
                    return self._create_result(
                        success=False,
                        step=self._current_step,
                        error="Timeout waiting for manual OTP entry",
                        start_time=start_time,
                    )
                self._current_step = SignupStep.OTP_VERIFIED
                self.log.info("OTP verified (profile form appeared)")

            await self._take_screenshot(page, "11_after_otp")

            # ============================================================
            # STEP 6: Fill profile form
            # ============================================================
            self.log.info("-" * 60)
            self.log.info("STEP 6: Filling profile form")
            self.log.info("-" * 60)
            self._current_step = SignupStep.PROFILE_COMPLETED

            if await signup_page.wait_for_profile_form():
                self.log.info("Profile form detected - filling...")
                await signup_page.fill_profile(profile)
                await self._take_screenshot(page, "12_profile_filled")

                self.log.info("Clicking agree and continue...")
                await signup_page.agree_and_continue()
                await page.wait_for_timeout(3000)
                await self._take_screenshot(page, "13_after_agree")
            else:
                self.log.warning("Profile form not found - may have skipped")

            # ============================================================
            # STEP 7: Verify signup success
            # ============================================================
            self.log.info("-" * 60)
            self.log.info("STEP 7: Verifying signup success")
            self.log.info("-" * 60)

            await page.wait_for_timeout(3000)
            await self._log_page_state(page, "Final state")
            await self._take_screenshot(page, "14_final_state")

            if await signup_page.is_signup_successful():
                self._current_step = SignupStep.SIGNUP_COMPLETED
                self.log.info("=" * 50)
                self.log.info("SIGNUP SUCCESSFUL!")
                self.log.info("=" * 50)

                account = AccountCredentials(
                    platform=self.platform,
                    email=profile.email,
                    password=profile.password,
                    phone=phone.formatted,
                    profile=profile,
                    status=AccountStatus.ACTIVE,
                )

                return self._create_result(
                    success=True,
                    step=self._current_step,
                    account=account,
                    start_time=start_time,
                )
            else:
                error_msg = await signup_page.get_error_message()
                self.log.error(f"Signup verification failed: {error_msg}")
                await self._take_screenshot(page, "14_ERROR_verification_failed")
                return self._create_result(
                    success=False,
                    step=self._current_step,
                    error=error_msg or "Signup verification failed",
                    start_time=start_time,
                )

        except PlaywrightTimeout as e:
            self.log.error(f"Timeout during signup: {e}")
            return self._create_result(
                success=False,
                step=self._current_step,
                error=f"Timeout: {e}",
                start_time=start_time,
            )
        except Exception as e:
            self.log.exception(f"Error during Airbnb signup: {e}")
            return self._create_result(
                success=False,
                step=self._current_step,
                error=str(e),
                start_time=start_time,
            )
        finally:
            # Always stop browser
            await browser_manager.stop()

    def _create_result(
        self,
        success: bool,
        step: SignupStep,
        start_time: datetime,
        error: str | None = None,
        account: AccountCredentials | None = None,
    ) -> SignupResult:
        """Create a SignupResult object."""
        duration = (datetime.now() - start_time).total_seconds()

        result = SignupResult(
            success=success,
            platform=self.platform,
            step_reached=step,
            account=account,
            error_message=error,
            duration_seconds=duration,
        )

        self.log.info("-" * 60)
        self.log.info(f"RESULT: {'SUCCESS' if success else 'FAILED'}")
        self.log.info(f"  Step reached: {step}")
        self.log.info(f"  Duration: {duration:.2f}s")
        if error:
            self.log.info(f"  Error: {error}")
        self.log.info("-" * 60)

        return result

    async def run_batch_signup(
        self,
        count: int,
        otp_callback: Callable | None = None,
        delay_between: int = 5,
    ) -> list[SignupResult]:
        """
        Run multiple signup attempts.

        Args:
            count: Number of signups to attempt.
            otp_callback: Callback to get OTP codes.
            delay_between: Seconds to wait between attempts.

        Returns:
            List of SignupResult objects.
        """
        results: list[SignupResult] = []

        for i in range(count):
            self.log.info(f"Starting signup {i + 1}/{count}")

            result = await self.run_single_signup(otp_callback=otp_callback)
            results.append(result)

            self.log.info(f"Signup {i + 1}/{count}: {result.summary}")

            # Delay between attempts
            if i < count - 1 and delay_between > 0:
                self.log.debug(f"Waiting {delay_between}s before next attempt")
                await asyncio.sleep(delay_between)

        # Summary
        successes = sum(1 for r in results if r.success)
        self.log.info(f"Batch complete: {successes}/{count} successful")

        return results
