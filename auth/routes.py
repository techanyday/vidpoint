from flask import redirect, url_for, session, current_app, request, flash, render_template, jsonify
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError
from functools import wraps
import os
import json
from models.user import User
from models.database import get_db
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import logging
from . import auth
import secrets
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

# OAuth 2.0 scopes
SCOPES = [
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile',
    'openid'
]

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

@auth.before_request
def before_request():
    """Set up session configuration."""
    try:
        session.permanent = True  # Make session permanent
        current_app.permanent_session_lifetime = timedelta(days=7)  # Set session lifetime to 7 days
    except Exception as e:
        logger.error(f"Error in before_request: {str(e)}")

@auth.after_request
def after_request(response):
    """Configure response headers for security."""
    try:
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        return response
    except Exception as e:
        logger.error(f"Error in after_request: {str(e)}")
        return response

@auth.route('/register', methods=['GET', 'POST'])
def register():
    """Register a new user."""
    try:
        if request.method == 'GET':
            return render_template('auth/register.html')
            
        if request.method == 'POST':
            db = get_db()
            
            # Get form data
            email = request.form.get('email')
            password = request.form.get('password')
            confirm_password = request.form.get('confirm_password')
            name = request.form.get('name')
            
            # Validate form data
            if not email or not password or not confirm_password or not name:
                flash('All fields are required.', 'error')
                return render_template('auth/register.html')
                
            if password != confirm_password:
                flash('Passwords do not match.', 'error')
                return render_template('auth/register.html')
                
            # Check if user already exists
            existing_user = User.get_by_email(email)
            if existing_user:
                flash('Email already registered. Please login.', 'error')
                return redirect(url_for('auth.login'))
                
            # Create new user
            user = User(
                email=email,
                name=name,
                created_at=datetime.now(),
                subscription_plan='free',
                subscription_end=datetime.now() + timedelta(days=30),
                summaries_remaining=3
            )
            user.set_password(password)
            
            # Insert user into database
            user_data = {
                'email': user.email,
                'name': user.name,
                'password_hash': user.password_hash,
                'created_at': user.created_at,
                'subscription_plan': user.subscription_plan,
                'subscription_end': user.subscription_end,
                'summaries_remaining': user.summaries_remaining
            }
            
            try:
                user_id = db.insert_one('users', user_data)
                if not user_id:
                    raise Exception("Failed to create user in database")
                    
                # Log user in
                session['user_id'] = str(user_id)
                flash('Account created successfully!', 'success')
                return redirect(url_for('dashboard.index'))
                
            except Exception as e:
                logger.error(f"Database error during registration: {str(e)}")
                flash('An error occurred during registration. Please try again.', 'error')
                return render_template('auth/register.html')
                
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        flash('An error occurred during registration. Please try again.', 'error')
        return render_template('auth/register.html')

