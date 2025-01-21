from flask import Flask, request, jsonify, send_file, render_template, session, redirect, url_for
# Temporarily comment out video processing imports
# from process_flow import VideoProcessor
# from document_exporter import export_to_word, export_to_pdf
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
import secrets

# Allow OAuth over HTTP for local development
if os.environ.get('FLASK_ENV') == 'development':
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Enable OAuth logging
logging.getLogger('oauthlib').setLevel(logging.DEBUG)
logging.getLogger('google_auth_oauthlib').setLevel(logging.DEBUG)
logging.getLogger('google.auth').setLevel(logging.DEBUG)
logging.getLogger('requests_oauthlib').setLevel(logging.DEBUG)

logger = logging.getLogger(__name__)

def create_app():
    app = Flask(__name__, 
        template_folder=os.path.abspath(os.path.join(os.path.dirname(__file__), 'templates')),
        static_folder='static'
    )
    
    # Set secret key
    app.secret_key = os.environ.get('FLASK_SECRET_KEY', os.urandom(24))
    
    # Basic Flask config
    is_production = os.environ.get('FLASK_ENV') == 'production'
    app.config.update(
        DEBUG=not is_production,
        GOOGLE_CLIENT_ID=os.environ.get('GOOGLE_CLIENT_ID'),
        GOOGLE_CLIENT_SECRET=os.environ.get('GOOGLE_CLIENT_SECRET'),
        SESSION_COOKIE_NAME='vidpoint_session',
        SESSION_COOKIE_SECURE=is_production,  # True in production
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
        PERMANENT_SESSION_LIFETIME=timedelta(days=7),
        SESSION_REFRESH_EACH_REQUEST=True,
        SESSION_COOKIE_DOMAIN='.onrender.com' if is_production else None
    )
    
    # Load configuration
    app.config.update(
        SECRET_KEY=os.environ.get('FLASK_SECRET_KEY') or secrets.token_hex(32),
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
    logger.info(f"Template directory: {os.path.abspath(os.path.join(os.path.dirname(__file__), 'templates'))}")
    logger.info(f"Template folder exists: {os.path.exists(os.path.abspath(os.path.join(os.path.dirname(__file__), 'templates')))}")
    logger.info(f"Base template exists: {os.path.exists(os.path.join(os.path.abspath(os.path.join(os.path.dirname(__file__), 'templates')), 'base.html'))}")

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
            # result = VideoProcessor(os.getenv("OPENAI_API_KEY")).process_video(video_url, format_type)
            
            # Deduct credit
            # Database().update_user_credits(user['_id'], -1)
            
            # Save processing history
            # Database().save_processing_history(
            #     user_id=user['_id'],
            #     video_url=video_url,
            #     format_type=format_type,
            #     result=result,
            #     processed_at=datetime.now()
            # )
            
            return jsonify({"error": "Video processing temporarily disabled"})
            
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
                
            # if format_type == 'docx':
            #     file_path = export_to_word(content)
            # elif format_type == 'pdf':
            #     file_path = export_to_pdf(content)
            # else:
            #     return jsonify({"error": "Invalid format type"}), 400
                
            return jsonify({"error": "Export functionality temporarily disabled"})
            
        except Exception as e:
            logger.error(f"Error exporting content: {str(e)}", exc_info=True)
            return jsonify({"error": str(e)}), 500

    return app

# Create the application instance for Gunicorn
app = create_app()

if __name__ == '__main__':
    app.run(debug=True)
