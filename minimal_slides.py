import os
import logging
import json
import time
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
    max_retries = 3
    retry_delay = 1

    for retry in range(max_retries):
        try:
            # Check if credentials.json exists
            if not os.path.exists(credentials_path):
                logger.error("credentials.json not found")
                raise FileNotFoundError("credentials.json not found")

            # Verify credentials.json format
            with open(credentials_path, 'r') as f:
                client_config = json.load(f)
                if 'installed' not in client_config:
                    raise ValueError("Invalid credentials.json format")
                required_fields = ['client_id', 'client_secret', 'auth_uri', 'token_uri']
                if not all(field in client_config['installed'] for field in required_fields):
                    raise ValueError("Missing required fields in credentials.json")

            # Load credentials from token file
            if os.path.exists(token_path):
                try:
                    with open(token_path, 'rb') as token:
                        creds = pickle.load(token)
                        logger.info("Loaded credentials from token.pickle")
                except Exception as e:
                    logger.warning(f"Error loading token.pickle: {str(e)}")
                    creds = None
                    # Delete corrupted token file
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
                        logger.warning(f"Error refreshing credentials: {str(e)}")
                        creds = None
                        # Delete invalid token file
                        if os.path.exists(token_path):
                            os.remove(token_path)
                            logger.info("Deleted invalid token.pickle")

                if not creds:
                    try:
                        logger.info("Starting OAuth flow for new credentials")
                        flow = InstalledAppFlow.from_client_secrets_file(
                            credentials_path, 
                            SCOPES,
                            redirect_uri='http://localhost:8080'
                        )
                        # Use headless mode for server environment
                        creds = flow.run_local_server(
                            host='localhost',
                            port=8080,
                            authorization_prompt_message='',
                            success_message='The authentication flow has completed. You may close this window.',
                            open_browser=False  # Don't open browser automatically
                        )
                        logger.info("Successfully completed OAuth flow")

                        # Save the credentials for the next run
                        try:
                            with open(token_path, 'wb') as token:
                                pickle.dump(creds, token)
                            logger.info("Saved new credentials to token.pickle")
                        except Exception as e:
                            logger.error(f"Error saving credentials: {str(e)}")
                    except Exception as e:
                        logger.error(f"Error in OAuth flow: {str(e)}")
                        if retry < max_retries - 1:
                            logger.info(f"Retrying OAuth flow (attempt {retry + 2}/{max_retries})")
                            time.sleep(retry_delay)
                            continue
                        raise

            # Verify credentials are valid
            if not creds or not creds.valid:
                raise ValueError("Failed to obtain valid credentials")

            return creds

        except Exception as e:
            logger.error(f"Error in get_credentials: {str(e)}", exc_info=True)
            if retry < max_retries - 1:
                logger.info(f"Retrying get_credentials (attempt {retry + 2}/{max_retries})")
                time.sleep(retry_delay)
                continue
            raise

    return None

