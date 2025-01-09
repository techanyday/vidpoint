import yt_dlp
import os
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def download_audio(video_url):
    """
    Downloads audio from a YouTube video.

    Args:
        video_url (str): URL of the YouTube video.

    Returns:
        str: Path to the downloaded audio file.
    """
    try:
        # Create downloads directory if it doesn't exist
        downloads_dir = "downloads"
        if not os.path.exists(downloads_dir):
            os.makedirs(downloads_dir)
            logger.info(f"Created downloads directory: {downloads_dir}")

        # Set output template
        output_template = os.path.join(downloads_dir, "%(id)s.%(ext)s")
        
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': output_template,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'verbose': True,
            'quiet': False,
            'no_warnings': False,
        }

        logger.info(f"Downloading audio from {video_url}")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Get video info first
            try:
                info = ydl.extract_info(video_url, download=False)
                video_id = info['id']
                logger.info(f"Video info extracted. ID: {video_id}")
            except Exception as e:
                logger.error(f"Error extracting video info: {str(e)}")
                raise

            # Download the video
            try:
                ydl.download([video_url])
                logger.info("Download completed successfully")
            except Exception as e:
                logger.error(f"Error downloading video: {str(e)}")
                raise

            # Get the output file path
            output_file = os.path.join(downloads_dir, f"{video_id}.mp3")
            
            if not os.path.exists(output_file):
                raise Exception(f"Output file not found: {output_file}")
                
            logger.info(f"Audio downloaded successfully to {output_file}")
            return output_file

    except Exception as e:
        logger.error(f"Error in download_audio: {str(e)}", exc_info=True)
        raise Exception(f"Failed to download audio: {str(e)}")
