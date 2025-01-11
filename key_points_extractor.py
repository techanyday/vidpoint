import logging
import os
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def clean_text(text):
    """Clean text for processing."""
    try:
        # Remove extra whitespace
        text = ' '.join(text.split())
        
        # Remove special characters but keep basic punctuation
        text = re.sub(r'[^\w\s.,!?-]', '', text)
        
        # Remove common filler words
        filler_words = ['basically', 'actually', 'literally', 'really', 'very', 'quite', 'simply', 'just', 'so', 'well']
        for word in filler_words:
            text = re.sub(rf'\b{word}\b', '', text, flags=re.IGNORECASE)
        
        # Clean up multiple spaces
        text = ' '.join(text.split())
        
        return text.strip()
    except Exception as e:
        logger.error(f"Error cleaning text: {str(e)}")
        return text

def shorten_sentence(sentence):
    """Aggressively shorten a sentence to make it more concise."""
    try:
        # Remove introductory phrases
        intros = [
            r'^(so|well|you see|you know|like|i mean|basically|actually)',
            r'^(what (im|i am) (saying|trying to say) is)',
            r'^(the (point|thing) is)',
            r'^(in other words)',
            r'^(as you can see)',
            r'^(as we know)',
        ]
        for intro in intros:
            sentence = re.sub(intro, '', sentence, flags=re.IGNORECASE).strip()
        
        # Remove redundant phrases
        redundant = [
            r'if you know what i mean',
            r'if you will',
            r'sort of',
            r'kind of',
            r'more or less',
            r'in my opinion',
            r'i think that',
            r'i believe that',
            r'you know',
            r'as you can see',
            r'what this means is',
            r'what im trying to say is',
            r'the thing is',
            r'the point is',
            r'going to',
            r'want to',
            r'trying to',
            r'in the future',
            r'at this point',
            r'at this time',
            r'for the most part',
            r'in terms of',
            r'when it comes to',
            r'the fact that',
            r'in order to',
            r'with respect to',
            r'with regard to',
            r'in relation to',
            r'in the process of',
            r'in the context of',
            r'in the case of',
            r'due to the fact that',
            r'for all intents and purposes',
            r'at the end of the day',
            r'that being said',
            r'needless to say',
            r'to be honest',
            r'to tell you the truth',
            r'as a matter of fact',
        ]
        for phrase in redundant:
            sentence = re.sub(phrase, '', sentence, flags=re.IGNORECASE).strip()
            
        # Replace common verbose phrases with shorter ones
        replacements = {
            r'in spite of': 'despite',
            r'take into account': 'consider',
            r'in the event that': 'if',
            r'in the near future': 'soon',
            r'at this point in time': 'now',
            r'due to': 'because',
            r'prior to': 'before',
            r'subsequent to': 'after',
            r'in addition': 'also',
            r'with the exception of': 'except',
            r'in order to': 'to',
            r'a large number of': 'many',
            r'a majority of': 'most',
            r'a small number of': 'few',
            r'in a situation where': 'when',
            r'make a decision': 'decide',
            r'at the present time': 'now',
            r'in the process of': '',
            r'on a regular basis': 'regularly',
            r'in a manner of speaking': '',
        }
        for verbose, concise in replacements.items():
            sentence = re.sub(verbose, concise, sentence, flags=re.IGNORECASE)
        
        # Remove unnecessary words
        unnecessary = [
            r'\breally\b',
            r'\bvery\b',
            r'\bquite\b',
            r'\bbasically\b',
            r'\bactually\b',
            r'\bliterally\b',
            r'\bsimply\b',
            r'\bjust\b',
            r'\blike\b',
            r'\btotally\b',
            r'\bdefinitely\b',
            r'\bprobably\b',
            r'\bmaybe\b',
            r'\bperhaps\b',
            r'\bsomewhat\b',
            r'\bsort of\b',
            r'\bkind of\b',
            r'\ba bit\b',
            r'\ba little\b',
            r'\bin my opinion\b',
            r'\bi think\b',
            r'\bi believe\b',
            r'\bi feel\b',
            r'\bseems to\b',
            r'\bappears to\b',
            r'\btends to\b',
        ]
        for word in unnecessary:
            sentence = re.sub(word, '', sentence, flags=re.IGNORECASE)
        
        # Clean up multiple spaces and punctuation
        sentence = ' '.join(sentence.split())
        sentence = re.sub(r'\s+([.,!?])', r'\1', sentence)
        sentence = re.sub(r'\.+', '.', sentence)
        
        # Extract main clause (try to get core message)
        clauses = re.split(r'[,;]', sentence)
        if clauses:
            main_clause = max(clauses, key=len).strip()
            if len(main_clause.split()) >= 5:  # Only use if substantial
                sentence = main_clause
        
        # Ensure proper capitalization and ending
        if sentence:
            sentence = sentence[0].upper() + sentence[1:]
            if not sentence.endswith(('.', '!', '?')):
                sentence += '.'
                
        # Final length check - if still too long, take first part
        words = sentence.split()
        if len(words) > 12:  # Maximum 12 words
            sentence = ' '.join(words[:12]) + '.'
            
        return sentence
        
    except Exception as e:
        logger.error(f"Error shortening sentence: {str(e)}")
        return sentence

