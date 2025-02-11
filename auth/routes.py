import os
import logging
import secrets
import json
from flask import (
    Blueprint, render_template, redirect, url_for, 
    session, request, flash, current_app, jsonify
)
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from google.auth.exceptions import RefreshError
from googleapiclient.discovery import build
from functools import wraps
from models.user import User
from models.database import get_db
from . import auth
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta

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
    # Clear any existing session
    session.clear()
    
    if request.method == 'POST':
        try:
            email = request.form.get('email')
            password = request.form.get('password')
            remember = request.form.get('remember') == 'on'
            
            if not email or not password:
                flash('Please provide both email and password.', 'error')
                return redirect(url_for('auth.login'))
                
            # Initialize session
            session.permanent = True
            session['created_at'] = datetime.utcnow().isoformat()
            session.modified = True
            
            db = get_db()
            user = db.get_user_by_email(email)
            
            if not user or not check_password_hash(user.get('password_hash', ''), password):
                flash('Invalid email or password.', 'error')
                return render_template('auth/login.html')
                
            session['user_id'] = str(user['_id'])
            flash('Logged in successfully!', 'success')
            return redirect(url_for('dashboard.index'))
        
        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            flash('An error occurred during login. Please try again.', 'error')
            return render_template('auth/login.html')
    
    # Show login form for GET requests
    return render_template('auth/login.html')

@auth.route('/google/login')
def google_login():
    """Initiate Google OAuth login flow."""
    try:
        logger.info("Starting Google OAuth flow")
        
        # Check if Google OAuth is configured
        client_id = current_app.config.get('GOOGLE_CLIENT_ID')
        client_secret = current_app.config.get('GOOGLE_CLIENT_SECRET')
        
        if not client_id or not client_secret:
            logger.error("Google OAuth credentials not configured")
            flash('Google login is not configured properly. Please try email login instead.', 'error')
            return redirect(url_for('auth.login'))
        
        # Clear any existing session
        session.clear()
        
        # Initialize new session
        session.permanent = True
        session['created_at'] = datetime.utcnow().isoformat()
        session.modified = True
        
        # Generate state
        state = secrets.token_urlsafe(32)
        session['oauth_state'] = state
        session['oauth_state_created'] = datetime.utcnow().isoformat()
        session.modified = True
        
        # Determine the base URL
        if current_app.config['ENV'] == 'production':
            base_url = 'https://vidpoint.onrender.com'
        else:
            base_url = 'http://localhost:5000'
            
        # Create flow
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [
                        f"{base_url}/auth/google/callback"
                    ]
                }
            },
            scopes=['openid', 'email', 'profile'],
            state=state
        )
        
        # Set the redirect URI
        flow.redirect_uri = f"{base_url}/auth/google/callback"
        
        # Generate authorization URL
        authorization_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )
        
        logger.info(f"Redirecting to Google OAuth URL: {authorization_url}")
        return redirect(authorization_url)
        
    except Exception as e:
        logger.error(f"Error in Google login: {str(e)}", exc_info=True)
        flash('Failed to initiate Google login. Please try again.', 'error')
        return redirect(url_for('auth.login'))

