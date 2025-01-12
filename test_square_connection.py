"""Test Square payment integration."""
import os
import sys
from square.client import Client
from dotenv import load_dotenv

def test_square_connection():
    """Test Square API connection."""
    # Load environment variables
    load_dotenv()
    
    print("\nTesting Square API connection...")

    try:
        # Initialize Square client with access token
        client = Client(
            access_token=os.getenv('SQUARE_ACCESS_TOKEN'),
            environment=os.getenv('SQUARE_ENVIRONMENT', 'production')
        )

        # Test connection by retrieving location
        location_result = client.locations.retrieve_location(
            location_id=os.getenv('SQUARE_LOCATION_ID')
        )

        if location_result.is_success():
            print("\nSUCCESS: Successfully connected to Square API!")
            print(f"Location Name: {location_result.body['location']['name']}")
            return True
        else:
            print("\nERROR: Failed to connect to Square API")
            print(f"Error: {location_result.errors}")
            return False

    except Exception as e:
        print("\nERROR: Error testing Square connection:", str(e))
        return False

if __name__ == '__main__':
    test_square_connection()
