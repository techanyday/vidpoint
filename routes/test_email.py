"""Test email functionality."""
from flask import Blueprint, jsonify
from notifications.email_service import EmailService

bp = Blueprint('test_email', __name__)

@bp.route('/test-email')
def test_email():
    """Send a test email."""
    try:
        email_service = EmailService()
        success = email_service.send_payment_success(
            'support@tekstreetz.com',
            'Test Plan',
            1000  # 10 GHS in pesewas
        )
        
        if success:
            return jsonify({
                'status': 'success',
                'message': 'Test email sent successfully'
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Failed to send test email'
            }), 500
            
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
