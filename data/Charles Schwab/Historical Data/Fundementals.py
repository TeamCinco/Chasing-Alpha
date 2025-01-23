import requests
import base64
import uuid
import json
import os
import pandas as pd
from datetime import datetime
import threading
import time
import os
from dotenv import load_dotenv
class Config:
    def __init__(self):
        self.app_key = os.getenv('APP_KEY'),
        self.app_secret = os.getenv('APP_SECRET'),
        self.save_dir = r"C:\Users\cinco\Desktop\DATA FOR SCRIPTS\Charles"
        self.token_manager = TokenManager()

    def initialize_token_refresh(self):
        # Start the token refresh thread
        refresh_thread = threading.Thread(
            target=self.token_refresh_thread,
            daemon=True
        )
        refresh_thread.start()

    def token_refresh_thread(self):
        while True:
            current_time = int(time.time())
            if (self.token_manager.access_token_expiry and 
                current_time >= self.token_manager.access_token_expiry):
                self.token_manager.refresh_access_token(self.app_key, self.app_secret)
            time.sleep(60)

    def get_auth_token(self):
        if self.token_manager.tokens_valid():
            return self.token_manager.access_token
        
        auth_url = f'https://api.schwabapi.com/v1/oauth/authorize?client_id={self.app_key}&redirect_uri=https://127.0.0.1'
        print(f"Click to authenticate: {auth_url}")
        returned_link = input("Paste the redirect URL here:")
        code = f"{returned_link[returned_link.index('code=')+5:returned_link.index('%40')]}@"
        
        app_credentials = f"{self.app_key}:{self.app_secret}"
        authorization = base64.b64encode(bytes(app_credentials, "utf-8")).decode("utf-8")
        
        headers = {
            'Authorization': f'Basic {authorization}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        data = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': 'https://127.0.0.1'
        }
        
        response = requests.post('https://api.schwabapi.com/v1/oauth/token', headers=headers, data=data)
        td = response.json()
        self.token_manager.update_tokens(td['access_token'], td['refresh_token'])
        return td['access_token']
        



class TokenManager:
    def __init__(self, token_file='tokens.json'):
        self.token_file = token_file
        self.access_token = None
        self.refresh_token = None
        self.access_token_expiry = None
        self.refresh_token_expiry = None
        self.load_tokens()

    def load_tokens(self):
        if os.path.exists(self.token_file):
            with open(self.token_file, 'r') as f:
                data = json.load(f)
                self.access_token = data.get('access_token')
                self.refresh_token = data.get('refresh_token')
                self.access_token_expiry = data.get('access_token_expiry')
                self.refresh_token_expiry = data.get('refresh_token_expiry')

    def save_tokens(self):
        data = {
            'access_token': self.access_token,
            'refresh_token': self.refresh_token,
            'access_token_expiry': self.access_token_expiry,
            'refresh_token_expiry': self.refresh_token_expiry
        }
        with open(self.token_file, 'w') as f:
            json.dump(data, f)

    def update_tokens(self, access_token, refresh_token):
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.access_token_expiry = int(time.time()) + 1740  # 29 minutes
        self.refresh_token_expiry = int(time.time()) + (7 * 24 * 60 * 60)  # 7 days
        self.save_tokens()

    def refresh_access_token(self, app_key, app_secret):
        if not self.refresh_token:
            return False

        headers = {
            'Authorization': f'Basic {base64.b64encode(bytes(f"{app_key}:{app_secret}", "utf-8")).decode("utf-8")}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        data = {
            'grant_type': 'refresh_token',
            'refresh_token': self.refresh_token
        }

        response = requests.post('https://api.schwabapi.com/v1/oauth/token', headers=headers, data=data)
        if response.status_code == 200:
            token_data = response.json()
            self.update_tokens(token_data['access_token'], token_data['refresh_token'])
            return True
        return False

    def tokens_valid(self):
        current_time = int(time.time())
        return (
            self.access_token and 
            self.refresh_token and 
            self.access_token_expiry > current_time and 
            self.refresh_token_expiry > current_time
        )



class FundamentalDataFetcher:
    def __init__(self, config):
        self.config = config
        self.base_url = 'https://api.schwabapi.com/marketdata/v1/quotes'
        
    def get_headers(self):
        return {
            'Authorization': f'Bearer {self.config.token_manager.access_token}',
            'Accept': 'application/json',
            'Schwab-Client-CorrelId': str(uuid.uuid4()),
            'Schwab-Resource-Version': '1'
        }
    
    def fetch_fundamentals(self, symbols):
        params = {
            'symbols': ','.join(symbols),
            'fields': 'fundamental'
        }
        
        try:
            response = requests.get(
                self.base_url,
                headers=self.get_headers(),
                params=params
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Error {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            print(f"Error fetching data: {str(e)}")
            return None

class DataProcessor:
    @staticmethod
    def process_fundamental_data(raw_data):
        if not raw_data:
            return pd.DataFrame()
        
        # Extract fundamental data for each symbol
        processed_data = []
        for symbol, data in raw_data.items():
            if 'fundamental' in data:
                fundamental_data = data['fundamental']
                fundamental_data['symbol'] = symbol
                processed_data.append(fundamental_data)
        
        return pd.DataFrame(processed_data)

class DataSaver:
    @staticmethod
    def save_fundamentals(df, save_dir):
        if df.empty:
            print("No data to save")
            return
            
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = os.path.join(save_dir, f'fundamentals_{timestamp}.csv')
        
        df.to_csv(filename, index=False)
        print(f"Data saved to {filename}")
def main():
    # Initialize configuration
    config = Config()
    config.initialize_token_refresh()
    
    # Ensure save directory exists
    os.makedirs(config.save_dir, exist_ok=True)
    
    # Get authentication token
    config.get_auth_token()
    
    # Initialize components
    fetcher = FundamentalDataFetcher(config)
    processor = DataProcessor()
    saver = DataSaver()
    
    # Sample symbols (can be modified as needed)
    #symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN']
    symbols = ['SPY']

    # Fetch data
    print("Fetching fundamental data...")
    raw_data = fetcher.fetch_fundamentals(symbols)
    
    # Process data
    print("Processing data...")
    processed_data = processor.process_fundamental_data(raw_data)
    
    # Save data
    print("Saving data...")
    saver.save_fundamentals(processed_data, config.save_dir)
    
    return processed_data

if __name__ == "__main__":
    print("Starting fundamental data collection...")
    data = main()
    print("Script completed!")
    
    # Display sample of the data
    if not data.empty:
        print("\nSample of collected data:")
        print(data.head())