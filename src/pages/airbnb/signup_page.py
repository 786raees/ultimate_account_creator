"""
Airbnb Signup Page
==================

Page object for the Airbnb signup/registration flow.
Handles the complete signup process including phone verification.

Updated: December 2025 to match current Airbnb UI
"""

from playwright.async_api import Page, TimeoutError as PlaywrightTimeout

from src.core.base_page import BasePage
from src.pages.airbnb.selectors import SignupPageSelectors, OTPSelectors
from src.types.models import PhoneNumber, UserProfile


class AirbnbSignupPage(BasePage):
    """
    Page object for Airbnb's signup flow.

    Handles the complete signup process including:
    - Phone entry (default method now)
    - OTP verification
    - Profile completion
    """

    def __init__(self, page: Page) -> None:
        """Initialize the signup page."""
        super().__init__(page)
        self.selectors = SignupPageSelectors
        self.otp_selectors = OTPSelectors

    @property
    def url(self) -> str:
        """Get the signup page URL (modal-based, no direct URL)."""
        return "https://www.airbnb.com"

    @property
    def page_identifier(self) -> str:
        """Get the signup modal identifier."""
        return '[role="dialog"]'

    async def wait_for_signup_modal(self, timeout: int = 10000) -> None:
        """
        Wait for the signup modal to appear.

        Args:
            timeout: Maximum time to wait in ms.
        """
        self.log.info("Waiting for signup modal...")

        # Try multiple indicators that the modal is visible
        modal_indicators = [
            '[role="dialog"]',
            '[aria-modal="true"]',
            'div:has-text("Welcome to Airbnb")',
            'div:has-text("Log in or sign up")',
            'input[type="tel"]',  # Phone input is visible in modal
        ]

        for selector in modal_indicators:
            try:
                self.log.debug(f"Trying modal selector: {selector}")
                await self.page.wait_for_selector(selector, state="visible", timeout=timeout // len(modal_indicators))
                self.log.info(f"Modal detected with: {selector}")
                return
            except PlaywrightTimeout:
                continue

        raise PlaywrightTimeout(f"Signup modal not found after {timeout}ms")

    async def is_signup_modal_visible(self) -> bool:
        """Check if the signup modal is visible."""
        try:
            modal = self.page.locator('[role="dialog"], [aria-modal="true"]').first
            return await modal.is_visible(timeout=2000)
        except PlaywrightTimeout:
            return False

    # -------------------------------------------------------------------------
    # Phone Signup Flow
    # -------------------------------------------------------------------------

    async def select_phone_signup(self) -> None:
        """
        Select phone number as the signup method.

        Note: Current Airbnb UI shows phone input by default,
        so this may not need to do anything.
        """
        self.log.info("Checking if phone input is already visible...")

        # Check if phone input is already visible (new Airbnb default)
        try:
            phone_input = self.page.locator('input[type="tel"]').first
            if await phone_input.is_visible(timeout=3000):
                self.log.info("Phone input already visible - skipping selection")
                return
        except PlaywrightTimeout:
            pass

        # Try to find and click phone option if needed
        self.log.info("Looking for phone signup option...")
        phone_options = [
            'button:has-text("phone")',
            'div:has-text("Continue with phone")',
            '[data-testid="social-auth-button-phone"]',
        ]

        for selector in phone_options:
            try:
                btn = self.page.locator(selector).first
                if await btn.is_visible(timeout=2000):
                    await btn.click()
                    self.log.info(f"Clicked phone option: {selector}")
                    await self.page.wait_for_timeout(1000)
                    return
            except PlaywrightTimeout:
                continue

        self.log.info("Phone signup already selected or default")

    async def select_country_code(self, country_code: str) -> None:
        """
        Select the country code from the dropdown.

        Airbnb uses a native HTML <select> element for country selection.
        The value format is "{country_code}{ISO_code}" like "380UA" for Ukraine.

        Args:
            country_code: Country code (e.g., "380" for Ukraine).
        """
        # Map country codes to their ISO codes and names for the native select
        # Value format: {dial_code}{ISO_2_letter_code}
        country_map = {
            "380": ("UA", "Ukraine"),
            "375": ("BY", "Belarus"),
            "261": ("MG", "Madagascar"),
            "962": ("JO", "Jordan"),
            "972": ("IL", "Israel"),
            "855": ("KH", "Cambodia"),
            "229": ("BJ", "Benin"),
            "1": ("US", "United States"),  # Note: US, CA, and others share +1
            "92": ("PK", "Pakistan"),
            "44": ("GB", "United Kingdom"),
            "49": ("DE", "Germany"),
            "33": ("FR", "France"),
            "7": ("RU", "Russia"),
            "48": ("PL", "Poland"),
            "91": ("IN", "India"),
            "86": ("CN", "China"),
            "81": ("JP", "Japan"),
            "82": ("KR", "South Korea"),
            "61": ("AU", "Australia"),
            "34": ("ES", "Spain"),
            "39": ("IT", "Italy"),
            "31": ("NL", "Netherlands"),
            "65": ("SG", "Singapore"),
            "977": ("NP", "Nepal"),
        }

        country_info = country_map.get(country_code)
        if not country_info:
            self.log.warning(f"Unknown country code: {country_code}, skipping selection")
            return

        iso_code, country_name = country_info
        # Airbnb select value format: {dial_code}{ISO_code} e.g., "380UA"
        select_value = f"{country_code}{iso_code}"
        self.log.info(f"Selecting country: {country_name} (+{country_code}) - value: {select_value}")

        try:
            # The country selector is a native <select> element
            select_selectors = [
                'select[data-testid="login-signup-countrycode"]',
                'select#country',
                'select[id*="country"]',
            ]

            for selector in select_selectors:
                try:
                    select_element = self.page.locator(selector).first
                    if await select_element.is_visible(timeout=3000):
                        self.log.debug(f"Found country select: {selector}")
                        # Use Playwright's select_option to select by value
                        await select_element.select_option(value=select_value)
                        self.log.info(f"Selected country: {country_name} (+{country_code})")
                        await self.page.wait_for_timeout(500)
                        return
                except PlaywrightTimeout:
                    continue

            self.log.error(f"Could not find country select element")

        except Exception as e:
            self.log.error(f"Country selection failed: {e}")

    async def enter_phone_number(self, phone: PhoneNumber) -> None:
        """
        Enter the phone number for signup.

        Args:
            phone: PhoneNumber object with the number to enter.
        """
        self.log.info(f"Entering phone number: {phone.formatted}")

        # Select country code first
        await self.select_country_code(phone.country_code)

        # Find and fill the phone input
        phone_selectors = [
            'input[type="tel"]',
            'input[name="phoneNumber"]',
            'input[placeholder*="Phone"]',
            'input[autocomplete="tel"]',
        ]

        for selector in phone_selectors:
            try:
                phone_input = self.page.locator(selector).first
                if await phone_input.is_visible(timeout=3000):
                    # Clear and enter number
                    await phone_input.click()
                    await phone_input.fill("")
                    # Enter local number (without country code)
                    number_to_enter = phone.local_number or phone.number
                    self.log.debug(f"Typing number: {number_to_enter}")
                    await phone_input.type(number_to_enter, delay=50)
                    self.log.info("Phone number entered successfully")
                    return
            except PlaywrightTimeout:
                continue

        raise RuntimeError("Phone input field not found")

    async def click_continue(self) -> None:
        """Click the continue button."""
        self.log.info("Clicking continue button...")

        continue_selectors = [
            'button:has-text("Continue")',
            'button[type="submit"]',
            '[data-testid="signup-login-submit-btn"]',
        ]

        for selector in continue_selectors:
            try:
                btn = self.page.locator(selector).first
                if await btn.is_visible(timeout=3000):
                    # Check if button is enabled
                    is_disabled = await btn.get_attribute("disabled")
                    if is_disabled:
                        self.log.warning("Continue button is disabled")
                        await self.page.wait_for_timeout(1000)

                    await btn.click()
                    self.log.info(f"Clicked continue: {selector}")
                    return
            except PlaywrightTimeout:
                continue

        raise RuntimeError("Continue button not found")

    # -------------------------------------------------------------------------
    # OTP Verification
    # -------------------------------------------------------------------------

    async def wait_for_otp_screen(self, timeout: int = 30000) -> bool:
        """
        Wait for the OTP verification screen.

        IMPORTANT: Checks for error messages FIRST before checking for OTP indicators.
        This prevents false positives when error text appears on same page as "Confirm your number".

        Args:
            timeout: Maximum time to wait.

        Returns:
            True if OTP screen appeared AND no errors (SMS was sent).
            False if error/captcha appeared (phone failed).
        """
        self.log.info("Waiting for OTP screen or error message...")

        # Known failure messages - check these FIRST before anything else!
        # These take priority over any OTP indicators
        failure_texts = [
            "you've reached the max confirmation attempts",
            "max confirmation attempts",
            "try again in 24 hours",
            "phone number isn't supported",
            "isn't supported",
            "not supported",
            "sign up using a different method",
            "different method",
            "too many attempts",
            "rate limit",
            "temporarily blocked",
            "try again later",
            "something went wrong",
            "we couldn't send",
            "couldn't send a code",
            "unable to send",
            "invalid phone",
            "phone number is invalid",
        ]

        # Captcha indicators (also means failure)
        captcha_indicators = [
            'iframe[src*="captcha"]',
            'iframe[src*="arkoselabs"]',
            'iframe[src*="funcaptcha"]',
            '#captcha',
            '[data-testid="captcha"]',
            'div:has-text("verify you\'re human")',
            'div:has-text("security check")',
        ]

        # OTP success text - this ONLY appears when SMS was actually sent
        otp_success_text = "enter the code we sent over sms to"

        # OTP input indicators (backup check)
        otp_indicators = [
            'input[inputmode="numeric"]',
            'input[autocomplete="one-time-code"]',
        ]

        check_interval = 1000  # Check every 1 second
        elapsed = 0

        while elapsed < timeout:
            # ============================================================
            # STEP 1: Check for ERROR text FIRST (highest priority)
            # ============================================================
            try:
                page_text = await self.page.inner_text('body')
                page_text_lower = page_text.lower()

                for failure_text in failure_texts:
                    if failure_text.lower() in page_text_lower:
                        self.log.error(f"=" * 50)
                        self.log.error(f"FAILURE DETECTED!")
                        self.log.error(f"Error text found: '{failure_text}'")
                        self.log.error(f"=" * 50)
                        return False
            except Exception as e:
                self.log.warning(f"Error checking page text: {e}")

            # ============================================================
            # STEP 2: Check for CAPTCHA (second priority)
            # ============================================================
            for captcha_sel in captcha_indicators:
                try:
                    captcha = self.page.locator(captcha_sel).first
                    if await captcha.is_visible(timeout=300):
                        self.log.error(f"CAPTCHA detected: {captcha_sel}")
                        return False
                except:
                    continue

            # ============================================================
            # STEP 3: Check for OTP SUCCESS text
            # "Enter the code we sent over SMS to" - confirms SMS was sent
            # ============================================================
            if otp_success_text in page_text_lower:
                self.log.info("=" * 50)
                self.log.info("SUCCESS: Found 'Enter the code we sent over SMS to'")
                self.log.info("SMS was sent successfully!")
                self.log.info("=" * 50)
                return True

            # Backup: check for OTP input field
            for otp_sel in otp_indicators:
                try:
                    otp_element = self.page.locator(otp_sel).first
                    if await otp_element.is_visible(timeout=300):
                        # Double-check page text for the success message
                        page_text_recheck = await self.page.inner_text('body')
                        page_text_lower_recheck = page_text_recheck.lower()

                        # Check for success text
                        if otp_success_text in page_text_lower_recheck:
                            self.log.info("SUCCESS: OTP input + success text found")
                            return True

                        # Check for errors
                        has_error = False
                        for failure_text in failure_texts:
                            if failure_text.lower() in page_text_lower_recheck:
                                self.log.error(f"Error found on recheck: '{failure_text}'")
                                has_error = True
                                break

                        if has_error:
                            return False

                        # Input found but no success text - might be loading, continue waiting
                        self.log.debug(f"OTP input found but no success text yet, waiting...")
                except:
                    continue

            # Wait before next check
            await self.page.wait_for_timeout(check_interval)
            elapsed += check_interval
            self.log.debug(f"Waiting for OTP/error... {elapsed//1000}s / {timeout//1000}s")

        self.log.warning(f"Timeout after {timeout//1000}s - no OTP screen or error detected")
        return False

    async def enter_otp(self, otp_code: str) -> None:
        """
        Enter the OTP verification code.

        Args:
            otp_code: The verification code to enter.
        """
        self.log.info(f"Entering OTP code: {otp_code}")

        # Try to find OTP input fields
        # First try: single input field
        single_input_selectors = [
            'input[autocomplete="one-time-code"]',
            'input[name="code"]',
            'input[name="otp"]',
        ]

        for selector in single_input_selectors:
            try:
                otp_input = self.page.locator(selector).first
                if await otp_input.is_visible(timeout=2000):
                    await otp_input.fill(otp_code)
                    self.log.info("Entered OTP in single field")
                    return
            except PlaywrightTimeout:
                continue

        # Second try: multiple numeric inputs
        try:
            numeric_inputs = self.page.locator('input[inputmode="numeric"]')
            count = await numeric_inputs.count()

            if count > 0:
                self.log.debug(f"Found {count} numeric input fields")
                # Click the first input to focus
                await numeric_inputs.first.click()
                # Type the code - it should auto-advance
                await self.page.keyboard.type(otp_code, delay=100)
                self.log.info("Entered OTP via numeric inputs")
                return
        except Exception as e:
            self.log.warning(f"Numeric input entry failed: {e}")

        # Last resort: just type on keyboard
        self.log.warning("Attempting keyboard entry as fallback")
        await self.page.keyboard.type(otp_code, delay=150)

    async def click_verify(self) -> None:
        """Click the verify/submit button for OTP."""
        self.log.info("Looking for verify button...")

        verify_selectors = [
            'button:has-text("Continue")',
            'button:has-text("Verify")',
            'button:has-text("Submit")',
            'button[type="submit"]',
        ]

        for selector in verify_selectors:
            try:
                btn = self.page.locator(selector).first
                if await btn.is_visible(timeout=2000):
                    await btn.click()
                    self.log.info(f"Clicked verify: {selector}")
                    return
            except PlaywrightTimeout:
                continue

        self.log.warning("Verify button not found - OTP may auto-submit")

    # -------------------------------------------------------------------------
    # Profile Completion
    # -------------------------------------------------------------------------

    async def wait_for_profile_form(self, timeout: int = 15000) -> bool:
        """
        Wait for the profile completion form.

        Args:
            timeout: Maximum time to wait.

        Returns:
            True if profile form appeared.
        """
        self.log.info("Waiting for profile form...")

        profile_indicators = [
            'input[name="firstName"]',
            'input[autocomplete="given-name"]',
            'input[placeholder*="First name"]',
            'div:has-text("Finish signing up")',
        ]

        for selector in profile_indicators:
            try:
                await self.page.wait_for_selector(selector, timeout=timeout // len(profile_indicators))
                self.log.info(f"Profile form detected with: {selector}")
                return True
            except PlaywrightTimeout:
                continue

        self.log.warning("Profile form not detected")
        return False

    async def fill_profile(self, profile: UserProfile) -> None:
        """Fill in the user profile information."""
        self.log.info(f"Filling profile for: {profile.full_name}")

        # First name
        await self._fill_field('input[name="firstName"], input[autocomplete="given-name"]', profile.first_name, "First name")

        # Last name
        await self._fill_field('input[name="lastName"], input[autocomplete="family-name"]', profile.last_name, "Last name")

        # Email (if visible)
        await self._fill_field('input[type="email"], input[name="email"]', profile.email, "Email")

        # Password (if visible)
        await self._fill_field('input[type="password"]', profile.password, "Password")

        # Birth date
        if profile.birth_date:
            await self._fill_birth_date(profile)

        self.log.info("Profile form filled")

    async def _fill_field(self, selector: str, value: str, field_name: str) -> None:
        """Fill a field if visible."""
        try:
            field = self.page.locator(selector).first
            if await field.is_visible(timeout=2000):
                await field.fill(value)
                self.log.debug(f"Filled {field_name}")
        except PlaywrightTimeout:
            self.log.debug(f"{field_name} field not visible")

    async def _fill_birth_date(self, profile: UserProfile) -> None:
        """Fill birth date fields."""
        self.log.debug("Filling birth date...")

        # Try select dropdowns first
        try:
            # Month
            month_sel = self.page.locator('select[name="month"]').first
            if await month_sel.is_visible(timeout=1000):
                await month_sel.select_option(index=profile.birth_month or 6)

            # Day
            day_sel = self.page.locator('select[name="day"]').first
            if await day_sel.is_visible(timeout=1000):
                await day_sel.select_option(value=str(profile.birth_day or 15))

            # Year
            year_sel = self.page.locator('select[name="year"]').first
            if await year_sel.is_visible(timeout=1000):
                await year_sel.select_option(value=str(profile.birth_year or 1990))

            self.log.debug("Birth date filled via selects")
            return
        except PlaywrightTimeout:
            pass

        # Try input fields
        try:
            birthdate_input = self.page.locator('input[name="birthdate"]').first
            if await birthdate_input.is_visible(timeout=1000):
                date_str = profile.birth_date.strftime("%m/%d/%Y")
                await birthdate_input.fill(date_str)
                self.log.debug("Birth date filled via input")
        except PlaywrightTimeout:
            self.log.debug("Birth date fields not found")

    async def agree_and_continue(self) -> None:
        """Click agree and continue."""
        self.log.info("Looking for agree/submit button...")

        agree_selectors = [
            'button:has-text("Agree and continue")',
            'button:has-text("Sign up")',
            'button:has-text("Create account")',
            'button[type="submit"]',
        ]

        for selector in agree_selectors:
            try:
                btn = self.page.locator(selector).first
                if await btn.is_visible(timeout=3000):
                    await btn.click()
                    self.log.info(f"Clicked: {selector}")
                    return
            except PlaywrightTimeout:
                continue

        self.log.warning("Agree button not found")

    # -------------------------------------------------------------------------
    # Error Handling & Success
    # -------------------------------------------------------------------------

    async def has_error(self) -> bool:
        """Check if there's an error message displayed."""
        error_selectors = [
            '[role="alert"]',
            'div[class*="error"]',
            '[data-testid="error-message"]',
        ]

        for selector in error_selectors:
            try:
                error = self.page.locator(selector).first
                if await error.is_visible(timeout=1000):
                    return True
            except PlaywrightTimeout:
                continue

        return False

    async def get_error_message(self) -> str | None:
        """Get the current error message if any."""
        # Known error patterns to look for in page text
        error_patterns = [
            "max confirmation attempts",
            "Try again in 24 hours",
            "phone number isn't supported",
            "sign up using a different method",
            "too many attempts",
            "temporarily blocked",
            "try again later",
            "invalid phone",
            "verify you're human",
        ]

        # First check page text for known error patterns
        try:
            page_text = await self.page.inner_text('body')
            page_text_lower = page_text.lower()
            for pattern in error_patterns:
                if pattern.lower() in page_text_lower:
                    return pattern
        except:
            pass

        # Then check error elements
        error_selectors = [
            '[role="alert"]',
            'div[class*="error"]',
            '[data-testid="error-message"]',
            'div[class*="Error"]',
            'span[class*="error"]',
        ]

        for selector in error_selectors:
            try:
                error = self.page.locator(selector).first
                if await error.is_visible(timeout=1000):
                    text = await error.text_content()
                    return text.strip() if text else None
            except PlaywrightTimeout:
                continue

        return None

    async def is_signup_successful(self) -> bool:
        """Check if signup was successful."""
        self.log.info("Checking for signup success...")

        success_indicators = [
            'div:has-text("You\'re all set")',
            'h1:has-text("Welcome")',
            '[data-testid="signup-success"]',
        ]

        for selector in success_indicators:
            try:
                element = self.page.locator(selector).first
                if await element.is_visible(timeout=2000):
                    self.log.info(f"Success indicator found: {selector}")
                    return True
            except PlaywrightTimeout:
                continue

        # Check if modal closed (indicates success)
        if not await self.is_signup_modal_visible():
            self.log.info("Modal closed - assuming success")
            return True

        return False
