"""
Option Order Builder Module

This module provides functions for building option orders based on
different trading strategies (credit spreads, debit spreads, iron condors, etc.)
"""

import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class OptionOrderBuilder:
    """Builder for option order payloads based on different strategies"""
    
    def __init__(self, api_client):
        """Initialize the option order builder
        
        Args:
            api_client: API client for the broker
        """
        self.api_client = api_client
    
    def build_option_order(self, 
                          strategy,
                          symbol,
                          quantity,
                          strikes,
                          expiration,
                          order_type="LIMIT",
                          price=None,
                          duration="DAY"):
        """Build an option order payload based on the strategy
        
        Args:
            strategy (str): Option strategy (e.g., "Put Credit Spread", "Iron Condor")
            symbol (str): Ticker symbol
            quantity (int): Number of contracts
            strikes (list): List of strike prices for the strategy
            expiration (str): Option expiration date (YYYY-MM-DD)
            order_type (str, optional): Order type (LIMIT, MARKET, etc.)
            price (float, optional): Limit price (required for LIMIT orders)
            duration (str, optional): Order duration (DAY, GTC, etc.)
            
        Returns:
            dict: Option order payload formatted for the broker API
        """
        # Map strategy names to builder methods
        strategy_builders = {
            "Put Credit Spread": self._build_put_credit_spread,
            "Call Credit Spread": self._build_call_credit_spread,
            "Put Debit Spread": self._build_put_debit_spread,
            "Call Debit Spread": self._build_call_debit_spread,
            "Iron Condor": self._build_iron_condor,
            "Calendar Spread": self._build_calendar_spread,
            "Diagonal Spread": self._build_diagonal_spread,
            "Long Call": self._build_long_call,
            "Long Put": self._build_long_put,
            "Short Call": self._build_short_call,
            "Short Put": self._build_short_put
        }
        
        # Validate strategy
        if strategy not in strategy_builders:
            raise ValueError(f"Unsupported strategy: {strategy}. Supported strategies: {', '.join(strategy_builders.keys())}")
        
        # Get the appropriate builder method
        builder = strategy_builders[strategy]
        
        # Build the order
        return builder(
            symbol=symbol,
            quantity=quantity,
            strikes=strikes,
            expiration=expiration,
            order_type=order_type,
            price=price,
            duration=duration
        )
    
    def _build_put_credit_spread(self, symbol, quantity, strikes, expiration, order_type, price, duration):
        """Build a Put Credit Spread order
        
        Args:
            symbol (str): Ticker symbol
            quantity (int): Number of contracts
            strikes (list): [sell_strike, buy_strike] (sell higher strike, buy lower strike)
            expiration (str): Option expiration date (YYYY-MM-DD)
            order_type (str): Order type (LIMIT, MARKET, etc.)
            price (float): Limit price
            duration (str): Order duration (DAY, GTC, etc.)
            
        Returns:
            dict: Option order payload
        """
        if len(strikes) != 2:
            raise ValueError("Put Credit Spread requires exactly 2 strikes: [sell_strike, buy_strike]")
        
        sell_strike, buy_strike = strikes
        
        # Validate strikes
        if sell_strike <= buy_strike:
            raise ValueError(f"For Put Credit Spread, sell strike ({sell_strike}) must be higher than buy strike ({buy_strike})")
        
        return {
            "orderType": order_type,
            "session": "NORMAL",
            "duration": duration,
            "orderStrategyType": "SINGLE",
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
    
    def _build_call_credit_spread(self, symbol, quantity, strikes, expiration, order_type, price, duration):
        """Build a Call Credit Spread order
        
        Args:
            symbol (str): Ticker symbol
            quantity (int): Number of contracts
            strikes (list): [buy_strike, sell_strike] (buy lower strike, sell higher strike)
            expiration (str): Option expiration date (YYYY-MM-DD)
            order_type (str): Order type (LIMIT, MARKET, etc.)
            price (float): Limit price
            duration (str): Order duration (DAY, GTC, etc.)
            
        Returns:
            dict: Option order payload
        """
        if len(strikes) != 2:
            raise ValueError("Call Credit Spread requires exactly 2 strikes: [buy_strike, sell_strike]")
        
        buy_strike, sell_strike = strikes
        
        # Validate strikes
        if buy_strike >= sell_strike:
            raise ValueError(f"For Call Credit Spread, buy strike ({buy_strike}) must be lower than sell strike ({sell_strike})")
        
        return {
            "orderType": order_type,
            "session": "NORMAL",
            "duration": duration,
            "orderStrategyType": "SINGLE",
            "price": str(price) if price else None,
            "orderLegCollection": [
                {
                    "instrument": {
                        "symbol": f"{symbol}_{expiration}C{sell_strike}",
                        "assetType": "OPTION"
                    },
                    "instruction": "SELL_TO_OPEN",
                    "quantity": quantity
                },
                {
                    "instrument": {
                        "symbol": f"{symbol}_{expiration}C{buy_strike}",
                        "assetType": "OPTION"
                    },
                    "instruction": "BUY_TO_OPEN",
                    "quantity": quantity
                }
            ]
        }
    
    def _build_put_debit_spread(self, symbol, quantity, strikes, expiration, order_type, price, duration):
        """Build a Put Debit Spread order
        
        Args:
            symbol (str): Ticker symbol
            quantity (int): Number of contracts
            strikes (list): [buy_strike, sell_strike] (buy higher strike, sell lower strike)
            expiration (str): Option expiration date (YYYY-MM-DD)
            order_type (str): Order type (LIMIT, MARKET, etc.)
            price (float): Limit price
            duration (str): Order duration (DAY, GTC, etc.)
            
        Returns:
            dict: Option order payload
        """
        if len(strikes) != 2:
            raise ValueError("Put Debit Spread requires exactly 2 strikes: [buy_strike, sell_strike]")
        
        buy_strike, sell_strike = strikes
        
        # Validate strikes
        if buy_strike <= sell_strike:
            raise ValueError(f"For Put Debit Spread, buy strike ({buy_strike}) must be higher than sell strike ({sell_strike})")
        
        return {
            "orderType": order_type,
            "session": "NORMAL",
            "duration": duration,
            "orderStrategyType": "SINGLE",
            "price": str(price) if price else None,
            "orderLegCollection": [
                {
                    "instrument": {
                        "symbol": f"{symbol}_{expiration}P{buy_strike}",
                        "assetType": "OPTION"
                    },
                    "instruction": "BUY_TO_OPEN",
                    "quantity": quantity
                },
                {
                    "instrument": {
                        "symbol": f"{symbol}_{expiration}P{sell_strike}",
                        "assetType": "OPTION"
                    },
                    "instruction": "SELL_TO_OPEN",
                    "quantity": quantity
                }
            ]
        }
    
    def _build_call_debit_spread(self, symbol, quantity, strikes, expiration, order_type, price, duration):
        """Build a Call Debit Spread order
        
        Args:
            symbol (str): Ticker symbol
            quantity (int): Number of contracts
            strikes (list): [buy_strike, sell_strike] (buy lower strike, sell higher strike)
            expiration (str): Option expiration date (YYYY-MM-DD)
            order_type (str): Order type (LIMIT, MARKET, etc.)
            price (float): Limit price
            duration (str): Order duration (DAY, GTC, etc.)
            
        Returns:
            dict: Option order payload
        """
        if len(strikes) != 2:
            raise ValueError("Call Debit Spread requires exactly 2 strikes: [buy_strike, sell_strike]")
        
        buy_strike, sell_strike = strikes
        
        # Validate strikes
        if buy_strike >= sell_strike:
            raise ValueError(f"For Call Debit Spread, buy strike ({buy_strike}) must be lower than sell strike ({sell_strike})")
        
        return {
            "orderType": order_type,
            "session": "NORMAL",
            "duration": duration,
            "orderStrategyType": "SINGLE",
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
    
    def _build_iron_condor(self, symbol, quantity, strikes, expiration, order_type, price, duration):
        """Build an Iron Condor order
        
        Args:
            symbol (str): Ticker symbol
            quantity (int): Number of contracts
            strikes (list): [put_sell_strike, put_buy_strike, call_buy_strike, call_sell_strike]
            expiration (str): Option expiration date (YYYY-MM-DD)
            order_type (str): Order type (LIMIT, MARKET, etc.)
            price (float): Limit price
            duration (str): Order duration (DAY, GTC, etc.)
            
        Returns:
            dict: Option order payload
        """
        if len(strikes) != 4:
            raise ValueError("Iron Condor requires exactly 4 strikes: [put_sell_strike, put_buy_strike, call_buy_strike, call_sell_strike]")
        
        put_sell_strike, put_buy_strike, call_buy_strike, call_sell_strike = strikes
        
        # Validate strikes
        if not (put_buy_strike < put_sell_strike < call_buy_strike < call_sell_strike):
            raise ValueError(f"For Iron Condor, strikes must be in order: put_buy_strike({put_buy_strike}) < "
                             f"put_sell_strike({put_sell_strike}) < call_buy_strike({call_buy_strike}) < "
                             f"call_sell_strike({call_sell_strike})")
        
        return {
            "orderType": order_type,
            "session": "NORMAL",
            "duration": duration,
            "orderStrategyType": "SINGLE", 
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
    
    def _build_calendar_spread(self, symbol, quantity, strikes, expirations, order_type, price, duration):
        """Build a Calendar Spread order
        
        Args:
            symbol (str): Ticker symbol
            quantity (int): Number of contracts
            strikes (list): [strike] (same strike for both legs)
            expirations (list): [near_exp, far_exp] (near-term and far-term expirations)
            order_type (str): Order type (LIMIT, MARKET, etc.)
            price (float): Limit price
            duration (str): Order duration (DAY, GTC, etc.)
            
        Returns:
            dict: Option order payload
        """
        if len(strikes) != 1:
            raise ValueError("Calendar Spread requires exactly 1 strike price")
        
        if not isinstance(expirations, list) or len(expirations) != 2:
            raise ValueError("Calendar Spread requires exactly 2 expirations: [near_exp, far_exp]")
        
        strike = strikes[0]
        near_exp, far_exp = expirations
        
        # For simplicity, we'll assume a call calendar spread
        # A put calendar spread would be similar but with 'P' instead of 'C'
        return {
            "orderType": order_type,
            "session": "NORMAL",
            "duration": duration,
            "orderStrategyType": "SINGLE",
            "price": str(price) if price else None,
            "orderLegCollection": [
                # Sell near-term
                {
                    "instrument": {
                        "symbol": f"{symbol}_{near_exp}C{strike}",
                        "assetType": "OPTION"
                    },
                    "instruction": "SELL_TO_OPEN",
                    "quantity": quantity
                },
                # Buy far-term
                {
                    "instrument": {
                        "symbol": f"{symbol}_{far_exp}C{strike}",
                        "assetType": "OPTION"
                    },
                    "instruction": "BUY_TO_OPEN",
                    "quantity": quantity
                }
            ]
        }
    
    def _build_diagonal_spread(self, symbol, quantity, strikes, expirations, order_type, price, duration):
        """Build a Diagonal Spread order
        
        Args:
            symbol (str): Ticker symbol
            quantity (int): Number of contracts
            strikes (list): [near_strike, far_strike] (strikes for near and far-term options)
            expirations (list): [near_exp, far_exp] (near-term and far-term expirations)
            order_type (str): Order type (LIMIT, MARKET, etc.)
            price (float): Limit price
            duration (str): Order duration (DAY, GTC, etc.)
            
        Returns:
            dict: Option order payload
        """
        if len(strikes) != 2:
            raise ValueError("Diagonal Spread requires exactly 2 strikes: [near_strike, far_strike]")
        
        if not isinstance(expirations, list) or len(expirations) != 2:
            raise ValueError("Diagonal Spread requires exactly 2 expirations: [near_exp, far_exp]")
        
        near_strike, far_strike = strikes
        near_exp, far_exp = expirations
        
        # For simplicity, we'll assume a call diagonal spread
        # A put diagonal spread would be similar but with 'P' instead of 'C'
        return {
            "orderType": order_type,
            "session": "NORMAL",
            "duration": duration,
            "orderStrategyType": "SINGLE",
            "price": str(price) if price else None,
            "orderLegCollection": [
                # Sell near-term
                {
                    "instrument": {
                        "symbol": f"{symbol}_{near_exp}C{near_strike}",
                        "assetType": "OPTION"
                    },
                    "instruction": "SELL_TO_OPEN",
                    "quantity": quantity
                },
                # Buy far-term
                {
                    "instrument": {
                        "symbol": f"{symbol}_{far_exp}C{far_strike}",
                        "assetType": "OPTION"
                    },
                    "instruction": "BUY_TO_OPEN",
                    "quantity": quantity
                }
            ]
        }
    
    def _build_long_call(self, symbol, quantity, strikes, expiration, order_type, price, duration):
        """Build a Long Call order
        
        Args:
            symbol (str): Ticker symbol
            quantity (int): Number of contracts
            strikes (list): [strike]
            expiration (str): Option expiration date (YYYY-MM-DD)
            order_type (str): Order type (LIMIT, MARKET, etc.)
            price (float): Limit price
            duration (str): Order duration (DAY, GTC, etc.)
            
        Returns:
            dict: Option order payload
        """
        if len(strikes) != 1:
            raise ValueError("Long Call requires exactly 1 strike")
        
        strike = strikes[0]
        
        return {
            "orderType": order_type,
            "session": "NORMAL",
            "duration": duration,
            "orderStrategyType": "SINGLE",
            "price": str(price) if price else None,
            "orderLegCollection": [
                {
                    "instrument": {
                        "symbol": f"{symbol}_{expiration}C{strike}",
                        "assetType": "OPTION"
                    },
                    "instruction": "BUY_TO_OPEN",
                    "quantity": quantity
                }
            ]
        }
    
    def _build_long_put(self, symbol, quantity, strikes, expiration, order_type, price, duration):
        """Build a Long Put order
        
        Args:
            symbol (str): Ticker symbol
            quantity (int): Number of contracts
            strikes (list): [strike]
            expiration (str): Option expiration date (YYYY-MM-DD)
            order_type (str): Order type (LIMIT, MARKET, etc.)
            price (float): Limit price
            duration (str): Order duration (DAY, GTC, etc.)
            
        Returns:
            dict: Option order payload
        """
        if len(strikes) != 1:
            raise ValueError("Long Put requires exactly 1 strike")
        
        strike = strikes[0]
        
        return {
            "orderType": order_type,
            "session": "NORMAL",
            "duration": duration,
            "orderStrategyType": "SINGLE",
            "price": str(price) if price else None,
            "orderLegCollection": [
                {
                    "instrument": {
                        "symbol": f"{symbol}_{expiration}P{strike}",
                        "assetType": "OPTION"
                    },
                    "instruction": "BUY_TO_OPEN",
                    "quantity": quantity
                }
            ]
        }
    
    def _build_short_call(self, symbol, quantity, strikes, expiration, order_type, price, duration):
        """Build a Short Call order
        
        Args:
            symbol (str): Ticker symbol
            quantity (int): Number of contracts
            strikes (list): [strike]
            expiration (str): Option expiration date (YYYY-MM-DD)
            order_type (str): Order type (LIMIT, MARKET, etc.)
            price (float): Limit price
            duration (str): Order duration (DAY, GTC, etc.)
            
        Returns:
            dict: Option order payload
        """
        if len(strikes) != 1:
            raise ValueError("Short Call requires exactly 1 strike")
        
        strike = strikes[0]
        
        return {
            "orderType": order_type,
            "session": "NORMAL",
            "duration": duration,
            "orderStrategyType": "SINGLE",
            "price": str(price) if price else None,
            "orderLegCollection": [
                {
                    "instrument": {
                        "symbol": f"{symbol}_{expiration}C{strike}",
                        "assetType": "OPTION"
                    },
                    "instruction": "SELL_TO_OPEN",
                    "quantity": quantity
                }
            ]
        }
    
    def _build_short_put(self, symbol, quantity, strikes, expiration, order_type, price, duration):
        """Build a Short Put order
        
        Args:
            symbol (str): Ticker symbol
            quantity (int): Number of contracts
            strikes (list): [strike]
            expiration (str): Option expiration date (YYYY-MM-DD)
            order_type (str): Order type (LIMIT, MARKET, etc.)
            price (float): Limit price
            duration (str): Order duration (DAY, GTC, etc.)
            
        Returns:
            dict: Option order payload
        """
        if len(strikes) != 1:
            raise ValueError("Short Put requires exactly 1 strike")
        
        strike = strikes[0]
        
        return {
            "orderType": order_type,
            "session": "NORMAL",
            "duration": duration,
            "orderStrategyType": "SINGLE",
            "price": str(price) if price else None,
            "orderLegCollection": [
                {
                    "instrument": {
                        "symbol": f"{symbol}_{expiration}P{strike}",
                        "assetType": "OPTION"
                    },
                    "instruction": "SELL_TO_OPEN",
                    "quantity": quantity
                }
            ]
        }
