import os
import json
import logging
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

    def handle_message(self, message, **kwargs):
        """Process incoming stream messages"""
        try:
            if isinstance(message, str):
                data = json.loads(message)
                
                if 'data' in data:
                    for item in data['data']:
                        if item.get('service') == 'LEVELONE_EQUITIES':
                            content = item.get('content', [{}])[0]
                            self.format_and_print_equity_data(content)
                            
        except Exception as e:
            print(f"Error processing message: {e}")

    def format_and_print_equity_data(self, content):
        """Format and print equity data"""
        equity_data = {
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
            # Subscribe to equity data
            fields = "0,1,2,3,8,10,11,12,17,18"  # Key fields for equity data
            subscription = self.stream.level_one_equities(
                keys=self.equity_symbols,
                fields=fields
            )
            
            # Start the stream with our message handler
            self.stream.start(receiver=self.handle_message)
            
            # Send the subscription request
            self.stream.send(subscription)

            # Keep the main thread running
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
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    
    # Get symbols from user input
    print("Enter ticker symbols separated by commas (e.g., AAPL,MSFT,GOOGL):")
    user_input = input().strip()
    equity_symbols = [symbol.strip().upper() for symbol in user_input.split(',')]
    
    # Configuration
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