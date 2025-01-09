import whisper
import os
import logging
from pydub import AudioSegment

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    Transcribes an audio file using OpenAI's Whisper model.
    
    Args:
        audio_file (str): Path to the audio file.
        
    Returns:
        str: Transcription text.
    """
    try:
        if not os.path.exists(audio_file):
            logger.error(f"Audio file not found: {audio_file}")
            return ""
            
        logger.info("Loading Whisper model...")
        model = whisper.load_model("base")
        
        logger.info(f"Transcribing {audio_file}...")
        result = model.transcribe(audio_file)
        
        if result and "text" in result:
            transcript = result["text"].strip()
            if not transcript:
                logger.error("Empty transcript generated")
                return ""
                
            logger.info(f"Transcription successful. Length: {len(transcript)} chars")
            logger.info(f"First 200 chars: {transcript[:200]}...")
            return transcript
        else:
            logger.error("No transcription text found in result")
            return ""
            
    except Exception as e:
        logger.error(f"Error transcribing audio: {str(e)}")
        return ""