def create_presentation(slides_content, title="Video Summary"):
    """Creates a Google Slides presentation."""
    try:
        # Debug logging
        logger.info("Starting presentation creation...")
        logger.info(f"Title: {title}")
        logger.info(f"Number of slides: {len(slides_content)}")
        logger.info(f"First slide content: {slides_content[0] if slides_content else 'None'}")

        # Input validation
        if not slides_content:
            logger.error("No slides content provided")
            raise ValueError("No slides content provided")

        # Validate each slide's content
        for i, slide in enumerate(slides_content):
            if not isinstance(slide, dict):
                error_msg = f"Invalid slide format at index {i}: expected dict, got {type(slide)}"
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            required_fields = ['title', 'layout']
            missing_fields = [field for field in required_fields if field not in slide]
            if missing_fields:
                error_msg = f"Missing required fields in slide {i}: {missing_fields}"
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            if slide['layout'] not in ['TITLE_AND_SUBTITLE', 'TITLE_AND_BODY']:
                error_msg = f"Invalid layout in slide {i}: {slide['layout']}"
                logger.error(error_msg)
                raise ValueError(error_msg)

        # Get credentials with retry
        max_retries = 3
        retry_count = 0
        creds = None
        
        while retry_count < max_retries:
            try:
                creds = get_credentials()
                if not creds:
                    raise ValueError("get_credentials() returned None")
                if not creds.valid:
                    raise ValueError("Invalid credentials")
                if creds.expired:
                    raise ValueError("Expired credentials")
                logger.info("Successfully loaded credentials")
                break
            except Exception as e:
                retry_count += 1
                error_msg = f"Attempt {retry_count}/{max_retries} failed: {str(e)}"
                if retry_count == max_retries:
                    logger.error(error_msg, exc_info=True)
                    raise Exception(f"Failed to get credentials: {str(e)}")
                logger.warning(error_msg)
                time.sleep(2 ** retry_count)  # Exponential backoff

        # Build service with retry
        retry_count = 0
        service = None
        
        while retry_count < max_retries:
            try:
                service = build('slides', 'v1', credentials=creds, cache_discovery=False)
                if not service:
                    raise ValueError("build() returned None")
                logger.info("Successfully built slides service")
                break
            except Exception as e:
                retry_count += 1
                error_msg = f"Attempt {retry_count}/{max_retries} failed: {str(e)}"
                if retry_count == max_retries:
                    logger.error(error_msg, exc_info=True)
                    raise Exception(f"Failed to build slides service: {str(e)}")
                logger.warning(error_msg)
                time.sleep(2 ** retry_count)  # Exponential backoff

        # Create presentation with retry
        retry_count = 0
        presentation_id = None
        
        while retry_count < max_retries:
            try:
                # Create presentation request
                request_body = {
                    'title': title,
                    'locale': 'en'
                }
                logger.info(f"Creating presentation with body: {request_body}")
                
                # Execute request
                presentation = service.presentations().create(body=request_body).execute()
                if not presentation:
                    raise ValueError("create() returned None")
                
                presentation_id = presentation.get('presentationId')
                if not presentation_id:
                    raise ValueError("No presentationId in response")
                
                logger.info(f"Created presentation with ID: {presentation_id}")
                break
            except Exception as e:
                retry_count += 1
                error_msg = f"Attempt {retry_count}/{max_retries} failed: {str(e)}"
                if retry_count == max_retries:
                    logger.error(error_msg, exc_info=True)
                    raise Exception(f"Failed to create presentation: {str(e)}")
                logger.warning(error_msg)
                time.sleep(2 ** retry_count)  # Exponential backoff

        # Create slides with batched requests
        batch_size = 10  # Process slides in batches to avoid rate limits
        for i in range(0, len(slides_content), batch_size):
            batch = slides_content[i:i + batch_size]
            retry_count = 0
            
            while retry_count < max_retries:
                try:
                    # Prepare batch request
                    requests = []
                    for slide in batch:
                        requests.extend([
                            {
                                'createSlide': {
                                    'objectId': f'slide_{len(requests)}',
                                    'slideLayoutReference': {
                                        'predefinedLayout': slide['layout']
                                    },
                                    'placeholderIdMappings': [
                                        {
                                            'layoutPlaceholder': {
                                                'type': 'TITLE',
                                                'index': 0
                                            },
                                            'objectId': f'title_{len(requests)}'
                                        }
                                    ] if slide['layout'] == 'TITLE_AND_BODY' else []
                                }
                            },
                            {
                                'insertText': {
                                    'objectId': f'title_{len(requests)}',
                                    'text': slide['title']
                                }
                            }
                        ])
                        
                        if 'content' in slide:
                            requests.append({
                                'insertText': {
                                    'objectId': f'body_{len(requests)}',
                                    'text': slide['content']
                                }
                            })
                    
                    # Execute batch request
                    logger.info(f"Executing batch request for slides {i} to {i + len(batch)}")
                    result = service.presentations().batchUpdate(
                        presentationId=presentation_id,
                        body={'requests': requests}
                    ).execute()
                    
                    if not result:
                        raise ValueError("batchUpdate() returned None")
                    
                    logger.info(f"Successfully created batch of {len(batch)} slides")
                    break
                    
                except Exception as e:
                    retry_count += 1
                    error_msg = f"Attempt {retry_count}/{max_retries} failed for batch {i}: {str(e)}"
                    if retry_count == max_retries:
                        logger.error(error_msg, exc_info=True)
                        # Try to delete the failed presentation
                        try:
                            service.presentations().delete(presentationId=presentation_id).execute()
                            logger.info(f"Deleted failed presentation: {presentation_id}")
                        except:
                            logger.warning(f"Failed to delete presentation: {presentation_id}")
                        raise Exception(f"Failed to create slides: {str(e)}")
                    logger.warning(error_msg)
                    time.sleep(2 ** retry_count)  # Exponential backoff
            
            # Add delay between batches to avoid rate limits
            if i + batch_size < len(slides_content):
                time.sleep(1)

        presentation_url = f"https://docs.google.com/presentation/d/{presentation_id}"
        logger.info(f"Successfully created presentation: {presentation_url}")
        return presentation_url

    except Exception as e:
        logger.error(f"Error in create_presentation: {str(e)}", exc_info=True)
        raise Exception(f"Failed to create presentation: {str(e)}")

if __name__ == '__main__':
    content = [
        {'title': 'Slide 1', 'content': 'This is the content of slide 1.', 'layout': 'TITLE_AND_BODY'},
        {'title': 'Slide 2', 'content': 'This is the content of slide 2.', 'layout': 'TITLE_AND_BODY'}
    ]
    
    url = create_presentation(content)
    if url:
        print(f'Created presentation! Open it at: {url}')
