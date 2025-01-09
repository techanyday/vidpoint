from transformers import pipeline
import re
from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np
import logging

def split_into_sentences(text):
    """Split text into sentences using regex"""
    text = text.strip()
    text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
    sentences = re.split(r'[.!?]+\s*', text)
    return [s.strip() for s in sentences if s.strip()]

def extract_key_points(transcript, num_points=5):
    """Extract key points using TF-IDF and position-based scoring"""
    try:
        # Split into sentences
        sentences = split_into_sentences(transcript)
        if len(sentences) < num_points:
            return sentences
        
        # Calculate TF-IDF scores
        vectorizer = TfidfVectorizer(stop_words='english')
        tfidf_matrix = vectorizer.fit_transform(sentences)
        importance_scores = np.array([sum(row) for row in tfidf_matrix.toarray()])
        
        # Calculate final scores
        final_scores = []
        for i, sentence in enumerate(sentences):
            # TF-IDF score
            tfidf_score = importance_scores[i]
            
            # Position score (favor sentences near the beginning and end)
            position_score = 1.0
            if i < len(sentences) * 0.2:  # First 20%
                position_score = 1.5
            elif i > len(sentences) * 0.8:  # Last 20%
                position_score = 1.2
            
            # Length penalty for very long sentences
            length_penalty = 1.0
            if len(sentence.split()) > 20:  # If sentence is longer than 20 words
                length_penalty = 0.8
            
            # Combine scores
            final_score = (0.7 * tfidf_score + 0.3 * position_score) * length_penalty
            final_scores.append((sentence, final_score))
        
        # Sort by score and get top points
        sorted_points = sorted(final_scores, key=lambda x: x[1], reverse=True)
        key_points = [point[0] for point in sorted_points[:num_points]]
        
        # Sort points by their original order in the transcript
        key_points.sort(key=lambda x: sentences.index(x))
        
        # Shorten and format points
        formatted_points = []
        for point in key_points:
            # Split into words and limit to first 15-20 words
            words = point.split()
            if len(words) > 15:
                shortened = ' '.join(words[:15]) + '...'
            else:
                shortened = point
            formatted_points.append(shortened)
        
        return formatted_points
    
    except Exception as e:
        logging.error(f"Error in extract_key_points: {e}")
        return []

def format_key_points(key_points):
    """Format key points for presentation slides"""
    slides_content = {
        'title': 'Video Key Points',
        'theme': {
            'presentationId': '1wGOmqUeqsi_9W5nEFC6-uPQkDgKDiW0PaQGhytXPDqE',  # Modern and clean theme
            'applyTo': 'ALL'
        },
        'slides': [
            {
                'title': 'Key Takeaways',
                'subtitle': 'Main points from the video',
                'layout': 'TITLE_AND_SUBTITLE'
            }
        ]
    }
    
    # Group points into slides (2 points per slide for better readability)
    current_points = []
    for i, point in enumerate(key_points):
        current_points.append(point)
        
        if len(current_points) == 2 or i == len(key_points) - 1:
            # Format points with bullet points and proper spacing
            content = '\n\n• ' + '\n\n• '.join(current_points)  # Add extra newlines for spacing
            slides_content['slides'].append({
                'title': 'Key Points',
                'content': content,
                'layout': 'TITLE_AND_BODY'
            })
            current_points = []
    
    return slides_content
