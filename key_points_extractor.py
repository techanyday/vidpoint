import logging
import re
import nltk
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import stopwords
from collections import Counter

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global cache for checking sentence similarity
sentence_cache = set()

# Download required NLTK data
try:
    nltk.download('punkt', quiet=True)
    nltk.download('stopwords', quiet=True)
    nltk.download('punkt_tab', quiet=True)
    nltk.download('averaged_perceptron_tagger', quiet=True)
    logger.info("Successfully downloaded NLTK data")
except Exception as e:
    logger.error(f"Error downloading NLTK data: {e}")

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
        # Fix contractions and possessives
        contractions = {
            r"\bim\b": "I'm",
            r"\bIm\b": "I'm",
            r"\btheres\b": "there's",
            r"\bTheirs\b": "there's",
            r"\bwont\b": "won't",
            r"\bcant\b": "can't",
            r"\bdont\b": "don't",
            r"\bits\b": "it's",
            r"\blets\b": "let's",
            r"\bive\b": "I've",
            r"\byoull\b": "you'll",
            r"\byoure\b": "you're",
            r"\btheyre\b": "they're",
            r"\bweve\b": "we've",
            r"\btheyve\b": "they've",
            r"\bcouldnt\b": "couldn't",
            r"\bwouldnt\b": "wouldn't",
            r"\bshouldnt\b": "shouldn't",
            r"\bhasnt\b": "hasn't",
            r"\bhavent\b": "haven't",
            r"\bwasnt\b": "wasn't",
            r"\bwerent\b": "weren't"
        }
        
        for pattern, replacement in contractions.items():
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        
        # Remove filler phrases
        filler_phrases = [
            r"\b(um|uh|like|you know|basically|actually|literally|I mean)\b",
            r"\b(in this video|hey guys|hey fellow|subscribe|hit the like button)\b",
            r"\b(I'm going to|I am going to|let me show you|let's talk about)\b",
        ]
        
        for phrase in filler_phrases:
            text = re.sub(phrase, "", text, flags=re.IGNORECASE)
        
        # Clean up whitespace and punctuation
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'[^\w\s.,!?\'"-]', '', text)  # Keep apostrophes for contractions
        text = text.strip()
        
        # Ensure proper sentence structure
        if text:
            # Capitalize first letter
            text = text[0].upper() + text[1:] if len(text) > 1 else text.upper()
            
            # Add period if no ending punctuation
            if not text[-1] in '.!?':
                text += '.'
            
            # Fix spacing around punctuation
            text = re.sub(r'\s+([.,!?])', r'\1', text)
            text = re.sub(r'([.,!?])([^\s])', r'\1 \2', text)
        
        return text
        
    except Exception as e:
        logger.error(f"Error cleaning sentence: {str(e)}")
        return text

def get_sentence_score(sentence):
    """Score a sentence based on content value and structure."""
    try:
        # Keywords related to software development and business
        keywords = {
            'software': 2.0,
            'development': 1.5,
            'business': 1.5,
            'company': 1.5,
            'product': 1.5,
            'service': 1.5,
            'customer': 1.5,
            'market': 1.5,
            'solution': 1.5,
            'platform': 1.5,
            'technology': 1.5,
            'application': 1.5,
            'tool': 1.5,
            'feature': 1.5,
            'system': 1.5,
            'process': 1.5,
            'strategy': 1.5,
            'revenue': 2.0,
            'profit': 2.0,
            'cost': 1.5,
            'price': 1.5,
            'investment': 1.5,
            'growth': 1.5,
            'scale': 1.5,
            'white-label': 2.0,
            'startup': 2.0,
            'enterprise': 1.8,
        }
        
        # Action verbs get bonus points
        action_verbs = {
            'build': 1.2,
            'create': 1.2,
            'develop': 1.2,
            'implement': 1.2,
            'launch': 1.2,
            'start': 1.2,
            'grow': 1.2,
            'expand': 1.2,
            'improve': 1.2,
            'optimize': 1.2,
            'increase': 1.2,
            'reduce': 1.2,
            'generate': 1.2,
            'offer': 1.2,
            'provide': 1.2,
        }
        
        words = word_tokenize(sentence.lower())
        score = 0.0
        
        # Score based on keywords and verbs
        for word in words:
            if word in keywords:
                score += keywords[word]
            if word in action_verbs:
                score += action_verbs[word]
        
        # Bonus for sentences with proper structure
        if re.match(r'^[A-Z].*[.!?]$', sentence):  # Starts with capital, ends with punctuation
            score *= 1.1
        
        # Bonus for medium-length sentences (not too short, not too long)
        length = len(words)
        if 8 <= length <= 15:  # Sweet spot for sentence length
            score *= 1.2
        elif length > 15:  # Penalty for very long sentences
            score *= 0.8
        elif length < 5:  # Penalty for very short sentences
            score *= 0.6
        
        # Penalty for sentences that are likely introductory or concluding
        intro_patterns = [
            r'^\s*(hi|hello|hey|welcome|today)',
            r'in this video',
            r'subscribe|like|comment',
            r'thank you|thanks for watching',
        ]
        
        for pattern in intro_patterns:
            if re.search(pattern, sentence.lower()):
                score *= 0.3
        
        return score
        
    except Exception as e:
        logger.error(f"Error scoring sentence: {str(e)}")
        return 0.0

