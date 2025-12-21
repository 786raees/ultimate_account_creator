# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build and Run Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium

# Run single signup
python -m src.main --platform airbnb

# Run batch signups
python -m src.main --platform airbnb --batch 5 --delay 10

# Run with visible browser (non-headless)
python -m src.main --platform airbnb  # headless=false is default

# Run headless
python -m src.main --platform airbnb --headless

# Debug mode with verbose logging
python -m src.main --platform airbnb --verbose

# Disable MultiLoginX (use direct Playwright)
python -m src.main --platform airbnb --no-multiloginx

# Run Airbnb runner directly
python -m src.runners.airbnb_runner
```

### Code Quality

```bash
# Format
black src/
isort src/

# Type check
mypy src/

# Lint
ruff check src/

# Test
pytest
pytest --cov=src
```

## Architecture Overview

This is a **Page Object Model (POM)** automation framework using **Playwright** for browser control. The architecture follows a layered design:

### Layer Structure

```
Runners (src/runners/)     → Entry points, CLI handling
    ↓
Orchestrator (src/services/signup_orchestrator.py)  → Flow control, retry logic
    ↓
Page Objects (src/pages/)  → Platform-specific UI interactions
    ↓
Core (src/core/)           → Base classes, browser management
    ↓
Utils (src/utils/)         → Data generation, phone management, fingerprinting
```

### Key Design Patterns

1. **Page Object Model**: Each page has a dedicated class inheriting from `BasePage`. Selectors are centralized in `selectors.py` files per platform.

2. **Orchestrator Pattern**: `SignupOrchestrator` manages the complete signup flow, handling retries, error recovery, and step tracking via `SignupStep` enum.

3. **Context Manager Sessions**: `BrowserManager.session()` provides async context manager for complete browser lifecycle:
   ```python
   async with browser_manager.session() as page:
       await page.goto("...")
   ```

4. **Country-Based Fingerprinting**: Browser fingerprint (timezone, locale, viewport) is generated to match the phone number's country code using `generate_fingerprint_for_phone()`.

5. **Rotating Proxy Integration**: Proxy ports are rotated from a configurable range (default 10001-10100) via `ProxySettings.get_rotated_port()`.

### Configuration System

Settings use Pydantic with nested configuration classes in `src/config/settings.py`:
- `ProxySettings` (PROXY_* env vars)
- `BrowserSettings` (HEADLESS, SLOW_MO, etc.)
- `FingerprintSettings` (FINGERPRINT_* env vars)
- `CaptchaSettings` (CAPTCHA_* env vars)
- `PathSettings` (file paths)
- `MultiLoginXSettings` (MLX_* env vars)

Access via cached singleton: `get_settings()`

### MultiLoginX Integration

The framework uses MultiLoginX for browser profile management. This provides:
- **Anti-fingerprint protection**: Each profile has unique browser fingerprints
- **Profile isolation**: Each signup uses a fresh, isolated browser profile
- **Rotating proxies**: Proxy port is automatically rotated for each profile

**How it works:**
1. At the start of each signup, a new "quick profile" is created via MultiLoginX API
2. The profile includes the country-matched fingerprint and rotated proxy
3. Playwright connects to the profile's browser via Chrome DevTools Protocol (CDP)
4. After the signup (success or failure), the profile is automatically stopped

**Configuration (env vars):**
```bash
MLX_ENABLED=true                              # Enable/disable MultiLoginX
MLX_EMAIL=your@email.com                      # MultiLoginX account email
MLX_PASSWORD=yourpassword                     # Account password (plain or MD5 hashed)
MLX_BASE_URL=https://launcher.mlx.yt:45001    # MultiLoginX launcher API URL
MLX_API_URL=https://api.multilogin.com        # MLX API URL for authentication
MLX_TIMEOUT=60                                # API request timeout (seconds)
MLX_BROWSER_TYPE=mimic                        # Browser type (mimic = Chromium-based)
MLX_CORE_VERSION=132                          # Browser core version
MLX_OS_TYPE=windows                           # OS type (windows, linux, macos)
```

**API Endpoints used:**
- `POST /api/v3/profile/quick` - Create and start a quick profile
- `GET /api/v1/profile/stop?profile_id=...` - Stop a profile

**Files:**
- `src/services/multiloginx_client.py` - MultiLoginX API client
- `src/core/browser_manager.py` - Browser lifecycle with MultiLoginX support

### Adding a New Platform

1. Create page objects in `src/pages/newplatform/`:
   - `selectors.py` - Centralized CSS selectors
   - `home_page.py` - Landing page interactions
   - `signup_page.py` - Signup flow logic

2. Add to `Platform` enum in `src/types/enums.py`

3. Add platform handling in `SignupOrchestrator._run_*_signup()`

4. Create runner in `src/runners/newplatform_runner.py`

### OTP Handling

Two modes supported:
- **Manual**: Script pauses, user enters OTP in browser, waits for profile form
- **Callback**: Pass async function `otp_callback(phone: str) -> str` to automate

### Phone Number Flow

`PhoneManager` tracks phone usage:
- Loads from `data/phones/airbnb_phones.txt`
- Tracks used phones in `data/state/used_phones.json`
- `get_next()` returns unused `PhoneNumber` with parsed country code

### CAPTCHA Integration

Arkose Labs FunCaptcha detected. CAPTCHA solver integration placeholder in `src/services/captcha_solver.py`. Public key: `2F0D6CB5-ACAC-4EA9-9B2A-A5F90A2DF15E`.

## Important Files

- `src/services/signup_orchestrator.py` - Main signup flow logic with step-by-step screenshots
- `src/services/multiloginx_client.py` - MultiLoginX API client for profile management
- `src/core/browser_manager.py` - Playwright browser lifecycle with MultiLoginX/fingerprinting
- `src/pages/airbnb/selectors.py` - All Airbnb UI selectors (multi-language support)
- `src/config/settings.py` - All configuration with env var mapping
- `src/utils/fingerprint.py` - Browser fingerprint generation per country
