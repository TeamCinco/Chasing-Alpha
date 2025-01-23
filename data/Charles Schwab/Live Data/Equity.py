import os
import json
import logging
import csv
from datetime import datetime
from dotenv import load_dotenv
import schwabdev

# Load environment variables
load_dotenv()

class SchwabEquityStreamer:
    def __init__(self, app_key, app_secret, equity_symbols):
        self.client = schwabdev.Client(app_key, app_secret)
        self.equity_symbols = equity_symbols
        self.stream = self.client.stream
        self.output_dir = r"C:\Users\cinco\Desktop\DATA FOR SCRIPTS\Charles\Live Data"
        
        # Create output directory if it doesn't exist
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
        
        # Initialize CSV files
        self.initialize_csv_files()

    def initialize_csv_files(self):
        headers = ['Timestamp', 'Symbol', 'Last', 'Bid', 'Ask', 'Net_Change', 
                  'Volume', 'Open', 'High', 'Low', 'Close']
        
        for symbol in self.equity_symbols:
            filepath = os.path.join(self.output_dir, f'{symbol}_equity_data.csv')
            if not os.path.exists(filepath):
                with open(filepath, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(headers)

    def save_to_csv(self, equity_data):
        filepath = os.path.join(self.output_dir, f'{equity_data["symbol"]}_equity_data.csv')
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
        
        with open(filepath, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                timestamp,
                equity_data['symbol'],
                equity_data['last'],
                equity_data['bid'],
                equity_data['ask'],
                equity_data['net_change'],
                equity_data['volume'],
                equity_data['open'],
                equity_data['high'],
                equity_data['low'],
                equity_data['close']
            ])

    def handle_message(self, message, **kwargs):
        """Process incoming stream messages"""
        try:
            if isinstance(message, str):
                data = json.loads(message)
                
                if 'data' in data:
                    for item in data['data']:
                        if item.get('service') == 'LEVELONE_EQUITIES':
                            content = item.get('content', [{}])[0]
                            equity_data = self.format_equity_data(content)
                            self.save_to_csv(equity_data)
                            self.print_equity_data(equity_data)
                            
        except Exception as e:
            print(f"Error processing message: {e}")

    def format_equity_data(self, content):
        """Format equity data"""
        return {
            'symbol': content.get('key', 'Unknown'),
            'bid': content.get('1', 'N/A'),
            'ask': content.get('2', 'N/A'),
            'last': content.get('3', 'N/A'),
            'volume': content.get('8', 'N/A'),
            'high': content.get('10', 'N/A'),
            'low': content.get('11', 'N/A'),
            'open': content.get('17', 'N/A'),
            'close': content.get('12', 'N/A'),
            'net_change': content.get('18', 'N/A')
        }

    def print_equity_data(self, equity_data):
        """Print equity data to console"""
        print(f"\r{datetime.now().strftime('%H:%M:%S')} | "
              f"{equity_data['symbol']} | "
              f"Last={equity_data['last']} | "
              f"Bid={equity_data['bid']} | "
              f"Ask={equity_data['ask']} | "
              f"Chg={equity_data['net_change']} | "
              f"Vol={equity_data['volume']} | "
              f"O={equity_data['open']} | "
              f"H={equity_data['high']} | "
              f"L={equity_data['low']} | "
              f"C={equity_data['close']}", 
              end='', flush=True)

    def start_streaming(self):
        """Start streaming equity data"""
        try:
            fields = "0,1,2,3,8,10,11,12,17,18"
            subscription = self.stream.level_one_equities(
                keys=self.equity_symbols,
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
    
    print("Enter ticker symbols separated by commas (e.g., AAPL,MSFT,GOOGL):")
    user_input = input().strip()
    equity_symbols = [symbol.strip().upper() for symbol in user_input.split(',')]
    
    CONFIG = {
        'app_key': os.getenv('APP_KEY'),
        'app_secret': os.getenv('APP_SECRET'),
        'equity_symbols': equity_symbols
    }

    try:
        streamer = SchwabEquityStreamer(
            CONFIG['app_key'], 
            CONFIG['app_secret'], 
            CONFIG['equity_symbols']
        )
        
        print(f"\nStarting stream for: {', '.join(CONFIG['equity_symbols'])}")
        streamer.start_streaming()
        
    except KeyboardInterrupt:
        print("\nProgram terminated by user")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()