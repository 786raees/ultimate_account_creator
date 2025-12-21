"""
Airbnb Signup Automation - Selenium + MultiLoginX
Same flow as before, just using Selenium instead of Playwright
"""

import requests
import time
import random
import csv
from datetime import datetime
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException


# ============================================================
# CONFIGURATION
# ============================================================

MLX_URL = "https://launcher.mlx.yt:45001/api/v2/profile/quick"
MLX_TOKEN = "Bearer eyJhbGciOiJIUzUxMiJ9.eyJicGRzLmJ1Y2tldCI6Im1seC1icGRzLXByb2QtZXUtMSIsIm1hY2hpbmVJRCI6IiIsInByb2R1Y3RJRCI6Im11bHRpbG9naW4iLCJ3b3Jrc3BhY2VSb2xlIjoib3duZXIiLCJ2ZXJpZmllZCI6dHJ1ZSwicGxhbk5hbWUiOiJTb2xvIiwic2hhcmRJRCI6ImNiZTEzODAwLWJiYWYtNGM4Zi04MGIzLTE5N2Y4OTYzOTRmMiIsInVzZXJJRCI6Ijg3Y2YyMTYwLWJhZDYtNGM0Mi1iNGFkLWQ4ZTE1MWYzN2Y0YyIsImVtYWlsIjoid2FxYXJraGFuMTI1MjYxN0BnbWFpbC5jb20iLCJpc0F1dG9tYXRpb24iOmZhbHNlLCJ3b3Jrc3BhY2VJRCI6ImNiMmFlZjZmLWY3ZTYtNGM0ZC04ZWYyLWQwNDI1MDIzZTk0ZSIsImp0aSI6IjI2YjYyMTJhLTljZDItNDhmYy1iMGUzLTIwODI3Y2MxZmYzOSIsInN1YiI6Ik1MWCIsImlzcyI6Ijg3Y2YyMTYwLWJhZDYtNGM0Mi1iNGFkLWQ4ZTE1MWYzN2Y0YyIsImlhdCI6MTc2NjI4MDkxMywiZXhwIjoxNzY2Mjg0NTEzfQ.9z3dsBAyZFYbiXqQ4bdYfPT3w-6UoDjb1OAkVk2CKBqZZ7TkuXlN2RfZqiNCRvnJxzhDe12Mmc0CAi5qcdHuLg"

# Proxy settings
PROXY_HOST = "gate.decodo.com"
PROXY_USER = "spcujh3425"
PROXY_PASS = "mmZxuBgSiW71vs65~e"

# Files
PHONES_FILE = Path("data/phones/airbnb_phones.txt")
USED_PHONES_CSV = Path("data/state/used_phones.csv")

