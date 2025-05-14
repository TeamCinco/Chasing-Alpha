# order_builder.py
import logging
import config

logger = logging.getLogger(__name__)

# --- Equity Instructions ---
# BUY: To establish or add to a long position.
# SELL: To close or reduce a long position.
# SELL_SHORT: To establish or add to a short position. (Requires margin account, specific permissions)
# BUY_TO_COVER: To close or reduce a short position.

# --- Order Types ---
# MARKET: Execute at the current best available price.
# LIMIT: Execute at a specified price or better.
# STOP: Becomes a market order when the stop price is reached.
# STOP_LIMIT: Becomes a limit order when the stop price is reached.
# TRAILING_STOP: Stop price trails the market price by a specified amount/percentage.

# --- Durations ---
# DAY: Valid for the current trading day only.
# GOOD_TILL_CANCEL (GTC): Remains active until filled or cancelled (max usually 60-180 days).
# FILL_OR_KILL (FOK): Execute entire order immediately or cancel.
# IMMEDIATE_OR_CANCEL (IOC): Execute any portion immediately, cancel the rest.

# --- Sessions ---
# NORMAL: Regular trading hours (e.g., 9:30 AM - 4:00 PM ET).
# AM: Pre-market session.
# PM: After-hours session.
# SEAMLESS: Order is eligible for execution across all available sessions (pre, normal, post).

# --- Allowed Values (for validation) ---
ALLOWED_EQUITY_INSTRUCTIONS = ["BUY", "SELL", "SELL_SHORT", "BUY_TO_COVER"]
ALLOWED_ORDER_TYPES = ["MARKET", "LIMIT", "STOP", "STOP_LIMIT", "TRAILING_STOP"]
ALLOWED_DURATIONS = ["DAY", "GOOD_TILL_CANCEL", "FILL_OR_KILL", "IMMEDIATE_OR_CANCEL"] # Add more if needed
ALLOWED_SESSIONS = ["NORMAL", "AM", "PM", "SEAMLESS"] # Add more if needed
ALLOWED_TRAILING_STOP_LINK_BASIS = ["ASK", "BID", "LAST", "MARK"] # Check API docs for exact list
ALLOWED_TRAILING_STOP_LINK_TYPES = ["VALUE", "PERCENT"] # Check API docs for exact list


def build_equity_order(
    symbol: str,
    quantity: int,
    instruction: str,
    order_type: str,
    price: float = None,            # For LIMIT, STOP_LIMIT orders (limit price)
    stop_price: float = None,       # For STOP, STOP_LIMIT orders (trigger price)
    trailing_stop_details: dict = None, # For TRAILING_STOP orders.
                                        # Example: {"link_basis": "BID", "link_type": "VALUE", "offset": 1.00}
                                        # or {"link_basis": "MARK", "link_type": "PERCENT", "offset": 5.0}
    duration: str = config.DEFAULT_DURATION,
    session: str = config.DEFAULT_SESSION,
    order_strategy_type: str = "SINGLE" # Usually "SINGLE" for simple equity trades
):
    """
    Builds a payload for a single leg equity order.
    Supports MARKET, LIMIT, STOP, STOP_LIMIT, and TRAILING_STOP orders.
    """
    # --- Input Validations ---
    if not isinstance(symbol, str) or not symbol.strip():
        raise ValueError("Symbol must be a non-empty string.")
    symbol = symbol.strip().upper()

    if not isinstance(quantity, int) or quantity <= 0:
        raise ValueError("Quantity must be a positive integer.")

    instruction = instruction.upper()
    if instruction not in ALLOWED_EQUITY_INSTRUCTIONS:
        raise ValueError(f"Invalid instruction '{instruction}'. Allowed: {ALLOWED_EQUITY_INSTRUCTIONS}")

    order_type = order_type.upper()
    if order_type not in ALLOWED_ORDER_TYPES:
        raise ValueError(f"Invalid order_type '{order_type}'. Allowed: {ALLOWED_ORDER_TYPES}")

    duration = duration.upper()
    if duration not in ALLOWED_DURATIONS:
        logger.warning(f"Duration '{duration}' not in predefined list. Ensure it's valid for the API.")
        # raise ValueError(f"Invalid duration '{duration}'. Allowed: {ALLOWED_DURATIONS}")

    session = session.upper()
    if session not in ALLOWED_SESSIONS:
        logger.warning(f"Session '{session}' not in predefined list. Ensure it's valid for the API.")
        # raise ValueError(f"Invalid session '{session}'. Allowed: {ALLOWED_SESSIONS}")

    # --- Order Type Specific Validations & Payload Construction ---
    order_payload = {
        "orderType": order_type,
        "session": session,
        "duration": duration,
        "orderStrategyType": order_strategy_type,
        # "complexOrderStrategyType": "NONE" # Often optional for single leg, can be added if required
    }

    if order_type == "LIMIT":
        if price is None or not isinstance(price, (float, int)) or price <= 0:
            raise ValueError("Price must be a positive number for LIMIT orders.")
        order_payload["price"] = f"{price:.2f}" # API expects string for price

    elif order_type == "STOP":
        if stop_price is None or not isinstance(stop_price, (float, int)) or stop_price <= 0:
            raise ValueError("Stop price must be a positive number for STOP orders.")
        order_payload["stopPrice"] = f"{stop_price:.2f}" # API expects string

    elif order_type == "STOP_LIMIT":
        if price is None or not isinstance(price, (float, int)) or price <= 0:
            raise ValueError("Price (limit price) must be a positive number for STOP_LIMIT orders.")
        if stop_price is None or not isinstance(stop_price, (float, int)) or stop_price <= 0:
            raise ValueError("Stop price must be a positive number for STOP_LIMIT orders.")
        order_payload["price"] = f"{price:.2f}"
        order_payload["stopPrice"] = f"{stop_price:.2f}"

    elif order_type == "TRAILING_STOP":
        if trailing_stop_details is None or not isinstance(trailing_stop_details, dict):
            raise ValueError("trailing_stop_details (dict) are required for TRAILING_STOP orders.")
        
        required_keys = ["link_basis", "link_type", "offset"]
        for key in required_keys:
            if key not in trailing_stop_details:
                raise ValueError(f"Missing '{key}' in trailing_stop_details for TRAILING_STOP order.")

        link_basis = str(trailing_stop_details["link_basis"]).upper()
        if link_basis not in ALLOWED_TRAILING_STOP_LINK_BASIS:
            raise ValueError(f"Invalid 'link_basis' in trailing_stop_details. Allowed: {ALLOWED_TRAILING_STOP_LINK_BASIS}")
        
        link_type = str(trailing_stop_details["link_type"]).upper()
        if link_type not in ALLOWED_TRAILING_STOP_LINK_TYPES:
            raise ValueError(f"Invalid 'link_type' in trailing_stop_details. Allowed: {ALLOWED_TRAILING_STOP_LINK_TYPES}")

        offset = trailing_stop_details["offset"]
        if not isinstance(offset, (float, int)) or offset <= 0:
            raise ValueError("'offset' in trailing_stop_details must be a positive number.")

        order_payload["stopPriceLinkBasis"] = link_basis
        order_payload["stopPriceLinkType"] = link_type
        order_payload["stopPriceOffset"] = float(offset) # API expects number for offset

    # --- Order Leg Collection ---
    instrument_details = {
        "symbol": symbol,
        "assetType": "EQUITY"
    }

    order_leg = {
        "instruction": instruction,
        "quantity": quantity,
        "instrument": instrument_details
    }
    order_payload["orderLegCollection"] = [order_leg]

    logger.debug(f"Built order payload: {order_payload}")
    return order_payload


