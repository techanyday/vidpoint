from flask import jsonify, request, current_app, url_for, session, redirect
from . import payments
from models.user import User
from models.database import Database
import requests
import os
from datetime import datetime, timedelta
import json
import hmac
import hashlib
import uuid

# Hubtel API configuration
HUBTEL_API_BASE = "https://api.hubtel.com/v2/pos"
HUBTEL_CLIENT_ID = os.environ.get('HUBTEL_CLIENT_ID')
HUBTEL_CLIENT_SECRET = os.environ.get('HUBTEL_CLIENT_SECRET')
HUBTEL_MERCHANT_ID = os.environ.get('HUBTEL_MERCHANT_ID')

PLAN_PRICES = {
    'starter': {
        'amount': 499,  # Amount in cents (GHS 4.99)
        'duration': 30,  # days
        'summaries': 100
    },
    'pro': {
        'amount': 999,  # Amount in cents (GHS 9.99)
        'duration': 30,
        'summaries': 'Unlimited'
    },
    'credits-500': {
        'amount': 500,  # Amount in cents (GHS 5.00)
        'summaries': 500
    },
    'credits-1000': {
        'amount': 1000,  # Amount in cents (GHS 10.00)
        'summaries': 1000
    }
}

def generate_signature(data, secret):
    """Generate HMAC signature for Hubtel webhook verification"""
    message = json.dumps(data, sort_keys=True)
    signature = hmac.new(
        secret.encode(),
        message.encode(),
        hashlib.sha512
    ).hexdigest()
    return signature

@payments.route('/checkout/<plan_id>')
def checkout(plan_id):
    """Show the checkout page for a specific plan."""
    plans = {
        'starter': {
            'id': 'starter',
            'name': 'Starter Plan',
            'amount': 499,  # Amount in pesewas (GHS 4.99)
            'duration': 30,
            'summaries': '100 summaries/month'
        },
        'pro': {
            'id': 'pro',
            'name': 'Pro Plan',
            'amount': 999,  # Amount in pesewas (GHS 9.99)
            'duration': 30,
            'summaries': 'Unlimited summaries'
        },
        'credits-500': {
            'id': 'credits-500',
            'name': '500 Credits',
            'amount': 500,  # Amount in pesewas (GHS 5.00)
            'duration': None,
            'summaries': '500 summaries'
        },
        'credits-1000': {
            'id': 'credits-1000',
            'name': '1000 Credits',
            'amount': 1000,  # Amount in pesewas (GHS 10.00)
            'duration': None,
            'summaries': '1000 summaries'
        }
    }
    
    plan = plans.get(plan_id)
    if not plan:
        return jsonify({'error': 'Invalid plan'}), 404
        
    return jsonify(plan)

@payments.route('/initialize-payment', methods=['POST'])
def initialize_payment():
    """Initialize a payment with Hubtel."""
    try:
        data = request.get_json()
        plan_id = data.get('plan')
        payment_method = data.get('payment_method')
        provider = data.get('provider')
        
        # Get plan details
        plans = {
            'starter': {
                'amount': 499,
                'description': 'Starter Plan - 100 summaries/month'
            },
            'pro': {
                'amount': 999,
                'description': 'Pro Plan - Unlimited summaries'
            },
            'credits-500': {
                'amount': 500,
                'description': '500 Credits'
            },
            'credits-1000': {
                'amount': 1000,
                'description': '1000 Credits'
            }
        }
        
        plan = plans.get(plan_id)
        if not plan:
            return jsonify({'status': 'error', 'error': 'Invalid plan'}), 400
            
        # Create transaction record
        invoice_id = str(uuid.uuid4())
        db = Database()
        db.create_transaction(
            user_id=session['user_id'],
            plan_id=plan_id,
            amount=plan['amount'],
            invoice_id=invoice_id
        )
        
        # Initialize Hubtel payment
        hubtel = Hubtel(
            client_id=HUBTEL_CLIENT_ID,
            client_secret=HUBTEL_CLIENT_SECRET,
            merchant_id=HUBTEL_MERCHANT_ID
        )
        
        payment_data = {
            'amount': plan['amount'],
            'title': 'VidPoint ' + plan['description'],
            'description': plan['description'],
            'clientReference': invoice_id,
            'callbackUrl': url_for('payments.webhook', _external=True),
            'returnUrl': url_for('payments.complete', _external=True),
            'cancellationUrl': url_for('payments.cancel', _external=True)
        }
        
        if payment_method == 'momo':
            payment_data['paymentMethod'] = provider.upper()
        
        response = hubtel.initiate_payment(payment_data)
        
        if response['status'] == 'Success':
            return jsonify({
                'status': 'success',
                'checkout_url': response['checkoutUrl']
            })
        else:
            return jsonify({
                'status': 'error',
                'error': response.get('message', 'Payment initialization failed')
            }), 400
            
    except Exception as e:
        current_app.logger.error(f'Payment initialization error: {str(e)}')
        return jsonify({
            'status': 'error',
            'error': 'An error occurred while initializing payment'
        }), 500

@payments.route('/webhook', methods=['POST'])
def webhook():
    """Handle Hubtel payment webhook."""
    try:
        # Verify webhook signature
        signature = request.headers.get('X-Hubtel-Signature')
        if not signature:
            return 'Missing signature', 400
            
        raw_data = request.get_data()
        expected_signature = hmac.new(
            HUBTEL_CLIENT_SECRET.encode(),
            raw_data,
            hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(signature, expected_signature):
            return 'Invalid signature', 400
            
        # Process webhook data
        data = request.get_json()
        invoice_id = data['clientReference']
        status = data['status']
        
        db = Database()
        db.update_transaction_status(invoice_id, status, data)
        
        if status == 'Success':
            # Get transaction details
            transaction = db.find_one('transactions', {'invoice_id': invoice_id})
            if transaction:
                if transaction['plan_id'].startswith('credits'):
                    # Add credits
                    credits = 500 if transaction['plan_id'] == 'credits-500' else 1000
                    db.update_user_credits(transaction['user_id'], credits)
                else:
                    # Update subscription
                    end_date = datetime.utcnow() + timedelta(days=30)
                    db.update_user_subscription(
                        transaction['user_id'],
                        transaction['plan_id'],
                        end_date
                    )
                    
                # Send success email
                user = db.find_one('users', {'_id': transaction['user_id']})
                if user:
                    send_payment_success_email(
                        user['email'],
                        transaction['plan_id'],
                        transaction['amount']
                    )
        
        return 'OK', 200
        
    except Exception as e:
        current_app.logger.error(f'Webhook processing error: {str(e)}')
        return 'Internal error', 500

@payments.route('/complete')
def complete():
    """Handle successful payment completion."""
    return redirect(url_for('index', payment_status='success'))

@payments.route('/cancel')
def cancel():
    """Handle payment cancellation."""
    return redirect(url_for('index', payment_status='cancelled'))

@payments.route('/payment-methods')
def get_payment_methods():
    """Get available payment methods"""
    return jsonify({
        'methods': [
            {
                'id': 'card',
                'name': 'Credit/Debit Card',
                'description': 'Pay with Visa or Mastercard'
            },
            {
                'id': 'momo',
                'name': 'Mobile Money',
                'description': 'Pay with Mobile Money',
                'providers': [
                    {
                        'id': 'mtn',
                        'name': 'MTN Mobile Money'
                    },
                    {
                        'id': 'vodafone',
                        'name': 'Vodafone Cash'
                    },
                    {
                        'id': 'tigo',
                        'name': 'AirtelTigo Money'
                    }
                ]
            }
        ]
    })
