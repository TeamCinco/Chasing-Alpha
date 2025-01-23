import os
import json
import base64
import requests
import threading
import time
import websocket
import uuid
import ssl
import csv
from datetime import datetime
from dotenv import load_dotenv
import urllib.parse

# Load environment variables
load_dotenv()

class SchwabForexStreamer:
    def __init__(self, app_key, app_secret, forex_symbols):
        self.app_key = app_key
        self.app_secret = app_secret
        self.forex_symbols = forex_symbols
        self.access_token = self.get_access_token()
        self.output_dir = r"C:\Users\cinco\Desktop\DATA FOR SCRIPTS\Charles\Live Data"
        
        # Create output directory if it doesn't exist
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
        
        # Initialize CSV files for each symbol
        self.initialize_csv_files()

    def initialize_csv_files(self):
        headers = ['Timestamp', 'Symbol', 'Bid', 'Ask', 'Last']
        for symbol in self.forex_symbols:
            safe_symbol = symbol.replace('/', '_')
            filepath = os.path.join(self.output_dir, f'{safe_symbol}_data.csv')
            if not os.path.exists(filepath):
                with open(filepath, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(headers)

    def save_to_csv(self, symbol, bid, ask, last):
        safe_symbol = symbol.replace('/', '_')
        filepath = os.path.join(self.output_dir, f'{safe_symbol}_data.csv')
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
        
        with open(filepath, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([timestamp, symbol, bid, ask, last])

    # [Previous get_access_token method remains the same]
    def get_access_token(self):
        auth_url = f'https://api.schwabapi.com/v1/oauth/authorize?client_id={self.app_key}&redirect_uri=https://127.0.0.1'
        print(f"Click to authenticate: {auth_url}")
        returned_link = input("Paste the redirect URL here: ")
        code = urllib.parse.unquote(returned_link.split('code=')[1].split('&')[0])
        
        app_credentials = f"{self.app_key}:{self.app_secret}"
        authorization = base64.b64encode(app_credentials.encode()).decode()
        
        headers = {
            'Authorization': f'Basic {authorization}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        data = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': 'https://127.0.0.1'
        }
        
        try:
            response = requests.post('https://api.schwabapi.com/v1/oauth/token', headers=headers, data=data)
            response.raise_for_status()
            return response.json()['access_token']
        except requests.exceptions.HTTPError as err:
            print(f"HTTP error occurred: {err}")
            print(f"Response content: {response.content}")
            raise
        except Exception as err:
            print(f"An error occurred: {err}")
            raise

    def stream_forex_quotes(self, interval=1):
        url = "https://api.schwabapi.com/marketdata/v1/quotes"
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json"
        }
        
        params = {
            "symbols": ",".join(self.forex_symbols),
            "fields": "quote",
            "indicative": "false"
        }
        
        while True:
            try:
                response = requests.get(url, headers=headers, params=params)
                response.raise_for_status()
                data = response.json()
                
                for symbol, info in data.items():
                    quote = info.get('quote', {})
                    bid = quote.get('bidPrice', 'N/A')
                    ask = quote.get('askPrice', 'N/A')
                    last = quote.get('lastPrice', 'N/A')
                    
                    # Save data to CSV
                    self.save_to_csv(symbol, bid, ask, last)
                    
                    # Print to console
                    print(f"{symbol}: Bid: {bid}, Ask: {ask}, Last: {last}, "
                          f"Time: {quote.get('quoteTime', 'N/A')}")
                
                print("---")
                time.sleep(interval)
            
            except requests.exceptions.RequestException as e:
                print(f"An error occurred: {e}")
                time.sleep(5)  # Wait for 5 seconds before retrying
            
            except KeyboardInterrupt:
                print("Streaming stopped by user.")
                break

def main():
    # Configuration
    CONFIG = {
        'app_key': os.getenv('APP_KEY'),
        'app_secret': os.getenv('APP_SECRET'),
        'forex_symbols': ['EUR/USD', 'USD/JPY', 'GBP/USD', 'USD/CHF', 'AUD/USD']
    }

    # Initialize and use Forex Streamer
    streamer = SchwabForexStreamer(
        CONFIG['app_key'], 
        CONFIG['app_secret'], 
        CONFIG['forex_symbols']
    )
    
    streamer.stream_forex_quotes()

if __name__ == "__main__":
    main()