# --- Example Usage (for testing this module directly) ---
if __name__ == "__main__":
    from utils import pretty_print_json, setup_logging
    setup_logging() # To see logger messages

    print("--- Building Market Buy Order ---")
    try:
        market_buy_order = build_equity_order(
            symbol="AAPL",
            quantity=10,
            instruction="BUY",
            order_type="MARKET",
            duration="DAY",
            session="NORMAL"
        )
        pretty_print_json(market_buy_order)
    except ValueError as e:
        print(f"Error: {e}")

    print("\n--- Building Limit Sell Order ---")
    try:
        limit_sell_order = build_equity_order(
            symbol="MSFT",
            quantity=5,
            instruction="SELL",
            order_type="LIMIT",
            price=300.50,
            duration="GOOD_TILL_CANCEL"
        )
        pretty_print_json(limit_sell_order)
    except ValueError as e:
        print(f"Error: {e}")

    print("\n--- Building Stop Loss Order ---")
    try:
        stop_loss_order = build_equity_order(
            symbol="GOOG",
            quantity=2,
            instruction="SELL",
            order_type="STOP",
            stop_price=2500.00
        )
        pretty_print_json(stop_loss_order)
    except ValueError as e:
        print(f"Error: {e}")

    print("\n--- Building Stop Limit Order ---")
    try:
        stop_limit_order = build_equity_order(
            symbol="TSLA",
            quantity=1,
            instruction="BUY",
            order_type="STOP_LIMIT",
            price=705.00, # Limit price
            stop_price=700.00 # Stop trigger price
        )
        pretty_print_json(stop_limit_order)
    except ValueError as e:
        print(f"Error: {e}")

    print("\n--- Building Trailing Stop Sell Order (Value) ---")
    try:
        trailing_stop_value_order = build_equity_order(
            symbol="NVDA",
            quantity=3,
            instruction="SELL",
            order_type="TRAILING_STOP",
            trailing_stop_details={
                "link_basis": "LAST", # or BID, ASK, MARK
                "link_type": "VALUE",
                "offset": 5.00 # $5.00 trailing stop
            }
        )
        pretty_print_json(trailing_stop_value_order)
    except ValueError as e:
        print(f"Error: {e}")

    print("\n--- Building Trailing Stop Sell Order (Percent) ---")
    try:
        trailing_stop_percent_order = build_equity_order(
            symbol="AMZN",
            quantity=1,
            instruction="SELL",
            order_type="TRAILING_STOP",
            trailing_stop_details={
                "link_basis": "MARK",
                "link_type": "PERCENT",
                "offset": 2.5 # 2.5% trailing stop
            }
        )
        pretty_print_json(trailing_stop_percent_order)
    except ValueError as e:
        print(f"Error: {e}")

    print("\n--- Building Invalid Order (Missing Price for Limit) ---")
    try:
        invalid_order = build_equity_order(
            symbol="FB",
            quantity=10,
            instruction="BUY",
            order_type="LIMIT" # Missing price
        )
        pretty_print_json(invalid_order)
    except ValueError as e:
        print(f"Error: {e}")