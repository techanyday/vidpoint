from flask import Flask, request, jsonify, send_file, render_template, session, redirect, url_for
from process_flow import VideoProcessor
from document_exporter import export_to_word, export_to_pdf
from models.database import Database, init_db, get_db
from models.user import User
from config.pricing import PRICING_PLANS, CREDIT_PACKAGES
from config import SQUARE_CONFIG, FLASK_CONFIG, validate_config
from auth import auth
from routes.dashboard import bp as dashboard_bp
from routes.payments import bp as payments_bp
from routes.test_email import bp as test_email_bp
from routes.webhooks import bp as webhooks_bp
import os
import logging
from datetime import datetime, timedelta
from functools import wraps
from jinja2 import FileSystemLoader

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app with explicit template path
template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'templates'))
app = Flask(__name__, 
    template_folder=template_dir,
    static_folder='static'
)

# Register blueprints
app.register_blueprint(auth)
app.register_blueprint(dashboard_bp)
app.register_blueprint(payments_bp)
app.register_blueprint(test_email_bp)
app.register_blueprint(webhooks_bp)

# Enable debug mode for development
app.debug = True

# Log template directory and blueprint registration
logger.info(f"Template directory: {template_dir}")
logger.info(f"Template folder exists: {os.path.exists(template_dir)}")
logger.info(f"Base template exists: {os.path.exists(os.path.join(template_dir, 'base.html'))}")

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

# Initialize database
try:
    init_db(app)
    logger.info("Database initialized successfully")
except Exception as e:
    logger.error(f"Error initializing database: {str(e)}")
    raise

@app.context_processor
def inject_user():
    """Inject user data into templates."""
    if 'user_id' in session:
        db = Database()
        user = db.get_user_by_id(session['user_id'])
        if user:
            return {
                'current_user': {
                    'is_authenticated': True,
                    'name': user.get('name'),
                    'email': user.get('email'),
                    'picture': user.get('picture', 'https://www.gravatar.com/avatar/00000000000000000000000000000000?d=mp&f=y'),
                    'subscription': user.get('subscription', {})
                }
            }
    return {
        'current_user': {
            'is_authenticated': False,
            'name': None,
            'email': None,
            'picture': None,
            'subscription': None
        }
    }

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

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

@app.route('/process-video', methods=['POST'])
@login_required
def process_video():
    """Process a video URL."""
    try:
        data = request.get_json()
        video_url = data.get('video_url')
        format_type = data.get('format_type', 'slides')  # Default to slides
        
        if not video_url:
            return jsonify({"error": "Video URL required"}), 400
            
        # Get user from session
        user = Database().get_user_by_id(session['user_id'])
        if not user:
            return jsonify({"error": "User not found"}), 404
            
        # Check if user has enough credits
        if user.get('subscription', {}).get('credits', 0) < 1:
            return jsonify({"error": "Insufficient credits"}), 403
            
        # Process video
        result = VideoProcessor(os.getenv("OPENAI_API_KEY")).process_video(video_url, format_type)
        
        # Deduct credit
        Database().update_user_credits(user['_id'], -1)
        
        # Save processing history
        Database().save_processing_history(
            user_id=user['_id'],
            video_url=video_url,
            format_type=format_type,
            result=result,
            processed_at=datetime.now()
        )
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error processing video: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/export', methods=['POST'])
@login_required
def export_content():
    """Export content to a document."""
    try:
        data = request.get_json()
        content = data.get('content')
        format_type = data.get('format_type', 'docx')
        
        if not content:
            return jsonify({"error": "Content required"}), 400
            
        if format_type == 'docx':
            file_path = export_to_word(content)
        elif format_type == 'pdf':
            file_path = export_to_pdf(content)
        else:
            return jsonify({"error": "Invalid format type"}), 400
            
        return send_file(file_path, as_attachment=True)
        
    except Exception as e:
        logger.error(f"Error exporting content: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=10000)
