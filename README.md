# VidPoint

VidPoint is a powerful web application that automatically generates summaries, key points, and transcripts from YouTube videos using AI technology.

## Features

- **Video Processing**: Extract information from YouTube videos using just the URL
- **AI-Powered Summaries**: Generate concise summaries using OpenAI's advanced language models
- **Key Points Extraction**: Automatically identify and list key points from the video
- **Transcript Generation**: Create accurate transcripts of video content
- **Export Options**: Export results to Word documents with professional formatting
- **User Management**: Multi-tier subscription system with different feature sets

## Pricing Plans

| Plan     | Price (USD) | Features                                                               |
|----------|-------------|------------------------------------------------------------------------|
| Free     | $0          | 3 summaries/month, up to 200 tokens, Word document export              |
| Starter  | $4.99/month | 50 summaries/month, up to 500 tokens, Word document export             |
| Pro      | $9.99/month | 1,000 summaries/month, up to 2,000 tokens, bulk processing, team accounts, Word document export |

### Additional Credits
- $5 for 500 extra summaries
- $10 for 1,000 extra summaries

## Tech Stack

- Backend: Python, Flask
- Frontend: HTML, CSS, JavaScript
- AI: OpenAI API
- Document Processing: python-docx
- Audio Processing: yt-dlp, pydub
- Authentication: PyJWT

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/vidpoint.git
cd vidpoint
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
Create a `.env` file in the root directory with:
```
OPENAI_API_KEY=your_openai_api_key
FLASK_SECRET_KEY=your_secret_key
```

5. Run the application:
```bash
python app.py
```

## Usage

1. Visit the application in your web browser
2. Enter a YouTube video URL
3. Wait for the AI to process the video
4. View the generated summary, key points, and transcript
5. Export the results to a Word document if needed

## Development

To contribute to VidPoint:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support, email support@vidpoint.com or open an issue on GitHub.
