from flask import jsonify, request, current_app, url_for, session, redirect
from . import payments
from models.user import User
from paystackapi.paystack import Paystack
from paystackapi.transaction import Transaction
import os
from datetime import datetime, timedelta

paystack = Paystack(secret_key=os.environ.get('PAYSTACK_SECRET_KEY'))

PLAN_PRICES = {
    'starter': {
        'amount': 499,  # Amount in cents (GHS 4.99)
        'duration': 30,  # days
        'summaries': 50
    },
    'pro': {
        'amount': 999,  # Amount in cents (GHS 9.99)
        'duration': 30,
        'summaries': 1000
    },
    'credits_500': {
        'amount': 500,  # Amount in cents (GHS 5.00)
        'summaries': 500
    },
    'credits_1000': {
        'amount': 1000,  # Amount in cents (GHS 10.00)
        'summaries': 1000
    }
}

@payments.route('/initialize-payment', methods=['POST'])
def initialize_payment():
    if 'user_id' not in session:
        return jsonify({'error': 'User not authenticated'}), 401

    user = User.get_by_id(session['user_id'])
    if not user:
        return jsonify({'error': 'User not found'}), 404

    plan_id = request.json.get('plan')
    if plan_id not in PLAN_PRICES:
        return jsonify({'error': 'Invalid plan selected'}), 400

    plan = PLAN_PRICES[plan_id]
    
    # Initialize transaction with Paystack
    try:
        response = Transaction.initialize(
            reference=f"vidpoint_{user.id}_{datetime.utcnow().timestamp()}",
            email=user.email,
            amount=plan['amount'] * 100,  # Convert to pesewas
            callback_url=url_for('payments.verify_payment', _external=True)
        )
        
        if response['status']:
            # Store transaction details in session
            session['pending_transaction'] = {
                'reference': response['data']['reference'],
                'plan_id': plan_id,
                'amount': plan['amount']
            }
            
            return jsonify({
                'status': 'success',
                'authorization_url': response['data']['authorization_url']
            })
        
        return jsonify({'error': 'Failed to initialize payment'}), 400
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@payments.route('/verify-payment')
def verify_payment():
    reference = request.args.get('reference')
    if not reference:
        return jsonify({'error': 'No reference provided'}), 400

    try:
        response = Transaction.verify(reference=reference)
        
        if response['status'] and response['data']['status'] == 'success':
            # Get the stored transaction details
            pending_transaction = session.get('pending_transaction')
            if not pending_transaction or pending_transaction['reference'] != reference:
                return jsonify({'error': 'Invalid transaction'}), 400

            user = User.get_by_id(session['user_id'])
            if not user:
                return jsonify({'error': 'User not found'}), 404

            plan_id = pending_transaction['plan_id']
            plan = PLAN_PRICES[plan_id]

            # Update user's subscription or credits
            if plan_id in ['starter', 'pro']:
                end_date = datetime.utcnow() + timedelta(days=plan['duration'])
                user.update_subscription(plan_id, end_date)
            else:  # Credits purchase
                user.add_summaries(plan['summaries'])

            # Clear the pending transaction
            session.pop('pending_transaction', None)

            return redirect(url_for('index', payment_status='success'))
        
        return redirect(url_for('index', payment_status='failed'))

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@payments.route('/payment-methods')
def get_payment_methods():
    """Get available payment methods"""
    return jsonify({
        'methods': [
            {
                'id': 'card',
                'name': 'Credit/Debit Card',
                'description': 'Pay with Visa, Mastercard, or Verve'
            },
            {
                'id': 'momo',
                'name': 'Mobile Money',
                'description': 'Pay with MTN Mobile Money, Vodafone Cash, or AirtelTigo Money'
            }
        ]
    })
