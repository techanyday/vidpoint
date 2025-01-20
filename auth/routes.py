from flask import redirect, url_for, session, current_app, request, flash, render_template
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
    if request.method == 'GET':
        return render_template('auth/login.html')
        
    if request.method == 'POST':
        # Handle email/password login
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
        
    # Create flow instance to manage the OAuth 2.0 Authorization Grant Flow
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": current_app.config['GOOGLE_CLIENT_ID'],
                "client_secret": current_app.config['GOOGLE_CLIENT_SECRET'],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [url_for('auth.oauth2callback', _external=True)]
            }
        },
        scopes=SCOPES
    )

    # Generate URL for request to Google's OAuth 2.0 server
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true'
    )

    session['state'] = state
    return redirect(authorization_url)

@auth.route('/oauth2callback')
def oauth2callback():
    state = session.get('state')
    
    if not state:
        flash('Authentication state mismatch. Please try again.', 'error')
        return redirect(url_for('index'))

    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": current_app.config['GOOGLE_CLIENT_ID'],
                "client_secret": current_app.config['GOOGLE_CLIENT_SECRET'],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [url_for('auth.oauth2callback', _external=True)]
            }
        },
        scopes=SCOPES,
        state=state
    )

    # Use the authorization server's response to fetch the OAuth 2.0 tokens
    authorization_response = request.url
    flow.fetch_token(authorization_response=authorization_response)
    credentials = flow.credentials

    # Get user info from Google
    import google.oauth2.credentials
    import google.auth.transport.requests
    import requests

    oauth2_client = google.auth.transport.requests.AuthorizedSession(
        google.oauth2.credentials.Credentials(
            token=credentials.token,
            refresh_token=credentials.refresh_token,
            token_uri=credentials.token_uri,
            client_id=credentials.client_id,
            client_secret=credentials.client_secret,
            scopes=credentials.scopes
        )
    )

    userinfo_response = oauth2_client.get(
        'https://www.googleapis.com/oauth2/v3/userinfo'
    ).json()

    if userinfo_response.get('email_verified'):
        unique_id = userinfo_response['sub']
        users_email = userinfo_response['email']
        users_name = userinfo_response.get('name', '')
        
        # Check if user exists
        db = get_db()
        user = db.get_user_by_email(users_email)
        
        if not user:
            # Create new user
            user_data = {
                'email': users_email,
                'name': users_name,
                'google_id': unique_id,
                'created_at': datetime.now(),
                'subscription': {
                    'plan': 'free',
                    'credits': 3,
                    'start_date': datetime.now(),
                    'end_date': datetime.now() + timedelta(days=30)
                },
                'notification_preferences': {
                    'subscription_expiry': True,
                    'low_credits': True,
                    'payment_confirmation': True,
                    'export_complete': True,
                    'promotional': False,
                    'email_digest': 'daily'
                }
            }
            user_id = db.create_user(user_data)
        else:
            user_id = user['_id']
        
        session['user_id'] = str(user_id)
        return redirect(url_for('dashboard.index'))
    else:
        flash('Google login failed. Please try again.', 'error')
        return redirect(url_for('auth.login'))

@auth.route('/logout')
def logout():
    """Log out the current user."""
    session.clear()
    flash('Logged out successfully.', 'success')
    return redirect(url_for('index'))
