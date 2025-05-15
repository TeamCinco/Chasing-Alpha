import requests
import base64
import uuid
import time
import random
from datetime import datetime, timedelta
import pandas as pd
import os
import json
import threading
import concurrent.futures
from functools import partial
from dotenv import load_dotenv
# import os # Duplicate
import queue

# Load environment variables from .env file
load_dotenv()

# Verify the variables are loaded
print("Environment variables after loading:")
print(f"APP_KEY: {os.getenv('APP_KEY')}")
print(f"APP_SECRET exists: {'Yes' if os.getenv('APP_SECRET') else 'No'}")

# Define stock tickers to analyze
stock_tickers = [
    # Original mega-cap tech
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'AMD', 'INTC',
    'IBM', 'CSCO', 'ORCL', 'QCOM', 'TXN', 'AVGO', 'ADBE', 'CRM', 'INTU', 'NOW',
    'SHOP', 'SNOW', 'DDOG', 'PANW', 'ZS', 'CRWD', 'PLTR', 'DOCU',
    'ASML', 'ADSK', 'ANET', 'MRVL', 'MU', 'TEAM', 'TWLO', 'SMCI',
    'MDB', 'NET', 'OKTA', 'FSLY', 'RBLX', 'ESTC', 'SPLK', 'APPN', 'ZS',
    'BILL', 'HUBS', 'S', 'U', 'AKAM', 'GLBE', 'WDAY', 'DT', 'CYBR', 'SAMSUNG',
    
    # Additional semiconductors
    'TSM', 'NXPI', 'KLAC', 'LRCX', 'AMAT', 'ON', 'GFS', 'WOLF', 'MPWR', 'ADI', 
    'STX', 'WDC', 'ENPH', 'SEDG', 'CREE', 'SWKS', 'SYNA', 'ENTG', 'OLED', 'POWI',
    
    # Additional software/cloud
    'ZM', 'COUP', 'PD', 'PING', 'VCRA', 'ZI', 'PATH', 'AI', 'ONDS', 'SMAR',
    'DOCN', 'GTLB', 'CFLT', 'HIMS', 'FROG', 'NCNO', 'MNDY', 'DAVA', 'DBX', 'ASAN',
    'SUMO', 'LYFT', 'UBER', 'ABNB', 'DASH', 'PTC', 'QLYS', 'TENB', 'RPD', 'MIME',
    
    # Hardware & equipment
    'HPQ', 'HPE', 'DELL', 'STX', 'WDC', 'NTAP', 'PSTG', 'NOK', 'ERIC', 'JNPR',
    'GLW', 'VIAV', 'CIEN', 'INFN', 'COHR', 'LITE', 'IIVI', 'MTSI', 'LOGI', 'HEAR',
    
    # Gaming & entertainment
    'EA', 'ATVI', 'TTWO', 'NTES', 'SONY', 'NTDOY', 'OTGLY', 'SE', 'NFLX', 'DIS',
    'ROKU', 'SPOT', 'SIRI', 'TME', 'WBD', 'PARA', 'CMCSA', 'LYV', 'PINS', 'SNAP',
    
    # Fintech
    'SQ', 'PYPL', 'COIN', 'HOOD', 'UPST', 'SOFI', 'AFRM', 'MELI', 'GPN', 'FIS',
    'FISV', 'MA', 'V', 'AXP', 'INMD', 'RKT', 'LC', 'GDOT', 'WU', 'EEFT',
    
    # International tech
    'BABA', 'JD', 'BIDU', 'PDD', 'TCEHY', '9988.HK', '9618.HK', '3690.HK', 'SAP',
    '005930.KS', 'TTE', 'SHOP.TO', 'BB', 'CGEMY', 'DASTY', 'SIEGY', 'FJTSY', 'HMC',
    
    # Electric vehicles & clean tech
    'TSLA', 'NIO', 'RIVN', 'LCID', 'XPEV', 'FSR', 'F', 'GM', 'CHPT', 'BLNK',
    'PLUG', 'FCEL', 'BE', 'NEE', 'STEM', 'RUN', 'SPWR', 'NOVA', 'TAN', 'FAN',
    
    # Healthcare tech
    'TDOC', 'DOCS', 'AMWL', 'ONEM', 'VEEV', 'CERT', 'CERN', 'DXCM', 'HOLX', 'ISRG',
    'IRTC', 'NVTA', 'PHR', 'PACB', 'DNA', 'CRISPR', 'ILMN', 'EXAS', 'GH', 'GDRX',
    
    # Robotics & automation
    'ROK', 'ABB', 'HON', 'IR', 'EMR', 'AME', 'FTV', 'NDSN', 'GRMN', 'IRBT',
    'ZBRA', 'CGNX', 'ISRG', 'NVTS', 'TER', 'CCMP', 'KEYS', 'A', 'ITRI', 'FARO',
    
    # Cybersecurity (additional)
    'FTNT', 'CHKP', 'RPD', 'VRNS', 'SAIL', 'SCWX', 'SOND', 'NLOK', 'SIMO', 'ATEN'
]

