# Signup Automation Framework

Enterprise-grade multi-platform signup automation using **Playwright** with **Page Object Model** architecture.

## Features

- **Page Object Model (POM)** - Clean separation of page elements and test logic
- **Proxy Support** - Built-in Smartproxy/Decodo integration
- **Phone Management** - Automatic tracking of used/available phone numbers
- **Data Generation** - Realistic fake user data via Faker
- **Async Architecture** - High-performance async/await patterns
- **Structured Logging** - Comprehensive logging with Loguru
- **Type Safety** - Full type hints with Pydantic models
- **Extensible** - Easy to add new platforms

## Project Structure

```
signup_automation/
├── src/
│   ├── config/              # Configuration management
│   │   ├── __init__.py
│   │   └── settings.py      # Pydantic settings
│   │
│   ├── core/                # Core framework components
│   │   ├── __init__.py
│   │   ├── base_page.py     # Base Page Object class
│   │   ├── base_component.py # Reusable UI components
│   │   └── browser_manager.py # Playwright browser lifecycle
│   │
│   ├── pages/               # Page Object implementations
│   │   ├── __init__.py
│   │   └── airbnb/          # Airbnb-specific pages
│   │       ├── __init__.py
│   │       ├── selectors.py  # Centralized selectors
│   │       ├── home_page.py  # Home page object
│   │       └── signup_page.py # Signup flow page object
│   │
│   ├── services/            # Business logic layer
│   │   ├── __init__.py
│   │   ├── account_saver.py  # Save created accounts
│   │   └── signup_orchestrator.py # Orchestrate signup flow
│   │
│   ├── types/               # Type definitions
│   │   ├── __init__.py
│   │   ├── enums.py         # Enumeration types
│   │   └── models.py        # Pydantic data models
│   │
│   ├── utils/               # Utility functions
│   │   ├── __init__.py
│   │   ├── logger.py        # Logging configuration
│   │   ├── phone_manager.py  # Phone number management
│   │   └── data_generator.py # Fake data generation
│   │
│   ├── runners/             # Execution scripts
│   │   ├── __init__.py
│   │   └── airbnb_runner.py # Airbnb-specific runner
│   │
│   └── main.py              # Main entry point
│
├── data/
│   ├── phones/              # Phone number lists
│   │   └── airbnb_phones.txt
│   ├── state/               # Phone usage tracking
│   └── accounts/            # Created accounts output
│
├── logs/                    # Application logs
├── .env                     # Environment configuration
├── .gitignore
├── pyproject.toml           # Project configuration
├── requirements.txt         # Dependencies
└── README.md
```

## Installation

### Prerequisites

- Python 3.11 or higher
- pip (Python package manager)

### Setup

1. **Clone/Navigate to the project:**
   ```bash
   cd signup_automation
   ```

2. **Create virtual environment:**
   ```bash
   python -m venv .venv

   # Windows
   .venv\Scripts\activate

   # Linux/Mac
   source .venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Install Playwright browsers:**
   ```bash
   playwright install chromium
   ```

5. **Configure environment:**
   - Edit `.env` file with your proxy credentials
   - Add phone numbers to `data/phones/airbnb_phones.txt`

## Configuration

### Environment Variables (`.env`)

```env
# Proxy Configuration
PROXY_HOST=gate.decodo.com
PROXY_PORT=10001
PROXY_USERNAME=your_username
PROXY_PASSWORD=your_password

# Browser Settings
HEADLESS=false          # Run browser visibly
SLOW_MO=50              # Slow down for debugging
DEFAULT_TIMEOUT=30000   # Element timeout (ms)
NAVIGATION_TIMEOUT=60000 # Page load timeout (ms)

# Data Paths
PHONE_LIST_AIRBNB=./data/phones/airbnb_phones.txt
USED_PHONES_PATH=./data/state/used_phones.json
ACCOUNTS_OUTPUT_PATH=./data/accounts/