@auth.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login."""
    # Check if Google login is requested
    if request.method == 'GET' and request.args.get('provider') == 'google':
        logger.info("Google login requested")
        
        # Log OAuth configuration
        logger.debug(f"Client ID: {current_app.config.get('GOOGLE_CLIENT_ID')}")
        logger.debug("Client Secret is configured: %s", bool(current_app.config.get('GOOGLE_CLIENT_SECRET')))
        logger.debug(f"Request host: {request.host}")
        logger.debug(f"Request URL: {request.url}")
        
        if not current_app.config.get('GOOGLE_CLIENT_ID') or not current_app.config.get('GOOGLE_CLIENT_SECRET'):
            logger.error("Google OAuth credentials not configured")
            flash('Google login is not configured properly. Please try email login instead.', 'error')
            return render_template('auth/login.html')
        
        try:
            # Create flow instance to manage the OAuth 2.0 Authorization Grant Flow
            client_config = {
                "web": {
                    "client_id": current_app.config['GOOGLE_CLIENT_ID'],
                    "client_secret": current_app.config['GOOGLE_CLIENT_SECRET'],
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [
                        "https://vidpoint.onrender.com/auth/google/callback",
                        "http://localhost:10000/auth/google/callback",
                        "http://localhost:5000/auth/google/callback"
                    ]
                }
            }
            
            logger.debug(f"Client config: {json.dumps(client_config, indent=2)}")
            
            flow = Flow.from_client_config(
                client_config,
                scopes=['openid', 'email', 'profile']
            )
            
            # Set the redirect URI based on the request
            if request.host.startswith('localhost'):
                if ':10000' in request.host:
                    flow.redirect_uri = "http://localhost:10000/auth/google/callback"
                else:
                    flow.redirect_uri = "http://localhost:5000/auth/google/callback"
            else:
                flow.redirect_uri = "https://vidpoint.onrender.com/auth/google/callback"
            
            logger.debug(f"Redirect URI set to: {flow.redirect_uri}")

            # Generate URL for request to Google's OAuth 2.0 server
            authorization_url, state = flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true',
                prompt='consent'
            )

            logger.info(f"Generated authorization URL: {authorization_url}")
            session['state'] = state
            logger.debug(f"State stored in session: {state}")
            
            return redirect(authorization_url)
            
        except Exception as e:
            logger.error(f"Error initiating Google OAuth flow: {str(e)}", exc_info=True)
            flash('An error occurred while setting up Google login. Please try again later.', 'error')
            return render_template('auth/login.html')

    # Handle regular email/password login
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not email or not password:
            flash('Email and password are required.', 'error')
            return render_template('auth/login.html')
            
        db = get_db()
        user = db.get_user_by_email(email)
        
        if not user or not check_password_hash(user.get('password_hash', ''), password):
            flash('Invalid email or password.', 'error')
            return render_template('auth/login.html')
            
        session['user_id'] = str(user['_id'])
        flash('Logged in successfully!', 'success')
        return redirect(url_for('dashboard.index'))
    
    # Show login form for GET requests
    return render_template('auth/login.html')

@auth.route('/google/login')
def google_login():
    """Initiate Google OAuth login flow."""
    try:
        logger.debug("Starting Google login flow")
        logger.debug(f"Current request URL: {request.url}")
        logger.debug(f"Session before login: {dict(session)}")
        
        # Verify OAuth configuration
        client_id = current_app.config['GOOGLE_CLIENT_ID']
        client_secret = current_app.config['GOOGLE_CLIENT_SECRET']
        
        if not client_id or client_id != "888239351498-jiim27rd47dngpccc1ed2a9pd7c7m082.apps.googleusercontent.com":
            raise ValueError("Invalid Google Client ID")
        if not client_secret:
            raise ValueError("Google Client Secret not configured")
            
        # Create client config
        # Use https for production, http for local development
        scheme = 'https' if os.environ.get('FLASK_ENV') == 'production' else 'http'
        redirect_uri = url_for('auth.google_callback', _external=True, _scheme=scheme)
        logger.debug(f"Redirect URI: {redirect_uri}")
        
        client_config = {
            "web": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [
                    "https://vidpoint.onrender.com/auth/google/callback",
                    "http://localhost:5000/auth/google/callback"
                ]
            }
        }
        
        # Generate state
        state = secrets.token_urlsafe(32)
        session['oauth_state'] = state
        session['oauth_flow'] = {
            'state': state,
            'redirect_uri': redirect_uri,
            'client_id': client_id
        }
        session.modified = True
        
        logger.debug(f"Generated state: {state}")
        logger.debug(f"Session after state: {dict(session)}")
        
        # Create flow
        flow = Flow.from_client_config(
            client_config,
            scopes=['openid', 'email', 'profile'],
            state=state
        )
        flow.redirect_uri = redirect_uri
        
        # Generate authorization URL
        authorization_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )
        
        logger.debug(f"Authorization URL: {authorization_url}")
        return redirect(authorization_url)
        
    except Exception as e:
        logger.error(f"Error in Google login: {str(e)}", exc_info=True)
        flash('Failed to initiate Google login. Please try again.', 'error')
        return redirect(url_for('auth.login'))

@auth.route('/google/callback')
def google_callback():
    """Handle the Google OAuth callback."""
    try:
        # Log request details
        logger.debug("Received callback request")
        logger.debug(f"Query string: {request.args}")
        logger.debug(f"Session before callback: {dict(session)}")
        
        # Check for error in callback
        if 'error' in request.args:
            logger.error(f"Error in OAuth callback: {request.args.get('error')}")
            flash('Authentication failed. Please try again.', 'error')
            return redirect(url_for('auth.login'))
            
        # Verify state
        received_state = request.args.get('state')
        stored_state = session.get('oauth_state')
        logger.debug(f"Received state: {received_state}")
        logger.debug(f"Stored state: {stored_state}")
        
        if not received_state or not stored_state or received_state != stored_state:
            logger.error("State mismatch or missing")
            logger.error(f"Received state: {received_state}")
            logger.error(f"Stored state: {stored_state}")
            flash('Invalid session state. Please try again.', 'error')
            return redirect(url_for('auth.login'))
            
        # Get stored flow data
        flow_data = session.get('oauth_flow')
        if not flow_data:
            logger.error("No flow data in session")
            flash('Session expired. Please try again.', 'error')
            return redirect(url_for('auth.login'))
            
        # Recreate the flow
        client_config = {
            "web": {
                "client_id": flow_data['client_id'],
                "client_secret": current_app.config['GOOGLE_CLIENT_SECRET'],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [flow_data['redirect_uri']]
            }
        }
        
        flow = Flow.from_client_config(
            client_config,
            scopes=['openid', 'email', 'profile'],
            state=stored_state
        )
        flow.redirect_uri = flow_data['redirect_uri']
        
        # Process the callback
        try:
            flow.fetch_token(authorization_response=request.url)
        except Exception as e:
            logger.error(f"Error fetching token: {str(e)}", exc_info=True)
            flash('Failed to complete authentication. Please try again.', 'error')
            return redirect(url_for('auth.login'))
            
        credentials = flow.credentials
        
        try:
            # Get user info from Google
            oauth2_client = build('oauth2', 'v2', credentials=credentials)
            user_info = oauth2_client.userinfo().get().execute()
            
            logger.debug(f"Retrieved user info: {user_info}")
            
            # Get or create user
            db = get_db()
            user = db.get_user_by_email(user_info['email'])
            
            if user:
                # Update existing user
                db.update_user(user['_id'], {
                    'name': user_info.get('name'),
                    'picture': user_info.get('picture'),
                    'last_login': datetime.utcnow()
                })
            else:
                # Create new user
                user = db.create_user({
                    'email': user_info['email'],
                    'name': user_info.get('name'),
                    'picture': user_info.get('picture'),
                    'created_at': datetime.utcnow(),
                    'last_login': datetime.utcnow()
                })
                
            # Set session data
            session['user_id'] = str(user['_id'])
            session.modified = True
            
            logger.debug(f"Session after login: {dict(session)}")
            
            flash('Successfully signed in!', 'success')
            return redirect(url_for('dashboard.index'))
            
        except Exception as e:
            logger.error(f"Error processing user info: {str(e)}", exc_info=True)
            flash('Failed to process user information. Please try again.', 'error')
            return redirect(url_for('auth.login'))
            
    except Exception as e:
        logger.error(f"Error in callback: {str(e)}", exc_info=True)
        flash('An error occurred during Google login. Please try again.', 'error')
        return redirect(url_for('auth.login'))

@auth.route('/debug/oauth')
def debug_oauth():
    """Debug route to check OAuth configuration."""
    if not current_app.config.get('GOOGLE_CLIENT_ID') or not current_app.config.get('GOOGLE_CLIENT_SECRET'):
        return jsonify({
            'error': 'OAuth credentials not configured',
            'client_id_configured': bool(current_app.config.get('GOOGLE_CLIENT_ID')),
            'client_secret_configured': bool(current_app.config.get('GOOGLE_CLIENT_SECRET'))
        })
    
    return jsonify({
        'session': {
            'state': session.get('state'),
            'user_id': session.get('user_id'),
            'session_id': session.get('_id')
        },
        'request': {
            'host': request.host,
            'url': request.url,
            'scheme': request.scheme
        },
        'oauth_config': {
            'client_id_length': len(current_app.config['GOOGLE_CLIENT_ID']),
            'client_secret_length': len(current_app.config['GOOGLE_CLIENT_SECRET']),
            'insecure_transport': os.environ.get('OAUTHLIB_INSECURE_TRANSPORT') == '1'
        }
    })

@auth.route('/debug/env')
def debug_env():
    """Debug route to check environment variables."""
    return jsonify({
        'google_client_id_configured': bool(current_app.config.get('GOOGLE_CLIENT_ID')),
        'google_client_secret_configured': bool(current_app.config.get('GOOGLE_CLIENT_SECRET')),
        'flask_env': os.environ.get('FLASK_ENV'),
        'flask_debug': os.environ.get('FLASK_DEBUG'),
        'oauthlib_insecure_transport': os.environ.get('OAUTHLIB_INSECURE_TRANSPORT'),
        'session_type': current_app.config.get('SESSION_TYPE'),
        'session_file_dir': current_app.config.get('SESSION_FILE_DIR'),
        'session_cookie_secure': current_app.config.get('SESSION_COOKIE_SECURE')
    })

@auth.route('/logout')
def logout():
    """Log out the current user."""
    session.clear()
    flash('Logged out successfully.', 'success')
    return redirect(url_for('index'))
