from flask import Flask, request, jsonify, send_file, render_template, session, redirect, url_for
from process_flow import VideoProcessor
from document_exporter import export_to_word, export_to_pdf
from models.database import Database
from models.user import User
from config.pricing import PRICING_PLANS, CREDIT_PACKAGES
from config import SQUARE_CONFIG, FLASK_CONFIG, validate_config
from auth import auth as auth_blueprint
from routes import dashboard, payments, test_email, webhooks
import os
import logging
from datetime import datetime
from functools import wraps

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Validate configuration
validate_config()

app = Flask(__name__)
app.config['SECRET_KEY'] = FLASK_CONFIG['secret_key']
app.config['GOOGLE_CLIENT_ID'] = os.environ.get('GOOGLE_CLIENT_ID')
app.config['GOOGLE_CLIENT_SECRET'] = os.environ.get('GOOGLE_CLIENT_SECRET')
app.config['PAYSTACK_SECRET_KEY'] = os.environ.get('PAYSTACK_SECRET_KEY')
app.config['PAYSTACK_PUBLIC_KEY'] = os.environ.get('PAYSTACK_PUBLIC_KEY')

# Square configuration
app.config['SQUARE_WEBHOOK_SIGNING_KEY'] = SQUARE_CONFIG['webhook_signing_key']

# Register blueprints
app.register_blueprint(auth_blueprint)
app.register_blueprint(dashboard.bp)
app.register_blueprint(payments.bp)
app.register_blueprint(test_email.bp)
app.register_blueprint(webhooks.bp)

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

# Initialize database and video processor
db = Database()
processor = VideoProcessor(os.getenv("OPENAI_API_KEY"))

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
    return render_template('index.html',
                         pricing_plans=PRICING_PLANS,
                         credit_packages=CREDIT_PACKAGES)

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
        user = db.get_user_by_id(session['user_id'])
        if not user:
            return jsonify({"error": "User not found"}), 404
            
        # Check if user has enough credits
        if user.get('subscription', {}).get('credits', 0) < 1:
            return jsonify({"error": "Insufficient credits"}), 403
            
        # Process video
        result = processor.process_video(video_url, format_type)
        
        # Deduct credit
        db.update_user_credits(user['_id'], -1)
        
        # Save processing history
        db.save_processing_history(
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
    app.run(debug=True, port=8080)
