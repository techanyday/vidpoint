from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import os

SCOPES = ['https://www.googleapis.com/auth/presentations']

def get_credentials():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
        creds = flow.run_local_server(port=8080)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return creds

def create_simple_presentation(title, content):
    try:
        creds = get_credentials()
        service = build('slides', 'v1', credentials=creds)
        
        # Create presentation
        presentation = service.presentations().create(
            body={'title': title}
        ).execute()
        presentation_id = presentation.get('presentationId')
        
        # Create title slide
        requests = [{
            'createSlide': {
                'slideLayoutReference': {
                    'predefinedLayout': 'TITLE'
                },
                'placeholderIdMappings': [
                    {
                        'layoutPlaceholder': {
                            'type': 'TITLE',
                            'index': 0
                        },
                        'objectId': 'title_0'
                    }
                ]
            }
        }]
        
        # Execute the create slide request
        service.presentations().batchUpdate(
            presentationId=presentation_id,
            body={'requests': requests}
        ).execute()
        
        # Add title text
        requests = [{
            'insertText': {
                'objectId': 'title_0',
                'text': title
            }
        }]
        
        # Create content slide
        requests.append({
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
                        'objectId': 'content_0'
                    }
                ]
            }
        })
        
        # Add content text
        requests.append({
            'insertText': {
                'objectId': 'content_0',
                'text': content
            }
        })
        
        # Execute the text insertion
        service.presentations().batchUpdate(
            presentationId=presentation_id,
            body={'requests': requests}
        ).execute()
        
        presentation_url = f'https://docs.google.com/presentation/d/{presentation_id}/edit'
        print(f'Created presentation: {presentation_url}')
        return presentation_url
        
    except HttpError as error:
        print(f'An error occurred: {error}')
        return None

if __name__ == '__main__':
    title = "Video Summary"
    content = """This is a test presentation.
    It demonstrates how to create slides with actual content.
    The content will be properly formatted on the slides."""
    
    url = create_simple_presentation(title, content)
    if url:
        print(f'Success! Open the presentation at: {url}')
