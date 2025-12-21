import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options


def create_quick_profile():
    """Create a quick browser profile using Multilogin API."""
    url = "https://launcher.mlx.yt:45001/api/v2/profile/quick"

    headers = {
        "accept": "application/json",
        "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
        "authorization": "Bearer eyJhbGciOiJIUzUxMiJ9.eyJicGRzLmJ1Y2tldCI6Im1seC1icGRzLXByb2QtZXUtMSIsIm1hY2hpbmVJRCI6IiIsInByb2R1Y3RJRCI6Im11bHRpbG9naW4iLCJ3b3Jrc3BhY2VSb2xlIjoib3duZXIiLCJ2ZXJpZmllZCI6dHJ1ZSwicGxhbk5hbWUiOiJTb2xvIiwic2hhcmRJRCI6ImNiZTEzODAwLWJiYWYtNGM4Zi04MGIzLTE5N2Y4OTYzOTRmMiIsInVzZXJJRCI6Ijg3Y2YyMTYwLWJhZDYtNGM0Mi1iNGFkLWQ4ZTE1MWYzN2Y0YyIsImVtYWlsIjoid2FxYXJraGFuMTI1MjYxN0BnbWFpbC5jb20iLCJpc0F1dG9tYXRpb24iOmZhbHNlLCJ3b3Jrc3BhY2VJRCI6ImNiMmFlZjZmLWY3ZTYtNGM0ZC04ZWYyLWQwNDI1MDIzZTk0ZSIsImp0aSI6IjI2YjYyMTJhLTljZDItNDhmYy1iMGUzLTIwODI3Y2MxZmYzOSIsInN1YiI6Ik1MWCIsImlzcyI6Ijg3Y2YyMTYwLWJhZDYtNGM0Mi1iNGFkLWQ4ZTE1MWYzN2Y0YyIsImlhdCI6MTc2NjI4MDkxMywiZXhwIjoxNzY2Mjg0NTEzfQ.9z3dsBAyZFYbiXqQ4bdYfPT3w-6UoDjb1OAkVk2CKBqZZ7TkuXlN2RfZqiNCRvnJxzhDe12Mmc0CAi5qcdHuLg",
        "content-type": "application/json",
        "origin": "https://app.multilogin.com",
        "referer": "https://app.multilogin.com/",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
        "x-request-origin": "UI",
    }

    payload = {
        "automation": "selenium",
        "browser_type": "mimic",
        "os_type": "windows",
        "parameters": {
            "custom_start_urls": ["https://whoerip.com/multilogin/"],
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
                "canvas_noise": "natural",
                "startup_behavior": "custom",
            },
            "fingerprint": {"ports": []},
        },
        "proxy": {
            "type": "socks5",
            "host": "gate.decodo.com",
            "port": 10001,
            "username": "spcujh3425",
            "password": "mmZxuBgSiW71vs65~e",
            "save_traffic": False,
        },
    }

    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()


def connect_to_browser(port):
    """Connect to the Multilogin browser using Selenium remote."""
    selenium_url = f"http://127.0.0.1:{port}"

    options = Options()

    driver = webdriver.Remote(
        command_executor=selenium_url,
        options=options,
    )

    return driver


def main():
    # Create quick profile
    print("Creating quick profile...")
    result = create_quick_profile()
    print(f"API Response: {result}")

    if result["status"]["http_code"] == 200:
        port = result["data"]["port"]
        profile_id = result["data"]["id"]
        print(f"Profile created successfully. ID: {profile_id}, Port: {port}")

        # Connect to browser using Selenium
        print(f"Connecting to browser on port {port}...")
        driver = connect_to_browser(port)
        print("Connected to browser successfully!")

        # Example: print current URL
        print(f"Current URL: {driver.current_url}")
        # go to airbnb sign up page
        driver.get("https://www.airbnb.com/signup_login")
        # wait for user to see the page
        input("Press Enter to close the browser...")

        return driver
    else:
        print(f"Failed to create profile: {result['status']['message']}")
        return None


if __name__ == "__main__":
    driver = main()
