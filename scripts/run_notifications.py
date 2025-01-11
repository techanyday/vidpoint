"""Script to run notifications checks."""
import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = str(Path(__file__).parent.parent)
sys.path.append(project_root)

from flask import Flask
from notifications.scheduler import NotificationScheduler
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_app():
    """Create Flask app for context."""
    app = Flask(__name__)
    
    # Configure app
    app.config['MONGODB_URI'] = os.getenv('MONGODB_URI')
    app.config['SMTP_SERVER'] = os.getenv('SMTP_SERVER')
    app.config['SMTP_PORT'] = int(os.getenv('SMTP_PORT', '465'))
    app.config['SMTP_USERNAME'] = os.getenv('SMTP_USERNAME')
    app.config['SMTP_PASSWORD'] = os.getenv('SMTP_PASSWORD')
    app.config['FROM_EMAIL'] = os.getenv('FROM_EMAIL')
    
    return app

def main():
    """Run notification checks."""
    try:
        app = create_app()
        with app.app_context():
            logger.info("Starting notification checks...")
            scheduler = NotificationScheduler()
            scheduler.run_checks()
            logger.info("Notification checks completed successfully!")
    except Exception as e:
        logger.error(f"Error running notification checks: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()
