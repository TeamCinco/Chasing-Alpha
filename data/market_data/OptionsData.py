import os
import json
import logging
from datetime import datetime
from dotenv import load_dotenv
import schwabdev

# Load environment variables
load_dotenv()

class SchwabOptionsStreamer:
    def __init__(self, app_key, app_secret, option_symbols):
        self.client = schwabdev.Client(app_key, app_secret)
        self.option_symbols = option_symbols
        # Create the stream object correctly
        self.stream = self.client.stream  # Changed to use stream property

    def handle_message(self, message, **kwargs):
        """Process incoming stream messages"""
        try:
            if isinstance(message, str):
                data = json.loads(message)
                
                if 'data' in data:
                    for item in data['data']:
                        if item.get('service') == 'LEVELONE_OPTIONS':
                            content = item.get('content', [{}])[0]
                            self.format_and_print_option_data(content)
                            
        except Exception as e:
            print(f"Error processing message: {e}")

    def format_and_print_option_data(self, content):
        """Format and print option data"""
        option_data = {
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
            # Subscribe to options data
            fields = "0,2,3,4,8,9,10,20,21,22,28,29,30,31"
            subscription = self.stream.level_one_options(
                keys=self.option_symbols,
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
    
    # Configuration
    CONFIG = {
        'app_key': os.getenv('APP_KEY'),
        'app_secret': os.getenv('APP_SECRET'),
        'option_symbols': [
            'SPY   250121C00595000'
  # Example SPY Put
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