from flask import Flask, request, jsonify
from flask_cors import CORS
import whisper
from pydub import AudioSegment
import torch
from transformers import T5ForConditionalGeneration,T5Tokenizer
import torch
import os
import urllib
import pymongo
import platform
import logging
import json
from process_video import process_youtube_video
from bson import json_util
import threading
import re
import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
logger.info(f"Using device: {device}")

try:
    models = T5ForConditionalGeneration.from_pretrained("Michau/t5-base-en-generate-headline")
    tokenizer = T5Tokenizer.from_pretrained("Michau/t5-base-en-generate-headline")
    models = models.to(device)
    model = whisper.load_model("base")
    logger.info("Models loaded successfully")
except Exception as e:
    logger.error(f"Error loading models: {str(e)}")

try:
    client = pymongo.MongoClient("mongodb://localhost:27017/")
    db = client.vidpoint
    # Test the connection
    client.server_info()
    logger.info("MongoDB connected successfully")
except Exception as e:
    logger.error(f"MongoDB connection error: {str(e)}")

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

def mongo_to_json(obj):
    """Convert MongoDB object to JSON serializable format."""
    if obj is None:
        return None
    try:
        return json.loads(json_util.dumps(obj))
    except Exception as e:
        logger.error(f"Error converting MongoDB object to JSON: {str(e)}")
        return None

def audioToText(audio):
    try:
        audio = whisper.load_audio(audio)
        audio = whisper.pad_or_trim(audio)
        mel = whisper.log_mel_spectrogram(audio).to(model.device)
        _, probs = model.detect_language(mel)
        options = whisper.DecodingOptions(fp16 = False)
        result = whisper.decode(model, mel, options)
        return result.text
    except Exception as e:
        logger.error(f"Error in audioToText: {str(e)}")
        return None

def youtubeToAudioSegments(url):
    try:
        if os.path.exists("audio.mp3"):
            os.remove("audio.mp3")
        os.system("youtube-dl "+"--write-thumbnail "+"--skip-download "+url + " -o logo")
        os.system("yt-dlp -f 140 -o audio.mp3 " + url)
        while not os.path.exists("audio.mp3"):
            continue
        
        if os.path.exists("segments"):
            if platform.system() == "Windows":
                os.system("rmdir /s /q segments")
            else:
                os.system("rm -rf segments")
        
        audio = AudioSegment.from_file("audio.mp3")
        segment_length = 50 * 1000
        
        if not os.path.exists("segments"):
            os.makedirs("segments")
        
        for i, segment in enumerate(audio[::segment_length]):
            segment.export(f"segments/{i}.mp3", format="mp3")
    except Exception as e:
        logger.error(f"Error in youtubeToAudioSegments: {str(e)}")

def generateHeadLine(text):
    try:
        ext =  "headline: " + text
        max_len = 256
        encoding = tokenizer.encode_plus(text, return_tensors = "pt")
        input_ids = encoding["input_ids"].to(device)
        attention_masks = encoding["attention_mask"].to(device)
        beam_outputs = models.generate(
            input_ids = input_ids,
            attention_mask = attention_masks,
            max_length = 64,
            num_beams = 3,
            early_stopping = True,
        )
        results = tokenizer.decode(beam_outputs[0])
        return results
    except Exception as e:
        logger.error(f"Error in generateHeadLine: {str(e)}")
        return None

def getDataForWeb(video_id, url):
    try:
        dataForWeb = {}   
        if  video_id not in db.list_collection_names():
            youtubeToAudioSegments(url) 
            for i  in range(len(os.listdir("segments"))):
                orginal_text = audioToText("segments/"+str(i)+".mp3")
                dataForWeb[i] = {
                    "heading" : generateHeadLine(orginal_text),
                    "text" :  orginal_text
                }
                try:
                    db[video_id].insert_one(dataForWeb[i])
                except: 
                    logger.error("Error in inserting data in database")
        else:
            j = 0
            for i in db[video_id].find({}, {"_id":0}):
                dataForWeb[j] = {
                    "heading" : i["heading"],
                    "text" : i["text"]
                }
                j += 1    
        return dataForWeb
    except Exception as e:
        logger.error(f"Error in getDataForWeb: {str(e)}")
        return None

