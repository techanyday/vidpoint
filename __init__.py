"""VidPoint Flask application factory."""
import os
from flask import Flask
from flask_login import LoginManager

def create_app(test_config=None):
    """Create and configure the app."""
    app = Flask(__name__, instance_relative_config=True)
    
    # Load default configuration
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev'),
        SQUARE_APP_ID=os.environ.get('SQUARE_APP_ID'),
        SQUARE_ACCESS_TOKEN=os.environ.get('SQUARE_ACCESS_TOKEN'),
        SQUARE_LOCATION_ID=os.environ.get('SQUARE_LOCATION_ID'),
        SQUARE_ENVIRONMENT=os.environ.get('SQUARE_ENVIRONMENT', 'sandbox'),
        SQUARE_WEBHOOK_SIGNING_KEY=os.environ.get('SQUARE_WEBHOOK_SIGNING_KEY'),
    )

    if test_config is None:
        # Load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # Load the test config if passed in
        app.config.update(test_config)

    # Ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # Initialize LoginManager
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    from . import db
    db.init_app(app)

    # Register blueprints
    from .routes import auth, dashboard, payments, webhooks
    app.register_blueprint(auth.bp)
    app.register_blueprint(dashboard.bp)
    app.register_blueprint(payments.bp)
    app.register_blueprint(webhooks.bp)

    # Make index point to dashboard
    app.add_url_rule('/', endpoint='index', view_func=dashboard.index)

    return app
