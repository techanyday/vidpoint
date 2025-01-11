"""Test Square payment integration."""
import os
from dotenv import load_dotenv
from square.client import Client

def test_square_connection():
    """Test Square API connection."""
    # Load environment variables
    load_dotenv()
    
    # Initialize Square client with access token
    client = Client(
        access_token=os.getenv('SQUARE_ACCESS_TOKEN'),
        environment=os.getenv('SQUARE_ENVIRONMENT', 'sandbox'),
        custom_url='https://connect.squareupsandbox.com'
    )
    
    # Test connection by trying to get location
    try:
        location_result = client.locations.retrieve_location(
            location_id=os.getenv('SQUARE_LOCATION_ID')
        )
        
        if location_result.is_success():
            print("\nSUCCESS: Successfully connected to Square API!")
            print(f"Location Name: {location_result.body['location']['name']}")
            print(f"Location ID: {location_result.body['location']['id']}")
            print(f"Currency: {location_result.body['location']['currency']}")
            return True
        else:
            print("\nERROR: Failed to connect to Square API")
            print("Errors:", location_result.errors)
            return False
            
    except Exception as e:
        print("\nERROR: Error testing Square connection:", str(e))
        return False

if __name__ == '__main__':
    test_square_connection()
