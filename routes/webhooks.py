"""Webhook handlers for payment notifications."""
import hmac
import hashlib
import json
import logging
from flask import Blueprint, request, current_app
from models.database import get_db
from notifications.notification_service import NotificationService

bp = Blueprint('webhooks', __name__, url_prefix='/webhooks')
notification_service = NotificationService()
logger = logging.getLogger(__name__)

# Configure logging
logger.setLevel(logging.DEBUG)

def verify_square_signature(request_data, signature, signing_key):
    """Verify Square webhook signature."""
    try:
        computed_signature = hmac.new(
            signing_key.encode('utf-8'),
            request_data,
            hashlib.sha256
        ).hexdigest()
        logger.debug(f"Computed signature: {computed_signature}")
        logger.debug(f"Received signature: {signature}")
        return hmac.compare_digest(computed_signature, signature)
    except Exception as e:
        logger.error(f"Error verifying signature: {str(e)}")
        return False

@bp.route('/square', methods=['POST'])
def square_webhook():
    """Handle Square payment notifications."""
    logger.debug("=== Square Webhook Request ===")
    logger.debug(f"Request Method: {request.method}")
    logger.debug(f"Request Path: {request.path}")
    logger.debug(f"Request URL: {request.url}")
    logger.debug(f"Headers: {dict(request.headers)}")
    logger.debug(f"Raw Data: {request.get_data().decode('utf-8')}")
    
    # Verify webhook signature
    signature = request.headers.get('x-square-hmacsha256-signature')
    signing_key = current_app.config['SQUARE_WEBHOOK_SIGNING_KEY']
    
    logger.debug(f"Signature Header Present: {bool(signature)}")
    logger.debug(f"Signing Key Present: {bool(signing_key)}")
    
    if not signature or not verify_square_signature(
        request.get_data(),
        signature,
        signing_key
    ):
        logger.error("Invalid signature")
        return {'error': 'Invalid signature'}, 401
    
    try:
        event = request.get_json()
        event_type = event.get('type')
        
        logger.debug(f"Event Type: {event_type}")
        logger.debug(f"Event Data: {json.dumps(event, indent=2)}")
        
        if not event_type:
            return {'error': 'Missing event type'}, 400
        
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
        
        logger.debug("=== Webhook Processing Complete ===")
        return {'success': True}, 200
        
    except Exception as e:
        logger.error(f"Webhook Error: {str(e)}", exc_info=True)
        return {'error': 'Internal server error'}, 500
