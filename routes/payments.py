"""Payment routes for VidPoint."""
from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required, current_user
import uuid
from payments.square_service import SquarePaymentService
from models.database import get_db

bp = Blueprint('payments', __name__, url_prefix='/payments')
square = SquarePaymentService()

@bp.route('/process', methods=['POST'])
@login_required
def process_payment():
    """Process a payment using Square."""
    data = request.get_json()
    
    if not data or 'sourceId' not in data or 'amount' not in data:
        return jsonify({
            'success': False,
            'error': 'Missing required payment information'
        }), 400
    
    try:
        # Create unique idempotency key
        idempotency_key = str(uuid.uuid4())
        
        # Process payment with Square
        result = square.create_payment(
            amount=data['amount'],
            currency='GHS',  # Ghana Cedis
            source_id=data['sourceId'],
            idempotency_key=idempotency_key,
            customer_id=str(current_user.id),
            reference_id=data.get('referenceId')
        )
        
        if result['success']:
            # Update user credits in database
            db = get_db()
            credits_to_add = data['amount'] // 100  # Convert cents to cedis
            db.add_user_credits(current_user.id, credits_to_add)
            
            # Record transaction
            db.record_transaction(
                user_id=current_user.id,
                amount=data['amount'],
                payment_id=result['payment_id'],
                payment_method='square',
                status='completed',
                credits=credits_to_add
            )
            
            return jsonify({
                'success': True,
                'payment': result
            })
        else:
            return jsonify({
                'success': False,
                'error': result['error']
            }), 400
            
    except Exception as e:
        current_app.logger.error(f"Payment processing error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'An error occurred while processing your payment'
        }), 500

@bp.route('/verify/<payment_id>', methods=['GET'])
@login_required
def verify_payment(payment_id):
    """Verify a payment status."""
    try:
        result = square.get_payment(payment_id)
        
        if result['success']:
            return jsonify({
                'success': True,
                'payment': result['payment']
            })
        else:
            return jsonify({
                'success': False,
                'error': result['error']
            }), 400
            
    except Exception as e:
        current_app.logger.error(f"Payment verification error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'An error occurred while verifying your payment'
        }), 500

@bp.route('/refund', methods=['POST'])
@login_required
def refund_payment():
    """Process a payment refund."""
    data = request.get_json()
    
    if not data or 'paymentId' not in data or 'amount' not in data:
        return jsonify({
            'success': False,
            'error': 'Missing required refund information'
        }), 400
    
    try:
        # Create unique idempotency key for refund
        idempotency_key = str(uuid.uuid4())
        
        result = square.refund_payment(
            payment_id=data['paymentId'],
            amount=data['amount'],
            currency='GHS',
            idempotency_key=idempotency_key,
            reason=data.get('reason')
        )
        
        if result['success']:
            # Update user credits in database
            db = get_db()
            credits_to_remove = data['amount'] // 100  # Convert cents to cedis
            db.remove_user_credits(current_user.id, credits_to_remove)
            
            # Record refund transaction
            db.record_transaction(
                user_id=current_user.id,
                amount=-data['amount'],  # Negative amount for refund
                payment_id=result['refund_id'],
                payment_method='square_refund',
                status='completed',
                credits=-credits_to_remove  # Negative credits for refund
            )
            
            return jsonify({
                'success': True,
                'refund': result
            })
        else:
            return jsonify({
                'success': False,
                'error': result['error']
            }), 400
            
    except Exception as e:
        current_app.logger.error(f"Refund processing error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'An error occurred while processing your refund'
        }), 500
