import os
import logging
from pydub import AudioSegment
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def convert_to_wav(input_file, output_file):
    """Convert audio file to WAV format."""
    try:
        logger.info(f"Converting {input_file} to WAV format...")
        audio = AudioSegment.from_file(input_file)
        audio.export(output_file, format="wav")
        logger.info("Audio conversion successful")
        return True
    except Exception as e:
        logger.error(f"Error converting audio: {e}")
        return False

def transcribe_audio(audio_file):
    """
    Transcribes an audio file using OpenAI's Whisper API.
    
    Args:
        audio_file (str): Path to the audio file.
        
    Returns:
        str: Transcription text.
    """
    try:
        if not os.path.exists(audio_file):
            logger.error(f"Audio file not found: {audio_file}")
            return ""
            
        logger.info(f"Transcribing {audio_file}...")
        
        with open(audio_file, "rb") as audio:
            response = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio,
                response_format="text"
            )
            
        if response:
            transcript = str(response)  # Convert response to string
            transcript = transcript.strip()
            if not transcript:
                logger.error("Empty transcript generated")
                return ""
                
            logger.info(f"Transcription successful. Length: {len(transcript)} chars")
            logger.info(f"First 200 chars: {transcript[:200]}...")
            return transcript
            
        logger.error("No text found in transcription result")
        return ""
        
    except Exception as e:
        logger.error(f"Error transcribing audio: {e}")
        return ""
