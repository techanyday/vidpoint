import os
import logging
import ffmpeg

logger = logging.getLogger(__name__)

def extract_audio(video_path: str) -> str:
    """Extract audio from video file."""
    try:
        # Create audio directory if it doesn't exist
        os.makedirs('audio', exist_ok=True)
        
        # Generate output audio path
        audio_path = os.path.join('audio', os.path.splitext(os.path.basename(video_path))[0] + '.mp3')
        
        # Extract audio using ffmpeg
        stream = ffmpeg.input(video_path)
        stream = ffmpeg.output(stream, audio_path, acodec='libmp3lame', ac=2, ar='44100')
        ffmpeg.run(stream, capture_stdout=True, capture_stderr=True)
        
        return audio_path
        
    except Exception as e:
        logger.error(f"Error extracting audio: {str(e)}")
        return None
