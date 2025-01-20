import requests
import base64
import uuid
import time
from datetime import datetime, timedelta
import pandas as pd
import os
import json
import threading
import os
from dotenv import load_dotenv
# Configuration
CONFIG = {
    'symbol': 'SPY',  # Required: Any valid stock symbol (e.g., 'AAPL', 'MSFT', 'SPY')
    'save_dir': r"C:\Users\cinco\Desktop\DATA FOR SCRIPTS\Charles",
    'app_key': os.getenv('APP_KEY'),
    'app_secret': os.getenv('APP_SECRET'),
    
    # Option Chain specific parameters
    'contract_type': 'ALL',     # Options: 'CALL', 'PUT', 'ALL'
    'strike_count': 10,         # Number of strikes above and below at-the-money
    'strategy': 'SINGLE',       # Options: 'SINGLE', 'ANALYTICAL', 'COVERED', 'VERTICAL', 'CALENDAR', 
                               # 'STRANGLE', 'STRADDLE', 'BUTTERFLY', 'CONDOR', 'DIAGONAL', 'COLLAR', 'ROLL'
    'include_quotes': True,     # Whether to include underlying quotes
    
    # Date range for options (format: YYYY-MM-DD)
    'from_date': None,          # Optional: Filter by expiration date
    'to_date': None,           # Optional: Filter by expiration date
    
    # Additional parameters for ANALYTICAL strategy
    'volatility': None,        # Optional: Used for theoretical calculations
    'interest_rate': None,     # Optional: Used for theoretical calculations
    'days_to_expiration': None,# Optional: Used for theoretical calculations
    'underlying_price': None,  # Optional: Used for theoretical calculations
    
    # Optional filters
    'exp_month': 'ALL',        # Options: 'JAN' through 'DEC', or 'ALL'
    'option_type': None        # Optional: Additional option type filter
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
def get_option_chain(symbol, access_token):
    base_url = 'https://api.schwabapi.com/marketdata/v1/chains'
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Accept': 'application/json',
        'Schwab-Client-CorrelId': str(uuid.uuid4()),
        'Schwab-Resource-Version': '1'
    }
    
    # Build parameters from config
    params = {
        'symbol': symbol,
        'contractType': CONFIG['contract_type'],
        'strikeCount': CONFIG['strike_count'],
        'includeUnderlyingQuote': CONFIG['include_quotes'],
        'strategy': CONFIG['strategy']
    }
    
    # Add optional parameters if they exist
    if CONFIG['from_date']:
        params['fromDate'] = CONFIG['from_date']
    if CONFIG['to_date']:
        params['toDate'] = CONFIG['to_date']
    if CONFIG['volatility']:
        params['volatility'] = CONFIG['volatility']
    if CONFIG['interest_rate']:
        params['interestRate'] = CONFIG['interest_rate']
    if CONFIG['days_to_expiration']:
        params['daysToExpiration'] = CONFIG['days_to_expiration']
    if CONFIG['underlying_price']:
        params['underlyingPrice'] = CONFIG['underlying_price']
    if CONFIG['exp_month'] != 'ALL':
        params['expMonth'] = CONFIG['exp_month']
    if CONFIG['option_type']:
        params['optionType'] = CONFIG['option_type']
    
    try:
        response = requests.get(base_url, headers=headers, params=params)
        
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
    
    # Create list to store flattened data
    flattened_data = []
    
    # Get base data that will be the same for all rows
    base_data = {
        'symbol': raw_data.get('symbol'),
        'status': raw_data.get('status'),
        'strategy': raw_data.get('strategy'),
        'interval': raw_data.get('interval'),
        'isDelayed': raw_data.get('isDelayed'),
        'isIndex': raw_data.get('isIndex'),
        'daysToExpiration': raw_data.get('daysToExpiration'),
        'interestRate': raw_data.get('interestRate'),
        'underlyingPrice': raw_data.get('underlyingPrice'),
        'volatility': raw_data.get('volatility')
    }
    
    def process_contract(contract, exp_date, strike, option_type):
        row_data = base_data.copy()
        row_data.update({
            'optionType': option_type,
            'expirationDate': exp_date,
            'strikePrice': strike,
            'symbol': contract.get('symbol'),
            'description': contract.get('description'),
            'exchangeName': contract.get('exchangeName'),
            'bidPrice': contract.get('bid'),
            'askPrice': contract.get('ask'),
            'lastPrice': contract.get('last'),
            'mark': contract.get('mark'),
            'bidSize': contract.get('bidSize'),
            'askSize': contract.get('askSize'),
            'lastSize': contract.get('lastSize'),
            'highPrice': contract.get('highPrice'),
            'lowPrice': contract.get('lowPrice'),
            'openPrice': contract.get('openPrice'),
            'closePrice': contract.get('closePrice'),
            'totalVolume': contract.get('totalVolume'),
            'tradeDate': contract.get('tradeDate'),
            'quoteTimeInLong': contract.get('quoteTimeInLong'),
            'tradeTimeInLong': contract.get('tradeTimeInLong'),
            'netChange': contract.get('netChange'),
            'volatility': contract.get('volatility'),
            'delta': contract.get('delta'),
            'gamma': contract.get('gamma'),
            'theta': contract.get('theta'),
            'vega': contract.get('vega'),
            'rho': contract.get('rho'),
            'timeValue': contract.get('timeValue'),
            'openInterest': contract.get('openInterest'),
            'isInTheMoney': contract.get('inTheMoney'),
            'theoreticalOptionValue': contract.get('theoreticalOptionValue'),
            'theoreticalVolatility': contract.get('theoreticalVolatility'),
            'isMini': contract.get('isMini'),
            'isNonStandard': contract.get('isNonStandard'),
            'optionDeliverablesList': str(contract.get('optionDeliverablesList')),  # Convert list to string for CSV
            'daysToExpiration': contract.get('daysToExpiration'),
            'expirationType': contract.get('expirationType'),
            'lastTradingDay': contract.get('lastTradingDay'),
            'multiplier': contract.get('multiplier'),
            'settlementType': contract.get('settlementType'),
            'deliverableNote': contract.get('deliverableNote'),
            'isIndexOption': contract.get('isIndexOption'),
            'percentChange': contract.get('percentChange'),
            'markChange': contract.get('markChange'),
            'markPercentChange': contract.get('markPercentChange'),
            'isPennyPilot': contract.get('isPennyPilot'),
            'intrinsicValue': contract.get('intrinsicValue'),
            'optionRoot': contract.get('optionRoot')
        })
        return row_data
    
    # Process call options
    call_map = raw_data.get('callExpDateMap', {})
    for exp_date, strikes in call_map.items():
        for strike, contracts in strikes.items():
            for contract in contracts:
                flattened_data.append(process_contract(contract, exp_date, strike, 'CALL'))
    
    # Process put options
    put_map = raw_data.get('putExpDateMap', {})
    for exp_date, strikes in put_map.items():
        for strike, contracts in strikes.items():
            for contract in contracts:
                flattened_data.append(process_contract(contract, exp_date, strike, 'PUT'))
    
    return pd.DataFrame(flattened_data)

