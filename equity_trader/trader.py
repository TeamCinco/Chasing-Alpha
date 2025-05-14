# trader.py
import argparse
import logging
import sys
import time
import os # For checking token file existence in --force_reauth

# IMPORTANT: Load .env variables BEFORE importing other modules that rely on them (like config)
from dotenv import load_dotenv
load_dotenv()

import config # Now config will have access to environment variables loaded by dotenv
from auth_manager import AuthManager
from api_client import APIClient
from order_builder import (
    build_equity_order,
    ALLOWED_EQUITY_INSTRUCTIONS,
    ALLOWED_ORDER_TYPES,
    ALLOWED_DURATIONS,
    ALLOWED_SESSIONS,
    ALLOWED_TRAILING_STOP_LINK_BASIS,
    ALLOWED_TRAILING_STOP_LINK_TYPES
)
from utils import setup_logging, pretty_print_json

logger = logging.getLogger(__name__)

def get_account_hash_interactive(api_client: APIClient, preferred_account_number: str = None):
    """
    Fetches account numbers. If a preferred_account_number is provided, it tries to find its hash.
    If not, or if not found, and multiple accounts exist, it prompts the user to choose.
    Returns the hash of the selected/found account, or the first one if only one exists.
    """
    logger.info("Fetching available account numbers...")
    accounts_data_response = api_client.get_account_numbers() # This now calls the method in api_client

    if not accounts_data_response or not isinstance(accounts_data_response, list) or \
       (isinstance(accounts_data_response, dict) and "error" in accounts_data_response):
        logger.error(f"Failed to fetch account numbers: {accounts_data_response}")
        return None

    if not accounts_data_response:
        logger.error("No accounts found associated with this API key/user.")
        return None

    accounts_list = accounts_data_response # Assuming the response is directly the list of accounts

    # Try to find by preferred account number first
    if preferred_account_number:
        for acc in accounts_list:
            if acc.get('accountNumber') == preferred_account_number:
                logger.info(f"Found preferred account: ...{preferred_account_number[-4:]} (Hash: {acc.get('hashValue')})")
                return acc.get('hashValue')
        logger.warning(f"Preferred account number '{preferred_account_number}' not found among linked accounts.")
        # Proceed to interactive selection or picking the first if only one

    if len(accounts_list) == 1:
        acc = accounts_list[0]
        acc_num_masked = f"...{acc.get('accountNumber')[-4:]}" if acc.get('accountNumber') else "N/A"
        logger.info(f"Using the only available account: {acc_num_masked} (Hash: {acc.get('hashValue')})")
        return acc.get('hashValue')

    # Multiple accounts, and preferred not found or not specified
    print("\nMultiple accounts found. Please select one to use:")
    for i, acc in enumerate(accounts_list):
        acc_num_masked = f"...{acc.get('accountNumber')[-4:]}" if acc.get('accountNumber') else "N/A"
        # You might want to display more info if available, e.g., account type or nickname
        print(f"  {i+1}. Account (masked): {acc_num_masked} (Hash: {acc.get('hashValue')})")

    while True:
        try:
            choice = int(input(f"Enter choice (1-{len(accounts_list)}): "))
            if 1 <= choice <= len(accounts_list):
                selected_account = accounts_list[choice-1]
                logger.info(f"Selected account: ...{selected_account.get('accountNumber')[-4:]} (Hash: {selected_account.get('hashValue')})")
                return selected_account.get('hashValue')
            else:
                print("Invalid choice. Please try again.")
        except ValueError:
            print("Invalid input. Please enter a number.")


