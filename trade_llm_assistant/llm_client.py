"""
LLM Client for the Trade Assistant

This module provides an interface to the LLM API (Claude from Anthropic).
It handles sending prompts and receiving responses from the LLM.
"""

import os
import json
import logging
import requests
import time
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

class LLMClient:
    """Client for interacting with the LLM API (Claude from Anthropic)"""
    
    def __init__(self):
        """Initialize the LLM client with API settings from environment variables"""
        load_dotenv()
        
        self.api_key = os.getenv('LLM_API_KEY')
        self.api_endpoint = os.getenv('LLM_API_ENDPOINT', 'https://api.anthropic.com/v1/messages')
        self.model = os.getenv('LLM_MODEL', 'claude-3-opus-20240229')
        
        if not self.api_key:
            logger.warning("LLM_API_KEY not set in environment variables")
    
    def query(self, prompt, system_prompt=None, max_tokens=4000, retry_count=3, retry_delay=2):
        """Send a query to the LLM API and get a response
        
        Args:
            prompt (str): The user prompt to send to the model
            system_prompt (str, optional): The system prompt to guide the model's behavior
            max_tokens (int, optional): Maximum number of tokens to generate
            retry_count (int, optional): Number of times to retry on failure
            retry_delay (int, optional): Delay between retries in seconds
            
        Returns:
            str or None: The model's response text, or None if the request failed
        """
        if not self.api_key:
            logger.error("Cannot query LLM: API key not set")
            return None
        
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}]
        }
        
        if system_prompt:
            payload["system"] = system_prompt
        
        for attempt in range(retry_count):
            try:
                logger.debug(f"Sending request to LLM API (attempt {attempt + 1})")
                response = requests.post(self.api_endpoint, json=payload, headers=headers)
                response.raise_for_status()
                return response.json()["content"][0]["text"]
            
            except (requests.exceptions.RequestException, KeyError, IndexError) as e:
                logger.error(f"Error querying LLM (attempt {attempt + 1}): {e}")
                
                if hasattr(response, 'text'):
                    logger.error(f"Response: {response.text}")
                
                if attempt < retry_count - 1:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    # Increase delay for next attempt
                    retry_delay *= 2
                else:
                    logger.error(f"Failed to query LLM after {retry_count} attempts")
                    return None
        
        return None
    
    def extract_json_from_response(self, response_text):
        """Extract JSON from the LLM response text
        
        Args:
            response_text (str): The raw text response from the LLM
            
        Returns:
            dict or None: The parsed JSON object, or None if parsing failed
        """
        if not response_text:
            return None
            
        try:
            # First try: assume the whole response is JSON
            return json.loads(response_text)
        except json.JSONDecodeError:
            pass
        
        try:
            # Second try: look for JSON within the response using regex
            import re
            json_match = re.search(r'(\{.*\})', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                return json.loads(json_str)
        except (json.JSONDecodeError, AttributeError):
            pass
        
        try:
            # Third try: look for triple backtick code blocks
            import re
            code_block_match = re.search(r'```(?:json)?(.*?)```', response_text, re.DOTALL)
            if code_block_match:
                json_str = code_block_match.group(1).strip()
                return json.loads(json_str)
        except (json.JSONDecodeError, AttributeError):
            pass
        
        logger.error("Failed to parse JSON from LLM response")
        logger.debug(f"Raw response: {response_text}")
        return None
