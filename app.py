from flask import Flask, request, jsonify, send_file, render_template, session
from process_flow import VideoProcessor
from document_exporter import export_to_word, export_to_pdf
from models.database import Database
from models.user import User
from config.pricing import PRICING_PLANS, CREDIT_PACKAGES
from auth import auth
from payments import payments
import os
import logging
from datetime import datetime
from functools import wraps

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY')
app.config['GOOGLE_CLIENT_ID'] = os.environ.get('GOOGLE_CLIENT_ID')
app.config['GOOGLE_CLIENT_SECRET'] = os.environ.get('GOOGLE_CLIENT_SECRET')
app.config['HUBTEL_CLIENT_ID'] = os.environ.get('HUBTEL_CLIENT_ID')
app.config['HUBTEL_CLIENT_SECRET'] = os.environ.get('HUBTEL_CLIENT_SECRET')
app.config['HUBTEL_MERCHANT_ID'] = os.environ.get('HUBTEL_MERCHANT_ID')
app.config['FLW_PUBLIC_KEY'] = os.environ.get('FLW_PUBLIC_KEY')
app.config['FLW_SECRET_KEY'] = os.environ.get('FLW_SECRET_KEY')
app.config['FLW_WEBHOOK_HASH'] = os.environ.get('FLW_WEBHOOK_HASH')
app.config['PAYSTACK_SECRET_KEY'] = os.environ.get('PAYSTACK_SECRET_KEY')
app.config['PAYSTACK_PUBLIC_KEY'] = os.environ.get('PAYSTACK_PUBLIC_KEY')

# Register blueprints
app.register_blueprint(auth, url_prefix='/auth')
app.register_blueprint(payments, url_prefix='/payments')

@app.context_processor
def inject_user():
    return {
        'current_user': {
            'is_authenticated': 'user_id' in session,
            'name': session.get('user_name'),
            'email': session.get('user_email'),
            'picture': session.get('picture')
        }
    }

# Initialize database and video processor
db = Database()
processor = VideoProcessor(os.getenv("OPENAI_API_KEY"))

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_email" not in session:
            return jsonify({"error": "Please log in"}), 401
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    """Render the main page."""
    return render_template('index.html', 
                         pricing_plans=PRICING_PLANS,
                         credit_packages=CREDIT_PACKAGES,
                         user=db.get_user(session.get("user_email")))

@app.route('/register', methods=['POST'])
def register():
    """Register a new user."""
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({"error": "Email and password required"}), 400
            
        user = db.create_user(email, password)
        if not user:
            return jsonify({"error": "Email already registered"}), 400
            
        session["user_email"] = email
        return jsonify({"message": "Registration successful"})
        
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/login', methods=['POST'])
def login():
    """Log in a user."""
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        
        user = db.get_user(email)
        if not user or not user.check_password(password):
            return jsonify({"error": "Invalid email or password"}), 401
            
        session["user_email"] = email
        return jsonify({"message": "Login successful"})
        
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/logout')
def logout():
    """Log out the current user."""
    session.pop("user_email", None)
    return jsonify({"message": "Logged out"})

@app.route('/process', methods=['POST'])
@login_required
def process_video():
    """Process a video URL."""
    try:
        data = request.get_json()
        video_url = data.get('videoUrl')
        is_premium = data.get('is_premium', False)
        
        if not video_url:
            return jsonify({"error": "No video URL provided"}), 400
            
        # Check user limits
        user = db.get_user(session["user_email"])
        can_process, error_message = user.can_process_video()
        if not can_process:
            return jsonify({"error": error_message}), 403
            
        # Process video
        result = processor.process_video(video_url, is_premium)
        if "error" in result:
            return jsonify({"error": result["error"]}), 500
            
        # Record usage
        user.process_video()
        db.update_user(user)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error processing video: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/export', methods=['POST'])
@login_required
def export_content():
    """Export content to a document."""
    try:
        data = request.get_json()
        content = data.get('content')
        content_type = data.get('type')
        format = data.get('format', 'word')
        title = data.get('title')
        
        if not content or not content_type:
            return jsonify({"error": "Missing content or type"}), 400
            
        if format == 'word':
            filepath = export_to_word(content, content_type, title)
        else:
            filepath = export_to_pdf(content, content_type, title)
            
        if filepath:
            return send_file(filepath, as_attachment=True)
        else:
            return jsonify({"error": "Failed to export content"}), 500
            
    except Exception as e:
        logger.error(f"Error in export_content: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/upgrade', methods=['POST'])
@login_required
def upgrade_plan():
    """Upgrade a user's plan."""
    try:
        data = request.get_json()
        new_plan = data.get('plan')
        
        if new_plan not in PRICING_PLANS:
            return jsonify({"error": "Invalid plan"}), 400
            
        user = db.get_user(session["user_email"])
        user.plan = new_plan
        db.update_user(user)
        
        return jsonify({"message": "Plan upgraded successfully"})
        
    except Exception as e:
        logger.error(f"Error upgrading plan: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/buy_credits', methods=['POST'])
@login_required
def buy_credits():
    """Purchase additional credits."""
    try:
        data = request.get_json()
        package = data.get('package')
        
        if package not in CREDIT_PACKAGES:
            return jsonify({"error": "Invalid credit package"}), 400
            
        user = db.get_user(session["user_email"])
        credits = CREDIT_PACKAGES[package]["summaries"]
        user.add_credits(credits)
        db.update_user(user)
        
        return jsonify({"message": f"Added {credits} credits"})
        
    except Exception as e:
        logger.error(f"Error buying credits: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=8080)
