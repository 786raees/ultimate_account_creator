"""
Airbnb Selectors
================

Centralized selector definitions for Airbnb pages.
Keeping selectors separate makes maintenance easier when
the UI changes.

Updated: December 2025 to match current Airbnb UI
"""


class HomePageSelectors:
    """Selectors for the Airbnb home page."""

    # Navigation - profile/menu button in top right (has hamburger menu icon + profile avatar)
    NAVBAR = 'header nav'
    # Target specifically by data-testid or aria-label for "Main navigation menu"
    PROFILE_MENU = 'button[data-testid="cypress-headernav-profile"], button[aria-label="Main navigation menu"]'

    # Page identifiers
    SEARCH_BAR = '[data-testid="structured-search-input-field-query"], input[placeholder*="Search"]'
    LOGO = 'a[aria-label="Airbnb homepage"], a[href="/"]'


class SignupPageSelectors:
    """Selectors for the Airbnb signup flow."""

    # Signup modal - multiple possible selectors for the modal dialog
    SIGNUP_MODAL = (
        '[role="dialog"], '
        '[aria-modal="true"], '
        'div[data-testid="login-pane"], '
        'div:has(> h3:text("Log in or sign up")), '
        'div:has(> div:text("Welcome to Airbnb"))'
    )

    # Modal header text indicators - multi-language
    MODAL_HEADER = (
        'h3:has-text("Log in or sign up"), '
        'div:has-text("Log in or sign up"), '
        'h3:has-text("Увійдіть або зареєструйтеся"), '  # Ukrainian
        'div:has-text("Увійдіть або зареєструйтеся"), '
        'h3:has-text("Войдите или зарегистрируйтесь"), '  # Russian
        'div:has-text("Войдите или зарегистрируйтесь")'
    )
    WELCOME_TEXT = (
        'div:has-text("Welcome to Airbnb"), '
        'h1:has-text("Welcome to Airbnb"), '
        'div:has-text("Ласкаво просимо"), '  # Ukrainian: Welcome
        'h1:has-text("Ласкаво просимо"), '
        'div:has-text("Добро пожаловать"), '  # Russian: Welcome
        'h1:has-text("Добро пожаловать")'
    )

    # Close button
    MODAL_CLOSE = 'button[aria-label="Close"], [data-testid="modal-close"]'

    # Country code selector (dropdown for phone country)
    COUNTRY_CODE_BUTTON = (
        'button:has-text("+"), '
        '[data-testid="country-picker"], '
        'button[id*="country"]'
    )
    COUNTRY_CODE_DROPDOWN = '[role="listbox"], [data-testid="country-list"]'
    COUNTRY_OPTION = '[role="option"]'

    # Phone number input - main phone field
    PHONE_INPUT = (
        'input[type="tel"], '
        'input[name="phoneNumber"], '
        'input[placeholder*="Phone"], '
        'input[autocomplete="tel"]'
    )

    # Continue button - main CTA - multi-language
    CONTINUE_BUTTON = (
        'button[data-testid="signup-login-submit-btn"], '
        'button:has-text("Continue"), '
        'button:has-text("Продовжити"), '  # Ukrainian: Continue
        'button:has-text("Далі"), '  # Ukrainian: Next
        'button:has-text("Продолжить"), '  # Russian: Continue
        'button:has-text("Далее"), '  # Russian: Next
        'button[type="submit"]'
    )

    # Social login options
    CONTINUE_WITH_EMAIL = (
        'button:has-text("Continue with email"), '
        'div[role="button"]:has-text("email")'
    )
    CONTINUE_WITH_GOOGLE = 'button:has-text("Continue with Google")'
    CONTINUE_WITH_APPLE = 'button:has-text("Continue with Apple")'
    CONTINUE_WITH_FACEBOOK = 'button:has-text("Continue with Facebook")'

    # Profile form fields (after OTP verification)
    FIRST_NAME_INPUT = (
        'input[name="firstName"], '
        'input[autocomplete="given-name"], '
        'input[placeholder*="First name"]'
    )
    LAST_NAME_INPUT = (
        'input[name="lastName"], '
        'input[autocomplete="family-name"], '
        'input[placeholder*="Last name"]'
    )
    EMAIL_INPUT = (
        'input[type="email"], '
        'input[name="email"], '
        'input[autocomplete="email"]'
    )
    PASSWORD_INPUT = (
        'input[type="password"], '
        'input[name="password"]'
    )

    # Birth date fields
    BIRTH_DATE_MONTH = 'select[name="month"], [data-testid="birth-date-month"]'
    BIRTH_DATE_DAY = 'select[name="day"], [data-testid="birth-date-day"], input[placeholder*="Day"]'
    BIRTH_DATE_YEAR = 'select[name="year"], [data-testid="birth-date-year"], input[placeholder*="Year"]'
    BIRTHDATE_INPUT = 'input[name="birthdate"], input[placeholder*="Birthdate"]'

    # Agreement and submit
    AGREE_AND_CONTINUE = (
        'button:has-text("Agree and continue"), '
        'button:has-text("Sign up"), '
        'button:has-text("Create account")'
    )

    # Error messages
    ERROR_MESSAGE = (
        '[data-testid="error-message"], '
        '[role="alert"], '
        'div[class*="error"], '
        'span[class*="error"]'
    )
    INLINE_ERROR = '[data-testid="inline-error"], div[class*="error-text"]'

    # Success indicators
    SIGNUP_SUCCESS = '[data-testid="signup-success"]'
    WELCOME_MESSAGE = 'h1:has-text("Welcome"), div:has-text("You\'re all set")'

    # Loading states
    LOADING_SPINNER = '[data-testid="loading-spinner"], [class*="loading"], [class*="spinner"]'