def print_option_statistics(data_df):
    if data_df is None or data_df.empty:
        return
    
    print("\nOption Chain Statistics:")
    print(f"Total number of contracts: {len(data_df)}")
    print(f"Calls: {len(data_df[data_df['optionType'] == 'CALL'])}")
    print(f"Puts: {len(data_df[data_df['optionType'] == 'PUT'])}")
    
    # Display all available columns
    print("\nAvailable columns:")
    print(data_df.columns.tolist())
    
    # Price and volume statistics
    basic_stats = ['strikePrice', 'bidPrice', 'askPrice', 'lastPrice', 'totalVolume', 'openInterest']
    print("\nBasic Statistics:")
    print(data_df[basic_stats].describe())
    
    # Greeks statistics
    greeks = ['delta', 'gamma', 'theta', 'vega', 'rho']
    print("\nGreeks Statistics:")
    print(data_df[greeks].describe())

def save_option_data(data_df, symbol, save_dir):
    if data_df is None or data_df.empty:
        return
    
    # Create filename based on CONFIG parameters
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    params = [
        symbol,
        f"type_{CONFIG['contract_type']}",
        f"strikes_{CONFIG['strike_count']}",
        f"strat_{CONFIG['strategy']}"
    ]
    
    # Add optional parameters if they exist
    if CONFIG['from_date']:
        params.append(f"from_{CONFIG['from_date']}")
    if CONFIG['to_date']:
        params.append(f"to_{CONFIG['to_date']}")
    if CONFIG['exp_month'] != 'ALL':
        params.append(f"month_{CONFIG['exp_month']}")
    
    filename = os.path.join(save_dir, f"{'_'.join(params)}_{timestamp}.csv")
    data_df.to_csv(filename, index=False)
    print(f"Option chain data saved to {filename}")

def main():
    print("Starting main execution...")
    # Setup
    setup_directory(CONFIG['save_dir'])
    access_token = get_auth_token()
    
    print("Fetching option chain data...")
    # Get option chain data
    raw_data = get_option_chain(CONFIG['symbol'], access_token)
    
    print("Processing data...")
    # Process data
    processed_data = process_option_data(raw_data)
    
    if processed_data is not None and not processed_data.empty:  # Fixed condition
        print("Saving data files...")
        # Save data
        save_option_data(processed_data, CONFIG['symbol'], CONFIG['save_dir'])
        
        # Print statistics
        print_option_statistics(processed_data)
        
        return processed_data
    else:
        print("Failed to retrieve and process option data")
        return None

if __name__ == "__main__":
    print("Script started")
    data = main()
    print("Script completed")