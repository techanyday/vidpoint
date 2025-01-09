from google_slides_generator import create_slides
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_slides_creation():
    try:
        title = "Test Presentation"
        summary = """This is a test summary for the Google Slides presentation.
        It will help us verify that the slides creation functionality is working properly.
        We'll use this to create a simple presentation with a few slides."""
        
        logger.info("Creating Google Slides presentation...")
        presentation_url = create_slides(title, summary)
        
        if presentation_url:
            logger.info(f"Success! Presentation created at: {presentation_url}")
            return presentation_url
        else:
            logger.error("Failed to create presentation")
            return None
            
    except Exception as e:
        logger.error(f"Error creating presentation: {str(e)}")
        raise e

if __name__ == "__main__":
    test_slides_creation()
