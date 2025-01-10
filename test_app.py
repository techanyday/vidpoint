from flask import Flask, render_template, request, jsonify
import os
from square.client import Client
import uuid
from dotenv import load_dotenv
from routes.webhooks import bp as webhooks_bp

app = Flask(__name__)
load_dotenv()

# Enable debug mode
app.debug = True

# Configure Square webhook signing key
app.config['SQUARE_WEBHOOK_SIGNING_KEY'] = os.getenv('SQUARE_WEBHOOK_SIGNING_KEY')

# Register blueprints
app.register_blueprint(webhooks_bp)

# Initialize Square client
square_client = Client(
    access_token=os.getenv('SQUARE_ACCESS_TOKEN'),
    environment='sandbox'
)

@app.route('/')
def hello():
    return 'Hello! VidPoint payment integration is working!'

@app.route('/test-payment')
def test_payment():
    app.logger.info('Loading test payment page')
    app.logger.info(f'Square App ID: {os.getenv("SQUARE_APP_ID")}')
    app.logger.info(f'Square Location ID: {os.getenv("SQUARE_LOCATION_ID")}')
    
    return render_template('test_payment.html',
                         square_app_id=os.getenv('SQUARE_APP_ID'),
                         square_location_id=os.getenv('SQUARE_LOCATION_ID'))

@app.route('/process-payment', methods=['POST'])
def process_payment():
    data = request.get_json()
    app.logger.info('Processing payment')
    app.logger.info(f'Payment data: {data}')
    
    try:
        # Create the payment with Square
        result = square_client.payments.create_payment(
            body={
                "source_id": data['sourceId'],
                "idempotency_key": data['idempotencyKey'],
                "amount_money": {
                    "amount": data['amount'],
                    "currency": "USD"
                },
                "reference_id": "test_user_123",
                "note": "Test payment for webhook"
            }
        )
        
        if result.is_success():
            app.logger.info(f'Payment successful: {result.body}')
            return jsonify(result.body)
        else:
            app.logger.error(f'Payment failed: {result.errors}')
            return jsonify({"errors": result.errors}), 400
            
    except Exception as e:
        app.logger.error(f'Payment error: {str(e)}')
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(port=5000, debug=True)
