"""Test Square payment integration."""
import os
from dotenv import load_dotenv
from payments.square_service import SquarePaymentService

def test_square_connection():
    """Test Square API connection."""
    # Load environment variables
    load_dotenv()
    
    # Initialize Square service
    square = SquarePaymentService()
    
    # Test connection by trying to get location
    try:
        location_result = square.client.locations.retrieve_location(
            os.getenv('SQUARE_LOCATION_ID')
        )
        
        if location_result.is_success():
            print("✅ Successfully connected to Square API!")
            print(f"Location Name: {location_result.body['location']['name']}")
            print(f"Location ID: {location_result.body['location']['id']}")
            print(f"Currency: {location_result.body['location']['currency']}")
            return True
        else:
            print("❌ Failed to connect to Square API")
            print("Errors:", location_result.errors)
            return False
            
    except Exception as e:
        print("❌ Error testing Square connection:", str(e))
        return False

if __name__ == '__main__':
    test_square_connection()