def main():
    setup_logging() # Initialize logging based on config.LOG_LEVEL

    # --- Pre-run checks for essential config from .env ---
    # These are checked again here because config.py only prints warnings.
    # trader.py should exit if critical configs are missing.
    if config.CLIENT_ID == "YOUR_CLIENT_ID_HERE" or config.CLIENT_SECRET == "YOUR_CLIENT_SECRET_HERE":
        logger.fatal(
            "CRITICAL: SCHWAB_APP_KEY or SCHWAB_APP_SECRET is missing or using placeholder values. "
            "Please set them correctly in your .env file. Exiting."
        )
        sys.exit(1)

    parser = argparse.ArgumentParser(description="Charles Schwab Equity Trader CLI")
    parser.add_argument("action", choices=["buy", "sell", "get_orders", "get_order", "cancel_order", "replace_order", "get_accounts", "get_balance"],
                        help="Action to perform.")
    # Trading arguments
    parser.add_argument("--symbol", type=str, help="Stock symbol (e.g., AAPL).")
    parser.add_argument("--quantity", type=int, help="Number of shares.")
    parser.add_argument("--order_type", type=str, default="MARKET", choices=ALLOWED_ORDER_TYPES,
                        help=f"Order type (default: MARKET). Allowed: {', '.join(ALLOWED_ORDER_TYPES)}")
    parser.add_argument("--price", type=float, help="Limit price for LIMIT or STOP_LIMIT orders.")
    parser.add_argument("--stop_price", type=float, help="Stop price for STOP, STOP_LIMIT orders.")
    parser.add_argument("--trailing_offset", type=float, help="Offset value for TRAILING_STOP (e.g., 1.0 for $1, 2.5 for 2.5%%).")
    parser.add_argument("--trailing_basis", type=str, default="LAST", choices=ALLOWED_TRAILING_STOP_LINK_BASIS,
                        help=f"Trailing stop link basis (default: LAST). Allowed: {', '.join(ALLOWED_TRAILING_STOP_LINK_BASIS)}")
    parser.add_argument("--trailing_type", type=str, default="VALUE", choices=ALLOWED_TRAILING_STOP_LINK_TYPES,
                        help=f"Trailing stop link type (default: VALUE). Allowed: {', '.join(ALLOWED_TRAILING_STOP_LINK_TYPES)}")
    parser.add_argument("--duration", type=str, default=config.DEFAULT_DURATION, # Get default from config
                        help=f"Order duration (default: {config.DEFAULT_DURATION}). Allowed: {', '.join(ALLOWED_DURATIONS)}")
    parser.add_argument("--session", type=str, default=config.DEFAULT_SESSION, # Get default from config
                        help=f"Trading session (default: {config.DEFAULT_SESSION}). Allowed: {', '.join(ALLOWED_SESSIONS)}")
    # Account and Order ID arguments
    parser.add_argument("--account_hash", type=str,
                        help="Encrypted account hash. Overrides .env SCHWAB_ACCOUNT_HASH and SCHWAB_ACCOUNT_NUMBER lookup.")
    parser.add_argument("--account_number", type=str,
                        help="Your Schwab account number (e.g., 12345678). Used to find the hash if --account_hash or SCHWAB_ACCOUNT_HASH (in .env) is not set.")
    parser.add_argument("--order_id", type=str, help="Order ID for get_order, cancel_order, or replace_order actions.")
    # Utility arguments
    parser.add_argument("--force_reauth", action="store_true", help="Force re-authentication by deleting existing tokens.")
    parser.add_argument("-y", "--yes", action="store_true", help="Automatically confirm order placement/cancellation (USE WITH CAUTION).")


    args = parser.parse_args()

    if args.force_reauth:
        try:
            if os.path.exists(config.TOKEN_FILE):
                os.remove(config.TOKEN_FILE)
                logger.info(f"Removed token file {config.TOKEN_FILE} due to --force_reauth flag.")
        except Exception as e:
            logger.error(f"Could not remove token file '{config.TOKEN_FILE}': {e}")


    auth_manager = AuthManager() # Uses CLIENT_ID, CLIENT_SECRET, CALLBACK_URL, TOKEN_FILE from config
    api_client = APIClient(auth_manager) # AuthManager is injected here

    # --- Determine Account Hash to Use ---
    account_hash_to_use = args.account_hash  # 1. Highest priority: CLI argument --account_hash

    if not account_hash_to_use:
        account_hash_to_use = config.DEFAULT_ACCOUNT_HASH_ENV  # 2. Next: SCHWAB_ACCOUNT_HASH from .env

    if not account_hash_to_use:
        # 3. Next: Use SCHWAB_ACCOUNT_NUMBER from .env (via config) or --account_number from CLI to find the hash
        preferred_account_number_for_lookup = args.account_number if args.account_number else config.DEFAULT_ACCOUNT_NUMBER_ENV
        if preferred_account_number_for_lookup:
            logger.info(f"Account hash not directly specified. Attempting to find hash for account number: '{preferred_account_number_for_lookup}'...")
            account_hash_to_use = get_account_hash_interactive(api_client, preferred_account_number_for_lookup)
        else:
            # 4. Fallback: Fetch all accounts and let user choose if multiple, or use first if single.
            logger.info("No specific account hash or number provided. Attempting to determine interactively or use the first available...")
            account_hash_to_use = get_account_hash_interactive(api_client)

    if not account_hash_to_use and args.action not in ["get_accounts"]: # get_accounts doesn't need a specific hash
        logger.error(
            "Could not determine account hash. This is required for most actions. "
            "Please provide --account_hash, or set SCHWAB_ACCOUNT_HASH in your .env, "
            "or provide --account_number (or SCHWAB_ACCOUNT_NUMBER in .env) for lookup. Exiting."
        )
        sys.exit(1)
    
    if account_hash_to_use: # Log only if a hash was determined
        logger.info(f"Using account hash: {account_hash_to_use} for action: {args.action}")


    # --- Perform Actions ---
    if args.action == "get_accounts":
        logger.info("Fetching account numbers and hashes...")
        accounts = api_client.get_account_numbers()
        if accounts:
            pretty_print_json(accounts)
        else:
            logger.error("Failed to retrieve account numbers.")

    elif args.action == "get_balance":
        if not account_hash_to_use: sys.exit("Account hash required for get_balance. Exiting.")
        logger.info(f"Fetching balance and positions for account hash: {account_hash_to_use}...")
        # Example: fetch positions along with balances. Adjust 'fields' as needed.
        balance_data = api_client.get_account_balances_positions(account_hash_to_use, fields="positions")
        if balance_data:
            pretty_print_json(balance_data)
        else:
            logger.error("Failed to retrieve balance and positions.")

    elif args.action in ["buy", "sell"]:
        if not account_hash_to_use: sys.exit("Account hash required for trading. Exiting.")
        if not args.symbol or not args.quantity:
            parser.error("--symbol and --quantity are required for buy/sell actions.")

        instruction = "BUY" if args.action == "buy" else "SELL"
        
        trailing_stop_details = None
        if args.order_type.upper() == "TRAILING_STOP":
            if args.trailing_offset is None:
                parser.error("--trailing_offset is required for TRAILING_STOP orders.")
            trailing_stop_details = {
                "link_basis": args.trailing_basis.upper(),
                "link_type": args.trailing_type.upper(),
                "offset": args.trailing_offset
            }
        try:
            order_payload = build_equity_order(
                symbol=args.symbol,
                quantity=args.quantity,
                instruction=instruction,
                order_type=args.order_type.upper(),
                price=args.price,
                stop_price=args.stop_price,
                trailing_stop_details=trailing_stop_details,
                duration=args.duration.upper(),
                session=args.session.upper()
            )
        except ValueError as e:
            logger.error(f"Error building order: {e}")
            sys.exit(1)

        logger.info(f"Preparing to place {instruction} order for {args.quantity} shares of {args.symbol} on account {account_hash_to_use[-10:]}...")
        logger.info("Order details:")
        pretty_print_json(order_payload)
        
        if not args.yes:
            confirmation = input("Confirm placing this order? (yes/no): ").strip().lower()
            if confirmation != 'yes':
                logger.info("Order placement cancelled by user.")
                sys.exit(0)
        else:
            logger.warning("Auto-confirming order placement due to -y/--yes flag.")

        response = api_client.place_order(account_hash_to_use, order_payload)
        if response:
            logger.info("Order placement response:")
            pretty_print_json(response)
            if isinstance(response, dict):
                if response.get("status_code") in [200, 201] and response.get("location"):
                    order_id_from_loc = response["location"].split('/')[-1]
                    logger.info(f"Order submitted successfully! Order ID (from location header): {order_id_from_loc}")
                    logger.info(f"Check status: python trader.py get_order --order_id {order_id_from_loc} --account_hash {account_hash_to_use}")
                elif "error" in response:
                     logger.error(f"Order placement failed: {response.get('details', response.get('error'))}")
                else: # Successful but no location header (e.g. some PUTs) or unexpected success format
                    logger.info("Order request processed. Check full response for details.")
        else:
            logger.error("Failed to place order. No response or error in API client.")


    elif args.action == "get_orders":
        if not account_hash_to_use: sys.exit("Account hash required for get_orders. Exiting.")
        logger.info(f"Fetching orders for account hash: {account_hash_to_use}...")
        # Add CLI args for max_results, from_entered_time, to_entered_time, status if needed
        orders = api_client.get_orders_for_account(account_hash_to_use, max_results=10)
        if orders:
            pretty_print_json(orders)
        else:
            logger.error("Failed to retrieve orders.")

    elif args.action == "get_order":
        if not account_hash_to_use: sys.exit("Account hash required for get_order. Exiting.")
        if not args.order_id:
            parser.error("--order_id is required for get_order action.")
        logger.info(f"Fetching order {args.order_id} for account hash: {account_hash_to_use}...")
        order_details = api_client.get_order_by_id(account_hash_to_use, args.order_id)
        if order_details:
            pretty_print_json(order_details)
        else:
            logger.error(f"Failed to retrieve order {args.order_id}.")

    elif args.action == "cancel_order":
        if not account_hash_to_use: sys.exit("Account hash required for cancel_order. Exiting.")
        if not args.order_id:
            parser.error("--order_id is required for cancel_order action.")
        
        logger.info(f"Attempting to cancel order {args.order_id} for account hash: {account_hash_to_use}...")
        order_to_cancel = api_client.get_order_by_id(account_hash_to_use, args.order_id)
        if not order_to_cancel or (isinstance(order_to_cancel, dict) and "error" in order_to_cancel):
            logger.error(f"Could not retrieve order {args.order_id} to check status before cancelling.")
            sys.exit(1)
        
        pretty_print_json(order_to_cancel)
        order_status = order_to_cancel.get("status")
        cancellable_statuses = ["WORKING", "PENDING_ACTIVATION", "QUEUED", "ACCEPTED", "AWAITING_PARENT_ORDER"] # Add more if needed

        if not args.yes:
            if order_status not in cancellable_statuses:
                logger.warning(f"Order {args.order_id} has status '{order_status}' and may not be cancellable.")
            confirmation = input(f"Confirm cancellation of order {args.order_id} (Status: {order_status})? (yes/no): ").strip().lower()
            if confirmation != 'yes':
                logger.info("Cancellation aborted by user.")
                sys.exit(0)
        else:
            logger.warning(f"Auto-confirming cancellation for order {args.order_id} (Status: {order_status}) due to -y/--yes flag.")


        response = api_client.cancel_order(account_hash_to_use, args.order_id)
        if response:
            logger.info(f"Cancel order response for order ID {args.order_id}:")
            pretty_print_json(response)
            if isinstance(response, dict):
                if response.get("status_code") == 200: # Schwab API typically returns 200 OK for successful DELETE
                     logger.info(f"Order {args.order_id} cancellation request submitted successfully.")
                elif "error" in response:
                     logger.error(f"Order cancellation failed: {response.get('details', response.get('error'))}")
                else:
                     logger.info("Order cancellation request processed. Check response for details.")
        else:
            logger.error(f"Failed to cancel order {args.order_id}. No response or error in API client.")
    
    elif args.action == "replace_order":
        # This is a more complex action. You'd need to:
        # 1. Get the current order details using get_order_by_id.
        # 2. Construct a new order payload, likely modifying parts of the old one.
        #    The Schwab API docs state: "The body of the PUT request functions as a new order"
        #    "and will completely replace the existing order."
        #    So, you need to provide a full, valid order payload.
        # 3. Prompt for confirmation.
        # 4. Call api_client.replace_order(account_hash_to_use, args.order_id, new_order_payload)
        logger.warning("Replace order functionality is complex and requires careful payload construction.")
        logger.info("To implement replace_order:")
        logger.info("1. Fetch the existing order details.")
        logger.info("2. Create a *complete new order payload* for the replacement.")
        logger.info("3. Call the replace_order endpoint with the new payload.")
        logger.info("Example: python trader.py replace_order --order_id <ID> --symbol <SYM> --quantity <QTY> --price <NEW_PRICE> ... etc.")
        
        if not account_hash_to_use: sys.exit("Account hash required for replace_order. Exiting.")
        if not args.order_id: parser.error("--order_id is required for replace_order action.")
        if not args.symbol or not args.quantity: # Basic requirements for a new order
            parser.error("--symbol and --quantity (and other relevant fields like --price for LIMIT) are required to define the new replacement order.")

        logger.info(f"Fetching original order {args.order_id} to see its details before replacing...")
        original_order = api_client.get_order_by_id(account_hash_to_use, args.order_id)
        if not original_order or (isinstance(original_order, dict) and "error" in original_order):
            logger.error(f"Could not retrieve original order {args.order_id}. Cannot proceed with replacement.")
            sys.exit(1)
        
        logger.info("Original order details:")
        pretty_print_json(original_order)

        # For simplicity, we'll assume the instruction and asset type remain the same.
        # A real replace might change more.
        # We'll take the instruction from the first leg of the original order.
        original_instruction = original_order.get("orderLegCollection", [{}])[0].get("instruction", "BUY") # Default to BUY if not found

        trailing_stop_details_replace = None
        if args.order_type.upper() == "TRAILING_STOP":
            if args.trailing_offset is None:
                parser.error("--trailing_offset is required for TRAILING_STOP orders.")
            trailing_stop_details_replace = {
                "link_basis": args.trailing_basis.upper(),
                "link_type": args.trailing_type.upper(),
                "offset": args.trailing_offset
            }

        try:
            replacement_order_payload = build_equity_order(
                symbol=args.symbol, # User must provide new symbol or re-confirm
                quantity=args.quantity, # User must provide new quantity
                instruction=original_instruction, # Assuming instruction type (BUY/SELL) doesn't change, or add CLI arg for it
                order_type=args.order_type.upper(), # User provides new order type
                price=args.price, # User provides new price if applicable
                stop_price=args.stop_price, # User provides new stop_price if applicable
                trailing_stop_details=trailing_stop_details_replace,
                duration=args.duration.upper(), # User provides new duration
                session=args.session.upper() # User provides new session
            )
        except ValueError as e:
            logger.error(f"Error building replacement order payload: {e}")
            sys.exit(1)

        logger.info(f"Preparing to REPLACE order {args.order_id} on account {account_hash_to_use[-10:]} with:")
        pretty_print_json(replacement_order_payload)

        if not args.yes:
            confirmation = input("Confirm REPLACING the order with these new details? (yes/no): ").strip().lower()
            if confirmation != 'yes':
                logger.info("Order replacement cancelled by user.")
                sys.exit(0)
        else:
            logger.warning("Auto-confirming order replacement due to -y/--yes flag.")

        response = api_client.replace_order(account_hash_to_use, args.order_id, replacement_order_payload)
        if response:
            logger.info(f"Replace order response for order ID {args.order_id}:")
            pretty_print_json(response)
            # Successful PUT for replace usually returns 200 OK. Location header might not be present.
            if isinstance(response, dict):
                if response.get("status_code") == 200:
                     logger.info(f"Order {args.order_id} replacement request submitted successfully.")
                     # The original order ID is modified, a new one isn't typically created for replace.
                     logger.info(f"Check status of order {args.order_id}: python trader.py get_order --order_id {args.order_id} --account_hash {account_hash_to_use}")
                elif "error" in response:
                     logger.error(f"Order replacement failed: {response.get('details', response.get('error'))}")
                else:
                     logger.info("Order replacement request processed. Check response for details.")
        else:
            logger.error(f"Failed to replace order {args.order_id}. No response or error in API client.")


    else:
        logger.error(f"Unknown action: {args.action}")
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()