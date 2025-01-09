import subprocess
import os

def preprocess_audio(input_file, output_file="processed_audio.mp3"):
    """
    Preprocess audio for Whisper transcription.

    Args:
        input_file (str): Path to the input audio file.
        output_file (str): Path to save the processed audio file.

    Returns:
        str: Path to the processed audio file.
    """
    if not os.path.exists(input_file):
        raise FileNotFoundError(f"Input file '{input_file}' not found.")
    command = [
        "ffmpeg", "-i", input_file, "-ac", "1", "-ar", "16000", output_file
    ]
    subprocess.run(command, check=True)
    return output_file
