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

class SchwabEquityStreamer:
    def __init__(self, app_key, app_secret, equity_symbols):
        self.app_key = app_key
        self.app_secret = app_secret
        self.equity_symbols = equity_symbols
        self.access_token = self.get_access_token()
        self.user_preferences = self.get_user_preferences()

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
            print(f"Response status code: {response.status_code}")
            print(f"Response headers: {response.headers}")
            print(f"Response content: {response.text}")
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
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Accept': 'application/json'
        }
        
        response = requests.get('https://api.schwabapi.com/user/v1/preferences', headers=headers)
        response.raise_for_status()
        return response.json()

    def on_message(self, ws, message):
        try:
            data = json.loads(message)
            
            if 'data' in data:
                for item in data['data']:
                    if item.get('service') == 'LEVELONE_EQUITIES':
                        content = item.get('content', [{}])[0]
                        symbol = content.get('key', 'Unknown')
                        bid = content.get('1', 'N/A')
                        ask = content.get('2', 'N/A')
                        last = content.get('3', 'N/A')
                        
                        print(f"\r{datetime.now().strftime('%H:%M:%S')} | "
                              f"{symbol}: Bid={bid}, Ask={ask}, Last={last}", 
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
        
        ws.send(json.dumps(login_request))
        
        subs_request = [{
            "service": "LEVELONE_EQUITIES",
            "requestid": "1",
            "command": "SUBS",
            "SchwabClientCustomerId": self.user_preferences.get('schwabClientCustomerId'),
            "SchwabClientCorrelId": str(uuid.uuid4()),
            "parameters": {
                "keys": ",".join(self.equity_symbols),
                "fields": "0,1,2,3"  # Symbol, Bid Price, Ask Price, Last Price
            }
        }]
        
        ws.send(json.dumps(subs_request))

    def connect_websocket(self):
        websocket_url = "wss://streamerapi.schwab.com/ws"
        
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
        
        wst = threading.Thread(target=self.ws.run_forever, 
                               kwargs={'sslopt': {"cert_reqs": ssl.CERT_NONE, "check_hostname": False},
                                       'ping_interval': 30,
                                       'ping_timeout': 10})
        wst.daemon = True
        wst.start()

    def stream_equity_quotes(self):
        self.connect_websocket()
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nStreaming stopped by user.")

def main():
    CONFIG = {
        'app_key': os.getenv('APP_KEY'),
        'app_secret': os.getenv('APP_SECRET'),
        'equity_symbols': ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'FB']  # Example equity symbols
    }

    streamer = SchwabEquityStreamer(
        CONFIG['app_key'], 
        CONFIG['app_secret'], 
        CONFIG['equity_symbols']
    )
    
    streamer.stream_equity_quotes()

if __name__ == "__main__":
    main()
