import json

def extract_tickers_from_file(file_path):
    try:
        # Open and read the JSON file
        with open(file_path, 'r') as file:
            data = json.load(file)
        
        # Extract tickers
        tickers = []
        for key, value in data.items():
            if isinstance(value, dict) and "ticker" in value:
                tickers.append(value["ticker"])
        
        # Create the output structure
        output = {
            "stock_tickers": tickers
        }
        
        # Convert to JSON string with indentation for readability
        return json.dumps(output, indent=2)
    
    except FileNotFoundError:
        return f"Error: File not found at {file_path}"
    except json.JSONDecodeError as e:
        return f"Error parsing JSON: {e}"
    except Exception as e:
        return f"Unexpected error: {e}"

# Use the specific file path you provided
#file_path = r"C:\Users\cinco\Desktop\Cinco-Quant\00_raw_data\ticker.json"
file_path = "/Users/jazzhashzzz/Desktop/Cinco-Quant/Chasing-Alpha/data/ticker.json"

result = extract_tickers_from_file(file_path)

# Save to a new file in the same directory
#output_file_path = r"C:\Users\cinco\Desktop\Cinco-Quant\00_raw_data\extracted_tickers.json"
output_file_path = "/Users/jazzhashzzz/Desktop/Cinco-Quant/Chasing-Alpha/data/extracted_tickers.py"

try:
    with open(output_file_path, 'w') as file:
        file.write(result)
    print(f"Success! Tickers extracted and saved to {output_file_path}")
except Exception as e:
    print(f"Error saving output file: {e}")
    print("Here's the extracted data:")
    print(result)