# Define index and sector tickers to analyze
index_tickers = [
    'GSPC', 'IXIC', 'DJI', 'RUT', 'VIX',
    'SPY', 'QQQ', 'VTI', 'VOO', 'DIA', 'IWM',
    'XLK', 'SMH', 'SOXX', 'ARKK',
    'XSD', 'IGV', 'SKYY', 'FINX', 'HACK',
    'FTEC', 'VGT', 'IYW'
]

# All tickers combined
# FOR 10K TICKERS, YOU WOULD REPLACE `stock_tickers` WITH YOUR LARGE LIST
all_tickers = list(set(stock_tickers + index_tickers)) # Use set to remove duplicates then convert to list
print(f"Total unique tickers to process: {len(all_tickers)}")


# Configuration
CONFIG = {
    'tickers': all_tickers,
    'start_date': '2010-01-01',
    'end_date': '2025-05-15',
    'save_dir': r"C:\Users\cinco\Desktop\Cinco-Quant\00_raw_data\5.15", # Original save dir
    #'save_dir': "/Users/jazzhashzzz/Desktop/Cinco-Quant/00_raw_data/5.14_10k", # New save dir for this run
    'app_key': os.getenv('APP_KEY'),
    'app_secret': os.getenv('APP_SECRET'),
    'max_workers': 25,
    'request_delay': 0.005,  # MODIFIED: Reduced delay before API call
    'retry_attempts': 3,
    'retry_delay': 2,
    'max_pending_tasks': 55, # MODIFIED: Increased pending tasks
    'period_type': 'year',
    'period': 10,
    'frequency_type': 'daily',
    'frequency': 1,
    'extended_hours': False,
    'need_previous_close': True
}

class RateLimiter:
    def __init__(self, max_requests=115, time_window=25): # MODIFIED: max_requests
        self.max_requests = max_requests
        self.time_window = time_window
        self.request_timestamps = []
        self.lock = threading.Lock()
        
    def wait_if_needed(self):
        with self.lock:
            current_time = time.time()
            # Remove timestamps older than the time window
            self.request_timestamps = [t for t in self.request_timestamps 
                                      if current_time - t < self.time_window]
            
            if len(self.request_timestamps) >= self.max_requests:
                # Wait until the oldest timestamp is outside the window
                oldest_timestamp = self.request_timestamps[0] # Assumes list is sorted by time
                sleep_time = (oldest_timestamp + self.time_window) - current_time
                if sleep_time > 0:
                    print(f"Rate limit of {self.max_requests}/{self.time_window}s reached. Waiting {sleep_time:.2f} seconds...")
                    time.sleep(sleep_time)
            
            # Add current request timestamp *after* potential sleep
            self.request_timestamps.append(time.time())

def setup_directory(dir_path):
    if not os.path.exists(dir_path):
        print(f"Creating directory: {dir_path}")
        os.makedirs(dir_path)
        