# Country mapping - SAME as signup_page.py
COUNTRY_MAP = {
    "380": ("UA", "Ukraine"),
    "375": ("BY", "Belarus"),
    "261": ("MG", "Madagascar"),
    "962": ("JO", "Jordan"),
    "972": ("IL", "Israel"),
    "855": ("KH", "Cambodia"),
    "229": ("BJ", "Benin"),
    "1": ("US", "United States"),
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


# ============================================================
# PHONE NUMBER PARSING - Same logic as PhoneNumber model
# ============================================================

def parse_phone(number: str) -> dict:
    """Parse phone number into country code and local number."""
    # Remove any + prefix
    number = number.lstrip("+")

    # Try to find matching country code (longest match first)
    for code in sorted(COUNTRY_MAP.keys(), key=len, reverse=True):
        if number.startswith(code):
            iso, name = COUNTRY_MAP[code]
            return {
                "number": number,
                "country_code": code,
                "local_number": number[len(code):],
                "iso": iso,
                "country_name": name,
                "formatted": f"+{number}",
            }

    # Default to US if no match
    return {
        "number": number,
        "country_code": "1",
        "local_number": number,
        "iso": "US",
        "country_name": "United States",
        "formatted": f"+{number}",
    }


# ============================================================
# MULTILOGINX - Same proxy logic
# ============================================================

def get_rotated_port():
    """Get random port for proxy rotation (10001-10100)."""
    return random.randint(10001, 10100)


def create_profile(country_iso: str):
    """Create MLX quick profile with country-targeted proxy."""

    proxy_port = get_rotated_port()
    proxy_user = f"user-{PROXY_USER}-country-{country_iso.lower()}"

    print(f"Creating MLX profile...")
    print(f"  Proxy: {PROXY_HOST}:{proxy_port}")
    print(f"  Proxy User: {proxy_user}")
    print(f"  Country: {country_iso}")

    headers = {
        "accept": "application/json",
        "authorization": MLX_TOKEN,
        "content-type": "application/json",
    }

    payload = {
        "automation": "selenium",
        "browser_type": "mimic",
        "os_type": "windows",
        "parameters": {
            "flags": {
                "navigator_masking": "mask",
                "audio_masking": "natural",
                "localization_masking": "mask",
                "geolocation_popup": "prompt",
                "geolocation_masking": "mask",
                "timezone_masking": "mask",
                "graphics_noise": "mask",
                "graphics_masking": "mask",
                "webrtc_masking": "mask",
                "fonts_masking": "mask",
                "media_devices_masking": "natural",
                "screen_masking": "mask",
                "proxy_masking": "custom",
                "ports_masking": "mask",
            },
            "fingerprint": {},
            "storage": {},
            "proxy": {
                "host": PROXY_HOST,
                "type": "http",
                "port": proxy_port,
                "username": proxy_user,
                "password": PROXY_PASS,
            },
        },
    }

    response = requests.post(MLX_URL, headers=headers, json=payload, verify=False)
    result = response.json()

    if result.get("status", {}).get("http_code") == 200:
        profile_id = result["data"]["id"]
        port = result["data"]["port"]
        print(f"  Profile ID: {profile_id}")
        print(f"  Selenium Port: {port}")
        return profile_id, port
    else:
        print(f"  FAILED: {result}")
        return None, None


def stop_profile(profile_id):
    """Stop MLX profile."""
    url = f"https://launcher.mlx.yt:45001/api/v1/profile/stop?profile_id={profile_id}"
    headers = {"authorization": MLX_TOKEN}
    try:
        requests.get(url, headers=headers, verify=False)
        print(f"Profile stopped: {profile_id}")
    except Exception as e:
        print(f"Error stopping profile: {e}")


def connect_browser(port):
    """Connect Selenium to MLX browser."""
    options = Options()
    driver = webdriver.Remote(
        command_executor=f"http://127.0.0.1:{port}",
        options=options,
    )
    return driver


# ============================================================
# PHONE MANAGEMENT - Same as phone_manager.py
# ============================================================

def load_phones():
    """Load phone numbers from file."""
    phones = []
    with open(PHONES_FILE, "r") as f:
        for line in f:
            num = line.strip()
            if num:
                phones.append(parse_phone(num))
    print(f"Loaded {len(phones)} phone numbers")
    return phones


def load_used_phones():
    """Load used phone numbers from CSV."""
    used = set()
    if USED_PHONES_CSV.exists():
        with open(USED_PHONES_CSV, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                phone = row.get("phone_number", "").strip()
                if phone:
                    used.add(phone)
    return used


def save_phone_result(phone: dict, success: bool):
    """Save phone result to CSV."""
    USED_PHONES_CSV.parent.mkdir(parents=True, exist_ok=True)

    file_exists = USED_PHONES_CSV.exists()

    with open(USED_PHONES_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["phone_number", "used_at", "platform", "success"])
        writer.writerow([
            phone["number"],
            datetime.now().isoformat(),
            "airbnb",
            str(success)
        ])

    status = "SUCCESS" if success else "FAILED"
    print(f"Saved {phone['formatted']} as {status}")


# ============================================================
# AIRBNB SIGNUP - Same selectors and flow as signup_page.py
# ============================================================

def wait_for_element(driver, selectors, timeout=10):
    """Wait for any of the selectors to be visible."""
    wait = WebDriverWait(driver, timeout)

    # Convert Playwright selectors to CSS
    for sel in selectors:
        # Remove Playwright-specific syntax
        css = sel.replace(':has-text(', '[*=').replace(')', ']')
        if ':has-text' in sel or 'text=' in sel:
            continue  # Skip text-based selectors, handle separately
        try:
            return wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, css)))
        except TimeoutException:
            continue
    return None


