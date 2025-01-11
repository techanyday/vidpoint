from square.client import Client
import uuid
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Square client
client = Client(
    access_token=os.getenv('SQUARE_ACCESS_TOKEN'),
    environment='sandbox'
)

# Create a payment
def create_test_payment():
    try:
        # Create a unique idempotency key
        idempotency_key = str(uuid.uuid4())
        
        # Create the payment
        result = client.payments.create_payment(
            body={
                "source_id": "cnon:card-nonce-ok",  # Test card nonce
                "idempotency_key": idempotency_key,
                "amount_money": {
                    "amount": 1000,  # $10.00
                    "currency": "USD"
                },
                "reference_id": "test_user_123",  # This would be your actual user ID
                "note": "Test payment for webhook",
                "autocomplete": True
            }
        )
        
        if result.is_success():
            print("Payment created successfully!")
            print(f"Payment ID: {result.body['payment']['id']}")
        else:
            print("Error creating payment:")
            print(result.errors)
            
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    create_test_payment()
