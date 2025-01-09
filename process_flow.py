import os
import logging
from typing import Dict
from datetime import datetime
from video_downloader import download_video
from audio_extractor import extract_audio
from transcriber import transcribe_audio
from chatgpt_extractor import ChatGPTExtractor

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VideoProcessor:
    def __init__(self, api_key=None):
        """Initialize the video processor with optional API key."""
        self.api_key = api_key
        self.chatgpt = ChatGPTExtractor(api_key)
        
    def process_video(self, video_url: str, is_premium: bool = False) -> Dict:
        """
        Process a video URL to extract key insights.
        
        Args:
            video_url (str): URL of the video to process
            is_premium (bool): Whether this is a premium user request
            
        Returns:
            dict: Dictionary containing transcript, key points, summary, and titles
        """
        try:
            # Download video
            video_path = download_video(video_url)
            if not video_path:
                raise Exception("Failed to download video")
                
            # Extract audio
            audio_path = extract_audio(video_path)
            if not audio_path:
                raise Exception("Failed to extract audio")
                
            # Transcribe audio
            transcript = transcribe_audio(audio_path)
            if not transcript:
                raise Exception("Failed to transcribe audio")
                
            # Extract key points, titles, and get summary
            results = self.chatgpt.extract_key_points(transcript)
            if not results or "error" in results:
                raise Exception("Failed to analyze transcript")
            
            # Clean up temporary files
            self._cleanup_files(video_path, audio_path)
            
            # Return combined results
            return {
                "transcript": transcript,
                "key_points": results["key_points"],
                "summary": results["summary"],
                "titles": results["titles"]
            }
            
        except Exception as e:
            logger.error(f"Error processing video: {str(e)}")
            return {"error": str(e)}
            
    def _cleanup_files(self, video_path: str, audio_path: str):
        """Clean up temporary files."""
        try:
            if os.path.exists(video_path):
                os.remove(video_path)
            if os.path.exists(audio_path):
                os.remove(audio_path)
        except Exception as e:
            logger.error(f"Error cleaning up files: {str(e)}")