@auth.route('/google/callback')
def google_callback():
    """Handle the response from Google OAuth."""
    try:
        logger.debug("Received Google callback")
        logger.debug(f"Request args: {request.args}")
        logger.debug(f"Session data: {dict(session)}")
        logger.debug(f"Cookies: {request.cookies}")
        logger.debug(f"Request URL: {request.url}")
        logger.debug(f"Request base URL: {request.base_url}")
        
        # Verify session exists
        if not hasattr(session, 'sid'):
            logger.error("No session found in callback")
            flash('Session expired. Please try again.', 'error')
            return redirect(url_for('auth.login'))
            
        # Check session age
        created_time = session.get('created_at')
        if created_time:
            created_dt = datetime.fromisoformat(created_time)
            if datetime.utcnow() - created_dt > current_app.permanent_session_lifetime:
                session.clear()
                flash('Session expired during OAuth flow. Please try again.', 'error')
                return redirect(url_for('auth.login'))
                
        # Check for error in callback
        if 'error' in request.args:
            error = request.args.get('error')
            error_description = request.args.get('error_description', 'No description provided')
            logger.error(f"OAuth error: {error} - {error_description}")
            flash('Authentication failed: ' + error_description, 'error')
            return redirect(url_for('auth.login'))

        # Get state from request
        request_state = request.args.get('state')
        logger.debug(f"Request state: {request_state}")
        
        # Get state from session
        session_state = session.get('oauth_state')
        state_created = session.get('oauth_state_created')
        logger.debug(f"Session state: {session_state}")
        logger.debug(f"State created at: {state_created}")
        
        if not request_state:
            logger.error("No state parameter in request")
            flash('Invalid request. Please try again.', 'error')
            return redirect(url_for('auth.login'))
            
        if not session_state:
            logger.error("No state found in session")
            flash('Session expired. Please try again.', 'error')
            return redirect(url_for('auth.login'))
            
        # Check state age
        if state_created:
            created_time = datetime.fromisoformat(state_created)
            age = datetime.utcnow() - created_time
            if age > timedelta(minutes=10):
                logger.error(f"State too old: {age}")
                flash('Authentication timeout. Please try again.', 'error')
                return redirect(url_for('auth.login'))
            
        # Log state comparison
        logger.debug(f"State comparison - Request: {request_state}, Session: {session_state}")
        
        # Verify state
        if request_state != session_state:
            logger.error(f"State mismatch - Request: {request_state}, Session: {session_state}")
            flash('Invalid session state. Please try again.', 'error')
            return redirect(url_for('auth.login'))
        
        # Create client config
        client_id = os.environ.get('GOOGLE_CLIENT_ID')
        client_secret = os.environ.get('GOOGLE_CLIENT_SECRET')
        
        if not client_id or not client_secret:
            raise ValueError("Google OAuth credentials not configured")
        
        # Get the actual callback URL from the request
        if request.headers.get('X-Forwarded-Proto') == 'https':
            actual_scheme = 'https'
        else:
            actual_scheme = 'http' if os.environ.get('FLASK_ENV') != 'production' else 'https'
        
        # Construct the redirect URI using the actual scheme and host
        redirect_uri = url_for('auth.google_callback', _external=True, _scheme=actual_scheme)
        logger.debug(f"Constructed redirect URI: {redirect_uri}")
        
        client_config = {
            "web": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [
                    "https://vidpoint.onrender.com/auth/google/callback",
                    "http://vidpoint.onrender.com/auth/google/callback",
                    "http://localhost:5000/auth/google/callback"
                ],
                "javascript_origins": [
                    "https://vidpoint.onrender.com",
                    "http://vidpoint.onrender.com",
                    "http://localhost:5000"
                ]
            }
        }
        
        # Create flow
        flow = Flow.from_client_config(
            client_config,
            scopes=['openid', 'email', 'profile'],
            state=request_state
        )
        flow.redirect_uri = redirect_uri
        
        # Log the authorization response URL
        logger.debug(f"Authorization response URL: {request.url}")
        logger.debug(f"Flow redirect URI: {flow.redirect_uri}")
        
        # Fetch token
        try:
            flow.fetch_token(authorization_response=request.url)
            logger.debug("Successfully fetched token")
        except Exception as token_error:
            logger.error(f"Error fetching token: {str(token_error)}", exc_info=True)
            raise ValueError(f"Failed to fetch token: {str(token_error)}")
        
        # Get user info from ID token
        try:
            credentials = flow.credentials
            logger.debug(f"Credentials obtained - Token valid: {credentials.valid}")
            logger.debug(f"Token expiry: {credentials.expiry}")
            
            # Store credentials in session
            session['google_credentials'] = {
                'token': credentials.token,
                'refresh_token': credentials.refresh_token,
                'token_uri': credentials.token_uri,
                'client_id': credentials.client_id,
                'client_secret': credentials.client_secret,
                'scopes': credentials.scopes,
                'expiry': credentials.expiry.isoformat() if credentials.expiry else None
            }
            
            # Verify ID token
            user_info = id_token.verify_oauth2_token(
                credentials.id_token,
                google_requests.Request(),
                client_id,
                clock_skew_in_seconds=60
            )
            logger.debug(f"User info received: {user_info}")
            
        except Exception as token_verify_error:
            logger.error(f"Error verifying token: {str(token_verify_error)}", exc_info=True)
            raise ValueError(f"Failed to verify token: {str(token_verify_error)}")
        
        # Store user info in session
        session['user'] = {
            'email': user_info.get('email'),
            'name': user_info.get('name'),
            'picture': user_info.get('picture'),
            'sub': user_info.get('sub')  # Google's unique user ID
        }
        session['logged_in'] = True
        session.modified = True
        
        logger.debug(f"Final session data: {dict(session)}")
        
        flash('Successfully logged in!', 'success')
        return redirect(url_for('dashboard.index'))
        
    except Exception as e:
        logger.error(f"Error in Google callback: {str(e)}", exc_info=True)
        flash('Authentication failed. Please try again.', 'error')
        return redirect(url_for('auth.login'))

