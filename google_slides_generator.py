import os
import pickle
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/presentations']

def get_credentials():
    """Gets valid user credentials from storage.
    
    Returns:
        Credentials, the obtained credential.
    """
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first time.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=8080)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    
    return creds

def create_presentation_with_google_slides(title, summary):
    """Creates a Google Slides presentation from the summary.
    
    Args:
        title (str): The title of the presentation
        summary (str): The content to be included in the presentation
    
    Returns:
        str: The ID of the created presentation
    """
    try:
        creds = get_credentials()
        service = build('slides', 'v1', credentials=creds)
        
        # Create a new presentation
        presentation = {
            'title': title
        }
        presentation = service.presentations().create(body=presentation).execute()
        presentation_id = presentation.get('presentationId')
        
        # Add title slide
        requests = [
            {
                'createSlide': {
                    'objectId': 'titleSlide',
                    'insertionIndex': '0',
                    'slideLayoutReference': {
                        'predefinedLayout': 'TITLE_AND_SUBTITLE'
                    }
                }
            }
        ]
        
        # Execute the request
        service.presentations().batchUpdate(
            presentationId=presentation_id,
            body={'requests': requests}
        ).execute()
        
        # Add title and content
        requests = [
            {
                'insertText': {
                    'objectId': 'titleSlide',
                    'insertionIndex': 0,
                    'text': title
                }
            },
            {
                'insertText': {
                    'objectId': 'titleSlide',
                    'insertionIndex': 0,
                    'text': summary
                }
            }
        ]
        
        # Execute the request
        service.presentations().batchUpdate(
            presentationId=presentation_id,
            body={'requests': requests}
        ).execute()
        
        print(f'Created presentation with ID: {presentation_id}')
        return presentation_id
        
    except HttpError as error:
        print(f'An error occurred: {error}')
        return None

def format_summary_for_slides(summary):
    """Formats the summary into slides by splitting into sections.
    
    Args:
        summary (str): The text to be formatted
        
    Returns:
        list: A list of dictionaries containing slide content
    """
    # Split the summary into sentences
    sentences = summary.split('. ')
    slides = []
    current_slide = []
    char_count = 0
    
    # Group sentences into slides (max 200 characters per slide)
    for sentence in sentences:
        if char_count + len(sentence) > 200:
            slides.append(' '.join(current_slide))
            current_slide = [sentence]
            char_count = len(sentence)
        else:
            current_slide.append(sentence)
            char_count += len(sentence)
    
    if current_slide:
        slides.append(' '.join(current_slide))
    
    return slides

def create_slides(title, summary):
    """Main function to create a presentation with formatted slides.
    
    Args:
        title (str): The title of the presentation
        summary (str): The content to be included in the presentation
        
    Returns:
        str: The URL of the created presentation
    """
    try:
        # Format the summary into slides
        slides_content = format_summary_for_slides(summary)
        
        # Create the presentation
        presentation_id = create_presentation_with_google_slides(title, slides_content[0])
        
        if presentation_id:
            # Add remaining slides
            creds = get_credentials()
            service = build('slides', 'v1', credentials=creds)
            
            for content in slides_content[1:]:
                requests = [
                    {
                        'createSlide': {
                            'slideLayoutReference': {
                                'predefinedLayout': 'TEXT'
                            },
                            'placeholderIdMappings': [
                                {
                                    'layoutPlaceholder': {
                                        'type': 'BODY',
                                        'index': 0
                                    },
                                    'objectId': f'content_{slides_content.index(content)}'
                                }
                            ]
                        }
                    },
                    {
                        'insertText': {
                            'objectId': f'content_{slides_content.index(content)}',
                            'text': content
                        }
                    }
                ]
                
                service.presentations().batchUpdate(
                    presentationId=presentation_id,
                    body={'requests': requests}
                ).execute()
            
            presentation_url = f'https://docs.google.com/presentation/d/{presentation_id}/edit'
            print(f'Created presentation: {presentation_url}')
            return presentation_url
            
    except Exception as e:
        print(f'An error occurred: {e}')
        raise e
