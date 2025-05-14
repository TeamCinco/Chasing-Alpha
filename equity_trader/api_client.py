# api_client.py
import requests
import logging
import json
import config
from auth_manager import AuthManager
from utils import pretty_print_json

logger = logging.getLogger(__name__)

class APIClient:
    def __init__(self, auth_manager: AuthManager):
        self.auth_manager = auth_manager
        self.base_url = config.BASE_URL

    def _make_request(self, method, endpoint_path, params=None, json_data=None, data=None, extra_headers=None):
        """Helper method to make authenticated API requests."""
        access_token = self.auth_manager.get_valid_access_token()
        if not access_token:
            logger.error("Cannot make API request: No valid access token.")
            return None

        url = f"{self.base_url}{endpoint_path}"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json" # Common for GET, adjust if needed
        }
        if json_data or data: # For POST/PUT/PATCH
             headers["Content-Type"] = "application/json" # Schwab API expects JSON body

        if extra_headers:
            headers.update(extra_headers)

        logger.debug(f"Making {method} request to {url}")
        logger.debug(f"Headers: {headers}")
        if params: logger.debug(f"Params: {params}")
        if json_data: logger.debug(f"JSON Body: {json.dumps(json_data, indent=2)}")
        if data: logger.debug(f"Form Data: {data}")


        try:
            response = requests.request(method, url, headers=headers, params=params, json=json_data, data=data)
            
            # Check for order placement success (201 Created often includes a Location header)
            if method.upper() in ["POST", "PUT"] and response.status_code in [200, 201]:
                if 'Location' in response.headers:
                    logger.info(f"Order action successful. Location: {response.headers['Location']}")
                    # The location header often contains the order ID.
                    # Example: https://api.schwabapi.com/trader/v1/accounts/xxxxxxxxxxxx/orders/123456789
                    # You might want to return this or the full response.
                    return {"status_code": response.status_code, "location": response.headers['Location'], "response_body": response.text}
                else: # For PUT (replace order), it might just be 200 OK without Location
                    logger.info(f"Order action successful with status {response.status_code}.")
                    return {"status_code": response.status_code, "response_body": response.text}


            response.raise_for_status() # Raise HTTPError for bad responses (4XX or 5XX)
            
            # For GET requests or other successful responses that return JSON
            if response.content:
                try:
                    return response.json()
                except requests.exceptions.JSONDecodeError:
                    logger.warning(f"Response was not JSON: {response.text}")
                    return response.text # Return raw text if not JSON
            return None # No content

        except requests.exceptions.HTTPError as http_err:
            logger.error(f"HTTP error occurred: {http_err} - {http_err.response.status_code}")
            logger.error(f"Response content: {http_err.response.text}")
            if http_err.response.status_code == 401: # Unauthorized
                logger.warning("Token might be expired or invalid. Attempting to refresh/re-auth on next call.")
                # Invalidate local token to force refresh on next get_valid_access_token call
                self.auth_manager.access_token = None 
                self.auth_manager.access_token_expires_at = 0
                self.auth_manager._save_tokens() # Save invalidated state
            return {"error": str(http_err), "status_code": http_err.response.status_code, "details": http_err.response.text}
        except requests.exceptions.RequestException as req_err:
            logger.error(f"Request exception occurred: {req_err}")
            return {"error": str(req_err), "details": "Network or request configuration issue."}
        except Exception as e:
            logger.error(f"An unexpected error occurred during API request: {e}")
            return {"error": str(e), "details": "Unexpected error."}

    # --- Account Endpoints ---
    def get_account_numbers(self):
        """Gets list of account numbers and their encrypted values."""
        return self._make_request("GET", "/trader/v1/accounts/accountNumbers")

    def get_account_balances_positions(self, account_hash, fields=None):
        """
        Get a specific account balance and positions for the logged in user.
        :param account_hash: Encrypted account number.
        :param fields: Optional. Comma-separated string of fields to include (e.g., "positions").
        """
        params = {}
        if fields:
            params['fields'] = fields
        return self._make_request("GET", f"/trader/v1/accounts/{account_hash}", params=params)

    # --- Order Endpoints ---
    def place_order(self, account_hash, order_payload):
        """
        Places an order for a specific account.
        :param account_hash: Encrypted account number.
        :param order_payload: Dictionary representing the order.
        """
        endpoint = f"/trader/v1/accounts/{account_hash}/orders"
        return self._make_request("POST", endpoint, json_data=order_payload)

    def get_orders_for_account(self, account_hash, max_results=50, from_entered_time=None, to_entered_time=None, status=None):
        """
        Get all orders for a specific account.
        :param account_hash: Encrypted account number.
        :param max_results: Max number of orders to retrieve.
        :param from_entered_time: ISO 8601 format (YYYY-MM-DDThh:mm:ss.sssZ).
        :param to_entered_time: ISO 8601 format.
        :param status: e.g., "WORKING", "FILLED", "CANCELLED".
        """
        params = {"maxResults": max_results}
        if from_entered_time: params["fromEnteredTime"] = from_entered_time
        if to_entered_time: params["toEnteredTime"] = to_entered_time
        if status: params["status"] = status
        endpoint = f"/trader/v1/accounts/{account_hash}/orders"
        return self._make_request("GET", endpoint, params=params)

    def get_order_by_id(self, account_hash, order_id):
        """Gets a specific order by its ID for a specific account."""
        endpoint = f"/trader/v1/accounts/{account_hash}/orders/{order_id}"
        return self._make_request("GET", endpoint)

    def cancel_order(self, account_hash, order_id):
        """Cancels an order for a specific account."""
        endpoint = f"/trader/v1/accounts/{account_hash}/orders/{order_id}"
        return self._make_request("DELETE", endpoint)

    def replace_order(self, account_hash, order_id, new_order_payload):
        """Replaces an order for a specific account."""
        endpoint = f"/trader/v1/accounts/{account_hash}/orders/{order_id}"
        return self._make_request("PUT", endpoint, json_data=new_order_payload)