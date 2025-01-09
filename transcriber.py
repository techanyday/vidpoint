import os
import logging
import whisper

logger = logging.getLogger(__name__)

def transcribe_audio(audio_path: str) -> str:
    """Transcribe audio using Whisper."""
    try:
        # Load Whisper model
        model = whisper.load_model("base")
        
        # Transcribe audio
        result = model.transcribe(audio_path)
        
        return result["text"]
        
    except Exception as e:
        logger.error(f"Error transcribing audio: {str(e)}")
        return None
