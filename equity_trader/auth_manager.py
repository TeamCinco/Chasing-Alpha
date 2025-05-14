# auth_manager.py
import base64
import json
import time
import webbrowser
from urllib.parse import urlparse, parse_qs, quote_plus
import requests
import logging

import config
from utils import pretty_print_json

logger = logging.getLogger(__name__)

class AuthManager:
    def __init__(self):
        self.client_id = config.CLIENT_ID
        self.client_secret = config.CLIENT_SECRET
        self.callback_url = config.CALLBACK_URL
        self.token_file = config.TOKEN_FILE
        self.access_token = None
        self.refresh_token = None
        self.access_token_expires_at = 0
        self.refresh_token_expires_at = 0 # Schwab refresh tokens expire in 7 days
        self._load_tokens()

    def _save_tokens(self):
        """Saves tokens and their expiry times to a file."""
        token_data = {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "access_token_expires_at": self.access_token_expires_at,
            "refresh_token_expires_at": self.refresh_token_expires_at,
        }
        try:
            with open(self.token_file, 'w') as f:
                json.dump(token_data, f)
            logger.info(f"Tokens saved to {self.token_file}")
        except IOError as e:
            logger.error(f"Error saving tokens: {e}")

    def _load_tokens(self):
        """Loads tokens from a file if it exists."""
        try:
            with open(self.token_file, 'r') as f:
                token_data = json.load(f)
                self.access_token = token_data.get("access_token")
                self.refresh_token = token_data.get("refresh_token")
                self.access_token_expires_at = token_data.get("access_token_expires_at", 0)
                self.refresh_token_expires_at = token_data.get("refresh_token_expires_at", 0)
                logger.info(f"Tokens loaded from {self.token_file}")
        except FileNotFoundError:
            logger.info(f"Token file {self.token_file} not found. Will need to authenticate.")
        except (IOError, json.JSONDecodeError) as e:
            logger.error(f"Error loading tokens: {e}. Please delete {self.token_file} and re-authenticate.")
            # Invalidate tokens if file is corrupt
            self.access_token = None
            self.refresh_token = None


    def _is_access_token_valid(self):
        """Checks if the current access token is valid and not expired (with a small buffer)."""
        buffer_seconds = 60  # Refresh 60 seconds before actual expiry
        return self.access_token and time.time() < (self.access_token_expires_at - buffer_seconds)

    def _is_refresh_token_valid(self):
        """Checks if the current refresh token is valid and not expired."""
        # Schwab refresh tokens are valid for 7 days.
        # We don't have an explicit expiry time from the API for refresh tokens,
        # but we know they are issued with the access token.
        # We'll assume it's valid if it exists and the access token was issued within 7 days.
        # A more robust way is to track the refresh_token_issued_at time.
        # For simplicity, we'll use the refresh_token_expires_at we calculate.
        buffer_seconds = 3600 # Refresh if less than an hour left on 7-day window
        return self.refresh_token and time.time() < (self.refresh_token_expires_at - buffer_seconds)


    def _get_authorization_code(self):
        """Guides the user through the manual authorization step to get a code."""
        auth_url = f"{config.AUTHORIZE_URL}?client_id={self.client_id}&redirect_uri={quote_plus(self.callback_url)}"
        print(f"Please open the following URL in your browser to authorize the application:\n{auth_url}")
        
        try:
            webbrowser.open(auth_url)
        except Exception as e:
            logger.warning(f"Could not open browser automatically: {e}. Please copy and paste the URL.")

        print(f"\nAfter authorization, you will be redirected to a URL like: {self.callback_url}/?code=YOUR_CODE&session=...")
        auth_response_url = input("Paste the full redirect URL here: ")

        try:
            parsed_url = urlparse(auth_response_url)
            query_params = parse_qs(parsed_url.query)
            if 'code' in query_params:
                return query_params['code'][0]
            else:
                logger.error("Could not find 'code' in the redirect URL.")
                if 'error' in query_params:
                    logger.error(f"OAuth Error: {query_params.get('error_description', query_params['error'])}")
                return None
        except Exception as e:
            logger.error(f"Error parsing redirect URL: {e}")
            return None

    def _exchange_code_for_tokens(self, auth_code):
        """Exchanges an authorization code for access and refresh tokens."""
        headers = {
            "Authorization": f"Basic {base64.b64encode(f'{self.client_id}:{self.client_secret}'.encode()).decode()}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        data = {
            "grant_type": "authorization_code",
            "code": auth_code, # The API docs say this should be URL decoded, but requests usually handles it.
                              # If issues, ensure it's decoded: `urllib.parse.unquote(auth_code)`
            "redirect_uri": self.callback_url
        }
        try:
            response = requests.post(config.TOKEN_URL, headers=headers, data=data)
            response.raise_for_status() # Raise HTTPError for bad responses (4XX or 5XX)
            token_data = response.json()

            self.access_token = token_data["access_token"]
            self.refresh_token = token_data.get("refresh_token") # refresh_token might not always be returned
            
            # Access token valid for 30 minutes (1800 seconds)
            self.access_token_expires_at = time.time() + token_data["expires_in"]
            # Refresh token valid for 7 days. We'll set its expiry based on current time.
            # This is an approximation; ideally, the API would provide refresh_token_expires_in
            if self.refresh_token:
                 self.refresh_token_expires_at = time.time() + (7 * 24 * 60 * 60) # 7 days in seconds

            self._save_tokens()
            logger.info("Successfully obtained and saved new tokens.")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Error exchanging code for tokens: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response content: {e.response.text}")
            return False
        except KeyError as e:
            logger.error(f"Missing key in token response: {e}. Response: {response.text if 'response' in locals() else 'N/A'}")
            return False


    def _refresh_access_token(self):
        """Refreshes the access token using the refresh token."""
        if not self.refresh_token:
            logger.warning("No refresh token available to refresh access token.")
            return False
        if not self._is_refresh_token_valid():
            logger.warning("Refresh token has expired. Need full re-authorization.")
            return False

        headers = {
            "Authorization": f"Basic {base64.b64encode(f'{self.client_id}:{self.client_secret}'.encode()).decode()}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        data = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token
        }
        try:
            response = requests.post(config.TOKEN_URL, headers=headers, data=data)
            response.raise_for_status()
            token_data = response.json()

            self.access_token = token_data["access_token"]
            # Schwab might return a new refresh token, or the old one remains valid.
            # The documentation implies the existing refresh token is used until it expires.
            # If a new one is provided, update it:
            if "refresh_token" in token_data:
                self.refresh_token = token_data["refresh_token"]
                self.refresh_token_expires_at = time.time() + (7 * 24 * 60 * 60)

            self.access_token_expires_at = time.time() + token_data["expires_in"]
            self._save_tokens()
            logger.info("Successfully refreshed access token.")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Error refreshing access token: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response content: {e.response.text}")
            # If refresh fails (e.g., refresh token revoked or expired), clear tokens
            if e.response and e.response.status_code in [400, 401]:
                logger.warning("Refresh token likely invalid. Clearing tokens for re-authentication.")
                self.access_token = None
                self.refresh_token = None
                self.access_token_expires_at = 0
                self.refresh_token_expires_at = 0
                self._save_tokens() # Save cleared state
            return False
        except KeyError as e:
            logger.error(f"Missing key in refresh token response: {e}. Response: {response.text if 'response' in locals() else 'N/A'}")
            return False

    def get_valid_access_token(self):
        """Ensures a valid access token is available, refreshing or re-authenticating if necessary."""
        if self._is_access_token_valid():
            logger.debug("Existing access token is valid.")
            return self.access_token

        logger.info("Access token is invalid or expired.")
        if self._is_refresh_token_valid():
            logger.info("Attempting to refresh access token...")
            if self._refresh_access_token():
                return self.access_token
            else:
                logger.warning("Failed to refresh access token. Proceeding to full authentication.")
        else:
            logger.info("Refresh token is invalid or expired. Proceeding to full authentication.")

        # Full authentication flow
        auth_code = self._get_authorization_code()
        if auth_code:
            if self._exchange_code_for_tokens(auth_code):
                return self.access_token
        
        logger.error("Failed to obtain a valid access token after all attempts.")
        return None