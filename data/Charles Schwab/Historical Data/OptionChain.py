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

# Load environment variables
load_dotenv()

# Configuration
CONFIG = {
    'symbol': 'SPY',
    #'save_dir': r"C:\Users\cinco\Desktop\DATA FOR SCRIPTS\Charles",
    'save_dir': r"C:\Users\cinco\Desktop\Cinco-HF\results\Charles\Historical Options Data",

    'app_key': os.getenv('APP_KEY'),
    'app_secret': os.getenv('APP_SECRET'),
    'contract_type': 'ALL',
    'strike_count': 10,
    'strategy': 'SINGLE',
    'include_quotes': True,
    'from_date': None,
    'to_date': None,
    'volatility': None,
    'interest_rate': None,
    'days_to_expiration': None,
    'underlying_price': None,
    'exp_month': 'ALL',
    'option_type': None
}

def setup_directory(dir_path):
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

def get_option_chain(symbol):
    base_url = f'https://api.schwabapi.com/marketdata/v1/chains'
    
    # Get the token using your existing token management
    access_token = get_auth_token()
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Accept': 'application/json',
        'Schwab-Client-CorrelId': str(uuid.uuid4()),
        'Schwab-Resource-Version': '1'
    }
    
    params = {
        'symbol': symbol,
        'contractType': CONFIG['contract_type'],
        'strikeCount': CONFIG['strike_count'],
        'includeQuotes': CONFIG['include_quotes'],
        'strategy': CONFIG['strategy']
    }
    
    # Add optional parameters if they exist
    if CONFIG['from_date']: params['fromDate'] = CONFIG['from_date']
    if CONFIG['to_date']: params['toDate'] = CONFIG['to_date']
    if CONFIG['volatility']: params['volatility'] = CONFIG['volatility']
    if CONFIG['interest_rate']: params['interestRate'] = CONFIG['interest_rate']
    if CONFIG['days_to_expiration']: params['daysToExpiration'] = CONFIG['days_to_expiration']
    if CONFIG['underlying_price']: params['underlyingPrice'] = CONFIG['underlying_price']
    if CONFIG['exp_month'] != 'ALL': params['expMonth'] = CONFIG['exp_month']
    if CONFIG['option_type']: params['optionType'] = CONFIG['option_type']
    
    try:
        response = requests.get(
            base_url,
            headers=headers,
            params=params
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error: {response.status_code}")
            print(f"Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"Exception occurred: {str(e)}")
        return None
def process_option_data(raw_data):
    if not raw_data:
        return None
    
    # Create lists to store call and put data
    calls = []
    puts = []
    
    # Process call options
    call_map = raw_data.get('callExpDateMap', {})
    for exp_date, strikes in call_map.items():
        for strike, contracts in strikes.items():
            for contract in contracts:
                contract['optionType'] = 'CALL'
                contract['expirationDate'] = exp_date
                contract['strike'] = strike
                calls.append(contract)
    
    # Process put options
    put_map = raw_data.get('putExpDateMap', {})
    for exp_date, strikes in put_map.items():
        for strike, contracts in strikes.items():
            for contract in contracts:
                contract['optionType'] = 'PUT'
                contract['expirationDate'] = exp_date
                contract['strike'] = strike
                puts.append(contract)
    
    # Convert to DataFrames
    calls_df = pd.DataFrame(calls) if calls else pd.DataFrame()
    puts_df = pd.DataFrame(puts) if puts else pd.DataFrame()
    
    return {'calls': calls_df, 'puts': puts_df}

def save_option_data(data_dict, symbol, save_dir):
    if not data_dict:
        return
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Save calls
    if not data_dict['calls'].empty:
        calls_filename = os.path.join(save_dir, f"{symbol}_calls_{timestamp}.csv")
        data_dict['calls'].to_csv(calls_filename, index=False)
        print(f"Calls data saved to {calls_filename}")
    
    # Save puts
    if not data_dict['puts'].empty:
        puts_filename = os.path.join(save_dir, f"{symbol}_puts_{timestamp}.csv")
        data_dict['puts'].to_csv(puts_filename, index=False)
        print(f"Puts data saved to {puts_filename}")

def print_option_statistics(data_dict):
    if not data_dict:
        return
    
    print("\nOption Chain Statistics:")
    
    # List of columns we want to analyze if they exist
    price_columns = ['strikePrice', 'bidPrice', 'askPrice', 'lastPrice', 'totalVolume', 'openInterest']
    
    # Calls statistics
    if not data_dict['calls'].empty:
        print("\nCalls:")
        print(f"Total number of call contracts: {len(data_dict['calls'])}")
        print("\nAvailable columns:", list(data_dict['calls'].columns))
        
        # Get intersection of desired columns and available columns
        available_columns = [col for col in price_columns if col in data_dict['calls'].columns]
        if available_columns:
            print("\nCall price statistics:")
            print(data_dict['calls'][available_columns].describe())
    
    # Puts statistics
    if not data_dict['puts'].empty:
        print("\nPuts:")
        print(f"Total number of put contracts: {len(data_dict['puts'])}")
        print("\nAvailable columns:", list(data_dict['puts'].columns))
        
        # Get intersection of desired columns and available columns
        available_columns = [col for col in price_columns if col in data_dict['puts'].columns]
        if available_columns:
            print("\nPut price statistics:")
            print(data_dict['puts'][available_columns].describe())
def main():
    print("Starting main execution...")
    setup_directory(CONFIG['save_dir'])
    
    print("Fetching option chain data...")
    raw_data = get_option_chain(CONFIG['symbol'])
    
    print("Processing data...")
    processed_data = process_option_data(raw_data)
    
    if processed_data:
        print("Saving data files...")
        save_option_data(processed_data, CONFIG['symbol'], CONFIG['save_dir'])
        print_option_statistics(processed_data)
        return processed_data
    else:
        print("Failed to retrieve and process option data")
        return None

if __name__ == "__main__":
    print("Script started")
    data = main()
    print("Script completed")