def clean_sentence(text):
    """Clean and format a sentence for better readability."""
    try:
        if not text:
            return ""
            
        # Basic cleaning
        text = clean_text(text)
        if not text:
            return ""
            
        # Remove common filler phrases
        filler_phrases = [
            r'\byou know\b',
            r'\bi mean\b',
            r'\bkind of\b',
            r'\bsort of\b',
            r'\blike\b',
            r'\bbasically\b',
            r'\bactually\b',
            r'\bliterally\b',
            r'\breally\b',
            r'\bvery\b',
            r'\bquite\b',
            r'\bjust\b',
            r'\bso\b',
            r'\bwell\b',
            r'\bum\b',
            r'\buh\b'
        ]
        
        for phrase in filler_phrases:
            text = re.sub(phrase, '', text, flags=re.IGNORECASE)
        
        # Clean up multiple spaces
        text = ' '.join(text.split())
        
        # Capitalize first letter
        if text:
            text = text[0].upper() + text[1:]
            
        # Ensure proper ending punctuation
        if text and text[-1] not in '.!?':
            text += '.'
            
        # Remove duplicate punctuation
        text = re.sub(r'([.!?])\1+', r'\1', text)
        
        # Clean up spaces around punctuation
        text = re.sub(r'\s+([.!?,])', r'\1', text)
        
        return text.strip()
        
    except Exception as e:
        logger.error(f"Error cleaning sentence: {str(e)}")
        return text

def extract_key_points(transcript, num_points=6):
    """Extract key points from a transcript using GPT-3.5-turbo."""
    try:
        logger.info("Starting key points extraction")
        
        # Create the prompt with clear instructions
        system_prompt = """You are an expert at extracting key business insights and value propositions from text.
        Extract the most important business-focused key points from the given transcript.
        Focus on pricing, revenue, business models, and actionable insights.
        Format each point as a clear, concise statement.
        Do not include generic or filler statements.
        Each point should provide specific value or actionable information."""
        
        user_prompt = f"Extract {num_points} key business points from this transcript:\n\n{transcript}"
        
        # Call GPT-3.5-turbo
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_tokens=300
        )
        
        # Extract and clean the key points
        key_points_text = response.choices[0].message.content.strip()
        key_points = [point.strip('- ').strip() for point in key_points_text.split('\n') if point.strip()]
        
        # Take only the requested number of points
        key_points = key_points[:num_points]
        
        logger.info(f"Extracted {len(key_points)} key points")
        return key_points
        
    except Exception as e:
        logger.error(f"Error extracting key points: {str(e)}")
        return []

def generate_key_points_title(key_points):
    """Generate a title for the key points using GPT-3.5-turbo."""
    try:
        if not key_points:
            return "Key Business Insights"
            
        # Join key points into a single text
        points_text = "\n".join(f"- {point}" for point in key_points)
        
        # Create the prompt
        system_prompt = """You are an expert at creating concise, business-focused titles.
        Create a title that captures the main theme of these key points.
        The title should be 3-6 words and highlight the business value."""
        
        user_prompt = f"Create a title for these key points:\n\n{points_text}"
        
        # Call GPT-3.5-turbo
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_tokens=50
        )
        
        title = response.choices[0].message.content.strip().strip('"')
        return title
        
    except Exception as e:
        logger.error(f"Error generating key points title: {str(e)}")
        return "Key Business Insights"

def format_key_points(key_points):
    """Format key points for presentation."""
    try:
        if not key_points:
            return "No key points extracted."
            
        title = generate_key_points_title(key_points)
        formatted_points = [f"{i+1}. {point}" for i, point in enumerate(key_points)]
        
        return f"{title}\n" + "\n".join(formatted_points)
        
    except Exception as e:
        logger.error(f"Error formatting key points: {str(e)}")
        return "Error formatting key points."

if __name__ == '__main__':
    # Test the extractor
    test_transcript = """
    I want to be dead serious right now. I think that learning to code is on easy mode. 
    We have ChatGPT, we have YouTube tutorials, we have documentation that's better than ever.
    The resources available to learn programming are incredible.
    You can literally ask ChatGPT to explain any concept to you like you're five years old.
    The barrier to entry for programming has never been lower.
    There are more free resources than ever before.
    If you want to learn to code, there's nothing stopping you except yourself.
    """
    
    points = extract_key_points(test_transcript)
    print("\nExtracted Key Points:")
    print(generate_key_points_title(points))
    for i, point in enumerate(points, 1):
        print(f"{i}. {point}")
