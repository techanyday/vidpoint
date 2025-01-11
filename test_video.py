from youtube_downloader import download_audio
from transcription import transcribe_audio
from gpt_summarization import generate_summary
from key_points_extractor import extract_key_points
import logging
import traceback

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def process_youtube_video(url):
    """Process a YouTube video URL through the complete workflow."""
    try:
        # Download audio
        logger.info("Downloading audio from YouTube...")
        audio_file = download_audio(url)
        if not audio_file:
            return {"error": "Failed to download audio"}

        # Transcribe audio
        logger.info("\nTranscribing audio...")
        transcript = transcribe_audio(audio_file)
        if not transcript:
            return {"error": "Failed to transcribe audio"}
        
        # Generate transcript title
        transcript_title = "Video Transcript: " + transcript[:50].strip() + "..."

        # Generate summary
        logger.info("\nGenerating summary...")
        summary = generate_summary(transcript)
        if not summary:
            return {"error": "Failed to generate summary"}

        # Extract key points
        logger.info("\nExtracting key points...")
        key_points = extract_key_points(transcript)
        if not key_points:
            return {"error": "Failed to extract key points"}

        # Format results
        results = {
            "transcript": {
                "title": transcript_title,
                "content": transcript
            },
            "summary": summary,  # Already has title and content
            "key_points": key_points  # Already has title and points
        }

        logger.info("\nResults:\n")
        logger.info(f"\n{results['transcript']['title']}")
        logger.info(results['transcript']['content'])
        
        logger.info(f"\n{results['summary']['title']}")
        logger.info(results['summary']['content'])
        
        logger.info(f"\n{results['key_points']['title']}")
        for i, point in enumerate(results['key_points']['points'], 1):
            logger.info(f"{i}. {point}")

        return results

    except Exception as e:
        logger.error(f"Error processing video: {str(e)}")
        logger.error(traceback.format_exc())
        return {"error": str(e)}

if __name__ == "__main__":
    # Test with a short video first
    video_url = "https://youtu.be/75i0tiz49MA?si=F7S4YpI5X1cgrNro"
    result = process_youtube_video(video_url)
    print("\nResults:")
    if "error" in result:
        print(f"Error: {result['error']}")
    else:
        print("\nTranscript:")
        print(result["transcript"]["title"])
        print(result["transcript"]["content"])
        print("\nSummary:")
        print(result["summary"]["title"])
        print(result["summary"]["content"])
        print("\nKey Points:")
        print(result["key_points"]["title"])
        for i, point in enumerate(result["key_points"]["points"], 1):
            print(f"{i}. {point}")
