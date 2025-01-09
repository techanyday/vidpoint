from youtube_downloader import download_audio
from transcription import transcribe_audio
from gpt_summarization import generate_summary_with_bart
from google_slides_generator import create_slides
import logging
import traceback

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def process_youtube_video(url):
    try:
        # Step 1: Download audio
        logger.info("Downloading audio from YouTube...")
        audio_file = download_audio(url)
        logger.info(f"Audio downloaded successfully to {audio_file}")

        # Step 2: Transcribe audio
        logger.info("Transcribing audio...")
        transcript = transcribe_audio(audio_file)
        logger.info("Transcription complete")

        # Step 3: Generate summary using BART
        logger.info("Generating summary with BART...")
        summary = generate_summary_with_bart(transcript)
        logger.info("Summary generated")

        # Step 4: Create Google Slides presentation
        logger.info("Creating Google Slides presentation...")
        try:
            presentation_url = create_slides("Video Summary", summary)
            logger.info(f"Presentation created: {presentation_url}")
        except Exception as e:
            logger.error(f"Error creating presentation: {str(e)}")
            logger.error(traceback.format_exc())
            presentation_url = None

        return {
            "transcript": transcript,
            "summary": summary,
            "presentation_url": presentation_url
        }
    except Exception as e:
        logger.error(f"Error processing video: {str(e)}")
        logger.error(traceback.format_exc())
        return {"error": str(e)}

if __name__ == "__main__":
    video_url = "https://youtu.be/75i0tiz49MA?si=F7S4YpI5X1cgrNro"
    result = process_youtube_video(video_url)
    print("\nResults:")
    if "error" in result:
        print(f"Error: {result['error']}")
    else:
        print("\nTranscript:")
        print(result["transcript"])
        print("\nSummary:")
        print(result["summary"])
        if result["presentation_url"]:
            print("\nPresentation URL:")
            print(result["presentation_url"])
        else:
            print("\nFailed to create presentation")
