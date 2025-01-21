import os
import json
import base64
import requests
import urllib.parse
from dotenv import load_dotenv

def generate_tokens():
    # Load environment variables
    load_dotenv()
    
    app_key = os.getenv('APP_KEY')
    app_secret = os.getenv('APP_SECRET')
    
    if not app_key or not app_secret:
        print("Please ensure APP_KEY and APP_SECRET are set in your .env file")
        return
    
    # Generate auth URL and get code
    auth_url = f'https://api.schwabapi.com/v1/oauth/authorize?client_id={app_key}&redirect_uri=https://127.0.0.1'
    print(f"\nPlease visit this URL to authenticate:")
    print(auth_url)
    
    returned_link = input("\nPaste the redirect URL here: ").strip()
    
    try:
        code = urllib.parse.unquote(returned_link.split('code=')[1].split('&')[0])
    except IndexError:
        print("Invalid redirect URL")
        return
    
    # Get access token
    app_credentials = f"{app_key}:{app_secret}"
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
        response = requests.post('https://api.schwabapi.com/v1/oauth/token', 
                               headers=headers, 
                               data=data)
        response.raise_for_status()
        token_data = response.json()
        
        # Save tokens to file
        tokens = {
            'access_token': token_data['access_token'],
            'refresh_token': token_data.get('refresh_token'),
            'expires_in': token_data.get('expires_in'),
            'token_type': token_data.get('token_type')
        }
        
        # Create tokens directory if it doesn't exist
        os.makedirs('tokens', exist_ok=True)
        
        # Save tokens to file
        with open('tokens/auth.json', 'w') as f:
            json.dump(tokens, f, indent=4)
        
        print("\nTokens successfully generated and saved to tokens/auth.json")
        
    except Exception as e:
        print(f"Error generating tokens: {e}")

if __name__ == "__main__":
    generate_tokens()