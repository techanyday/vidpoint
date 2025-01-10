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

def verify_square_signature(request_data, signature, signing_key):
    """Verify Square webhook signature."""
    try:
        computed_signature = hmac.new(
            signing_key.encode('utf-8'),
            request_data,
            hashlib.sha256
        ).hexdigest()
        logger.info(f"Computed signature: {computed_signature}")
        logger.info(f"Received signature: {signature}")
        return hmac.compare_digest(computed_signature, signature)
    except Exception as e:
        logger.error(f"Error verifying signature: {str(e)}")
        return False

@bp.route('/square', methods=['POST'])
def square_webhook():
    """Handle Square payment notifications."""
    # Log request details
    logger.info("Received Square webhook")
    logger.info(f"Headers: {dict(request.headers)}")
    logger.info(f"Body: {request.get_data().decode('utf-8')}")
    
    # Verify webhook signature
    signature = request.headers.get('x-square-hmacsha256-signature')
    signing_key = current_app.config['SQUARE_WEBHOOK_SIGNING_KEY']
    
    logger.info(f"Using signing key: {signing_key}")
    
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
        
        if not event_type:
            return {'error': 'Missing event type'}, 400
        
        db = get_db()
        
        # Handle different event types
        if event_type == 'payment.created':
            payment = event['data']['object']['payment']
            
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
        
        elif event_type == 'payout.failed':
            payout = event['data']['object']['payout']
            
            # Update transaction status
            db.update_transaction_status(
                payment_id=payout['id'],
                status='failed',
                metadata=payout
            )
            
            # Get user ID from reference ID
            user_id = payout.get('reference_id')
            if user_id:
                # Send notification
                notification_service.send_notification(
                    user_id=user_id,
                    type='payment_failed',
                    title='Payment Failed',
                    message='Your payment could not be processed. Please try again.',
                    metadata={
                        'payout_id': payout['id'],
                        'error': payout.get('failure_reason', 'Unknown error')
                    }
                )
        
        elif event_type == 'refund.created':
            refund = event['data']['object']['refund']
            
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
        
        return {'success': True}, 200
        
    except Exception as e:
        current_app.logger.error(f"Webhook Error: {str(e)}")
        return {'error': 'Internal server error'}, 500
