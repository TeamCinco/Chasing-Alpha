# config.py
import os

# --- OAuth Credentials ---
# These will be loaded from environment variables by a script that imports this (e.g., trader.py using dotenv).
# The string "YOUR_..." are placeholders if environment variables are not found.
CLIENT_ID = os.getenv('SCHWAB_APP_KEY', "YOUR_CLIENT_ID_HERE")
CLIENT_SECRET = os.getenv('SCHWAB_APP_SECRET', "YOUR_CLIENT_SECRET_HERE")
CALLBACK_URL = os.getenv('SCHWAB_CALLBACK_URL', "https://127.0.0.1")

# --- API Endpoints (Generally Static) ---
BASE_URL = "https://api.schwabapi.com" # This is unlikely to change often
TOKEN_URL = f"{BASE_URL}/v1/oauth/token"
AUTHORIZE_URL = f"{BASE_URL}/v1/oauth/authorize"

# --- Trader API Endpoints ---
# More specific base for trader endpoints, makes it easier if v2, v3 etc. come out
TRADER_API_BASE_URL = f"{BASE_URL}/trader/v1"

# Specific endpoint paths
ACCOUNT_NUMBERS_ENDPOINT = "/accounts/accountNumbers" # Relative to TRADER_API_BASE_URL
# Templates for URLs requiring path parameters
ACCOUNT_DETAILS_ENDPOINT_TEMPLATE = "/accounts/{accountHash}" # Relative to TRADER_API_BASE_URL
ORDERS_ENDPOINT_TEMPLATE = "/accounts/{accountHash}/orders" # Relative to TRADER_API_BASE_URL
ORDER_DETAIL_ENDPOINT_TEMPLATE = "/accounts/{accountHash}/orders/{orderId}" # Relative to TRADER_API_BASE_URL

# --- Token Storage ---
TOKEN_FILE = os.getenv('SCHWAB_TOKEN_FILE', 'tokens.json')


# --- Default Account Identifiers (to be used by trader.py) ---
# The trader.py script will decide how to use these.
# It can prioritize SCHWAB_ACCOUNT_HASH if set, otherwise use SCHWAB_ACCOUNT_NUMBER to find the hash.
DEFAULT_ACCOUNT_HASH_ENV = os.getenv('SCHWAB_ACCOUNT_HASH', None)
DEFAULT_ACCOUNT_NUMBER_ENV = os.getenv('SCHWAB_ACCOUNT_NUMBER', None)


# --- Default Trading Parameters (can be overridden by CLI args) ---
DEFAULT_DURATION = os.getenv('SCHWAB_DEFAULT_DURATION', "DAY")
DEFAULT_SESSION = os.getenv('SCHWAB_DEFAULT_SESSION', "NORMAL")

# --- Logging ---
LOG_LEVEL = os.getenv('SCHWAB_LOG_LEVEL', "INFO").upper()


# --- Sanity Checks (executed when this module is imported) ---
# These print warnings if essential configs seem to be using placeholder values.
# The actual failure will happen during API calls if credentials are wrong.
if CLIENT_ID == "YOUR_CLIENT_ID_HERE" or CLIENT_SECRET == "YOUR_CLIENT_SECRET_HERE":
    print(
        "CONFIG WARNING: SCHWAB_APP_KEY or SCHWAB_APP_SECRET appears to be using placeholder values. "
        "Ensure they are correctly set in your .env file or environment variables."
    )
if not CALLBACK_URL.startswith("https://") and CALLBACK_URL != "http://127.0.0.1": # Allow http for 127.0.0.1 for local dev if needed
     print(
        f"CONFIG INFO: CALLBACK_URL ('{CALLBACK_URL}') is not HTTPS. "
        "Schwab typically requires HTTPS for callback URLs, even for localhost. "
        "Ensure this matches your Schwab App registration."
    )

# Helper to construct full URLs for the API client, reducing direct string formatting there
def get_trader_api_url(relative_path: str) -> str:
    """Constructs a full URL for the Trader API."""
    return f"{TRADER_API_BASE_URL}{relative_path}"