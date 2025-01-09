import json
from youtube_downloader import download_audio
from transcription import transcribe_audio
from key_points_extractor import extract_key_points, format_key_points
from pptx_creator import create_presentation
import logging
import os
from pymongo import MongoClient

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Connect to MongoDB
client = MongoClient()
db = client.vidpoint

def update_status(video_id, status, step=None, error=None, presentation_url=None):
    """Update processing status in MongoDB."""
    try:
        update_data = {"status": status}
        if step:
            update_data["step"] = step
        if error:
            update_data["error"] = error
        if presentation_url:
            update_data["presentation_url"] = presentation_url
        
        db.processing_status.update_one(
            {"video_id": video_id},
            {"$set": update_data}
        )
        logger.info(f"Updated status for video {video_id}: {status} {step or ''}")
    except Exception as e:
        logger.error(f"Error updating status: {str(e)}")

def process_youtube_video(url, video_id):
    """Complete workflow to process a YouTube video."""
    audio_file = None
    try:
        logger.info(f"Starting video processing for URL: {url}, Video ID: {video_id}")

        # Update MongoDB status
        update_status(video_id, "processing", "downloading")
        logger.info("Updated MongoDB status to downloading")

        # Step 1: Download audio
        try:
            logger.info(f"Downloading audio from YouTube for video {video_id}...")
            audio_file = download_audio(url)
            if not audio_file or not os.path.exists(audio_file):
                raise Exception("Audio file not found after download")
            logger.info(f"Audio downloaded successfully to {audio_file}")
        except Exception as e:
            error_msg = f"Failed to download audio: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)

        # Update status for transcription
        update_status(video_id, "processing", "transcribing")
        logger.info("Updated MongoDB status to transcribing")

        # Step 2: Transcribe audio
        try:
            logger.info(f"Transcribing audio file: {audio_file}")
            transcript = transcribe_audio(audio_file)
            
            # Validate transcript
            if not transcript:
                raise Exception("No transcript generated")
            if len(transcript.split()) < 10:  # At least 10 words
                raise Exception("Transcript too short")
                
            logger.info(f"Transcription completed. Length: {len(transcript)} chars")
            logger.info(f"Transcript preview: {transcript[:500]}...")
            
        except Exception as e:
            error_msg = f"Failed to transcribe audio: {str(e)}"
            logger.error(error_msg)
            update_status(video_id, "error", error=error_msg)
            raise Exception(error_msg)

        # Update status for key points extraction
        update_status(video_id, "processing", "extracting")
        logger.info("Updated MongoDB status to extracting")

        # Step 3: Extract key points
        try:
            logger.info("Extracting key points from transcript...")
            logger.info(f"Input transcript length: {len(transcript)} chars")
            
            # Split transcript into sentences for debugging
            sentences = transcript.split('.')
            logger.info(f"Found {len(sentences)} sentences in transcript")
            logger.info(f"First few sentences: {'. '.join(sentences[:3])}...")
            
            key_points = extract_key_points(transcript)
            
            if not key_points:
                raise Exception("No key points extracted from transcript")
            if len(key_points) < 3:  # At least 3 key points
                raise Exception(f"Too few key points extracted (got {len(key_points)})")
                
            logger.info(f"Successfully extracted {len(key_points)} key points")
            for i, point in enumerate(key_points, 1):
                logger.info(f"Key Point {i}: {point}")
                
        except Exception as e:
            error_msg = f"Failed to extract key points: {str(e)}"
            logger.error(error_msg)
            update_status(video_id, "error", error=error_msg)
            raise Exception(error_msg)

        # Format key points for slides
        formatted_points = []
        for i, point in enumerate(key_points):
            # Further clean and shorten if needed
            point = point.strip()
            if len(point.split()) > 10:  # Hard limit of 10 words per point
                point = ' '.join(point.split()[:10]) + '.'
            formatted_points.append(point)
            logger.info(f"Key Point {i+1}: {point}")

        # Update status for slides creation
        update_status(video_id, "processing", "creating_slides")
        logger.info("Updated MongoDB status to creating_slides")

        # Step 4: Create presentation
        try:
            logger.info("Creating PowerPoint presentation...")
            
            # Prepare slides content
            slides_content = [
                {
                    "title": "Key Takeaways",
                    "content": "Main Points from the Video",
                    "layout": "TITLE"
                }
            ]
            
            # Add key points slides (1 point per slide for maximum readability)
            for point in formatted_points:
                slides_content.append({
                    "title": "Key Point",
                    "content": [point],  # Single point per slide
                    "layout": "BULLET_POINTS"
                })
            
            logger.info(f"Created {len(slides_content)} slides")
            
            # Create the presentation
            presentation_path = create_presentation(
                slides_content,
                title=f"Video Summary - {video_id}"
            )
            
            if not presentation_path or not os.path.exists(presentation_path):
                raise Exception("Presentation file not created")
                
            # Convert to proper file URL
            presentation_url = f"file:///{os.path.abspath(presentation_path).replace(os.sep, '/')}"
            logger.info(f"Presentation created successfully at: {presentation_url}")
            
        except Exception as e:
            error_msg = f"Failed to create presentation: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)

        # Update status to completed
        update_status(
            video_id,
            "completed",
            presentation_url=presentation_url
        )
        logger.info("Updated MongoDB status to completed")
        
        # Clean up audio file
        try:
            if audio_file and os.path.exists(audio_file):
                os.remove(audio_file)
                logger.info(f"Cleaned up audio file: {audio_file}")
        except Exception as e:
            logger.warning(f"Error cleaning up audio file: {str(e)}")
        
        return presentation_url

    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error processing video: {error_msg}", exc_info=True)
        
        # Update status to error
        update_status(video_id, "error", error=error_msg)
        logger.info("Updated MongoDB status to error")
        
        # Clean up on error
        try:
            if audio_file and os.path.exists(audio_file):
                os.remove(audio_file)
                logger.info(f"Cleaned up audio file after error: {audio_file}")
        except Exception as cleanup_error:
            logger.warning(f"Error during cleanup: {str(cleanup_error)}")
        
        raise Exception(f"Failed to process video: {error_msg}")

if __name__ == "__main__":
    # Example YouTube video URL
    video_url = "https://youtu.be/75i0tiz49MA?si=F7S4YpI5X1cgrNro"
    video_id = "75i0tiz49MA"
    
    result = process_youtube_video(video_url, video_id)
    if "error" in result:
        print(f"\nError: {result['error']}")
    else:
        print("\nProcessing completed successfully!")
        print(f"Presentation URL: {result}")
