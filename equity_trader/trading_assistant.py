# trade_assistant.py
import pandas as pd
import json
import logging
import os
from dotenv import load_dotenv
import argparse
from trader import main as run_trader
import config
from utils import setup_logging, pretty_print_json
from api_client import APIClient
from auth_manager import AuthManager

# For LLM API calls
import requests
import time

setup_logging()
logger = logging.getLogger(__name__)
load_dotenv()

# LLM API Configuration
LLM_API_KEY = os.getenv('LLM_API_KEY')
LLM_API_ENDPOINT = os.getenv('LLM_API_ENDPOINT', 'https://api.anthropic.com/v1/messages')
LLM_MODEL = os.getenv('LLM_MODEL', 'claude-3-opus-20240229')

def query_llm(prompt, system_prompt=None, max_tokens=4000):
    """Send a query to the LLM API and get a response."""
    if not LLM_API_KEY:
        logger.error("LLM_API_KEY not set in environment variables")
        return None
    
    headers = {
        "x-api-key": LLM_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    
    payload = {
        "model": LLM_MODEL,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}]
    }
    
    if system_prompt:
        payload["system"] = system_prompt
    
    try:
        response = requests.post(LLM_API_ENDPOINT, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()["content"][0]["text"]
    except Exception as e:
        logger.error(f"Error querying LLM: {e}")
        if 'response' in locals() and hasattr(response, 'text'):
            logger.error(f"Response: {response.text}")
        return None

def read_trade_sheet(file_path):
    """Read the Excel file with trade recommendations."""
    try:
        df = pd.read_excel(file_path)
        return df
    except Exception as e:
        logger.error(f"Error reading Excel file: {e}")
        return None

def get_account_info(api_client, account_hash):
    """Get account balance and positions."""
    return api_client.get_account_balances_positions(account_hash, fields="positions")

def analyze_trades_with_llm(trades_df, account_info):
    """Send trade data and account info to LLM for analysis and sizing recommendations."""
    
    # Format the data for the LLM
    trades_text = trades_df.to_string(index=False)
    account_text = json.dumps(account_info, indent=2)
    
    system_prompt = """
    You are a trading assistant AI that helps determine optimal position sizing for options trades.
    Your task is to analyze the provided trade recommendations and account information to suggest:
    1. The specific trades to execute
    2. The appropriate position sizing based on account balance and risk management
    3. The strike prices to use based on current price and the recommended wing width
    
    Use these risk management guidelines:
    - Never risk more than 5% of the account on any single trade
    - For high confidence trades, can allocate up to the maximum recommended position size
    - For medium confidence, reduce position size by 30%
    - For low confidence, reduce position size by 50%
    - Consider existing positions when calculating total portfolio risk
    
    Provide your recommendations in a structured JSON format that can be programmatically processed.
    """
    
    prompt = f"""
    Please analyze these trade recommendations and my account information to provide specific trade execution plans.
    
    ## TRADE RECOMMENDATIONS:
    {trades_text}
    
    ## ACCOUNT INFORMATION:
    {account_text}
    
    Based on this information, please provide:
    1. A JSON-formatted list of trades to execute
    2. For each trade, specify:
       - Ticker symbol
       - Strategy to use (from the recommendations)
       - Position sizing (number of contracts)
       - Appropriate strike prices based on current market prices and the recommended wing width
       - Order types (LIMIT, STOP, etc.)
       - Duration (based on the expiration recommendation)
    
    Return your analysis in a structured JSON format (without Markdown formatting) that I can parse programmatically.
    """
    
    response = query_llm(prompt, system_prompt)
    return response

def extract_trades_from_llm_response(llm_response):
    """Extract the JSON trades data from the LLM response."""
    try:
        # Find JSON in the response - look for content between curly braces
        import re
        json_match = re.search(r'(\{.*\})', llm_response, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            trades_data = json.loads(json_str)
            return trades_data
        else:
            # If no JSON format detected, try to parse the whole response
            trades_data = json.loads(llm_response)
            return trades_data
    except Exception as e:
        logger.error(f"Error extracting trades from LLM response: {e}")
        logger.debug(f"LLM response: {llm_response}")
        return None

def execute_trades(trades_data, api_client, account_hash, dry_run=True):
    """Execute the recommended trades."""
    results = []
    
    for trade in trades_data.get("trades", []):
        try:
            symbol = trade.get("symbol")
            strategy = trade.get("strategy")
            order_type = trade.get("order_type", "LIMIT")
            duration = trade.get("duration", "DAY")
            price = trade.get("limit_price")
            quantity = trade.get("quantity", 1)
            
            # Build the order based on the strategy
            if strategy == "Put Credit Spread":
                # Example for a Put Credit Spread
                # This would need to be expanded for different strategy types
                order_payload = {
                    "orderType": order_type,
                    "session": "NORMAL",
                    "duration": duration,
                    "orderStrategyType": "TRIGGER",
                    "price": str(price) if price else None,
                    # Additional complex option order details would go here
                }
                
                logger.info(f"Preparing order for {symbol}: {strategy}, {quantity} contracts")
                if dry_run:
                    logger.info(f"DRY RUN - Would execute: {json.dumps(order_payload, indent=2)}")
                    results.append({"symbol": symbol, "status": "DRY_RUN", "details": order_payload})
                else:
                    # This would need to be expanded to handle the specific option order types
                    # The actual implementation depends on how your broker API handles options
                    response = api_client.place_order(account_hash, order_payload)
                    results.append({"symbol": symbol, "status": "EXECUTED", "response": response})
            else:
                logger.warning(f"Unsupported strategy: {strategy} for {symbol}")
                results.append({"symbol": symbol, "status": "SKIPPED", "reason": f"Unsupported strategy: {strategy}"})
        
        except Exception as e:
            logger.error(f"Error executing trade for {trade.get('symbol', 'unknown')}: {e}")
            results.append({"symbol": trade.get("symbol", "unknown"), "status": "ERROR", "error": str(e)})
    
    return results
# Add this to trade_assistant.py

def build_option_order(strategy, symbol, quantity, strikes, expiration, order_type="LIMIT", price=None, duration="DAY"):
    """Build an option order payload based on the strategy."""
    
    if strategy == "Put Credit Spread":
        # Example for a Put Credit Spread (sell higher strike put, buy lower strike put)
        sell_strike, buy_strike = strikes
        
        option_payload = {
            "orderType": order_type,
            "session": "NORMAL",
            "duration": duration,
            "orderStrategyType": "SPREAD",
            "price": str(price) if price else None,
            "orderLegCollection": [
                {
                    "instrument": {
                        "symbol": f"{symbol}_{expiration}P{sell_strike}",
                        "assetType": "OPTION"
                    },
                    "instruction": "SELL_TO_OPEN",
                    "quantity": quantity
                },
                {
                    "instrument": {
                        "symbol": f"{symbol}_{expiration}P{buy_strike}",
                        "assetType": "OPTION"
                    },
                    "instruction": "BUY_TO_OPEN",
                    "quantity": quantity
                }
            ]
        }
        return option_payload
    
    elif strategy == "Call Debit Spread":
        # Buy lower strike call, sell higher strike call
        buy_strike, sell_strike = strikes
        
        option_payload = {
            "orderType": order_type,
            "session": "NORMAL",
            "duration": duration,
            "orderStrategyType": "SPREAD",
            "price": str(price) if price else None,
            "orderLegCollection": [
                {
                    "instrument": {
                        "symbol": f"{symbol}_{expiration}C{buy_strike}",
                        "assetType": "OPTION"
                    },
                    "instruction": "BUY_TO_OPEN",
                    "quantity": quantity
                },
                {
                    "instrument": {
                        "symbol": f"{symbol}_{expiration}C{sell_strike}",
                        "assetType": "OPTION"
                    },
                    "instruction": "SELL_TO_OPEN",
                    "quantity": quantity
                }
            ]
        }
        return option_payload
    
    elif strategy == "Iron Condor":
        # Sell put spread and call spread
        put_sell_strike, put_buy_strike, call_sell_strike, call_buy_strike = strikes
        
        option_payload = {
            "orderType": order_type,
            "session": "NORMAL",
            "duration": duration,
            "orderStrategyType": "SPREAD",
            "price": str(price) if price else None,
            "orderLegCollection": [
                # Put credit spread leg
                {
                    "instrument": {
                        "symbol": f"{symbol}_{expiration}P{put_sell_strike}",
                        "assetType": "OPTION"
                    },
                    "instruction": "SELL_TO_OPEN",
                    "quantity": quantity
                },
                {
                    "instrument": {
                        "symbol": f"{symbol}_{expiration}P{put_buy_strike}",
                        "assetType": "OPTION"
                    },
                    "instruction": "BUY_TO_OPEN",
                    "quantity": quantity
                },
                # Call credit spread leg
                {
                    "instrument": {
                        "symbol": f"{symbol}_{expiration}C{call_sell_strike}",
                        "assetType": "OPTION"
                    },
                    "instruction": "SELL_TO_OPEN",
                    "quantity": quantity
                },
                {
                    "instrument": {
                        "symbol": f"{symbol}_{expiration}C{call_buy_strike}",
                        "assetType": "OPTION"
                    },
                    "instruction": "BUY_TO_OPEN",
                    "quantity": quantity
                }
            ]
        }
        return option_payload
    
    # Add more strategies as needed...
    else:
        raise ValueError(f"Unsupported strategy: {strategy}")
def main():
    parser = argparse.ArgumentParser(description="Trade Assistant - LLM-powered trading")
    parser.add_argument("--excel", type=str, required=True, help="Path to Excel file with trade recommendations")
    parser.add_argument("--account_hash", type=str, help="Account hash to use")
    parser.add_argument("--account_number", type=str, help="Account number to use (will look up hash)")
    parser.add_argument("--dry_run", action="store_true", default=True, help="Don't execute trades, just print what would happen")
    parser.add_argument("--execute", action="store_true", help="Actually execute the trades (overrides --dry_run)")
    
    args = parser.parse_args()
    
    # Initialize API client
    auth_manager = AuthManager()
    api_client = APIClient(auth_manager)
    
    # Determine account hash to use (similar logic as in trader.py)
    account_hash_to_use = args.account_hash
    if not account_hash_to_use:
        account_hash_to_use = config.DEFAULT_ACCOUNT_HASH_ENV
    
    if not account_hash_to_use:
        # Use account number to find hash
        preferred_account_number = args.account_number if args.account_number else config.DEFAULT_ACCOUNT_NUMBER_ENV
        if preferred_account_number:
            logger.info(f"Looking up hash for account number: {preferred_account_number}")
            from trader import get_account_hash_interactive
            account_hash_to_use = get_account_hash_interactive(api_client, preferred_account_number)
        else:
            logger.info("No account specified, using interactive selection")
            from trader import get_account_hash_interactive
            account_hash_to_use = get_account_hash_interactive(api_client)
    
    if not account_hash_to_use:
        logger.error("Could not determine account hash. Exiting.")
        return
    
    # Read trade recommendations
    trades_df = read_trade_sheet(args.excel)
    if trades_df is None:
        logger.error("Failed to read trade recommendations. Exiting.")
        return
    
    # Get account information
    account_info = get_account_info(api_client, account_hash_to_use)
    if not account_info or (isinstance(account_info, dict) and "error" in account_info):
        logger.error(f"Failed to get account information: {account_info}")
        return
    
    # Analyze trades with LLM
    logger.info("Analyzing trades with LLM...")
    llm_analysis = analyze_trades_with_llm(trades_df, account_info)
    if not llm_analysis:
        logger.error("Failed to get LLM analysis. Exiting.")
        return
    
    # Extract trade recommendations from LLM response
    trades_to_execute = extract_trades_from_llm_response(llm_analysis)
    if not trades_to_execute:
        logger.error("Failed to extract trades from LLM response. Exiting.")
        return
    
    # Print the trade recommendations
    logger.info("LLM Trade Recommendations:")
    pretty_print_json(trades_to_execute)
    
    # Execute trades (or dry run)
    dry_run = not args.execute
    logger.info(f"{'DRY RUN - ' if dry_run else ''}Executing trades...")
    execution_results = execute_trades(trades_to_execute, api_client, account_hash_to_use, dry_run)
    
    # Print results
    logger.info("Execution Results:")
    pretty_print_json(execution_results)
    
    if dry_run:
        logger.info("This was a dry run. Use --execute to actually place trades.")

if __name__ == "__main__":
    main()