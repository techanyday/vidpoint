from flask import Blueprint
import os

# Create the blueprint with template folder configuration
template_dir = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates'))
auth = Blueprint('auth', __name__,
    url_prefix='/auth',
    template_folder=template_dir
)

# Import routes after blueprint creation to avoid circular imports
from . import routes
