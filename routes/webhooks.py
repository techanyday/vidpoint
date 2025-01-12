"""Webhook handlers for payment notifications."""
import hmac
import hashlib
import json
import logging
from flask import Blueprint, request, current_app, make_response
from models.database import get_db
from notifications.notification_service import NotificationService

bp = Blueprint('webhooks', __name__, url_prefix='/webhooks')
notification_service = NotificationService()
logger = logging.getLogger(__name__)

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def add_cors_headers(response):
    """Add CORS headers to response."""
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', '*')
    response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
    response.headers.add('Access-Control-Expose-Headers', '*')
    return response

def verify_square_signature(request_data, signature, signing_key):
    """Verify Square webhook signature."""
    try:
        logger.debug("=== Signature Verification Debug ===")
        logger.debug(f"Request Data Type: {type(request_data)}")
        logger.debug(f"Request Data Length: {len(request_data) if request_data else 0}")
        logger.debug(f"Signature: {signature}")
        logger.debug(f"Signing Key: {signing_key}")
        
        if not request_data:
            logger.error("No request data to verify")
            return False
            
        if not signature:
            logger.error("No signature provided")
            return False
            
        if not signing_key:
            logger.error("No signing key configured")
            return False

        # For test notifications, skip signature verification
        try:
            if isinstance(request_data, bytes):
                data = json.loads(request_data.decode('utf-8'))
                logger.debug(f"Parsed request data: {json.dumps(data, indent=2)}")
                if data.get('type') == 'test_notification':
                    logger.info("Test notification detected, skipping signature verification")
                    return True
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse request data as JSON: {str(e)}")
            return False

        # Compute signature
        computed_signature = hmac.new(
            signing_key.encode('utf-8'),
            request_data,
            hashlib.sha256
        ).hexdigest()
        
        logger.debug(f"Computed Signature: {computed_signature}")
        logger.debug(f"Received Signature: {signature}")
        
        # Compare signatures
        signatures_match = hmac.compare_digest(computed_signature, signature)
        logger.debug(f"Signatures Match: {signatures_match}")
        
        return signatures_match
    except Exception as e:
        logger.error(f"Error verifying signature: {str(e)}", exc_info=True)
        return False

@bp.route('/square', methods=['POST', 'OPTIONS'])
def square_webhook():
    """Handle Square payment notifications."""
    logger.debug("\n=== Square Webhook Request ===")
    logger.debug(f"Request Method: {request.method}")
    logger.debug(f"Request Path: {request.path}")
    logger.debug(f"Request URL: {request.url}")
    logger.debug(f"Headers: {dict(request.headers)}")
    
    # Get raw data before parsing json
    raw_data = request.get_data()
    logger.debug(f"Raw Data: {raw_data.decode('utf-8') if raw_data else 'No data'}")
    
    # Handle preflight OPTIONS request
    if request.method == 'OPTIONS':
        response = make_response()
        return add_cors_headers(response)
    
    # Get webhook signing key from config
    signing_key = current_app.config.get('SQUARE_WEBHOOK_SIGNING_KEY')
    logger.debug(f"Webhook Signing Key from Config: {signing_key}")
    
    if not signing_key:
        logger.error("Missing webhook signing key in configuration")
        response = make_response({'error': 'Missing webhook signing key'}, 500)
        return add_cors_headers(response)
    
    # Get signature from headers
    signature = request.headers.get('x-square-hmacsha256-signature')
    logger.debug(f"Signature from Headers: {signature}")
    
    if not signature:
        logger.error("Missing signature header")
        response = make_response({'error': 'Missing signature header'}, 401)
        return add_cors_headers(response)
    
    # Verify signature
    if not verify_square_signature(raw_data, signature, signing_key):
        logger.error("Invalid signature")
        response = make_response({'error': 'Invalid signature'}, 401)
        return add_cors_headers(response)
    
    try:
        # Parse request data
        event = json.loads(raw_data.decode('utf-8')) if raw_data else None
        if not event:
            logger.error("No event data received")
            response = make_response({'error': 'No event data'}, 400)
            return add_cors_headers(response)
            
        event_type = event.get('type')
        logger.debug(f"Event Type: {event_type}")
        logger.debug(f"Event Data: {json.dumps(event, indent=2)}")
        
        # Handle test notifications
        if event_type == 'test_notification':
            logger.info("Successfully processed test notification")
            response = make_response({
                'success': True,
                'message': 'Test notification received and verified'
            }, 200)
            return add_cors_headers(response)
        
        if not event_type:
            response = make_response({'error': 'Missing event type'}, 400)
            return add_cors_headers(response)
        
        db = get_db()
        
        # Handle different event types
        if event_type == 'payment.created':
            payment = event['data']['object']['payment']
            logger.info(f"Processing payment.created: {payment['id']}")
            
            # Update transaction status
            db.update_transaction_status(
                payment_id=payment['id'],
                status='completed',
                metadata=payment
            )
            
            # Get user ID from reference ID
            user_id = payment.get('reference_id')
            if user_id:
                # Add credits to user account
                amount = payment['amount_money']['amount']
                credits = amount // 100  # Convert cents to credits
                db.add_user_credits(user_id, credits)
                
                # Send notification
                notification_service.send_notification(
                    user_id=user_id,
                    type='payment_success',
                    title='Payment Successful',
                    message=f'Your payment of {credits} credits was successful.',
                    metadata={
                        'payment_id': payment['id'],
                        'amount': amount,
                        'credits': credits
                    }
                )
                logger.info(f"Added {credits} credits to user {user_id}")
        
        elif event_type == 'payment.failed':
            payment = event['data']['object']['payment']
            logger.info(f"Processing payment.failed: {payment['id']}")
            
            # Update transaction status
            db.update_transaction_status(
                payment_id=payment['id'],
                status='failed',
                metadata=payment
            )
            
            # Get user ID from reference ID
            user_id = payment.get('reference_id')
            if user_id:
                # Send notification
                notification_service.send_notification(
                    user_id=user_id,
                    type='payment_failed',
                    title='Payment Failed',
                    message='Your payment could not be processed. Please try again.',
                    metadata={
                        'payment_id': payment['id'],
                        'error': payment.get('failure_reason', 'Unknown error')
                    }
                )
                logger.info(f"Sent payment failed notification to user {user_id}")
        
        elif event_type == 'refund.created':
            refund = event['data']['object']['refund']
            logger.info(f"Processing refund.created: {refund['id']}")
            
            # Update transaction status
            db.update_transaction_status(
                payment_id=refund['payment_id'],
                status='refunded',
                metadata=refund
            )
            
            # Get user ID from reference ID
            payment = refund.get('payment_id')
            if payment:
                user_id = db.get_user_id_from_payment(payment)
                if user_id:
                    # Remove credits from user account
                    amount = refund['amount_money']['amount']
                    credits = amount // 100
                    db.remove_user_credits(user_id, credits)
                    
                    # Send notification
                    notification_service.send_notification(
                        user_id=user_id,
                        type='refund_processed',
                        title='Refund Processed',
                        message=f'Your refund of {credits} credits has been processed.',
                        metadata={
                            'refund_id': refund['id'],
                            'amount': amount,
                            'credits': credits
                        }
                    )
                    logger.info(f"Processed refund of {credits} credits for user {user_id}")
        
        # Add CORS headers to response
        response = make_response({'success': True}, 200)
        return add_cors_headers(response)
        
    except Exception as e:
        logger.error(f"Webhook Error: {str(e)}", exc_info=True)
        response = make_response({'error': 'Internal server error'}, 500)
        return add_cors_headers(response)