def find_element(driver, selectors):
    """Find element using multiple selectors."""
    for sel in selectors:
        try:
            # Try CSS selector
            el = driver.find_element(By.CSS_SELECTOR, sel)
            if el.is_displayed():
                return el
        except NoSuchElementException:
            continue
    return None


def select_country_code(driver, phone: dict):
    """Select country code from dropdown - SAME logic as signup_page.py"""
    country_code = phone["country_code"]
    iso_code = phone["iso"]
    select_value = f"{country_code}{iso_code}"

    print(f"  Selecting country: {phone['country_name']} (+{country_code})")

    select_selectors = [
        'select[data-testid="login-signup-countrycode"]',
        'select#country',
        'select[id*="country"]',
    ]

    for sel in select_selectors:
        try:
            from selenium.webdriver.support.ui import Select
            select_el = driver.find_element(By.CSS_SELECTOR, sel)
            if select_el.is_displayed():
                select = Select(select_el)
                select.select_by_value(select_value)
                print(f"  Country selected: {select_value}")
                time.sleep(0.5)
                return True
        except Exception as e:
            continue

    print(f"  Could not find country selector")
    return False


def enter_phone_number(driver, phone: dict):
    """Enter phone number - SAME selectors as signup_page.py"""
    print(f"  Entering phone: {phone['formatted']}")

    phone_selectors = [
        'input[type="tel"]',
        'input[name="phoneNumber"]',
        'input[autocomplete="tel"]',
    ]

    for sel in phone_selectors:
        try:
            input_el = driver.find_element(By.CSS_SELECTOR, sel)
            if input_el.is_displayed():
                input_el.clear()
                input_el.send_keys(phone["local_number"])
                print(f"  Phone entered: {phone['local_number']}")
                return True
        except NoSuchElementException:
            continue

    print("  Phone input not found!")
    return False


def click_continue(driver):
    """Click continue button - SAME selectors as signup_page.py"""
    print("  Clicking continue...")

    continue_selectors = [
        'button[data-testid="signup-login-submit-btn"]',
        'button[type="submit"]',
    ]

    # Also try by text
    try:
        buttons = driver.find_elements(By.TAG_NAME, "button")
        for btn in buttons:
            text = btn.text.lower()
            if "continue" in text or "продовжити" in text or "далі" in text:
                if btn.is_displayed() and btn.is_enabled():
                    btn.click()
                    print("  Continue clicked (by text)")
                    return True
    except:
        pass

    for sel in continue_selectors:
        try:
            btn = driver.find_element(By.CSS_SELECTOR, sel)
            if btn.is_displayed() and btn.is_enabled():
                btn.click()
                print("  Continue clicked")
                return True
        except NoSuchElementException:
            continue

    print("  Continue button not found!")
    return False


def wait_for_otp_screen(driver, timeout=120):
    """Wait for OTP screen - SAME indicators as signup_page.py"""
    print("  Waiting for OTP screen...")

    otp_indicators = [
        'input[inputmode="numeric"]',
        'input[autocomplete="one-time-code"]',
    ]

    wait = WebDriverWait(driver, timeout)

    for sel in otp_indicators:
        try:
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, sel)))
            print("  OTP screen detected!")
            return True
        except TimeoutException:
            continue

    # Check by text
    try:
        body = driver.find_element(By.TAG_NAME, "body").text.lower()
        if "enter the code" in body or "confirm your number" in body or "verification" in body:
            print("  OTP screen detected (by text)!")
            return True
    except:
        pass

    return False


def wait_for_profile_form(driver, timeout=30):
    """Wait for profile form after OTP - SAME as signup_page.py"""
    print("  Waiting for profile form...")

    profile_indicators = [
        'input[name="firstName"]',
        'input[autocomplete="given-name"]',
    ]

    wait = WebDriverWait(driver, timeout)

    for sel in profile_indicators:
        try:
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, sel)))
            print("  Profile form detected!")
            return True
        except TimeoutException:
            continue

    return False


def check_for_error(driver):
    """Check if there's an error message."""
    error_selectors = [
        '[role="alert"]',
        'div[class*="error"]',
        '[data-testid="error-message"]',
    ]

    for sel in error_selectors:
        try:
            el = driver.find_element(By.CSS_SELECTOR, sel)
            if el.is_displayed():
                return el.text
        except NoSuchElementException:
            continue

    return None


