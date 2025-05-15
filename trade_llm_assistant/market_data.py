"""
Market Data Module for Trade Assistant

This module provides functions for retrieving market data and option chains
to support the LLM-powered trade assistant.
"""

import logging
import random
import pandas as pd
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

def get_market_data(api_client, symbols):
    """
    Get current market prices for a list of symbols
    
    Args:
        api_client: API client object for the broker
        symbols (list): List of ticker symbols
        
    Returns:
        dict: Market data for each symbol with price information
    """
    market_data = {}
    
    for symbol in symbols:
        try:
            # Try to get actual market data from the broker API
            # If available, use api_client.get_quote() or similar method
            try:
                quote = api_client.get_quotes([symbol])
                if quote and isinstance(quote, dict) and symbol in quote:
                    market_data[symbol] = {
                        "last_price": quote[symbol].get("lastPrice"),
                        "bid": quote[symbol].get("bidPrice"),
                        "ask": quote[symbol].get("askPrice"),
                        "volume": quote[symbol].get("totalVolume"),
                        "timestamp": datetime.now().isoformat()
                    }
                    logger.info(f"Retrieved market data for {symbol}")
                    continue
            except Exception as api_err:
                logger.warning(f"Could not get market data for {symbol} from API: {api_err}")
            
            # Fallback: Generate mock data for testing
            # This is a placeholder - in production, you'd want to handle API errors differently
            mock_price = random.uniform(100, 500)
            market_data[symbol] = {
                "last_price": mock_price,
                "bid": mock_price - 0.50,
                "ask": mock_price + 0.50,
                "volume": random.randint(10000, 1000000),
                "timestamp": datetime.now().isoformat(),
                "mock_data": True  # Flag to indicate this is not real market data
            }
            logger.warning(f"Using mock market data for {symbol}")
            
        except Exception as e:
            logger.error(f"Error getting market data for {symbol}: {e}")
    
    return market_data

def get_option_chains(api_client, symbols, expiration_date=None):
    """
    Get option chain data for a list of symbols
    
    Args:
        api_client: API client object for the broker
        symbols (list): List of ticker symbols
        expiration_date (str, optional): Target expiration date (YYYY-MM-DD)
        
    Returns:
        dict: Option chain data for each symbol
    """
    option_chains = {}
    
    for symbol in symbols:
        try:
            # Try to get actual option chain data from the broker API
            try:
                # If the API method is available, use it
                option_chain = api_client.get_option_chain(symbol, expiration_date=expiration_date)
                if option_chain:
                    option_chains[symbol] = option_chain
                    logger.info(f"Retrieved option chain for {symbol}")
                    continue
            except Exception as api_err:
                logger.warning(f"Could not get option chain for {symbol} from API: {api_err}")
            
            # Fallback: Generate mock option chain data for testing
            # This is only for development/testing purposes
            mock_stock_price = random.uniform(100, 500)
            
            # Generate some dummy expiration dates (current month + 1,2,3 months out)
            today = datetime.now()
            expirations = []
            for i in range(1, 4):
                exp_date = (today.replace(day=21) + timedelta(days=30*i))
                expirations.append(exp_date.strftime("%Y-%m-%d"))
            
            # Generate strikes around the mock price
            strikes = [
                round(mock_stock_price * 0.7, 1),
                round(mock_stock_price * 0.8, 1),
                round(mock_stock_price * 0.9, 1),
                round(mock_stock_price, 1),
                round(mock_stock_price * 1.1, 1),
                round(mock_stock_price * 1.2, 1),
                round(mock_stock_price * 1.3, 1)
            ]
            
            # Create a mock option chain
            option_chains[symbol] = {
                "stock_price": mock_stock_price,
                "symbol": symbol,
                "expiration_dates": expirations,
                "strikes": strikes,
                "mock_data": True  # Flag to indicate this is not real option chain data
            }
            logger.warning(f"Using mock option chain data for {symbol}")
        
        except Exception as e:
            logger.error(f"Error getting option chain for {symbol}: {e}")
    
    return option_chains

def get_historical_volatility(api_client, symbols, lookback_days=30):
    """
    Calculate historical volatility for a list of symbols
    
    Args:
        api_client: API client object for the broker
        symbols (list): List of ticker symbols
        lookback_days (int): Number of days to look back for volatility calculation
        
    Returns:
        dict: Historical volatility data for each symbol
    """
    volatility_data = {}
    
    for symbol in symbols:
        try:
            # Try to get historical price data from the broker API
            try:
                # If the API method is available, use it
                end_date = datetime.now()
                start_date = end_date - timedelta(days=lookback_days + 10)  # Add buffer
                
                history = api_client.get_price_history(
                    symbol,
                    start_date=start_date.strftime("%Y-%m-%d"),
                    end_date=end_date.strftime("%Y-%m-%d"),
                    frequency_type="daily"
                )
                
                if history:
                    # Convert to pandas DataFrame and calculate volatility
                    # This assumes the API returns a list of candles with 'close' prices
                    df = pd.DataFrame(history['candles'])
                    df['log_return'] = np.log(df['close'] / df['close'].shift(1))
                    
                    # Annual volatility (assuming 252 trading days in a year)
                    annual_vol = df['log_return'].std() * np.sqrt(252)
                    
                    volatility_data[symbol] = {
                        "annual_volatility": annual_vol,
                        "daily_volatility": annual_vol / np.sqrt(252),
                        "period_volatility": df['log_return'].std() * np.sqrt(lookback_days),
                        "lookback_days": lookback_days
                    }
                    
                    logger.info(f"Calculated historical volatility for {symbol}")
                    continue
            except Exception as api_err:
                logger.warning(f"Could not calculate volatility for {symbol} from API: {api_err}")
            
            # Fallback: Generate mock volatility data
            volatility_data[symbol] = {
                "annual_volatility": random.uniform(0.15, 0.45),  # 15-45% annual vol
                "daily_volatility": random.uniform(0.01, 0.03),
                "lookback_days": lookback_days,
                "mock_data": True  # Flag to indicate this is not real volatility data
            }
            logger.warning(f"Using mock volatility data for {symbol}")
            
        except Exception as e:
            logger.error(f"Error calculating volatility for {symbol}: {e}")
    
    return volatility_data