class OTPSelectors:
    """Selectors for OTP/verification code entry."""

    # OTP screen indicators - multi-language
    OTP_SCREEN = (
        'div:has-text("Enter the code"), '
        'div:has-text("Confirm your number"), '
        'div:has-text("verification code"), '
        'div:has-text("Введіть код"), '  # Ukrainian: Enter the code
        'div:has-text("Підтвердіть номер"), '  # Ukrainian: Confirm your number
        'div:has-text("код підтвердження"), '  # Ukrainian: verification code
        'div:has-text("Введите код"), '  # Russian: Enter the code
        'div:has-text("Подтвердите номер"), '  # Russian: Confirm your number
        'div:has-text("код подтверждения")'  # Russian: verification code
    )

    # Code/OTP heading - multi-language
    CODE_HEADING = (
        'h1:has-text("Confirm your number"), '
        'h2:has-text("Enter code"), '
        'div:has-text("Enter the code we"), '
        'h1:has-text("Підтвердіть номер"), '  # Ukrainian
        'h2:has-text("Введіть код"), '  # Ukrainian
        'div:has-text("Введіть код"), '  # Ukrainian
        'h1:has-text("Подтвердите номер"), '  # Russian
        'h2:has-text("Введите код"), '  # Russian
        'div:has-text("Введите код")'  # Russian
    )

    # OTP input fields - could be single or multiple inputs
    OTP_INPUT_SINGLE = (
        'input[name="code"], '
        'input[name="otp"], '
        'input[autocomplete="one-time-code"], '
        'input[inputmode="numeric"]'
    )

    # Multiple OTP input fields (for 4-6 digit codes)
    OTP_INPUT_FIRST = 'input[data-index="0"], input:first-of-type[inputmode="numeric"]'
    OTP_INPUTS_ALL = 'input[inputmode="numeric"], input[data-testid*="otp"]'

    # Verify/Submit button
    VERIFY_BUTTON = (
        'button:has-text("Verify"), '
        'button:has-text("Submit"), '
        'button:has-text("Continue"), '
        'button[type="submit"]'
    )

    # Resend code
    RESEND_CODE = (
        'button:has-text("Resend"), '
        'button:has-text("send again"), '
        'a:has-text("Resend"), '
        'button:has-text("I didn\'t get a code")'
    )

    # Error message for wrong code
    CODE_ERROR = (
        '[data-testid="otp-error"], '
        'div:has-text("incorrect code"), '
        'div:has-text("wrong code"), '
        '[role="alert"]'
    )
