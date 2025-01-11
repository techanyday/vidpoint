import os
from key_points_extractor import extract_key_points, generate_key_points_title, format_key_points
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_key_points_extraction():
    """Test the key points extraction with a sample transcript."""
    # Sample transcript with business content
    test_transcript = """
    Let me break down our pricing model and business strategy. We offer three tiers of service:
    The Basic tier starts at $49 per month, perfect for small businesses just getting started.
    Our Professional tier is $99 per month and includes advanced analytics and white-label options.
    For enterprise customers, we have a custom pricing model starting at $499 per month with dedicated support.
    
    What makes our solution unique is the ROI our customers see. On average, businesses save 40% on their operational costs
    in the first three months. We've seen some clients generate up to $50,000 in additional revenue through our platform.
    
    The implementation process is straightforward. We provide a full onboarding package, API documentation, and dedicated
    support to get you up and running in less than a week. Our white-label solution allows you to resell our platform
    under your own brand, creating an additional revenue stream.
    
    Looking at market trends, we're seeing a 200% year-over-year growth in demand for this type of solution. Our customer
    retention rate is 95%, and we're continuously adding new features based on customer feedback.
    """
    
    print("Testing key points extraction...")
    print("\nInput Transcript:")
    print(test_transcript)
    
    # Extract key points
    key_points = extract_key_points(test_transcript)
    
    # Generate title
    title = generate_key_points_title(key_points)
    
    # Format the results
    formatted_output = format_key_points(key_points)
    
    print("\nFormatted Output:")
    print(formatted_output)

if __name__ == "__main__":
    test_key_points_extraction()