def is_valid_youtube_url(url):
    """Validate if the URL is a valid YouTube URL."""
    try:
        # Common YouTube URL patterns
        patterns = [
            r'^https?://(?:www\.)?youtube\.com/watch\?v=[\w-]+',
            r'^https?://(?:www\.)?youtube\.com/v/[\w-]+',
            r'^https?://youtu\.be/[\w-]+',
            r'^https?://(?:www\.)?youtube\.com/embed/[\w-]+',
            r'^https?://(?:www\.)?youtube\.com/shorts/[\w-]+'
        ]
        return any(re.match(pattern, url) for pattern in patterns)
    except Exception as e:
        logger.error(f"Error validating YouTube URL: {str(e)}")
        return False

def extract_video_id(url):
    """Extract video ID from various YouTube URL formats."""
    try:
        # Try different URL patterns
        if 'youtube.com/watch?v=' in url:
            return url.split('watch?v=')[1].split('&')[0]
        elif 'youtu.be/' in url:
            return url.split('youtu.be/')[1].split('?')[0]
        elif 'youtube.com/v/' in url:
            return url.split('youtube.com/v/')[1].split('?')[0]
        elif 'youtube.com/embed/' in url:
            return url.split('youtube.com/embed/')[1].split('?')[0]
        elif 'youtube.com/shorts/' in url:
            return url.split('youtube.com/shorts/')[1].split('?')[0]
        else:
            raise ValueError("Invalid YouTube URL format")
    except Exception as e:
        logger.error(f"Error extracting video ID: {str(e)}")
        raise ValueError("Could not extract video ID from URL")

@app.route("/status/<video_id>", methods=["GET"])
def get_status(video_id):
    """Get the processing status for a video."""
    try:
        # Check MongoDB for status
        status = db.processing_status.find_one({"video_id": video_id})
        if not status:
            return jsonify({"status": "not_found"}), 404
            
        json_status = mongo_to_json(status)
        if not json_status:
            return jsonify({"error": "Error converting status to JSON"}), 500
            
        return jsonify(json_status)
    except Exception as e:
        logger.error(f"Error getting status: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/", methods=["GET", "POST"])
