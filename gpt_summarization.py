import os
import logging
import openai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure OpenAI
openai.api_key = os.getenv('OPENAI_API_KEY')

def generate_title(text):
    """Generate a title for the given text using GPT."""
    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a professional content writer. Generate a concise, engaging title for the given text. The title should be 3-8 words and capture the main topic."},
                {"role": "user", "content": f"Generate a title for this text:\n\n{text[:1000]}"}  # Use first 1000 chars for context
            ],
            max_tokens=30,
            temperature=0.7
        )
        title = response.choices[0].message.content.strip().strip('"')
        logger.info(f"Generated title: {title}")
        return title
    except Exception as e:
        logger.error(f"Error generating title: {str(e)}")
        return "Video Summary"

def generate_summary(transcript, max_length=300):
    """
    Summarize a transcript using OpenAI's GPT model.
    """
    try:
        # First, generate a summary
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a professional content summarizer. Create a clear, concise summary that captures the main points and key ideas from the transcript."},
                {"role": "user", "content": f"Summarize this transcript:\n\n{transcript}"}
            ],
            max_tokens=max_length,
            temperature=0.7
        )
        summary = response.choices[0].message.content.strip()
        
        # Then, generate a title for the summary
        title = generate_title(summary)
        
        logger.info("Summary generated successfully")
        return {
            "title": title,
            "content": summary
        }
    except Exception as e:
        logger.error(f"Error generating summary: {str(e)}")
        return {
            "title": "Video Summary",
            "content": "Error generating summary."
        }
