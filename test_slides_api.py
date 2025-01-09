import os
import logging
import json
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import pickle

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/presentations']

def get_credentials():
    """Gets valid user credentials from storage."""
    creds = None
    token_path = 'token.pickle'
    credentials_path = 'credentials.json'

    try:
        # Check if credentials.json exists
        if not os.path.exists(credentials_path):
            logger.error("credentials.json not found")
            return None

        # Verify credentials.json format
        with open(credentials_path, 'r') as f:
            client_config = json.load(f)
            logger.info("Loaded client config from credentials.json")
            if 'installed' not in client_config:
                logger.error("Invalid credentials.json format - missing 'installed' key")
                return None
            required_fields = ['client_id', 'client_secret', 'auth_uri', 'token_uri']
            missing_fields = [field for field in required_fields if field not in client_config['installed']]
            if missing_fields:
                logger.error(f"Missing required fields in credentials.json: {missing_fields}")
                return None
            logger.info("Credentials.json format validated successfully")

        # Load credentials from token file
        if os.path.exists(token_path):
            try:
                with open(token_path, 'rb') as token:
                    creds = pickle.load(token)
                    logger.info("Loaded credentials from token.pickle")
            except Exception as e:
                logger.warning(f"Error loading token.pickle: {str(e)}")
                if os.path.exists(token_path):
                    os.remove(token_path)
                    logger.info("Deleted corrupted token.pickle")

        # If no valid credentials, get new ones
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    logger.info("Refreshing expired credentials")
                    creds.refresh(Request())
                    logger.info("Successfully refreshed credentials")
                except Exception as e:
                    logger.error(f"Error refreshing credentials: {str(e)}")
                    if os.path.exists(token_path):
                        os.remove(token_path)
                        logger.info("Deleted invalid token.pickle")
                    creds = None

            if not creds:
                logger.info("Starting OAuth flow for new credentials")
                flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
                creds = flow.run_local_server(port=8080)
                logger.info("Successfully completed OAuth flow")

                # Save the credentials for the next run
                try:
                    with open(token_path, 'wb') as token:
                        pickle.dump(creds, token)
                    logger.info("Saved new credentials to token.pickle")
                except Exception as e:
                    logger.error(f"Error saving credentials: {str(e)}")

        return creds

    except Exception as e:
        logger.error(f"Error in get_credentials: {str(e)}", exc_info=True)
        return None

def test_slides_api():
    """Test the Google Slides API by creating a simple presentation."""
    try:
        # Get credentials
        logger.info("Getting credentials...")
        creds = get_credentials()
        if not creds:
            logger.error("Failed to get credentials")
            return False

        # Build service
        logger.info("Building slides service...")
        service = build('slides', 'v1', credentials=creds, cache_discovery=False)
        if not service:
            logger.error("Failed to build service")
            return False

        # Create presentation
        logger.info("Creating test presentation...")
        presentation = service.presentations().create(
            body={
                'title': 'Test Presentation',
                'locale': 'en'
            }
        ).execute()

        presentation_id = presentation.get('presentationId')
        if not presentation_id:
            logger.error("No presentation ID returned")
            return False

        logger.info(f"Created presentation with ID: {presentation_id}")

        # Create a slide
        logger.info("Creating test slide...")
        requests = [
            {
                'createSlide': {
                    'objectId': 'slide1',
                    'slideLayoutReference': {
                        'predefinedLayout': 'TITLE_AND_BODY'
                    },
                    'placeholderIdMappings': [
                        {
                            'layoutPlaceholder': {
                                'type': 'TITLE',
                                'index': 0
                            },
                            'objectId': 'title1'
                        }
                    ]
                }
            },
            {
                'insertText': {
                    'objectId': 'title1',
                    'text': 'Test Title'
                }
            }
        ]

        result = service.presentations().batchUpdate(
            presentationId=presentation_id,
            body={'requests': requests}
        ).execute()

        if not result:
            logger.error("Failed to create slide")
            return False

        logger.info("Successfully created test slide")
        presentation_url = f"https://docs.google.com/presentation/d/{presentation_id}"
        logger.info(f"Test presentation URL: {presentation_url}")
        return True

    except Exception as e:
        logger.error(f"Error in test_slides_api: {str(e)}", exc_info=True)
        return False

if __name__ == '__main__':
    success = test_slides_api()
    print(f"\nTest {'succeeded' if success else 'failed'}")
