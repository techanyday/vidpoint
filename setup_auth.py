"""
Run this script once to set up Google OAuth authentication.
This will create a token.pickle file that will be used for future authentication.
"""

import os
import logging
import pickle
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
import webbrowser

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/presentations']

def setup_auth():
    """Sets up Google OAuth authentication."""
    try:
        if not os.path.exists('credentials.json'):
            logger.error("credentials.json not found. Please download it from Google Cloud Console")
            return False
            
        # Try different redirect URIs
        redirect_uris = [
            'http://localhost:8080/',
            'http://localhost:8080',
            'http://127.0.0.1:8080',
            'http://127.0.0.1:8080/'
        ]
        
        for redirect_uri in redirect_uris:
            try:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', 
                    SCOPES,
                    redirect_uri=redirect_uri
                )
                creds = flow.run_local_server(port=8080)
                
                # If we get here, authentication was successful
                with open('token.pickle', 'wb') as token:
                    pickle.dump(creds, token)
                    
                logger.info("Authentication successful! You can now use the application.")
                return True
                
            except Exception as e:
                logger.warning(f"Failed with redirect URI {redirect_uri}: {str(e)}")
                continue
                
        raise Exception("All redirect URIs failed")
        
    except Exception as e:
        logger.error(f"Error setting up authentication: {str(e)}")
        return False

if __name__ == '__main__':
    setup_auth()