class TokenManager:
    def __init__(self, token_file='tokens.json'):
        self.token_file = token_file
        self.access_token = None
        self.refresh_token = None
        self.access_token_expiry = None
        self.refresh_token_expiry = None
        self.lock = threading.Lock()
        self.load_tokens()

    def load_tokens(self):
        if os.path.exists(self.token_file):
            try:
                with open(self.token_file, 'r') as f:
                    data = json.load(f)
                with self.lock:
                    self.access_token = data.get('access_token')
                    self.refresh_token = data.get('refresh_token')
                    self.access_token_expiry = data.get('access_token_expiry')
                    self.refresh_token_expiry = data.get('refresh_token_expiry')
            except Exception as e:
                print(f"Error loading tokens from {self.token_file}: {e}")

    def save_tokens(self):
        # Assumes lock is held by caller (update_tokens)
        data = {
            'access_token': self.access_token,
            'refresh_token': self.refresh_token,
            'access_token_expiry': self.access_token_expiry,
            'refresh_token_expiry': self.refresh_token_expiry
        }
        try:
            with open(self.token_file, 'w') as f:
                json.dump(data, f)
        except Exception as e:
            print(f"Error saving tokens to {self.token_file}: {e}")

    def update_tokens(self, access_token, refresh_token):
        with self.lock:
            self.access_token = access_token
            self.refresh_token = refresh_token
            self.access_token_expiry = int(time.time()) + 1740  # 29 minutes
            self.refresh_token_expiry = int(time.time()) + (7 * 24 * 60 * 60)  # 7 days
            self.save_tokens()

    def refresh_access_token(self, app_key, app_secret):
        current_refresh_token = None
        with self.lock:
            current_refresh_token = self.refresh_token

        if not current_refresh_token:
            print("Refresh token not available for refreshing access token.")
            return False

        headers = {
            'Authorization': f'Basic {base64.b64encode(bytes(f"{app_key}:{app_secret}", "utf-8")).decode("utf-8")}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        data = {'grant_type': 'refresh_token', 'refresh_token': current_refresh_token}

        try:
            print("Attempting to refresh access token via API...")
            response = requests.post('https://api.schwabapi.com/v1/oauth/token', headers=headers, data=data, timeout=30)
            if response.status_code == 200:
                token_data = response.json()
                self.update_tokens(token_data['access_token'], token_data.get('refresh_token', current_refresh_token))
                print("Access token refreshed successfully.")
                return True
            print(f"Token refresh API call failed: {response.status_code} - {response.text}")
            return False
        except Exception as e:
            print(f"Exception during token refresh API call: {str(e)}")
            return False

    def tokens_valid(self):
        with self.lock:
            current_time = int(time.time())
            access_valid = self.access_token and self.access_token_expiry and self.access_token_expiry > current_time
            refresh_valid = self.refresh_token # Removed expiry check on refresh token for this simple valid check, main check is access token
            return access_valid and refresh_valid # Primarily concerned if access token is valid
    
    def get_access_token(self):
        with self.lock:
            return self.access_token

def token_refresh_thread(token_manager, app_key, app_secret):
    while True:
        try:
            needs_refresh = False
            with token_manager.lock:
                current_time = int(time.time())
                # Refresh if access token is missing, or expired, or expiring within 5 minutes
                if not token_manager.access_token or \
                   (token_manager.access_token_expiry and current_time >= token_manager.access_token_expiry - 300):
                    needs_refresh = True
            
            if needs_refresh:
                print("[REFRESH THREAD] Access token needs refresh. Calling refresh_access_token.")
                if not token_manager.refresh_access_token(app_key, app_secret):
                    print("[REFRESH THREAD] Failed to refresh token. Will retry later.")
            
            time.sleep(25)
        except Exception as e:
            print(f"[REFRESH THREAD] Error: {str(e)}")
            time.sleep(25)

CONFIG.update({
    'token_manager': TokenManager(),
    'rate_limiter': RateLimiter(max_requests=115, time_window=25) # MODIFIED
})

refresh_thread = threading.Thread(
    target=token_refresh_thread, 
    args=(CONFIG['token_manager'], CONFIG['app_key'], CONFIG['app_secret']),
    daemon=True
)
refresh_thread.start()

def get_auth_token_with_retry(max_retries=3):
    for attempt in range(max_retries):
        try:
            if CONFIG['token_manager'].tokens_valid():
                print("Tokens are already valid.")
                return CONFIG['token_manager'].get_access_token()
            
            # Try to use refresh token first if available
            can_try_refresh = False
            with CONFIG['token_manager'].lock: # Check refresh token existence under lock
                if CONFIG['token_manager'].refresh_token:
                    can_try_refresh = True
            
            if can_try_refresh:
                print("Attempting to refresh token via refresh_access_token as part of get_auth_token_with_retry...")
                if CONFIG['token_manager'].refresh_access_token(CONFIG['app_key'], CONFIG['app_secret']):
                    print("Token refreshed successfully within get_auth_token_with_retry.")
                    return CONFIG['token_manager'].get_access_token()
                else:
                    print("Failed to refresh token via refresh_access_token. Proceeding to full OAuth.")

            print("Need to perform full OAuth authentication.")
            auth_url = f'https://api.schwabapi.com/v1/oauth/authorize?client_id={CONFIG["app_key"]}&redirect_uri=https://127.0.0.1'
            print(f"Click to authenticate: {auth_url}")
            returned_link = input("Paste the redirect URL here:")
            
            if '%40' in returned_link:
                code = f"{returned_link[returned_link.index('code=')+5:returned_link.index('%40')]}@"
            else:
                code = returned_link[returned_link.index('code=')+5:]
                
            app_credentials = f"{CONFIG['app_key']}:{CONFIG['app_secret']}"
            authorization = base64.b64encode(bytes(app_credentials, "utf-8")).decode("utf-8")
            headers = {'Authorization': f'Basic {authorization}', 'Content-Type': 'application/x-www-form-urlencoded'}
            data = {'grant_type': 'authorization_code', 'code': code, 'redirect_uri': 'https://127.0.0.1'}
            
            response = requests.post('https://api.schwabapi.com/v1/oauth/token', headers=headers, data=data, timeout=30)
            response.raise_for_status()
            td = response.json()
            CONFIG['token_manager'].update_tokens(td['access_token'], td['refresh_token'])
            print("Full OAuth authentication successful, tokens updated.")
            return td['access_token']
        except Exception as e:
            if attempt < max_retries - 1:
                delay = CONFIG.get('retry_delay', 2) * (2 ** attempt)
                print(f"Auth error: {str(e)}. Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                print(f"Failed to get auth token after {max_retries} attempts: {str(e)}")
                raise
    raise Exception("Failed to get auth token after all retries.")


def get_price_history(symbol, start_date_str, end_date_str, access_token, config_local): # Pass config for params
    base_url = 'https://api.schwabapi.com/marketdata/v1/pricehistory'
    try:
        start_date_dt = datetime.strptime(start_date_str, '%Y-%m-%d')
        end_date_dt = datetime.strptime(end_date_str, '%Y-%m-%d')
        start_date_ms = int(start_date_dt.timestamp() * 1000)
        end_date_ms = int(end_date_dt.timestamp() * 1000)
    except ValueError:
        print(f"[{symbol} GetPriceHistory] Error: Dates must be in YYYY-MM-DD format.")
        return None
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Accept': 'application/json',
        'Schwab-Client-CorrelId': str(uuid.uuid4()),
        'Schwab-Resource-Version': '1.0'
    }
    params = {
        'symbol': symbol,
        'startDate': start_date_ms,
        'endDate': end_date_ms,
        'periodType': config_local['period_type'],
        'period': config_local['period'],
        'frequencyType': config_local['frequency_type'],
        'frequency': config_local['frequency'],
        'needExtendedHoursData': str(config_local['extended_hours']).lower()
    }
    
    try:
        response = requests.get(base_url, headers=headers, params=params, timeout=30) # 30s timeout for request
        if response.status_code == 200:
            data = response.json()
            if data.get('empty', True) or not data.get('candles'):
                print(f"[{symbol} GetPriceHistory] No data available with specified parameters.")
                return None
            return data
        elif response.status_code == 429: # Too Many Requests
            print(f"[{symbol} GetPriceHistory] Error 429: Too Many Requests. {response.text}")
            # This specific error should trigger a longer wait or backoff in the retry logic
            raise requests.exceptions.ConnectionError("Rate limit hit (429)") # Re-raise as a type that might trigger specific retry
        elif response.status_code in [401, 403]: # Unauthorized or Forbidden
            print(f"[{symbol} GetPriceHistory] Auth Error {response.status_code}: {response.text}")
            raise Exception(f"Auth error {response.status_code} for {symbol}")
        else:
            print(f"[{symbol} GetPriceHistory] Error: {response.status_code} - {response.text}")
            return None # Other errors might not be retryable in the same way
    except requests.exceptions.Timeout:
        print(f"[{symbol} GetPriceHistory] Request timeout.")
        raise
    except Exception as e: # Catch other exceptions like JSONDecodeError, ConnectionError
        print(f"[{symbol} GetPriceHistory] Exception: {str(e)}")
        raise


def get_price_history_with_retry(symbol, start_date_str, end_date_str, access_token_initial, config_local):
    max_retries = config_local.get('retry_attempts', 3)
    rate_limiter = config_local.get('rate_limiter')
    current_access_token = access_token_initial

    for attempt in range(max_retries):
        try:
            if not current_access_token: # Ensure we have a token
                print(f"[{symbol} Retry] No access token at attempt {attempt + 1}. Getting fresh token.")
                current_access_token = config_local['token_manager'].get_access_token()
                if not current_access_token:
                    print(f"[{symbol} Retry] Failed to get fresh token. Retrying auth process if applicable or failing.")
                    # Potentially, this could trigger a call to get_auth_token_with_retry if token system fully breaks
                    raise Exception("Access token unavailable after trying to refresh.")

            if rate_limiter: rate_limiter.wait_if_needed() # This is where the RateLimiter is used
            
            result = get_price_history(symbol, start_date_str, end_date_str, current_access_token, config_local)
            if result is not None: return result # Success or valid "no data" response
            
            # If get_price_history returns None for non-exception reasons (e.g. specific error codes it handles)
            # and doesn't raise, we might not want to retry. Here, it means API said no data or unhandled error.
            # Assuming 'None' means non-retryable "no data" or error handled within get_price_history
            print(f"[{symbol} Retry] get_price_history returned None, not an exception. Assuming no data or unretryable issue.")
            return None

        except requests.exceptions.ConnectionError as e: # Catch 429 re-raised as ConnectionError
            print(f"[{symbol} Retry] ConnectionError (likely 429 Rate Limit) on attempt {attempt + 1}: {e}")
            # For 429, use a longer, escalating backoff
            delay = config_local.get('retry_delay', 2) * (3 ** attempt) + random.uniform(1, 5) # Exponential with base 3, plus jitter
            print(f"[{symbol} Retry] Rate limit likely. Waiting {delay:.2f}s before retry {attempt + 2}...")
            time.sleep(delay)
            # Also, attempt to ensure token is fresh after a long delay, as it might have expired.
            current_access_token = config_local['token_manager'].get_access_token()


        except Exception as e: # Catches timeouts, explicit auth errors from get_price_history, etc.
            print(f"[{symbol} Retry] Exception on attempt {attempt + 1}: {str(e)}")
            if "Auth error" in str(e): # Token expired or invalid
                print(f"[{symbol} Retry] Auth error detected. Attempting to get a new token.")
                # Try to get a new token. The token_manager's refresh thread should be working,
                # but we can also explicitly try to refresh or re-auth here if needed.
                # For simplicity, just get whatever the token_manager has, assuming refresh thread fixed it.
                current_access_token = config_local['token_manager'].get_access_token()
                if not config_local['token_manager'].tokens_valid(): # If still not valid
                    print(f"[{symbol} Retry] Token still not valid after get. Trying full re-auth for next attempt.")
                    # This is tricky in a worker; ideally signal main thread or rely on refresh thread.
                    # For now, we'll just retry with potentially same bad token or a refreshed one.
                    # A more robust solution might involve a global re-authentication flag.
                    current_access_token = None # Force re-check at start of next loop iteration

            if attempt < max_retries - 1:
                delay = config_local.get('retry_delay', 2) * (2 ** attempt) + random.uniform(0, 1)
                print(f"[{symbol} Retry] Retrying in {delay:.2f} seconds...")
                time.sleep(delay)
            else:
                print(f"[{symbol} Retry] Failed after {max_retries} attempts: {str(e)}")
                return None # Critical failure after retries
    return None


def process_data(raw_data, symbol):
    if not raw_data or raw_data.get('empty', True) or not raw_data.get('candles'):
        return None
    df = pd.DataFrame(raw_data['candles'])
    df['datetime'] = pd.to_datetime(df['datetime'], unit='ms')
    df['symbol'] = symbol
    columns_order = ['symbol', 'datetime', 'open', 'high', 'low', 'close', 'volume']
    df = df[columns_order]
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    return df

def save_data(df, config, symbol, save_dir):
    if df is None or df.empty:
        # print(f"[{symbol} SaveData] No data to save.") # Reduce noise
        return
    period_suffix = f"{config['period']}{config['period_type']}"
    freq_suffix = f"{config['frequency']}{config['frequency_type']}"
    extended_hours = "_ext" if config['extended_hours'] else ""
    filename = os.path.join(save_dir, f"{symbol}_{period_suffix}_{freq_suffix}{extended_hours}_{config['start_date']}_to_{config['end_date']}.csv")
    try:
        df.to_csv(filename, index=False)
        print(f"[{symbol} WORKER] Data saved to {filename}")
    except Exception as e:
        print(f"[{symbol} WORKER] Error saving data to {filename}: {e}")

def print_statistics(df, symbol):
    if df is None or df.empty: return
    print(f"\n[{symbol} WORKER] Dataset Statistics for {symbol}:")
    print(f"Total records: {len(df)}, Date range: {df['datetime'].min()} to {df['datetime'].max()}")
    # stats = df['close'].describe() # Less verbose for many tickers
    # print(f"Close Price Stats: Min: {stats.get('min', float('nan')):.2f}, Max: {stats.get('max', float('nan')):.2f}, Mean: {stats.get('mean', float('nan')):.2f}")
    # print(f"Total missing values: {df.isnull().sum().sum()}")


def fetch_and_process_ticker(ticker, config, progress_tracker=None):
    # print(f"[{ticker} WORKER] Starting task.") # Reduce noise
    try:
        if progress_tracker and progress_tracker.is_completed(ticker):
            # print(f"[{ticker} WORKER] Skipping {ticker} - already processed.") # Reduce noise
            return None
            
        # MODIFIED: Short random sleep using configured request_delay
        time.sleep(random.uniform(0.01, config.get('request_delay', 0.05))) 
            
        access_token = config['token_manager'].get_access_token()
        if not access_token:
            print(f"[{ticker} WORKER] CRITICAL: No access token from TokenManager for {ticker}. Failing task.")
            # This situation should ideally be rare if token refresh thread is robust
            # and initial auth succeeded.
            return None # Cannot proceed without a token
        
        raw_data = get_price_history_with_retry(
            ticker, 
            config['start_date'], 
            config['end_date'], 
            access_token,
            config # Pass the main CONFIG dict here
        )
        
        df = process_data(raw_data, ticker)
        
        if df is not None and not df.empty:
            save_data(df, config, ticker, config['save_dir'])
            # print_statistics(df, ticker) # Reduce noise for 10k run
            if progress_tracker:
                progress_tracker.mark_completed(ticker)
            return df
        else:
            # print(f"[{ticker} WORKER] No data processed or DataFrame empty for {ticker}.") # Reduce noise
            if progress_tracker: # Still mark as "attempted" so we don't retry it if it genuinely has no data
                progress_tracker.mark_completed(ticker) # Or a different status like "attempted_no_data"
            return None
            
    except Exception as e:
        print(f"[{ticker} WORKER] CRITICAL EXCEPTION processing {ticker}: {str(e)}")
        import traceback
        # traceback.print_exc() # Potentially too verbose for 10k tickers if many fail
        return None

class ProgressTracker:
    def __init__(self, save_dir, filename='progress.json'):
        self.save_dir = save_dir
        self.filename = os.path.join(save_dir, filename)
        self.completed_tickers = set()
        self.lock = threading.Lock()
        self.load_progress()
        
    def load_progress(self):
        with self.lock:
            if os.path.exists(self.filename):
                try:
                    with open(self.filename, 'r') as f:
                        data = json.load(f)
                        self.completed_tickers = set(data.get('completed_tickers', []))
                    print(f"Loaded progress: {len(self.completed_tickers)} tickers already processed from {self.filename}")
                except Exception as e:
                    print(f"Error loading progress file {self.filename}: {str(e)}")
                
    def save_progress(self):
        # Called by mark_completed which holds lock
        try:
            with open(self.filename, 'w') as f:
                json.dump({'completed_tickers': sorted(list(self.completed_tickers))}, f, indent=2)
        except Exception as e:
            print(f"Error saving progress file {self.filename}: {str(e)}")
                
    def mark_completed(self, ticker):
        with self.lock:
            if ticker not in self.completed_tickers:
                self.completed_tickers.add(ticker)
                self.save_progress() # Save more frequently
            
    def is_completed(self, ticker):
        with self.lock:
            return ticker in self.completed_tickers
        
    def get_remaining_tickers(self, all_tickers_list):
        with self.lock:
            return [ticker for ticker in all_tickers_list if ticker not in self.completed_tickers]
        
    def get_completion_percentage(self, all_tickers_list):
        with self.lock:
            total = len(all_tickers_list)
            completed_relevant = len(self.completed_tickers.intersection(set(all_tickers_list)))
            return (completed_relevant / total) * 100 if total > 0 else 0

def main_parallel():
    print(f"Using save directory: {CONFIG['save_dir']}")
    setup_directory(CONFIG['save_dir'])
    
    initial_access_token = None
    try:
        print("[MAIN THREAD] Attempting initial authentication...")
        initial_access_token = get_auth_token_with_retry()
        if not initial_access_token:
            print("[MAIN THREAD] CRITICAL: Failed to obtain initial access token. Exiting.")
            return {}
        print("[MAIN THREAD] Initial authentication successful.")
        
        progress_tracker = ProgressTracker(CONFIG['save_dir'])
        
        # Ensure 'tickers' in CONFIG is a list for progress tracking compatibility
        config_tickers_list = list(CONFIG['tickers'])
        remaining_tickers = progress_tracker.get_remaining_tickers(config_tickers_list)
        
        print(f"[MAIN THREAD] Total unique tickers in config: {len(config_tickers_list)}")
        print(f"[MAIN THREAD] Remaining tickers to process: {len(remaining_tickers)}")
        
        if not remaining_tickers:
            print("[MAIN THREAD] All tickers have already been processed. Nothing to do.")
            return {}
        
        max_workers = CONFIG.get('max_workers', 5)
        max_pending = CONFIG.get('max_pending_tasks', 20) # Using updated config
        results = {}
        
        print(f"[MAIN THREAD] Starting parallel processing: {max_workers} workers, {max_pending} max pending tasks.")
        batch_size = 50 
        
        total_batches = (len(remaining_tickers) + batch_size - 1) // batch_size

        for batch_num_idx, batch_start in enumerate(range(0, len(remaining_tickers), batch_size)):
            current_batch_num = batch_num_idx + 1
            batch_end = min(batch_start + batch_size, len(remaining_tickers))
            batch_tickers = remaining_tickers[batch_start:batch_end]
            
            print(f"\n[MAIN THREAD] Processing Batch {current_batch_num}/{total_batches} ({len(batch_tickers)} tickers)")
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                pending_futures = set()
                
                for i, ticker in enumerate(batch_tickers):
                    while len(pending_futures) >= max_pending:
                        # print(f"[MAIN THREAD] Pending tasks ({len(pending_futures)}) at max. Waiting...") # Reduce noise
                        done_futures_list, pending_futures_after_wait = concurrent.futures.wait(
                            pending_futures, return_when=concurrent.futures.FIRST_COMPLETED
                        )
                        pending_futures = pending_futures_after_wait
                        for future_item in done_futures_list: # Process results of completed tasks
                            try: future_item.result() # Check for exceptions from worker
                            except Exception as e_fut:
                                print(f"[MAIN THREAD] Error from completed task {getattr(future_item, 'ticker_name', 'UNKNOWN')} (wait block): {e_fut}")
                    
                    # print(f"[MAIN THREAD] Submitting {ticker} (Batch {current_batch_num}, Item {i+1}/{len(batch_tickers)})") # Reduce noise
                    future = executor.submit(fetch_and_process_ticker, ticker, CONFIG, progress_tracker)
                    future.ticker_name = ticker
                    pending_futures.add(future)
                    
                    if (i + 1) % 10 == 0 or (i + 1) == len(batch_tickers): # Progress update every 10 or at end of batch submission
                        overall_comp = progress_tracker.get_completion_percentage(config_tickers_list)
                        print(f"[MAIN THREAD] Batch {current_batch_num} Submit Progress: {i+1}/{len(batch_tickers)}. Overall: {overall_comp:.1f}% ({len(progress_tracker.completed_tickers)}/{len(config_tickers_list)})")

                # print(f"[MAIN THREAD] All tasks for Batch {current_batch_num} submitted. Waiting for {len(pending_futures)} to complete.") # Reduce noise
                for future_item in concurrent.futures.as_completed(pending_futures):
                    ticker_name = getattr(future_item, 'ticker_name', 'UNKNOWN_TICKER')
                    try:
                        ticker_result_df = future_item.result() # Process result, check for exceptions
                        if ticker_result_df is not None:
                            results[ticker_name] = ticker_result_df # Store if needed, or just ensure it ran
                            # print(f"[MAIN THREAD] ✓ Completed: {ticker_name}") # Reduce noise
                        # else: (worker handles "no data" or failure prints)
                        #    print(f"[MAIN THREAD] ✓ Completed (no data/failed): {ticker_name}")
                    except Exception as e:
                        print(f"[MAIN THREAD] ✗ Error processing {ticker_name} (as_completed): {str(e)}")
            
            if batch_end < len(remaining_tickers):
                delay_between_batches = 1 # MODIFIED: Reduced delay
                # print(f"\n[MAIN THREAD] Batch {current_batch_num} done. Resting {delay_between_batches}s...") # Reduce noise
                time.sleep(delay_between_batches)
        
        final_completion = progress_tracker.get_completion_percentage(config_tickers_list)
        print(f"\n[MAIN THREAD] Processing COMPLETE! Overall progress: {final_completion:.1f}% ({len(progress_tracker.completed_tickers)}/{len(config_tickers_list)})")
        print(f"[MAIN THREAD] DataFrames collected in this run: {len(results)}")
        return results
    
    except KeyboardInterrupt:
        print("\n[MAIN THREAD] Operation interrupted by user. Progress saved. Exiting.")
        return None
    except Exception as e:
        print(f"[MAIN THREAD] CRITICAL ERROR in main process: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    # Important: If you have a list of 10k tickers, load it into CONFIG['tickers'] before calling main_parallel.
    # Example:
    #
    # with open('my_10k_tickers.txt', 'r') as f:
    #     ten_k_tickers_list = [line.strip() for line in f if line.strip()]
    # CONFIG['tickers'] = ten_k_tickers_list 
    # print(f"Loaded {len(CONFIG['tickers'])} tickers for processing.")
    #
    # For now, it uses the `all_tickers` list defined above.

    print(f"Script starting. Will process {len(CONFIG['tickers'])} tickers.")
    results_data = main_parallel()
    if results_data is not None: # Check if not None (None can be returned on interrupt/error)
        print(f"\n[MAIN SCRIPT] main_parallel finished. Collected {len(results_data)} dataframes in this session.")
    else:
        print("\n[MAIN SCRIPT] main_parallel did not complete successfully or was interrupted.")