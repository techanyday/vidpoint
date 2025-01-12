"""Configuration module for VidPoint."""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Square configuration
SQUARE_CONFIG = {
    'app_id': os.getenv('SQUARE_APP_ID'),
    'access_token': os.getenv('SQUARE_ACCESS_TOKEN'),
    'location_id': os.getenv('SQUARE_LOCATION_ID'),
    'environment': os.getenv('SQUARE_ENVIRONMENT', 'sandbox'),
    'webhook_signing_key': os.getenv('SQUARE_WEBHOOK_SIGNING_KEY')
}

# Flask configuration
FLASK_CONFIG = {
    'secret_key': os.getenv('FLASK_SECRET_KEY'),
    'debug': os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
}

# Database configuration
DB_CONFIG = {
    'mongodb_uri': os.getenv('MONGODB_URI')
}

def validate_config():
    """Validate required configuration values are present."""
    missing = []
    
    # Check Square config
    for key, value in SQUARE_CONFIG.items():
        if value is None:
            missing.append(f'SQUARE_{key.upper()}')
    
    # Check Flask config
    if not FLASK_CONFIG['secret_key']:
        missing.append('FLASK_SECRET_KEY')
    
    # Check DB config
    if not DB_CONFIG['mongodb_uri']:
        missing.append('MONGODB_URI')
    
    if missing:
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
