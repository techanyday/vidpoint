from youtube_downloader import download_audio
from transcription import transcribe_audio
from extract_points import extract_key_points, format_key_points
from minimal_slides import create_presentation
import logging
import os

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def process_youtube_video(url):
    """
    Complete workflow to process a YouTube video:
    1. Download audio from YouTube
    2. Transcribe the audio
    3. Extract key points from transcript
    4. Create a presentation
    """
    try:
        # Step 1: Download audio
        logger.info("Downloading audio from YouTube...")
        audio_file = download_audio(url)
        logger.info(f"Audio downloaded successfully to {audio_file}")

        # Step 2: Transcribe audio
        logger.info("Transcribing audio...")
        transcript = transcribe_audio(audio_file)
        logger.info("Transcription complete")

        # Step 3: Extract key points
        logger.info("Extracting key points from transcript...")
        key_points = extract_key_points(transcript)
        logger.info(f"Extracted {len(key_points)} key points")

        # Step 4: Format content for slides
        slides_content = format_key_points(key_points)

        # Step 5: Create Google Slides presentation
        logger.info("Creating Google Slides presentation...")
        presentation_url = create_presentation(slides_content)
        logger.info(f"Presentation created: {presentation_url}")

        return {
            "transcript": transcript,
            "key_points": key_points,
            "presentation_url": presentation_url
        }
    except Exception as e:
        logger.error(f"Error processing video: {str(e)}")
        return {"error": str(e)}

if __name__ == "__main__":
    # Example YouTube video URL
    video_url = "https://youtu.be/75i0tiz49MA?si=F7S4YpI5X1cgrNro"
    
    print("Starting video processing workflow...")
    result = process_youtube_video(video_url)
    
    if "error" in result:
        print(f"\nError: {result['error']}")
    else:
        print("\nWorkflow completed successfully!")
        print("\nTranscript (first 300 chars):")
        print(result["transcript"][:300] + "...")
        print("\nExtracted Key Points:")
        for i, point in enumerate(result["key_points"], 1):
            print(f"{i}. {point}")
        print("\nPresentation URL:")
        print(result["presentation_url"])
