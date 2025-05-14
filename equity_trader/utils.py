# utils.py
import json
import logging
import config

def setup_logging():
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL.upper(), logging.INFO),
        format='%(asctime)s - %(levelname)s - %(module)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    # Suppress overly verbose logs from libraries like 'requests' if needed
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)

def pretty_print_json(data, indent=2):
    """Prints JSON data in a readable format."""
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except json.JSONDecodeError:
            print(data) # Not JSON, print as is
            return
    print(json.dumps(data, indent=indent, sort_keys=True))