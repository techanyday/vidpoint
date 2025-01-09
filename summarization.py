from transformers import pipeline

def summarize_text(transcript):
    """
    Summarizes the transcription using Hugging Face's transformers.

    Args:
        transcript (str): The full transcription text.

    Returns:
        str: Summary text.
    """
    summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
    summary = summarizer(transcript, max_length=130, min_length=30, do_sample=False)
    return summary[0]['summary_text']
