import os
import json
import logging
import csv
from datetime import datetime
from dotenv import load_dotenv
import schwabdev

# Load environment variables
load_dotenv()

class SchwabOptionsStreamer:
    def __init__(self, app_key, app_secret, option_symbols):
        self.client = schwabdev.Client(app_key, app_secret)
        self.option_symbols = option_symbols
        self.stream = self.client.stream
        #self.output_dir = r"C:\Users\cinco\Desktop\DATA FOR SCRIPTS\Charles\Live Data"
        self.output_dir = '/Users/jazzhashzzz/Desktop/data for scripts/charles/Live Data'

        # Create output directory if it doesn't exist
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
        
        # Initialize CSV files
        self.initialize_csv_files()

    def initialize_csv_files(self):
        headers = ['Timestamp', 'Symbol', 'Strike', 'Type', 'Bid', 'Ask', 'Last', 
                  'Volume', 'Open_Interest', 'Implied_Volatility', 'Delta', 
                  'Gamma', 'Theta', 'Vega', 'Underlying']
        
        for symbol in self.option_symbols:
            safe_symbol = symbol.replace(' ', '_').replace('/', '_')
            filepath = os.path.join(self.output_dir, f'{safe_symbol}_options_data.csv')
            if not os.path.exists(filepath):
                with open(filepath, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(headers)

    def save_to_csv(self, option_data):
        safe_symbol = option_data['symbol'].replace(' ', '_').replace('/', '_')
        filepath = os.path.join(self.output_dir, f'{safe_symbol}_options_data.csv')
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
        
        with open(filepath, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                timestamp,
                option_data['symbol'],
                option_data['strike'],
                option_data['type'],
                option_data['bid'],
                option_data['ask'],
                option_data['last'],
                option_data['volume'],
                option_data['open_interest'],
                option_data['volatility'],
                option_data['delta'],
                option_data['gamma'],
                option_data['theta'],
                option_data['vega'],
                option_data['underlying']
            ])

    def handle_message(self, message, **kwargs):
        """Process incoming stream messages"""
        try:
            if isinstance(message, str):
                data = json.loads(message)
                
                if 'data' in data:
                    for item in data['data']:
                        if item.get('service') == 'LEVELONE_OPTIONS':
                            content = item.get('content', [{}])[0]
                            option_data = self.format_option_data(content)
                            self.save_to_csv(option_data)
                            self.print_option_data(option_data)
                            
        except Exception as e:
            print(f"Error processing message: {e}")

    def format_option_data(self, content):
        """Format option data"""
        return {
            'symbol': content.get('key', 'Unknown'),
            'bid': content.get('2', 'N/A'),
            'ask': content.get('3', 'N/A'),
            'last': content.get('4', 'N/A'),
            'volume': content.get('8', 'N/A'),
            'open_interest': content.get('9', 'N/A'),
            'volatility': content.get('10', 'N/A'),
            'strike': content.get('20', 'N/A'),
            'type': content.get('21', 'N/A'),
            'underlying': content.get('22', 'N/A'),
            'delta': content.get('28', 'N/A'),
            'gamma': content.get('29', 'N/A'),
            'theta': content.get('30', 'N/A'),
            'vega': content.get('31', 'N/A')
        }

    def print_option_data(self, option_data):
        """Print option data to console"""
        print(f"\r{datetime.now().strftime('%H:%M:%S')} | "
              f"{option_data['symbol']} | "
              f"Strike={option_data['strike']} | "
              f"Type={option_data['type']} | "
              f"Bid={option_data['bid']} | "
              f"Ask={option_data['ask']} | "
              f"Last={option_data['last']} | "
              f"Vol={option_data['volume']} | "
              f"OI={option_data['open_interest']} | "
              f"IV={option_data['volatility']} | "
              f"Δ={option_data['delta']} | "
              f"γ={option_data['gamma']} | "
              f"θ={option_data['theta']} | "
              f"ν={option_data['vega']}", 
              end='', flush=True)

    def start_streaming(self):
        """Start streaming options data"""
        try:
            fields = "0,2,3,4,8,9,10,20,21,22,28,29,30,31"
            subscription = self.stream.level_one_options(
                keys=self.option_symbols,
                fields=fields
            )
            
            self.stream.start(receiver=self.handle_message)
            self.stream.send(subscription)

            try:
                while True:
                    import time
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\nStreaming stopped by user")
                self.stream.stop()

        except Exception as e:
            print(f"Error starting stream: {e}")
            self.stream.stop()

def main():
    logging.basicConfig(level=logging.INFO)
    
    CONFIG = {
        'app_key': os.getenv('APP_KEY'),
        'app_secret': os.getenv('APP_SECRET'),
        'option_symbols': [
            'SPY   250930C00605000'
        ]
    }

    try:
        streamer = SchwabOptionsStreamer(
            CONFIG['app_key'], 
            CONFIG['app_secret'], 
            CONFIG['option_symbols']
        )
        
        streamer.start_streaming()
        
    except KeyboardInterrupt:
        print("\nProgram terminated by user")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()