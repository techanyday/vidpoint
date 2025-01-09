import torch
from transformers import BartForConditionalGeneration, BartTokenizer

def generate_summary_with_bart(transcript, max_length=300):
    """
    Summarize a transcript using BART model from Hugging Face.
    """
    try:
        # Load model and tokenizer
        tokenizer = BartTokenizer.from_pretrained('facebook/bart-large-cnn')
        model = BartForConditionalGeneration.from_pretrained('facebook/bart-large-cnn')
        
        # Ensure model is on the same device as the input
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model = model.to(device)
        
        # Prepare the input text
        inputs = tokenizer.encode("summarize: " + transcript, 
                                return_tensors='pt',
                                max_length=1024,
                                truncation=True).to(device)
        
        # Generate summary
        summary_ids = model.generate(inputs,
                                   max_length=max_length,
                                   min_length=50,
                                   length_penalty=2.0,
                                   num_beams=4,
                                   early_stopping=True)
        
        summary = tokenizer.decode(summary_ids[0], skip_special_tokens=True)
        return summary
        
    except Exception as e:
        return f"Error during summarization: {str(e)}"