def process_video():
    if request.method == "GET":
        return """
        <html>
            <head>
                <title>VidPoint</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 40px; background-color: #f5f5f5; }
                    .container { max-width: 800px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
                    input[type="text"] { width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ddd; border-radius: 4px; }
                    button { padding: 10px 20px; background: #007bff; color: white; border: none; cursor: pointer; border-radius: 4px; }
                    button:hover { background: #0056b3; }
                    #result { margin-top: 20px; white-space: pre-wrap; }
                    .loading { display: none; margin: 20px 0; text-align: center; }
                    .progress { display: none; margin: 20px 0; }
                    .progress-bar { width: 100%; height: 20px; background-color: #f0f0f0; border-radius: 10px; overflow: hidden; }
                    .progress-bar-fill { width: 0%; height: 100%; background-color: #007bff; transition: width 0.5s ease-in-out; }
                    .status-text { text-align: center; margin-top: 10px; }
                    h1 { color: #333; text-align: center; }
                    .error { color: #dc3545; margin-top: 10px; }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>VidPoint</h1>
                    <p>Enter a YouTube URL to process:</p>
                    <input type="text" id="url" placeholder="Enter YouTube URL (e.g., https://www.youtube.com/watch?v=...)">
                    <button onclick="processVideo()">Process Video</button>
                    <div class="loading" id="loading">Processing video...</div>
                    <div class="progress" id="progress">
                        <div class="progress-bar">
                            <div class="progress-bar-fill" id="progress-bar-fill"></div>
                        </div>
                        <div class="status-text" id="status-text">Initializing...</div>
                    </div>
                    <div id="result"></div>
                </div>
                <script>
                    let statusCheckInterval;
                    
                    function validateYouTubeUrl(url) {
                        const patterns = [
                            /^https?:\/\/(?:www\.)?youtube\.com\/watch\?v=[\w-]+/,
                            /^https?:\/\/(?:www\.)?youtube\.com\/v\/[\w-]+/,
                            /^https?:\/\/youtu\.be\/[\w-]+/
                        ];
                        return patterns.some(pattern => pattern.test(url));
                    }
                    
                    function checkStatus(videoId) {
                        fetch(`/status/${videoId}`)
                        .then(response => response.json())
                        .then(data => {
                            const progress = document.getElementById('progress');
                            const progressBarFill = document.getElementById('progress-bar-fill');
                            const statusText = document.getElementById('status-text');
                            const result = document.getElementById('result');
                            
                            if (data.error) {
                                clearInterval(statusCheckInterval);
                                progress.style.display = 'block';
                                statusText.textContent = `Error: ${data.error}`;
                                statusText.className = 'status-text error';
                            } else if (data.status === 'completed') {
                                clearInterval(statusCheckInterval);
                                progress.style.display = 'block';
                                progressBarFill.style.width = '100%';
                                statusText.textContent = 'Processing complete!';
                                if (data.presentation_url) {
                                    result.innerHTML = `<p>View your presentation: <a href="${data.presentation_url}" target="_blank">${data.presentation_url}</a></p>`;
                                }
                            } else if (data.status === 'error') {
                                clearInterval(statusCheckInterval);
                                progress.style.display = 'block';
                                statusText.textContent = data.error || 'An error occurred';
                                statusText.className = 'status-text error';
                            } else if (data.status === 'processing') {
                                progress.style.display = 'block';
                                let step = data.step || 'processing';
                                let stepProgress = {
                                    'starting': 10,
                                    'downloading': 30,
                                    'transcribing': 50,
                                    'extracting': 70,
                                    'creating_slides': 90
                                };
                                progressBarFill.style.width = `${stepProgress[step] || 0}%`;
                                statusText.textContent = `Status: ${step.replace('_', ' ')}...`;
                            }
                        })
                        .catch(error => {
                            console.error('Error:', error);
                            const statusText = document.getElementById('status-text');
                            statusText.textContent = 'Error checking status';
                            statusText.className = 'status-text error';
                        });
                    }
                    
                    function processVideo() {
                        const url = document.getElementById('url').value.trim();
                        const loading = document.getElementById('loading');
                        const progress = document.getElementById('progress');
                        const statusText = document.getElementById('status-text');
                        const result = document.getElementById('result');
                        
                        // Reset UI
                        result.innerHTML = '';
                        clearInterval(statusCheckInterval);
                        
                        if (!url) {
                            statusText.textContent = 'Please enter a YouTube URL';
                            statusText.className = 'status-text error';
                            return;
                        }
                        
                        if (!validateYouTubeUrl(url)) {
                            statusText.textContent = 'Please enter a valid YouTube URL';
                            statusText.className = 'status-text error';
                            return;
                        }
                        
                        loading.style.display = 'block';
                        progress.style.display = 'block';
                        statusText.textContent = 'Starting...';
                        statusText.className = 'status-text';

                        fetch('/', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                            },
                            body: JSON.stringify({url: url}),
                        })
                        .then(response => {
                            if (!response.ok) {
                                return response.json().then(data => {
                                    throw new Error(data.error || `HTTP error! status: ${response.status}`);
                                });
                            }
                            return response.json();
                        })
                        .then(data => {
                            loading.style.display = 'none';
                            if (data.error) {
                                statusText.textContent = `Error: ${data.error}`;
                                statusText.className = 'status-text error';
                            } else if (data.video_id) {
                                statusText.className = 'status-text';
                                statusCheckInterval = setInterval(() => checkStatus(data.video_id), 2000);
                            } else {
                                throw new Error('Invalid response from server');
                            }
                        })
                        .catch((error) => {
                            loading.style.display = 'none';
                            console.error('Error:', error);
                            statusText.textContent = error.message || 'Error processing video';
                            statusText.className = 'status-text error';
                        });
                    }
                </script>
            </body>
        </html>
        """
    
    if request.method == "POST":
        try:
            # Get and validate request data
            if not request.is_json:
                logger.error("Invalid request: not JSON")
                return jsonify({'error': 'Invalid request format'}), 400

            data = request.get_json()
            if not data:
                logger.error("Invalid request: no data")
                return jsonify({'error': 'Invalid request data'}), 400

            url = data.get("url")
            if not url:
                logger.error("No video URL provided")
                return jsonify({'error': 'No video URL provided'}), 400

            logger.info(f"Processing video URL: {url}")

            # Validate YouTube URL
            if not is_valid_youtube_url(url):
                logger.error(f"Invalid YouTube URL: {url}")
                return jsonify({'error': 'Invalid YouTube URL'}), 400

            # Extract video ID
            try:
                video_id = extract_video_id(url)
                if not video_id:
                    logger.error(f"Could not extract video ID from URL: {url}")
                    return jsonify({'error': 'Invalid YouTube URL format'}), 400
                logger.info(f"Extracted video ID: {video_id}")
            except Exception as e:
                logger.error(f"Error extracting video ID: {str(e)}")
                return jsonify({'error': 'Invalid YouTube URL format'}), 400

            # Check existing status
            try:
                existing_status = db.processing_status.find_one({"video_id": video_id})
                if existing_status:
                    if existing_status.get('status') == 'completed':
                        logger.info(f"Video {video_id} already processed")
                        return jsonify({
                            'status': 'completed',
                            'video_id': video_id,
                            'presentation_url': existing_status.get('presentation_url')
                        })
                    elif existing_status.get('status') == 'processing':
                        logger.info(f"Video {video_id} is already being processed")
                        return jsonify({
                            'status': 'processing',
                            'video_id': video_id,
                            'step': existing_status.get('step', 'starting')
                        })
            except Exception as e:
                logger.error(f"Error checking existing status: {str(e)}")
                return jsonify({'error': 'Database error'}), 500

            # Initialize processing status
            try:
                db.processing_status.update_one(
                    {"video_id": video_id},
                    {
                        "$set": {
                            "status": "processing",
                            "step": "starting",
                            "error": None,
                            "start_time": datetime.datetime.utcnow()
                        }
                    },
                    upsert=True
                )
                logger.info(f"Initialized processing status for video {video_id}")
            except Exception as e:
                logger.error(f"Error initializing status: {str(e)}")
                return jsonify({'error': 'Database error'}), 500

            # Start processing thread
            try:
                thread = threading.Thread(target=process_youtube_video, args=(url, video_id))
                thread.daemon = True
                thread.start()
                logger.info(f"Started processing thread for video {video_id}")
            except Exception as e:
                logger.error(f"Error starting processing thread: {str(e)}")
                return jsonify({'error': 'Failed to start processing'}), 500

            return jsonify({
                'status': 'processing',
                'video_id': video_id,
                'step': 'starting'
            })

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Unexpected error in process_video: {error_msg}", exc_info=True)
            return jsonify({'error': 'Internal server error'}), 500

@app.route("/getData", methods=["GET", "POST"])
def helloWorld():
    try:
        url = request.args.get('url')
        video_id = ""
        try:
            video_id = url.split("=")[1]
        except:
            video_id = url.split("/")[-1] 
            
        duration = os.popen("youtube-dl --get-duration " + url).read().strip()
        title = os.popen("youtube-dl --get-title " + url).read().strip()
        print(duration, title)
        dataForWeb = {}
        dataToStore = {}
        dataToStore["duration"] = str(duration)
        dataToStore["title"] = str(title)

        dataForWeb = getDataForWeb(video_id, url)
        if dataForWeb is None:
            return jsonify({"error": "Failed to retrieve data"}), 500
        
        dataToStore["data"] = dataForWeb
        return jsonify(dataToStore)
    except Exception as e:
        logger.error(f"Error in helloWorld: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    try:
        logger.info("Starting Flask server...")
        app.run(debug=True, host='0.0.0.0', port=5000)
    except Exception as e:
        logger.error(f"Failed to start server: {str(e)}")