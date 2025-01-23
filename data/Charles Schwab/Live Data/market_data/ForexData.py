import os
import json
import base64
import requests
import threading
import time
import websocket
import uuid
import ssl
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
        
        print(f"Headers: {headers}")
        print(f"Data: {data}")
        
        try:
            response = requests.post('https://api.schwabapi.com/v1/oauth/token', headers=headers, data=data)
            print(f"Full request URL: {response.request.url}")
            print(f"Full request headers: {response.request.headers}")
            print(f"Full request body: {response.request.body}")
            response.raise_for_status()
            return response.json()['access_token']
        except requests.exceptions.HTTPError as err:
            print(f"HTTP error occurred: {err}")
            print(f"Response content: {response.content}")
            raise
        except Exception as err:
            print(f"An error occurred: {err}")
            raise


    def get_user_preferences(self):
        # Get user preferences for streaming
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Accept': 'application/json'
        }
        
        response = requests.get('https://api.schwabapi.com/user/v1/preferences', headers=headers)
        response.raise_for_status()  # Raise an exception for bad responses
        return response.json()

    def on_message(self, ws, message):
        try:
            data = json.loads(message)
            
            # Process streaming data
            if 'data' in data:
                for item in data['data']:
                    if item.get('service') == 'LEVELONE_FOREX':
                        content = item.get('content', [{}])[0]
                        symbol = content.get('key', 'Unknown')
                        bid = content.get('1', 'N/A')
                        ask = content.get('2', 'N/A')
                        last = content.get('3', 'N/A')
                        
                        # Print live updates
                        print(f"\r{datetime.now().strftime('%H:%M:%S')} | "
                              f"{symbol}: Bid={bid}, Ask={ask}, Last={last}    ", 
                              end='', flush=True)
        
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON: {e}")
        except Exception as e:
            print(f"Error processing message: {e}")

    def on_error(self, ws, error):
        print(f"WebSocket Error: {error}")

    def on_close(self, ws, close_status_code, close_msg):
        print(f"### WebSocket Connection Closed ### Status code: {close_status_code}, Message: {close_msg}")

    def on_open(self, ws):
        print("### WebSocket Connection Opened ###")
        
        # Prepare login request
        login_request = [{
            "service": "ADMIN",
            "requestid": "0",
            "command": "LOGIN",
            "SchwabClientCustomerId": self.user_preferences.get('schwabClientCustomerId'),
            "SchwabClientCorrelId": str(uuid.uuid4()),
            "parameters": {
                "Authorization": self.access_token,
                "SchwabClientChannel": "SOCKET_STREAM_PROD",
                "SchwabClientFunctionId": "APIAPP"
            }
        }]
        
        # Send login request
        ws.send(json.dumps(login_request))
        
        # Prepare subscription request for forex symbols
        subs_request = [{
            "service": "LEVELONE_FOREX",
            "requestid": "0",
            "command": "SUBS",
            "SchwabClientCustomerId": "Your_Customer_ID",
            "SchwabClientCorrelId": "Unique_Correlation_ID",
            "parameters": {
                "keys": "EUR/USD",
                "fields": "0,1,2"  # Symbol, Bid Price, Ask Price
            }
        }]
        
        # Send subscription request
        ws.send(json.dumps(subs_request))

    def connect_websocket(self):
        # WebSocket connection parameters
        websocket_url = "wss://streamerapi.schwab.com/ws"
        
        # Create a custom SSL context
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE  # Use with caution in production
        
        self.ws = websocket.WebSocketApp(
            websocket_url,
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close
        )
        
        # Run WebSocket in a separate thread
        wst = threading.Thread(target=self.ws.run_forever, 
                               kwargs={'sslopt': {"cert_reqs": ssl.CERT_NONE, "check_hostname": False},
                                       'ping_interval': 30,
                                       'ping_timeout': 10})
        wst.daemon = True
        wst.start()
    def fetch_forex_quotes(self):
        url = "https://api.schwabapi.com/marketdata/v1/quotes"
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json"
        }
        
        params = {
            "symbols": ",".join(self.forex_symbols),
            "fields": "quote,reference"  # You can adjust fields as needed
        }
        
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error: {response.status_code}")
            print(response.text)
            return None
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
                    print(f"{symbol}: Bid: {quote.get('bidPrice', 'N/A')}, "
                          f"Ask: {quote.get('askPrice', 'N/A')}, "
                          f"Last: {quote.get('lastPrice', 'N/A')}, "
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