import requests
import base64
import uuid
from datetime import datetime, timedelta
import pandas as pd
import os
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

CONFIG = {
    'symbol': 'EUR/USD',
    'start_date': '2023-01-23',
    'end_date': '2024-01-23',
    'save_dir': './forex_data',
    'app_key': os.getenv('APP_KEY'),
    'app_secret': os.getenv('APP_SECRET'),
    'interval': 60  # seconds between data points
}

def get_auth_token():
    auth_url = f'https://api.schwabapi.com/v1/oauth/authorize'
    params = {
        'response_type': 'code',
        'client_id': CONFIG['app_key'],
        'redirect_uri': 'https://127.0.0.1',
        'scope': 'trade:forex marketdata:forex'
    }
    
    print(f"Visit this URL to authorize: {auth_url}?{'&'.join(f'{k}={v}' for k,v in params.items())}")
    full_url = input("Enter the complete redirect URL: ")
    
    code_start = full_url.find('code=') + 5
    code_end = full_url.find('%', code_start)
    auth_code = full_url[code_start:code_end] + '@'
    
    token_url = 'https://api.schwabapi.com/v1/oauth/token'
    auth_string = base64.b64encode(f"{CONFIG['app_key']}:{CONFIG['app_secret']}".encode()).decode()
    
    headers = {
        'Authorization': f'Basic {auth_string}',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    data = {
        'grant_type': 'authorization_code',
        'code': auth_code,
        'redirect_uri': 'https://127.0.0.1'
    }
    
    response = requests.post(token_url, headers=headers, data=data)
    return response.json().get('access_token')

def get_forex_data(symbol, access_token):
    base_url = 'https://api.schwabapi.com/marketdata/v1/quotes'
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Accept': 'application/json',
        'Schwab-Client-CorrelId': str(uuid.uuid4()),
        'Schwab-Resource-Version': '1'
    }
    
    params = {
        'symbols': symbol,
        'fields': 'quote'
    }
    
    try:
        response = requests.get(base_url, headers=headers, params=params)
        if response.status_code == 200:
            data = response.json()
            quote_data = data.get(symbol, {}).get('quote', {})
            if quote_data:
                current_time = datetime.now()
                quote_data['datetime'] = current_time
                return quote_data
        else:
            print(f"Error: {response.status_code}")
            print(f"Response: {response.text}")
        return None
            
    except Exception as e:
        print(f"Exception occurred: {str(e)}")
        return None

def collect_data(symbol, access_token, duration_minutes=60):
    print(f"Collecting data for {duration_minutes} minutes...")
    data_points = []
    start_time = datetime.now()
    end_time = start_time + timedelta(minutes=duration_minutes)
    
    while datetime.now() < end_time:
        data = get_forex_data(symbol, access_token)
        if data:
            data_points.append(data)
            print(f"Collected data point at {datetime.now()}: Bid={data.get('bidPrice')}, Ask={data.get('askPrice')}")
        time.sleep(CONFIG['interval'])
    
    return pd.DataFrame(data_points)

def save_data(df, symbol):
    if df is None or df.empty:
        print("No data to save")
        return
    
    if not os.path.exists(CONFIG['save_dir']):
        os.makedirs(CONFIG['save_dir'])
        
    filename = os.path.join(
        CONFIG['save_dir'], 
        f"{symbol.replace('/', '_')}_data_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
    )
    
    # Select and rename relevant columns
    columns = {
        'datetime': 'datetime',
        'bidPrice': 'bid',
        'askPrice': 'ask',
        'lastPrice': 'last',
        'highPrice': 'high',
        'lowPrice': 'low',
        'openPrice': 'open',
        'closePrice': 'close',
        'totalVolume': 'volume'
    }
    
    df = df.rename(columns=columns)
    df = df[[col for col in columns.values() if col in df.columns]]
    
    df.to_csv(filename, index=False)
    print(f"\nData saved to {filename}")
    print("\nData preview:")
    print(df.head())
    print("\nData shape:", df.shape)

def main():
    # Get authentication token
    access_token = get_auth_token()
    if not access_token:
        print("Failed to obtain access token")
        return
    
    # Collect real-time data
    data = collect_data(CONFIG['symbol'], access_token, duration_minutes=60)
    
    if data is not None and not data.empty:
        save_data(data, CONFIG['symbol'])
    else:
        print("Failed to collect forex data")

if __name__ == "__main__":
    main()