# Logging
LOG_LEVEL=INFO          # DEBUG, INFO, WARNING, ERROR
LOG_DIR=./logs
```

### Phone Numbers

Add phone numbers to `data/phones/airbnb_phones.txt`, one per line:
```
380969200145
380969200184
380969200286
```

## Usage

### Single Signup

```bash
# Run from project root
python -m src.main --platform airbnb

# Or use the runner directly
python -m src.runners.airbnb_runner
```

### Batch Signup

```bash
# Run 5 signups
python -m src.main --platform airbnb --batch 5

# With custom delay between attempts
python -m src.main --platform airbnb --batch 10 --delay 10
```

### Options

```bash
python -m src.main --help

Options:
  --platform, -p    Target platform (airbnb)
  --batch, -b       Number of signup attempts
  --headless        Run in headless mode
  --no-proxy        Disable proxy
  --delay, -d       Delay between batch attempts (seconds)
  --verbose, -v     Enable debug logging
```

## OTP Handling

The framework supports two OTP handling modes:

### 1. Manual Entry (Default)
When OTP is required, the script pauses and prompts you to enter the code:
```
==================================================
OTP REQUIRED for phone: +380969200145
==================================================
Enter OTP code (or 'skip' to skip): 123456
```

### 2. Automated Callback
Pass an async callback function to handle OTP automatically:

```python
async def my_otp_callback(phone: str) -> str:
    # Integrate with SMS API or other service
    otp = await fetch_otp_from_api(phone)
    return otp

result = await orchestrator.run_single_signup(
    otp_callback=my_otp_callback
)
```

## Adding New Platforms

1. **Create page objects** in `src/pages/newplatform/`:
   ```python
   # src/pages/newplatform/selectors.py
   class SignupSelectors:
       EMAIL_INPUT = 'input[name="email"]'
       ...

   # src/pages/newplatform/signup_page.py
   class NewPlatformSignupPage(BasePage):
       ...
   ```

2. **Add to Platform enum** in `src/types/enums.py`:
   ```python
   class Platform(str, Enum):
       AIRBNB = "airbnb"
       NEWPLATFORM = "newplatform"
   ```

3. **Add orchestrator logic** in `signup_orchestrator.py`:
   ```python
   if self.platform == Platform.NEWPLATFORM:
       result = await self._run_newplatform_signup(...)
   ```

4. **Create runner** in `src/runners/newplatform_runner.py`

## Output

### Created Accounts

Saved to `data/accounts/airbnb_accounts_YYYY-MM-DD.json`:
```json
[
  {
    "platform": "airbnb",
    "email": "john.smith42@gmail.com",
    "password": "xK9#mL2$pQ",
    "phone": "+380969200145",
    "first_name": "John",
    "last_name": "Smith",
    "created_at": "2024-01-15T10:30:00",
    "status": "active"
  }
]
```

### Phone Usage Tracking

Saved to `data/state/used_phones.json`:
```json
{
  "airbnb": {
    "380969200145": {
      "used_at": "2024-01-15T10:30:00",
      "success": true,
      "platform": "airbnb"
    }
  }
}
```

### Logs

Logs are saved to `logs/` directory with:
- `signup_YYYY-MM-DD.log` - All logs
- `errors_YYYY-MM-DD.log` - Error logs only

## Development

### Code Quality

```bash
# Format code
black src/
isort src/

# Type checking
mypy src/

# Linting
ruff check src/
```

### Testing

```bash
# Run tests
pytest

# With coverage
pytest --cov=src
```

## Troubleshooting

### Common Issues

1. **Proxy Connection Failed**
   - Verify proxy credentials in `.env`
   - Check if proxy service is active

2. **Phone Number Rejected**
   - Number may already be registered
   - Try a different number from the pool

3. **OTP Not Received**
   - Check SMS service
   - Verify phone number format

4. **Element Not Found**
   - Website UI may have changed
   - Update selectors in `selectors.py`

### Debug Mode

```bash
python -m src.main --platform airbnb --verbose
```

This enables detailed logging for troubleshooting.

## License

MIT License - See LICENSE file for details.
