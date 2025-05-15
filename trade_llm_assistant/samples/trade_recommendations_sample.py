"""
Sample Trade Recommendations Generator

This script generates a sample Excel file with trade recommendations
to demonstrate the expected format for the LLM-powered trade assistant.
"""

import os
import pandas as pd
from datetime import datetime, timedelta

# Create the samples directory if it doesn't exist
samples_dir = os.path.dirname(os.path.abspath(__file__))
os.makedirs(samples_dir, exist_ok=True)

# Calculate some future expiration dates
today = datetime.now()
exp_30_days = (today + timedelta(days=30)).strftime("%Y-%m-%d")
exp_45_days = (today + timedelta(days=45)).strftime("%Y-%m-%d")
exp_60_days = (today + timedelta(days=60)).strftime("%Y-%m-%d")
exp_90_days = (today + timedelta(days=90)).strftime("%Y-%m-%d")

# Create sample trade recommendations
trade_recommendations = [
    {
        "Ticker": "AAPL",
        "Strategy": "Put Credit Spread",
        "Direction": "Bullish",
        "Confidence": "High",
        "Wing Width": "Medium",
        "Expiration": exp_30_days,
        "Notes": "Strong technical support at $175, recent earnings beat, low IV environment"
    },
    {
        "Ticker": "MSFT",
        "Strategy": "Call Debit Spread",
        "Direction": "Bullish",
        "Confidence": "Medium",
        "Wing Width": "Narrow",
        "Expiration": exp_45_days,
        "Notes": "Cloud segment growth, AI initiatives, approaching all-time highs"
    },
    {
        "Ticker": "SPY",
        "Strategy": "Iron Condor",
        "Direction": "Neutral",
        "Confidence": "Medium",
        "Wing Width": "Wide",
        "Expiration": exp_30_days,
        "Notes": "Low VIX environment, trading in a range, no major catalysts expected"
    },
    {
        "Ticker": "QQQ",
        "Strategy": "Call Credit Spread",
        "Direction": "Bearish",
        "Confidence": "Low",
        "Wing Width": "Medium",
        "Expiration": exp_45_days,
        "Notes": "Tech sector showing signs of overvaluation, potential for pullback"
    },
    {
        "Ticker": "AMZN",
        "Strategy": "Put Debit Spread",
        "Direction": "Bearish",
        "Confidence": "Medium",
        "Wing Width": "Medium",
        "Expiration": exp_60_days,
        "Notes": "Recent weakness in e-commerce segment, high inventory levels"
    },
    {
        "Ticker": "NVDA",
        "Strategy": "Calendar Spread",
        "Direction": "Neutral",
        "Confidence": "High",
        "Wing Width": "N/A",
        "Expiration": f"{exp_30_days}/{exp_90_days}",
        "Notes": "High IV in near-term options, earnings expected in 45 days"
    },
    {
        "Ticker": "TSLA",
        "Strategy": "Long Call",
        "Direction": "Bullish",
        "Confidence": "High",
        "Wing Width": "N/A",
        "Expiration": exp_90_days,
        "Notes": "New model announcement expected, technical breakout pattern"
    },
    {
        "Ticker": "GOOG",
        "Strategy": "Short Put",
        "Direction": "Bullish",
        "Confidence": "Medium",
        "Wing Width": "N/A",
        "Expiration": exp_30_days,
        "Notes": "Strong cash position, willing to acquire shares at support level"
    },
    {
        "Ticker": "IWM",
        "Strategy": "Iron Butterfly",
        "Direction": "Neutral",
        "Confidence": "High",
        "Wing Width": "Narrow",
        "Expiration": exp_30_days,
        "Notes": "Small caps consolidating, low expected movement in next month"
    },
    {
        "Ticker": "TLT",
        "Strategy": "Diagonal Spread",
        "Direction": "Bearish",
        "Confidence": "Medium",
        "Wing Width": "Medium",
        "Expiration": f"{exp_30_days}/{exp_90_days}",
        "Notes": "Rising rate environment expected to pressure bond prices"
    }
]

# Create a DataFrame
df = pd.DataFrame(trade_recommendations)

# Save to Excel
output_file = os.path.join(samples_dir, "trade_recommendations_sample.xlsx")
df.to_excel(output_file, index=False)

print(f"Sample trade recommendations saved to: {output_file}")

if __name__ == "__main__":
    # If this script is run directly, it will generate the sample file
    print("Run this script to generate a sample trade recommendations Excel file.")
    print(f"The file will be saved to: {output_file}")