def extract_key_points(transcript, num_points=6):
    """Extract key points from a transcript."""
    try:
        global sentence_cache
        sentence_cache.clear()  # Clear cache for new extraction
        
        logger.info("Starting key points extraction")
        
        if not transcript or not isinstance(transcript, str):
            logger.error("Invalid transcript provided")
            return []
        
        # Clean the transcript
        transcript = clean_text(transcript)
        if not transcript:
            logger.error("Empty transcript after cleaning")
            return []
        
        # Split into sentences
        try:
            sentences = sent_tokenize(transcript)
        except Exception as e:
            logger.warning(f"NLTK tokenizer failed: {e}, falling back to simple split")
            sentences = [s.strip() for s in re.split(r'[.!?]+', transcript) if s.strip()]
        
        if not sentences:
            logger.error("No sentences found in transcript")
            return []
        
        # Clean and filter sentences
        cleaned_sentences = []
        for s in sentences:
            cleaned = clean_text(s)
            if cleaned and 5 <= len(cleaned.split()) <= 20:  # Initial length filter
                cleaned = clean_sentence(cleaned)
                if cleaned and 5 <= len(cleaned.split()) <= 15:  # Must be within final length limits
                    cleaned_sentences.append(cleaned)
        
        sentences = cleaned_sentences
        if not sentences:
            logger.error("No valid sentences after cleaning")
            return []
        
        # Get word frequencies (excluding stopwords)
        try:
            stop_words = set(stopwords.words('english'))
            # Add custom stopwords
            custom_stops = {
                'like', 'going', 'want', 'know', 'think', 'really', 'actually',
                'basically', 'literally', 'obviously', 'simply', 'just', 'right',
                'yeah', 'hey', 'okay', 'um', 'uh', 'well', 'so', 'guys', 'folks',
                'everybody', 'everyone', 'anybody', 'anyone', 'somebody', 'someone',
                'gonna', 'wanna', 'kinda', 'sorta', 'lemme', 'gimme', 'dunno',
                'gotta', 'imma', 'yall', 'yknow', 'ima', 'tryna'
            }
            stop_words.update(custom_stops)
        except Exception as e:
            logger.warning(f"Could not load stopwords: {e}, using empty set")
            stop_words = set()
        
        words = ' '.join(sentences).lower().split()
        words = [w for w in words if w not in stop_words and len(w) > 2]
        
        if not words:
            logger.error("No valid words found after filtering")
            return []
        
        word_freq = Counter(words)
        total_freq = sum(word_freq.values())
        
        # Score and select sentences
        scored_sentences = []
        for sentence in sentences:
            score = get_sentence_score(sentence)
            if score > 0:
                scored_sentences.append((sentence, score))
        
        if not scored_sentences:
            logger.error("No sentences scored above 0")
            return []
        
        # Sort by score and get top points
        scored_sentences.sort(key=lambda x: x[1], reverse=True)
        key_points = []
        
        for sentence, score in scored_sentences:
            if len(key_points) >= num_points:
                break
            
            # Final cleaning
            point = clean_sentence(sentence)
            if point and 5 <= len(point.split()) <= 15:  # Must meet length requirements
                if point not in sentence_cache:  # Check for duplicates
                    key_points.append(point)
                    sentence_cache.add(point)
                    logger.info(f"Added key point (score: {score:.4f}): {point}")
        
        if not key_points:
            logger.error("No key points found after scoring")
            return []
        
        logger.info(f"Successfully extracted {len(key_points)} key points")
        return key_points
        
    except Exception as e:
        logger.error(f"Error extracting key points: {str(e)}", exc_info=True)
        return []

def format_key_points(key_points):
    """Format key points for presentation slides."""
    try:
        if not key_points:
            return []
            
        # Group points into slides (5 points per slide)
        slides = []
        for i in range(0, len(key_points), 5):
            group = key_points[i:i+5]
            slides.append({
                'title': f'Key Points {i//5 + 1}',
                'content': [f'• {point}' for point in group]
            })
            
        return slides
        
    except Exception as e:
        logger.error(f"Error formatting key points: {str(e)}")
        return []

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
    for i, point in enumerate(points, 1):
        print(f"{i}. {point}")
