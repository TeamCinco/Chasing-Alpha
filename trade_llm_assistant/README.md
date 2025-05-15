# LLM-Powered Trade Assistant

This module integrates a Large Language Model (LLM) with your Schwab trading system to analyze account information and Excel-based trade recommendations for optimal options trade sizing and execution.

## Features

- Analyzes Excel-based trade recommendations with an advanced LLM
- Determines optimal position sizing based on account balance and risk parameters
- Suggests appropriate strike prices based on current market prices and wing width preferences
- Builds option orders for various strategies (spreads, iron condors, etc.)
- Supports dry-run mode for risk-free testing
- Caches market data and option chains to reduce API calls
- Saves analysis and execution results for record-keeping

## Installation

1. Ensure you have the required dependencies:

```bash
pip install pandas numpy requests python-dotenv openpyxl
```

2. Add your API credentials to your .env file:

```
# Schwab API credentials
SCHWAB_APP_KEY=your_app_key
SCHWAB_APP_SECRET=your_app_secret
SCHWAB_CALLBACK_URL=your_callback_url
SCHWAB_ACCOUNT_NUMBER=your_account_number
SCHWAB_ACCOUNT_HASH=your_account_hash

# LLM API credentials (Claude from Anthropic)
LLM_API_KEY=your_anthropic_api_key
LLM_API_ENDPOINT=https://api.anthropic.com/v1/messages
LLM_MODEL=claude-3-opus-20240229
```

## Usage

The trade assistant is designed to be used as a command-line tool:

```bash
# Dry run (doesn't place orders, just analyzes and simulates)
python -m trade_llm_assistant.trade_assistant --excel path/to/trade_recommendations.xlsx

# To execute the trades after analysis
python -m trade_llm_assistant.trade_assistant --excel path/to/trade_recommendations.xlsx --execute

# Specify account by hash or number
python -m trade_llm_assistant.trade_assistant --excel path/to/trade_recommendations.xlsx --account_hash YOUR_ACCOUNT_HASH
python -m trade_llm_assistant.trade_assistant --excel path/to/trade_recommendations.xlsx --account_number YOUR_ACCOUNT_NUMBER
```

### Command Line Arguments

- `--excel`: Path to Excel file with trade recommendations (required)
- `--account_hash`: Account hash to use for trading
- `--account_number`: Account number to use (will look up hash)
- `--dry_run`: Don't execute trades, just simulate (default behavior)
- `--execute`: Actually execute the trades (overrides --dry_run)
- `--output_dir`: Directory to save analysis and execution results
- `--skip_market_data`: Skip fetching market data (useful for testing)

## Excel Format for Trade Recommendations

The trade assistant expects an Excel file with trade recommendations. The file should include columns for:

- **Ticker/Symbol**: Stock or ETF symbol
- **Strategy**: Options strategy (e.g., "Put Credit Spread", "Iron Condor")
- **Direction**: Market outlook (Bullish, Bearish, Neutral)
- **Confidence**: Conviction level (High, Medium, Low)
- **Wing Width**: Distance between strikes (Narrow, Medium, Wide)
- **Expiration**: Target expiration date or days to expiration
- **Notes**: Additional information or rationale

Example Excel format:

| Ticker | Strategy | Direction | Confidence | Wing Width | Expiration | Notes |
|--------|----------|-----------|------------|------------|------------|-------|
| AAPL | Put Credit Spread | Bullish | High | Medium | 30 days | Support at $175 |
| SPY | Iron Condor | Neutral | Medium | Wide | 45 days | Low IV environment |
| QQQ | Call Debit Spread | Bullish | Medium | Narrow | June 21 | Earnings catalyst |

## Risk Management Parameters

The trade assistant uses the following default risk management parameters:

- Maximum risk per trade: 5% of account value
- Maximum total portfolio risk: 20% of account value
- Position size adjustments based on confidence:
  - High confidence: 100% of calculated size
  - Medium confidence: 70% of calculated size
  - Low confidence: 50% of calculated size

You can modify these parameters in the `TradeAssistant` class if needed.

## Output Files

The trade assistant saves two JSON files in the specified output directory (or in a 'results' subfolder by default):

1. **LLM Analysis**: Contains the full analysis and trade recommendations from the LLM
2. **Execution Results**: Contains the results of trade execution or simulation

These files use timestamps in their names for easy reference and record-keeping.

## Supported Option Strategies

The trade assistant supports the following option strategies:

- Put Credit Spread
- Call Credit Spread
- Put Debit Spread
- Call Debit Spread
- Iron Condor
- Calendar Spread
- Diagonal Spread
- Long Call
- Long Put
- Short Call
- Short Put

## Custom Strategy Guidelines

The LLM is guided to use the following wing width guidelines:

- Narrow (0.5-0.75 standard deviation): Typically 8-12% of the stock price
- Medium (1 standard deviation): Typically 16% of the stock price
- Wide (1.5-2 standard deviations): Typically 24-32% of the stock price

## Example Output

```json
{
  "trades": [
    {
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
    },
    {
      "symbol": "SPY",
      "strategy": "Iron Condor",
      "quantity": 1,
      "strikes": [410, 400, 450, 460],
      "expiration": "2025-06-15",
      "order_type": "LIMIT",
      "limit_price": 2.5,
      "duration": "DAY",
      "max_loss": "$750",
      "reason": "Medium confidence neutral outlook with wide wings"
    }
  ],
  "total_risk": "$1,250",
  "account_value": "$50,000",
  "risk_percentage": "2.5%",
  "analysis": "Conservative allocation with diversified strategies aligns with current market conditions."
}
