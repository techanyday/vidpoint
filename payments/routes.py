from flask import jsonify, request, current_app, url_for, session, redirect
from . import payments
from models.user import User
import requests
import os
from datetime import datetime, timedelta
import json
import hmac
import hashlib

# Hubtel API configuration
HUBTEL_API_BASE = "https://api.hubtel.com/v2/pos"
HUBTEL_CLIENT_ID = os.environ.get('HUBTEL_CLIENT_ID')
HUBTEL_CLIENT_SECRET = os.environ.get('HUBTEL_CLIENT_SECRET')
HUBTEL_MERCHANT_ID = os.environ.get('HUBTEL_MERCHANT_ID')

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

def generate_signature(data, secret):
    """Generate HMAC signature for Hubtel webhook verification"""
    message = json.dumps(data, sort_keys=True)
    signature = hmac.new(
        secret.encode(),
        message.encode(),
        hashlib.sha512
    ).hexdigest()
    return signature

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
    
    # Initialize transaction with Hubtel
    try:
        invoice_id = f"vidpoint_{user.id}_{datetime.utcnow().timestamp()}"
        
        headers = {
            "Authorization": f"Basic {HUBTEL_CLIENT_ID}:{HUBTEL_CLIENT_SECRET}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "invoice": {
                "items": [{
                    "name": f"VidPoint {plan_id.title()} Plan",
                    "quantity": 1,
                    "unitPrice": plan['amount'] / 100,  # Convert from cents to GHS
                    "totalAmount": plan['amount'] / 100
                }],
                "totalAmount": plan['amount'] / 100,
                "description": f"Payment for VidPoint {plan_id.title()} Plan",
                "callbackUrl": url_for('payments.verify_payment', _external=True),
                "returnUrl": url_for('index', _external=True),
                "merchantAccountNumber": HUBTEL_MERCHANT_ID,
                "cancellationUrl": url_for('index', _external=True),
                "clientReference": invoice_id
            }
        }
        
        response = requests.post(
            f"{HUBTEL_API_BASE}/invoice/create",
            headers=headers,
            json=payload
        )
        
        if response.status_code == 200:
            data = response.json()
            
            # Store transaction details in session
            session['pending_transaction'] = {
                'invoice_id': invoice_id,
                'plan_id': plan_id,
                'amount': plan['amount']
            }
            
            return jsonify({
                'status': 'success',
                'checkout_url': data['data']['checkoutUrl']
            })
        
        return jsonify({'error': 'Failed to initialize payment'}), 400
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@payments.route('/verify-payment')
def verify_payment():
    invoice_id = request.args.get('clientReference')
    status = request.args.get('status')
    
    if not invoice_id:
        return jsonify({'error': 'Invalid transaction parameters'}), 400

    try:
        # Verify the transaction with Hubtel
        headers = {
            "Authorization": f"Basic {HUBTEL_CLIENT_ID}:{HUBTEL_CLIENT_SECRET}",
            "Content-Type": "application/json"
        }
        
        response = requests.get(
            f"{HUBTEL_API_BASE}/invoice/status/{invoice_id}",
            headers=headers
        )
        
        if response.status_code == 200:
            data = response.json()
            
            if data['data']['status'] == 'paid':
                # Get the stored transaction details
                pending_transaction = session.get('pending_transaction')
                if not pending_transaction or pending_transaction['invoice_id'] != invoice_id:
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

@payments.route('/webhook', methods=['POST'])
def handle_webhook():
    """Handle Hubtel webhook notifications"""
    signature = request.headers.get('X-Hubtel-Signature')
    if not signature:
        return jsonify({'error': 'Missing signature'}), 401
        
    try:
        payload = request.get_json()
        
        # Verify webhook signature
        expected_signature = generate_signature(payload, HUBTEL_CLIENT_SECRET)
        if signature != expected_signature:
            return jsonify({'error': 'Invalid signature'}), 401
        
        if payload['status'] == 'paid':
            invoice_id = payload['clientReference']
            
            # Get transaction details from database or cache
            # Here we'll need to implement a way to store pending transactions
            # in the database instead of relying on session
            
            user = User.get_by_id(payload['metadata']['user_id'])
            if not user:
                return jsonify({'error': 'User not found'}), 404
                
            plan_id = payload['metadata']['plan_id']
            plan = PLAN_PRICES[plan_id]
            
            # Update user's subscription or credits
            if plan_id in ['starter', 'pro']:
                end_date = datetime.utcnow() + timedelta(days=plan['duration'])
                user.update_subscription(plan_id, end_date)
            else:  # Credits purchase
                user.add_summaries(plan['summaries'])
                
        return jsonify({'status': 'success'}), 200
        
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
