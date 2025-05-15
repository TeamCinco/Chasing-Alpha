"""
LLM-Powered Trade Assistant

This script integrates a Large Language Model (LLM) with your Schwab trading system
to analyze account information and Excel-based trade recommendations to determine 
optimal trade sizing and execution parameters.
"""

import os
import sys
import json
import logging
import argparse
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path to import from other modules
parent_dir = str(Path(__file__).resolve().parent.parent)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# Import local modules
from trade_llm_assistant.llm_client import LLMClient
from trade_llm_assistant.market_data import get_market_data, get_option_chains, get_historical_volatility
from trade_llm_assistant.option_order_builder import OptionOrderBuilder

# Import from parent project
try:
    from equity_trader.utils import setup_logging, pretty_print_json
    from equity_trader.api_client import APIClient
    from equity_trader.auth_manager import AuthManager
    from equity_trader import config
    from equity_trader.trader import get_account_hash_interactive
except ImportError as e:
    print(f"Error importing from parent project: {e}")
    print("Make sure the equity_trader module is properly configured.")
    sys.exit(1)

# Set up logging
setup_logging()
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class TradeAssistant:
    """
    LLM-powered assistant for trade analysis and execution
    
    This class integrates LLM capabilities with your trading platform to analyze
    trade recommendations and account data, determine optimal position sizing, 
    and execute trades according to risk management guidelines.
    """
    
    def __init__(self, api_client, account_hash=None):
        """
        Initialize the Trade Assistant
        
        Args:
            api_client: The broker API client
            account_hash (str, optional): Account identifier hash
        """
        self.api_client = api_client
        self.account_hash = account_hash
        self.llm_client = LLMClient()
        self.order_builder = OptionOrderBuilder(api_client)
        
        # Initialize cache for market data to avoid redundant API calls
        self.market_data_cache = {}
        self.option_chains_cache = {}
        self.account_info_cache = None
        
        # Set default risk management parameters
        self.risk_params = {
            "max_account_risk_pct": 0.05,  # 5% max risk on any trade
            "max_total_risk_pct": 0.20,     # 20% max total portfolio risk
            "confidence_scaling": {
                "high": 1.0,     # No reduction
                "medium": 0.7,   # 30% reduction
                "low": 0.5       # 50% reduction
            }
        }
    
    def read_trade_sheet(self, file_path):
        """
        Read the Excel file containing trade recommendations
        
        Args:
            file_path (str): Path to the Excel file
            
        Returns:
            DataFrame: The trade recommendations
        """
        try:
            df = pd.read_excel(file_path)
            logger.info(f"Successfully read {len(df)} trade recommendations from {file_path}")
            return df
        except Exception as e:
            logger.error(f"Error reading Excel file: {e}")
            return None
    
    def get_account_info(self):
        """
        Get account balance and positions
        
        Returns:
            dict: Account information including balances and positions
        """
        if self.account_info_cache:
            logger.debug("Using cached account information")
            return self.account_info_cache
            
        try:
            account_info = self.api_client.get_account_balances_positions(
                self.account_hash, 
                fields="positions"
            )
            
            if not account_info or (isinstance(account_info, dict) and "error" in account_info):
                logger.error(f"Failed to get account information: {account_info}")
                return None
                
            logger.info("Successfully retrieved account information")
            self.account_info_cache = account_info
            return account_info
            
        except Exception as e:
            logger.error(f"Error getting account information: {e}")
            return None
    
    def get_market_data_for_symbols(self, symbols):
        """
        Get market data for a list of symbols
        
        Args:
            symbols (list): List of ticker symbols
            
        Returns:
            dict: Market data for the symbols
        """
        # Filter out symbols for which we already have cached data
        symbols_to_fetch = [s for s in symbols if s not in self.market_data_cache]
        
        if symbols_to_fetch:
            logger.info(f"Fetching market data for {len(symbols_to_fetch)} symbols")
            new_data = get_market_data(self.api_client, symbols_to_fetch)
            
            # Update cache with new data
            self.market_data_cache.update(new_data)
        
        # Return data for all requested symbols from the cache
        return {s: self.market_data_cache.get(s) for s in symbols}
    
    def get_option_chains_for_symbols(self, symbols, expiration_date=None):
        """
        Get option chain data for a list of symbols
        
        Args:
            symbols (list): List of ticker symbols
            expiration_date (str, optional): Target expiration date
            
        Returns:
            dict: Option chain data for the symbols
        """
        # Create cache key using both symbol and expiration date
        cache_keys = {s: f"{s}_{expiration_date}" if expiration_date else s for s in symbols}
        
        # Filter out symbols for which we already have cached data
        symbols_to_fetch = [s for s in symbols if cache_keys[s] not in self.option_chains_cache]
        
        if symbols_to_fetch:
            logger.info(f"Fetching option chains for {len(symbols_to_fetch)} symbols")
            new_chains = get_option_chains(self.api_client, symbols_to_fetch, expiration_date)
            
            # Update cache with new data
            for s in symbols_to_fetch:
                self.option_chains_cache[cache_keys[s]] = new_chains.get(s)
        
        # Return data for all requested symbols from the cache
        return {s: self.option_chains_cache.get(cache_keys[s]) for s in symbols}
    
    def analyze_trades_with_llm(self, trades_df, account_info, market_data=None, option_chains=None):
        """
        Send trade recommendations, account info, and market data to LLM for analysis
        
        Args:
            trades_df (DataFrame): DataFrame containing trade recommendations
            account_info (dict): Account balance and positions
            market_data (dict, optional): Current market prices for symbols
            option_chains (dict, optional): Option chain data for symbols
            
        Returns:
            str: The LLM's analysis and recommendations
        """
        # Format the data for the LLM
        trades_text = trades_df.to_string(index=False)
        account_text = json.dumps(account_info, indent=2)
        
        market_data_text = ""
        if market_data:
            market_data_text = "## CURRENT MARKET PRICES:\n" + json.dumps(market_data, indent=2)
        
        option_chains_text = ""
        if option_chains:
            # Option chains can be very large, so we'll summarize them
            option_chains_summary = {}
            
            for symbol, chain in option_chains.items():
                if not chain:
                    continue
                    
                # Create a more concise summary
                if 'mock_data' in chain and chain['mock_data']:
                    # This is mock data, just include the basic info
                    option_chains_summary[symbol] = {
                        "stock_price": chain.get("stock_price"),
                        "expiration_dates": chain.get("expiration_dates", [])[:3],  # First 3
                        "strike_range": [min(chain.get("strikes", [])), max(chain.get("strikes", []))]
                    }
                else:
                    # This is real data, create a more meaningful summary based on the structure
                    # This would need to be adapted to the actual structure of your option chain data
                    option_chains_summary[symbol] = {
                        "available_expirations": chain.get("expirationDates", [])[:3],  # First 3
                        "strike_count": len(chain.get("strikes", [])),
                        "underlying_price": chain.get("underlyingPrice")
                    }
            
            option_chains_text = "## OPTION CHAIN SUMMARY:\n" + json.dumps(option_chains_summary, indent=2)
        
        # Create system prompt to guide the LLM
        system_prompt = """
        You are a sophisticated trading assistant AI that helps determine optimal position sizing for options trades.
        Your task is to analyze trade recommendations, account information, and market data to suggest:
        
        1. Which specific trades to execute based on the recommendations
        2. The appropriate position sizing based on account balance and risk management
        3. The optimal strike prices to use based on current market prices and the recommended wing width
        4. Appropriate order types and limit prices based on market conditions
        
        Use these risk management guidelines:
        - Never risk more than 5% of the account on any single trade
        - Total portfolio risk should not exceed 20% of the account
        - For high confidence trades, allocate up to the maximum recommended position size
        - For medium confidence, reduce position size by 30%
        - For low confidence, reduce position size by 50%
        - Consider existing positions when calculating total portfolio risk
        
        For options strategies:
        - Put Credit Spread: Sell a put at a higher strike, buy a put at a lower strike
        - Call Credit Spread: Sell a call at a higher strike, buy a call at a lower strike
        - Call Debit Spread: Buy a call at a lower strike, sell a call at a higher strike
        - Put Debit Spread: Buy a put at a higher strike, sell a put at a lower strike
        - Iron Condor: Combine a put credit spread below the market and a call credit spread above the market
        
        Wing width guidelines:
        - Narrow (0.5-0.75 standard deviation): Typically 8-12% of the stock price
        - Medium (1 standard deviation): Typically 16% of the stock price
        - Wide (1.5-2 standard deviations): Typically 24-32% of the stock price
        
        Provide your recommendations in a structured JSON format that can be programmatically processed.
        """
        
        # Create user prompt with the specific data and request
        prompt = f"""
        Please analyze these trade recommendations, account information, and market data to provide specific trade execution plans.
        
        ## TRADE RECOMMENDATIONS:
        {trades_text}
        
        ## ACCOUNT INFORMATION:
        {account_text}
        
        {market_data_text}
        
        {option_chains_text}
        
        Based on this information, please provide:
        1. A JSON-formatted list of trades to execute
        2. For each trade, specify:
           - Ticker symbol
           - Strategy to use (from the recommendations)
           - Position sizing (number of contracts)
           - Appropriate strike prices based on current market prices and the recommended wing width
           - Order types (LIMIT, STOP, etc.)
           - Duration (based on the expiration recommendation)
           - Limit price (for LIMIT orders)
           - Maximum risk for the trade
           - Justification for the trade
        
        Return your analysis in a structured JSON format like this:
        {{
          "trades": [
            {{
              "symbol": "AAPL",
              "strategy": "Put Credit Spread",
              "quantity": 2,
              "strikes": [170, 165],
              "expiration": "2025-06-15",
              "order_type": "LIMIT",
              "limit_price": 1.25,
              "duration": "DAY",
              "max_loss": "$500",
              "reason": "High confidence bullish trade with medium wing width"
            }}
          ],
          "total_risk": "$500",
          "account_value": "$50000",
          "risk_percentage": "1%",
          "analysis": "Brief explanation of the overall trading plan and risk considerations"
        }}
        """
        
        # Send the request to the LLM
        logger.info("Sending request to LLM for trade analysis...")
        response = self.llm_client.query(prompt, system_prompt)
        
        if not response:
            logger.error("Failed to get response from LLM")
            return None
            
        return response
    
    def extract_trades_from_llm_response(self, llm_response):
        """
        Extract the JSON trades data from the LLM response
        
        Args:
            llm_response (str): The raw text response from the LLM
            
        Returns:
            dict or None: The parsed JSON object, or None if parsing failed
        """
        if not llm_response:
            return None
            
        trades_data = self.llm_client.extract_json_from_response(llm_response)
        
        if not trades_data:
            logger.error("Failed to extract JSON from LLM response")
            logger.debug(f"Raw LLM response: {llm_response}")
            return None
        
        if "trades" not in trades_data:
            logger.error("Extracted JSON does not contain 'trades' key")
            logger.debug(f"Extracted JSON: {trades_data}")
            return None
        
        return trades_data
    
    def execute_trades(self, trades_data, dry_run=True):
        """
        Execute the recommended trades
        
        Args:
            trades_data (dict): The trade recommendations from the LLM
            dry_run (bool): If True, simulate execution without placing actual orders
            
        Returns:
            list: Results of trade execution
        """
        results = []
        
        if not trades_data or "trades" not in trades_data:
            logger.error("No valid trades data provided")
            return results
        
        for trade in trades_data["trades"]:
            try:
                symbol = trade.get("symbol")
                strategy = trade.get("strategy")
                order_type = trade.get("order_type", "LIMIT")
                duration = trade.get("duration", "DAY")
                price = trade.get("limit_price")
                quantity = trade.get("quantity", 1)
                strikes = trade.get("strikes")
                expiration = trade.get("expiration")
                
                logger.info(f"Processing trade for {symbol}: {strategy}, {quantity} contracts")
                
                try:
                    # Build the option order
                    order_payload = self.order_builder.build_option_order(
                        strategy=strategy,
                        symbol=symbol,
                        quantity=quantity,
                        strikes=strikes,
                        expiration=expiration,
                        order_type=order_type,
                        price=price,
                        duration=duration
                    )
                    
                    if dry_run:
                        logger.info(f"DRY RUN - Would execute: {json.dumps(order_payload, indent=2)}")
                        results.append({
                            "symbol": symbol,
                            "strategy": strategy,
                            "status": "DRY_RUN",
                            "details": order_payload,
                            "max_loss": trade.get("max_loss")
                        })
                    else:
                        # Place the actual order
                        logger.info(f"Placing order for {symbol}: {strategy}")
                        response = self.api_client.place_order(self.account_hash, order_payload)
                        
                        results.append({
                            "symbol": symbol,
                            "strategy": strategy,
                            "status": "EXECUTED",
                            "response": response,
                            "max_loss": trade.get("max_loss"),
                            "order_id": response.get("orderId") if response else None
                        })
                
                except ValueError as e:
                    logger.warning(f"Error building order: {e}")
                    results.append({
                        "symbol": symbol,
                        "strategy": strategy,
                        "status": "SKIPPED",
                        "reason": str(e)
                    })
                    
            except Exception as e:
                logger.error(f"Error executing trade for {trade.get('symbol', 'unknown')}: {e}")
                results.append({
                    "symbol": trade.get("symbol", "unknown"),
                    "status": "ERROR",
                    "error": str(e)
                })
        
        return results
    
    def save_results(self, trades_data, execution_results, output_dir=None):
        """
        Save the LLM analysis and execution results to files
        
        Args:
            trades_data (dict): The trade recommendations from the LLM
            execution_results (list): Results of trade execution
            output_dir (str, optional): Directory to save results
            
        Returns:
            tuple: Paths to the saved files
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if not output_dir:
            output_dir = os.path.join(os.path.dirname(__file__), "results")
            
        os.makedirs(output_dir, exist_ok=True)
        
        # Save LLM analysis
        analysis_path = os.path.join(output_dir, f"llm_analysis_{timestamp}.json")
        with open(analysis_path, "w") as f:
            json.dump(trades_data, f, indent=2)
        
        # Save execution results
        results_path = os.path.join(output_dir, f"execution_results_{timestamp}.json")
        with open(results_path, "w") as f:
            json.dump(execution_results, f, indent=2)
        
        logger.info(f"Saved analysis to {analysis_path}")
        logger.info(f"Saved execution results to {results_path}")
        
        return analysis_path, results_path


def main():
    """Main entry point for the trade assistant"""
    parser = argparse.ArgumentParser(description="LLM-Powered Trade Assistant")
    parser.add_argument("--excel", type=str, required=True, help="Path to Excel file with trade recommendations")
    parser.add_argument("--account_hash", type=str, help="Account hash to use")
    parser.add_argument("--account_number", type=str, help="Account number to use (will look up hash)")
    parser.add_argument("--dry_run", action="store_true", default=True, help="Don't execute trades, just simulate")
    parser.add_argument("--execute", action="store_true", help="Actually execute the trades (overrides --dry_run)")
    parser.add_argument("--output_dir", type=str, help="Directory to save results")
    parser.add_argument("--skip_market_data", action="store_true", help="Skip fetching market data")
    
    args = parser.parse_args()
    
    # Initialize API client and auth manager
    auth_manager = AuthManager()
    api_client = APIClient(auth_manager)
    
    # Determine account hash to use
    account_hash_to_use = args.account_hash
    if not account_hash_to_use:
        account_hash_to_use = os.getenv('SCHWAB_ACCOUNT_HASH')
    
    if not account_hash_to_use:
        # Use account number to find hash
        preferred_account_number = args.account_number
        if not preferred_account_number:
            preferred_account_number = os.getenv('SCHWAB_ACCOUNT_NUMBER')
            
        if preferred_account_number:
            logger.info(f"Looking up hash for account number: {preferred_account_number}")
            account_hash_to_use = get_account_hash_interactive(api_client, preferred_account_number)
        else:
            logger.info("No account specified, using interactive selection")
            account_hash_to_use = get_account_hash_interactive(api_client)
    
    if not account_hash_to_use:
        logger.error("Could not determine account hash. Exiting.")
        return 1
    
    # Create trade assistant
    trade_assistant = TradeAssistant(api_client, account_hash_to_use)
    
    # Read trade recommendations
    trades_df = trade_assistant.read_trade_sheet(args.excel)
    if trades_df is None:
        logger.error("Failed to read trade recommendations. Exiting.")
        return 1
    
    # Get account information
    account_info = trade_assistant.get_account_info()
    if not account_info:
        logger.error("Failed to get account information. Exiting.")
        return 1
    
    market_data = None
    option_chains = None
    
    if not args.skip_market_data:
        # Get list of symbols from the trades dataframe
        if 'Ticker' in trades_df.columns:
            symbols = trades_df["Ticker"].unique().tolist()
        elif 'Symbol' in trades_df.columns:
            symbols = trades_df["Symbol"].unique().tolist()
        else:
            logger.warning("Could not find 'Ticker' or 'Symbol' column in trade recommendations")
            symbols = []
        
        # Get market data for the symbols
        logger.info(f"Getting market data for {len(symbols)} symbols...")
        market_data = trade_assistant.get_market_data_for_symbols(symbols)
        
        # Get option chains for the symbols
        logger.info(f"Getting option chains for {len(symbols)} symbols...")
        option_chains = trade_assistant.get_option_chains_for_symbols(symbols)
    
    # Analyze trades with LLM
    logger.info("Analyzing trades with LLM...")
    llm_analysis = trade_assistant.analyze_trades_with_llm(
        trades_df, 
        account_info, 
        market_data=market_data, 
        option_chains=option_chains
    )
    
    if not llm_analysis:
        logger.error("Failed to get LLM analysis. Exiting.")
        return 1
    
    # Extract trade recommendations from LLM response
    trades_to_execute = trade_assistant.extract_trades_from_llm_response(llm_analysis)
    if not trades_to_execute:
        logger.error("Failed to extract trades from LLM response. Exiting.")
        return 1
    
    # Print the trade recommendations
    logger.info("LLM Trade Recommendations:")
    pretty_print_json(trades_to_execute)
    
    # Execute trades (or dry run)
    dry_run = not args.execute
    logger.info(f"{'DRY RUN - ' if dry_run else ''}Executing trades...")
    execution_results = trade_assistant.execute_trades(trades_to_execute, dry_run)
    
    # Print results
    logger.info("Execution Results:")
    pretty_print_json(execution_results)
    
    # Save results
    trade_assistant.save_results(trades_to_execute, execution_results, args.output_dir)
    
    if dry_run:
        logger.info("This was a dry run. Use --execute to actually place trades.")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
