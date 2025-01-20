from flask import Flask, request, jsonify, render_template
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
from auth.routes import auth_blueprint  # Import directly from routes
from models.database import init_db, get_db
from datetime import timedelta
from jinja2 import FileSystemLoader

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
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

# Initialize Flask app with explicit template path
template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'templates'))
app = Flask(__name__, 
    template_folder=template_dir,
    static_folder='static'
)

# Register blueprints
app.register_blueprint(auth_blueprint)

# Enable debug mode for development
app.debug = True

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Log template directory and blueprint registration
logger.info(f"Template directory: {template_dir}")
logger.info(f"Template folder exists: {os.path.exists(template_dir)}")
logger.info(f"Base template exists: {os.path.exists(os.path.join(template_dir, 'base.html'))}")
logger.info("Registered auth blueprint with URL prefix: /auth")

# Generate a secure secret key if not provided
if not os.environ.get('SECRET_KEY'):
    import secrets
    generated_key = secrets.token_hex(32)
    logger.warning("SECRET_KEY not set in environment. Using generated key. "
                  "For production, please set a permanent SECRET_KEY in your environment variables.")
    app.config['SECRET_KEY'] = generated_key
else:
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')

# Configure MongoDB
mongodb_uri = os.environ.get('MONGODB_URI')
if not mongodb_uri:
    logger.error("MONGODB_URI environment variable not set")
    raise ValueError("MONGODB_URI environment variable is required")

# Validate MongoDB URI format
if not mongodb_uri.startswith('mongodb+srv://'):
    logger.error("Invalid MongoDB URI format. Must be a MongoDB Atlas URI starting with 'mongodb+srv://'")
    raise ValueError("Invalid MongoDB URI format")

app.config['MONGODB_URI'] = mongodb_uri
logger.info("MongoDB Atlas configuration loaded")

app.config['GOOGLE_CLIENT_ID'] = os.environ.get('GOOGLE_CLIENT_ID')
app.config['GOOGLE_CLIENT_SECRET'] = os.environ.get('GOOGLE_CLIENT_SECRET')

# Configure session
app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Configure CORS for Render deployment
CORS(app, resources={
    r"/*": {
        "origins": [
            "http://localhost:5000",
            "https://vidpoint.onrender.com"
        ],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "supports_credentials": True
    }
})

# Initialize database
try:
    logger.info("Initializing database connection to MongoDB Atlas...")
    init_db(app)
    logger.info("Database initialized successfully")
except Exception as e:
    logger.error(f"Error initializing database: {str(e)}")
    raise

# Configure Jinja2 to look for templates in the root templates directory
app.jinja_loader = FileSystemLoader([
    os.path.join(app.root_path, 'templates'),
    os.path.join(app.root_path, 'templates/auth')
])
logger.info(f"Template directories: {app.jinja_loader.searchpath}")

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

@app.route('/')
def index():
    """Render the main page."""
    # Get pricing plans from database or config
    pricing_plans = {
        'free': {
            'name': 'Free',
            'description': 'Perfect for getting started',
            'price': 0,
            'features': [
                '3 summaries per month',
                'Up to 200 tokens',
                'Word document export',
                'Basic support'
            ]
        },
        'starter': {
            'name': 'Starter',
            'description': 'Great for regular users',
            'price': 4.99,
            'features': [
                '50 summaries per month',
                'Up to 500 tokens',
                'Word document export',
                'Priority support',
                'Purchase additional credits'
            ]
        },
        'pro': {
            'name': 'Pro',
            'description': 'Best for power users',
            'price': 9.99,
            'features': [
                '1,000 summaries per month',
                'Up to 2,000 tokens',
                'Bulk processing',
                'Team accounts',
                'Premium support',
                'Purchase additional credits'
            ]
        }
    }
    return render_template('index.html', pricing_plans=pricing_plans)

@app.route("/", methods=["POST"])
def process_video():
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