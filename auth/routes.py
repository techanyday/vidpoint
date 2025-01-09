from flask import redirect, url_for, session, current_app, request, flash
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError
from functools import wraps
import os
import json
from . import auth
from models.user import User

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

@auth.route('/login')
def login():
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
        picture = userinfo_response.get('picture', '')

        # Create or update user
        user = User.get_by_email(users_email)
        if not user:
            user = User.create(
                email=users_email,
                name=users_name,
                google_id=unique_id,
                profile_picture=picture
            )
        else:
            user.update(
                name=users_name,
                google_id=unique_id,
                profile_picture=picture
            )

        # Begin user session
        session['user_id'] = user.id
        session['user_email'] = users_email
        session['user_name'] = users_name
        session['picture'] = picture

        # Store credentials for future use
        session['credentials'] = {
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes
        }

        return redirect(url_for('index'))
    else:
        flash('User email not verified by Google.', 'error')
        return redirect(url_for('index'))

@auth.route('/logout')
def logout():
    # Clear session
    session.clear()
    return redirect(url_for('index'))
