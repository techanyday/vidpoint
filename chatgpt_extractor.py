import openai
import logging
import os
from typing import List, Dict

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ChatGPTExtractor:
    def __init__(self, api_key: str = None):
        """Initialize the ChatGPT extractor with API key."""
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key is required")
        
        self.client = openai.OpenAI(api_key=self.api_key)
        
    def generate_title(self, text: str, content_type: str) -> str:
        """Generate an engaging title for the content."""
        try:
            # Prepare the prompt based on content type
            if content_type == "transcript":
                prompt = f"""Generate a short, engaging title for this video transcript.
                Make it descriptive but concise (max 60 characters).
                The title should reflect the main topic or theme.
                
                Transcript excerpt (first 500 chars):
                {text[:500]}..."""
            elif content_type == "key_points":
                prompt = f"""Generate a short, engaging title for these key points.
                Make it descriptive but concise (max 60 characters).
                The title should reflect the main insights.
                
                Key Points:
                {text}"""
            else:  # summary
                prompt = f"""Generate a short, engaging title for this summary.
                Make it descriptive but concise (max 60 characters).
                The title should capture the main message.
                
                Summary:
                {text}"""
            
            # Call ChatGPT API
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a professional content writer that creates engaging, concise titles."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=60
            )
            
            # Extract and clean title
            title = response.choices[0].message.content.strip()
            # Remove quotes if present
            title = title.strip('"\'')
            # Truncate if too long
            title = title[:60] + '...' if len(title) > 60 else title
            
            return title
            
        except Exception as e:
            logger.error(f"Error generating title: {str(e)}")
            return f"Video {content_type.title()}"
        
    def extract_key_points(self, transcript: str, max_points: int = 6) -> Dict:
        """Extract key points from transcript using ChatGPT."""
        try:
            # Prepare the prompt
            prompt = f"""Extract the {max_points} most important key points from this video transcript. 
            Focus on actionable insights and main concepts. Format each point as a clear, concise sentence.
            Make sure each point is unique and provides valuable information.
            Return ONLY bullet points, one per line, starting with a hyphen (-).
            
            Transcript:
            {transcript}"""
            
            # Call ChatGPT API
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a professional content analyzer that extracts key points from video transcripts. Format all points as bullet points starting with a hyphen (-)"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                max_tokens=500
            )
            
            # Extract key points from response
            content = response.choices[0].message.content
            key_points = [point.strip('- ').strip() for point in content.split('\n') if point.strip().startswith('-')]
            
            # Ensure we have a valid list of points
            if not key_points:
                return {
                    "key_points": ["No key points could be extracted"],
                    "summary": "Failed to extract key points from transcript.",
                    "titles": {
                        "transcript": "Video Transcript",
                        "key_points": "Key Points",
                        "summary": "Video Summary"
                    }
                }
            
            # Generate summary
            summary = self.generate_summary(transcript)
            
            # Generate titles
            transcript_title = self.generate_title(transcript, "transcript")
            key_points_title = self.generate_title("\n".join(key_points), "key_points")
            summary_title = self.generate_title(summary, "summary")
            
            return {
                "key_points": key_points[:max_points],
                "summary": summary,
                "titles": {
                    "transcript": transcript_title,
                    "key_points": key_points_title,
                    "summary": summary_title
                }
            }
            
        except Exception as e:
            logger.error(f"Error extracting key points: {str(e)}")
            return {
                "key_points": ["Error extracting key points"],
                "summary": "Error processing transcript",
                "titles": {
                    "transcript": "Video Transcript",
                    "key_points": "Key Points",
                    "summary": "Video Summary"
                }
            }
    
    def generate_summary(self, transcript: str, max_length: int = 250) -> str:
        """Generate a concise summary of the transcript."""
        try:
            # Prepare the prompt
            prompt = f"""Generate a concise summary of this video transcript in about {max_length} characters.
            Focus on the main message and key takeaways. Keep it clear and engaging.
            
            Transcript:
            {transcript}"""
            
            # Call ChatGPT API
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a professional content summarizer that creates concise, engaging summaries."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                max_tokens=200
            )
            
            # Extract summary from response
            summary = response.choices[0].message.content.strip()
            
            return summary
            
        except Exception as e:
            logger.error(f"Error generating summary: {str(e)}")
            return "Failed to generate summary."
    
    def get_token_count(self, text: str) -> int:
        """Estimate the number of tokens in the text."""
        # Rough estimation: 1 token ≈ 4 characters
        return len(text) // 4
    
    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate the approximate cost of API call."""
        input_cost = (input_tokens / 1000) * 0.001  # $0.001 per 1K tokens
        output_cost = (output_tokens / 1000) * 0.002  # $0.002 per 1K tokens
        return input_cost + output_cost
