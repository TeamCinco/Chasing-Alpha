import requests
import base64
import uuid
import time
from datetime import datetime, timedelta
import pandas as pd
import os
import json
import threading
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Verify the variables are loaded
print("Environment variables after loading:")
print(f"APP_KEY: {os.getenv('APP_KEY')}")
print(f"APP_SECRET exists: {'Yes' if os.getenv('APP_SECRET') else 'No'}")

# Rest of your code...
# Configuration
CONFIG = {
    'symbol': 'SPY',  # Required: Any valid stock symbol (e.g., 'AAPL', 'MSFT', 'SPY')
    
    # Date range for data retrieval (format: YYYY-MM-DD)
    'start_date': '2000-01-01',
    'end_date': '2025-01-23',
    
    # Directory for saving data
    #'save_dir': r"C:\Users\cinco\Desktop\DATA FOR SCRIPTS\Charles",
    'save_dir': "/Users/jazzhashzzz/Desktop/data for scripts/charles/Historical Equities Data",
    
    # API credentials
    'app_key': os.getenv('APP_KEY'),
    'app_secret': os.getenv('APP_SECRET'),

    
    # Period type for the data request
    # Available options: 'day', 'month', 'year', 'ytd'
    'period_type': 'day',
    
    # Number of periods to return
    # If period_type is:
    #   'day'   - valid values: 1, 2, 3, 4, 5, 10
    #   'month' - valid values: 1, 2, 3, 6
    #   'year'  - valid values: 1, 2, 3, 5, 10, 15, 20
    #   'ytd'   - valid values: 1
    'period': 5,
    
    # Frequency type of returned data
    # If period_type is:
    #   'day'   - valid value: 'minute'
    #   'month' - valid values: 'daily', 'weekly'
    #   'year'  - valid values: 'daily', 'weekly', 'monthly'
    #   'ytd'   - valid values: 'daily', 'weekly'
    'frequency_type': 'minute',
    
    # Frequency of returned data
    # If frequency_type is:
    #   'minute'  - valid values: 1, 5, 10, 15, 30
    #   'daily'   - valid value: 1
    #   'weekly'  - valid value: 1
    #   'monthly' - valid value: 1
    'frequency': 30,
    
    # Whether to include extended hours data
    'extended_hours': True,
    
    # Whether to include previous close price/date
    'need_previous_close': True
}

def setup_directory(dir_path):#1
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
        


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

def token_refresh_thread(token_manager, app_key, app_secret):
    while True:
        current_time = int(time.time())
        if token_manager.access_token_expiry and current_time >= token_manager.access_token_expiry:
            token_manager.refresh_access_token(app_key, app_secret)
        time.sleep(60)  # Check every minute

# Modify the CONFIG to include token management
CONFIG.update({
    'token_manager': TokenManager()
})

# Start the token refresh thread
refresh_thread = threading.Thread(
    target=token_refresh_thread, 
    args=(CONFIG['token_manager'], CONFIG['app_key'], CONFIG['app_secret']),
    daemon=True
)
refresh_thread.start()

def get_auth_token():
    if CONFIG['token_manager'].tokens_valid():
        return CONFIG['token_manager'].access_token
    
    # Original authentication code here
    auth_url = f'https://api.schwabapi.com/v1/oauth/authorize?client_id={CONFIG["app_key"]}&redirect_uri=https://127.0.0.1'
    print(f"Click to authenticate: {auth_url}")
    returned_link = input("Paste the redirect URL here:")
    code = f"{returned_link[returned_link.index('code=')+5:returned_link.index('%40')]}@"
    
    # Fix the nested quotes in the f-string
    app_credentials = f"{CONFIG['app_key']}:{CONFIG['app_secret']}"
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
    CONFIG['token_manager'].update_tokens(td['access_token'], td['refresh_token'])
    return td['access_token']

def get_price_history(symbol, start_date_str, end_date_str, access_token):
    base_url = 'https://api.schwabapi.com/marketdata/v1/pricehistory'
    
    try:
        start_date = int(datetime.strptime(start_date_str, '%Y-%m-%d').timestamp() * 1000)
        end_date = int(datetime.strptime(end_date_str, '%Y-%m-%d').timestamp() * 1000)
    except ValueError:
        print("Error: Dates must be in YYYY-MM-DD format")
        return None
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Accept': 'application/json',
        'Schwab-Client-CorrelId': str(uuid.uuid4()),
        'Schwab-Resource-Version': '1'
    }
    
    params = {
        'symbol': symbol,
        'startDate': start_date,
        'endDate': end_date,
        'periodType': CONFIG['period_type'],
        'period': CONFIG['period'],
        'frequencyType': CONFIG['frequency_type'],
        'frequency': CONFIG['frequency'],
        'needExtendedHoursData': CONFIG['extended_hours']
    }
    
    try:
        response = requests.get(base_url, headers=headers, params=params)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('empty', True):
                print("No data available for the specified parameters")
                return None
            return data
        else:
            print(f"Error: {response.status_code}")
            print(f"Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"Exception occurred: {str(e)}")
        return None

def process_data(raw_data):
    if not raw_data or raw_data.get('empty', True):
        return None
        
    df = pd.DataFrame(raw_data['candles'])
    df['datetime'] = pd.to_datetime(df['datetime'], unit='ms')
    columns_order = ['datetime', 'open', 'high', 'low', 'close', 'volume']
    return df[columns_order]

def save_data(df, config, save_dir):
    if df is None:
        return
        
    # Create filename components based on config
    period_suffix = f"{config['period']}{config['period_type']}"
    freq_suffix = f"{config['frequency']}{config['frequency_type']}"
    extended_hours = "_ext" if config['extended_hours'] else ""
    
    filename = os.path.join(
        save_dir, 
        f"{config['symbol']}_{period_suffix}_{freq_suffix}{extended_hours}_{config['start_date']}_to_{config['end_date']}.csv"
    )
    
    df.to_csv(filename, index=False)
    print(f"Data saved to {filename}")

def print_statistics(df):
    if df is None:
        return
        
    print("\nDataset Statistics:")
    print(f"Total number of records: {len(df)}")
    print("\nData range:")
    print(f"Start date: {df['datetime'].min()}")
    print(f"End date: {df['datetime'].max()}")
    print("\nBasic statistics:")
    print(df.describe())
    
    missing_values = df.isnull().sum()
    if missing_values.sum() > 0:
        print("\nMissing values:")
        print(missing_values)
    else:
        print("\nNo missing values found in the dataset")

def main():
    # Setup
    setup_directory(CONFIG['save_dir'])
    access_token = get_auth_token()
    
    # Get data
    raw_data = get_price_history(
        CONFIG['symbol'], 
        CONFIG['start_date'], 
        CONFIG['end_date'], 
        access_token
    )
    
    # Process data
    df = process_data(raw_data)
    
    if df is not None:
        # Save data using config
        save_data(df, CONFIG, CONFIG['save_dir'])
        
        # Print statistics
        print_statistics(df)
        
        return df
    else:
        print("Failed to retrieve and process data")
        return None

if __name__ == "__main__":
    df = main()