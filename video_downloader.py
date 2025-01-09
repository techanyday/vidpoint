import os
import logging
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError

logger = logging.getLogger(__name__)

def download_video(video_url: str) -> str:
    """Download video from URL."""
    try:
        # Configure yt-dlp options
        ydl_opts = {
            'format': 'best[height<=720]',  # Download 720p or lower for faster processing
            'outtmpl': 'downloads/%(title)s.%(ext)s',  # Output template
            'quiet': False,  # Show download progress
            'no_warnings': False,  # Show warnings
            'extract_flat': False,
            'writethumbnail': False,
            'writesubtitles': False,
            'postprocessors': [],
        }
        
        # Create downloads directory if it doesn't exist
        os.makedirs('downloads', exist_ok=True)
        
        # Download the video
        with YoutubeDL(ydl_opts) as ydl:
            try:
                logger.info(f"Attempting to download video from URL: {video_url}")
                info = ydl.extract_info(video_url, download=True)
                video_path = ydl.prepare_filename(info)
                
                if os.path.exists(video_path):
                    logger.info(f"Successfully downloaded video to: {video_path}")
                    return video_path
                else:
                    logger.error(f"Video file not found after download: {video_path}")
                    return None
                    
            except DownloadError as de:
                logger.error(f"YouTube-DL download error: {str(de)}")
                return None
                
    except Exception as e:
        logger.error(f"Unexpected error downloading video: {str(e)}")
        return None