def do_signup(driver, phone: dict):
    """
    Perform Airbnb signup - SAME FLOW as signup_orchestrator.py
    """
    print(f"\n{'='*60}")
    print(f"STARTING SIGNUP: {phone['formatted']}")
    print(f"Country: {phone['country_name']} ({phone['iso']})")
    print(f"{'='*60}")

    try:
        # STEP 1: Navigate to signup
        print("\nSTEP 1: Navigate to signup page")
        driver.get("https://www.airbnb.com/signup_login")
        time.sleep(3)
        print(f"  URL: {driver.current_url}")

        # STEP 2: Wait for signup form
        print("\nSTEP 2: Wait for signup form")
        time.sleep(2)

        # Check if phone input is visible
        try:
            phone_input = driver.find_element(By.CSS_SELECTOR, 'input[type="tel"]')
            if phone_input.is_displayed():
                print("  Signup form visible!")
        except NoSuchElementException:
            print("  Signup form not found!")
            return False

        # STEP 3: Select country and enter phone
        print("\nSTEP 3: Enter phone number")
        select_country_code(driver, phone)
        time.sleep(1)

        if not enter_phone_number(driver, phone):
            return False
        time.sleep(1)

        # STEP 4: Click continue
        print("\nSTEP 4: Click continue")
        if not click_continue(driver):
            return False
        time.sleep(3)

        # Check for errors
        error = check_for_error(driver)
        if error:
            print(f"  ERROR: {error}")
            return False

        # STEP 5: Wait for OTP
        print("\nSTEP 5: Wait for OTP screen")
        if not wait_for_otp_screen(driver, timeout=30):
            print("  OTP screen not detected!")
            error = check_for_error(driver)
            if error:
                print(f"  ERROR: {error}")
            return False

        # STEP 6: Manual OTP entry
        print("\n" + "="*60)
        print("MANUAL OTP ENTRY REQUIRED")
        print(f"Phone: {phone['formatted']}")
        print("Enter OTP in browser, then wait for profile form...")
        print("="*60)

        # Wait for profile form (indicates OTP was entered correctly)
        if not wait_for_profile_form(driver, timeout=120):
            print("  Timeout waiting for profile form!")
            return False

        print("\nOTP verified! Profile form appeared.")

        # STEP 7: Ask user to complete profile
        print("\n" + "="*60)
        print("COMPLETE PROFILE IN BROWSER")
        print("="*60)
        result = input("Did signup succeed? (y/n): ").strip().lower()

        return result == "y"

    except Exception as e:
        print(f"\nERROR: {e}")
        return False


# ============================================================
# MAIN LOOP
# ============================================================

def main():
    """Main signup loop."""
    print("="*60)
    print("AIRBNB SIGNUP AUTOMATION")
    print("="*60)

    # Load phones
    all_phones = load_phones()
    used_phones = load_used_phones()

    # Filter available phones
    phones = [p for p in all_phones if p["number"] not in used_phones]
    print(f"Available: {len(phones)} | Used: {len(used_phones)} | Total: {len(all_phones)}")

    if not phones:
        print("No phones available!")
        return

    # Process each phone
    for i, phone in enumerate(phones):
        print(f"\n{'#'*60}")
        print(f"# PHONE {i+1}/{len(phones)}: {phone['formatted']}")
        print(f"{'#'*60}")

        profile_id = None
        driver = None

        try:
            # Create MLX profile with country-targeted proxy
            profile_id, port = create_profile(phone["iso"])
            if not profile_id:
                save_phone_result(phone, success=False)
                continue

            # Wait for browser
            time.sleep(3)

            # Connect Selenium
            driver = connect_browser(port)
            print("Connected to browser")

            # Do signup
            success = do_signup(driver, phone)

            # Save result
            save_phone_result(phone, success=success)

        except Exception as e:
            print(f"ERROR: {e}")
            save_phone_result(phone, success=False)

        finally:
            # Close browser
            if driver:
                try:
                    driver.quit()
                    print("Browser closed")
                except:
                    pass

            # Stop MLX profile
            if profile_id:
                stop_profile(profile_id)

            # Delay before next
            print("\nWaiting 5 seconds...")
            time.sleep(5)

    print("\n" + "="*60)
    print("ALL DONE!")
    print("="*60)


if __name__ == "__main__":
    import urllib3
    urllib3.disable_warnings()
    main()