@auth.route('/refresh-token')
def refresh_token():
    """Refresh the Google OAuth token."""
    try:
        if 'google_credentials' not in session:
            logger.error("No credentials found in session")
            return jsonify({'error': 'No credentials found'}), 401
            
        creds_data = session['google_credentials']
        
        # Create credentials object
        credentials = Credentials(
            token=creds_data['token'],
            refresh_token=creds_data['refresh_token'],
            token_uri=creds_data['token_uri'],
            client_id=creds_data['client_id'],
            client_secret=creds_data['client_secret'],
            scopes=creds_data['scopes']
        )
        
        # Check if token needs refresh
        if not credentials.valid:
            logger.debug("Token expired, refreshing...")
            credentials.refresh(google_requests.Request())
            
            # Update session with new credentials
            session['google_credentials'] = {
                'token': credentials.token,
                'refresh_token': credentials.refresh_token,
                'token_uri': credentials.token_uri,
                'client_id': credentials.client_id,
                'client_secret': credentials.client_secret,
                'scopes': credentials.scopes,
                'expiry': credentials.expiry.isoformat() if credentials.expiry else None
            }
            session.modified = True
            logger.debug("Token refreshed successfully")
            
        return jsonify({'success': True, 'message': 'Token is valid'})
        
    except Exception as e:
        logger.error(f"Error refreshing token: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@auth.route('/debug/oauth')
def debug_oauth():
    """Debug route to check OAuth configuration."""
    if not os.environ.get('GOOGLE_CLIENT_ID') or not os.environ.get('GOOGLE_CLIENT_SECRET'):
        return jsonify({
            'error': 'OAuth credentials not configured',
            'client_id_configured': bool(os.environ.get('GOOGLE_CLIENT_ID')),
            'client_secret_configured': bool(os.environ.get('GOOGLE_CLIENT_SECRET'))
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
            'client_id_length': len(os.environ.get('GOOGLE_CLIENT_ID')),
            'client_secret_length': len(os.environ.get('GOOGLE_CLIENT_SECRET')),
            'insecure_transport': os.environ.get('OAUTHLIB_INSECURE_TRANSPORT') == '1'
        }
    })

@auth.route('/debug/env')
def debug_env():
    """Debug route to check environment variables."""
    return jsonify({
        'google_client_id_configured': bool(os.environ.get('GOOGLE_CLIENT_ID')),
        'google_client_secret_configured': bool(os.environ.get('GOOGLE_CLIENT_SECRET')),
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
