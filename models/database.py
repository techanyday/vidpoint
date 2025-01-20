"""Database interface for VidPoint."""
import json
import os
import time
from urllib.parse import urlparse
from pymongo import MongoClient, ASCENDING
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError, OperationFailure
from datetime import datetime
from typing import Optional, Dict, List

class Database:
    _instance = None
    MAX_RETRY_ATTEMPTS = 3
    RETRY_DELAY_SECONDS = 5

    @classmethod
    def _get_connection_uri(cls, uri: str) -> str:
        """Process MongoDB URI to ensure proper format."""
        if not uri:
            raise ValueError("MongoDB URI cannot be empty")
            
        if uri.startswith('mongodb+srv://'):
            print("Using MongoDB Atlas connection")
            return uri  # Return the srv URI as is for Atlas connections
            
        return uri

    @classmethod
    def _connect_with_retry(cls, uri: str) -> MongoClient:
        """Attempt to connect to MongoDB with retries."""
        last_error = None
        
        for attempt in range(cls.MAX_RETRY_ATTEMPTS):
            try:
                print(f"MongoDB connection attempt {attempt + 1}/{cls.MAX_RETRY_ATTEMPTS}")
                
                # Parse the URI to extract database name
                parsed_uri = urlparse(uri)
                db_name = parsed_uri.path.lstrip('/').split('?')[0]
                print(f"Connecting to database: {db_name}")
                
                # Use Atlas-optimized settings
                client = MongoClient(
                    uri,
                    connectTimeoutMS=30000,
                    serverSelectionTimeoutMS=30000,
                    socketTimeoutMS=30000,
                    retryWrites=True,
                    retryReads=True,
                    w='majority',
                    maxPoolSize=50,
                    minPoolSize=10,
                    maxIdleTimeMS=60000,
                    appName='VidPoint'
                )
                
                # Test connection with a light command
                client.admin.command('ping')
                print(f"Successfully connected to MongoDB Atlas - Database: {db_name}")
                
                # Verify we can access the specific database
                db = client[db_name]
                db.list_collection_names()
                print("Database access verified")
                
                return client
                
            except (ConnectionFailure, ServerSelectionTimeoutError) as e:
                last_error = e
                error_msg = str(e).lower()
                
                if "unauthorized" in error_msg:
                    print("\nAuthentication Error:")
                    print("1. Check if username 'lawrencekarthur' is correct")
                    print("2. Verify the password in the connection string")
                    print("3. Ensure the user has readWrite permissions")
                    raise ConnectionFailure("Authentication failed. Please check your MongoDB Atlas credentials.")
                elif "network" in error_msg or "timeout" in error_msg:
                    print("\nNetwork Error:")
                    print("1. Checking connection to cluster0.us2j7.mongodb.net")
                    print("2. Ensure IP 0.0.0.0/0 is in Atlas Network Access")
                    print("3. Verify Render's outbound connections")
                
                print(f"Connection attempt {attempt + 1} failed: {str(e)}")
                if attempt < cls.MAX_RETRY_ATTEMPTS - 1:
                    print(f"Retrying in {cls.RETRY_DELAY_SECONDS} seconds...")
                    time.sleep(cls.RETRY_DELAY_SECONDS)
            except OperationFailure as e:
                if e.code == 8000:
                    print("\nDatabase Access Error:")
                    print("1. Verify access to 'vidpoint' database")
                    print("2. Check user permissions in MongoDB Atlas")
                    raise ConnectionFailure("Database access denied. Please check permissions.")
                raise
                    
        raise ConnectionFailure(f"Failed to connect to MongoDB Atlas after {cls.MAX_RETRY_ATTEMPTS} attempts. Last error: {str(last_error)}")

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Database, cls).__new__(cls)
            
            # Initialize MongoDB connection
            mongodb_uri = os.environ.get('MONGODB_URI')
            if not mongodb_uri:
                mongodb_uri = 'mongodb://localhost:27017/vidpoint'
                print("Warning: Using localhost MongoDB. Set MONGODB_URI for production.")
            
            try:
                # Process the connection URI
                processed_uri = cls._get_connection_uri(mongodb_uri)
                print("Connecting to MongoDB...")
                
                # Connect with retry mechanism
                client = cls._connect_with_retry(processed_uri)
                cls._instance.client = client
                
                # Get database name from URI or use default
                parsed_uri = urlparse(mongodb_uri)
                db_name = parsed_uri.path.lstrip('/') or 'vidpoint'
                cls._instance.db = client[db_name]
                print(f"Using database: {cls._instance.db.name}")
                
                # Initialize database and collections
                cls._instance._init_database()
            except Exception as e:
                print(f"Error initializing database: {str(e)}")
                print("\nTroubleshooting steps:")
                print("1. Check if your IP is whitelisted in MongoDB Atlas")
                print("2. Verify your MongoDB URI format")
                print("3. Ensure all environment variables are set")
                print("4. Check MongoDB Atlas network access settings")
                raise
                
        return cls._instance

    def _init_database(self):
        """Initialize database collections and indexes."""
        try:
            # Create collections if they don't exist
            if 'users' not in self.db.list_collection_names():
                self.db.create_collection('users')
            
            # Create indexes
            self.db.users.create_index([('email', ASCENDING)], unique=True)
            self.db.users.create_index([('google_id', ASCENDING)], sparse=True)
            
            print("Database collections and indexes initialized")
        except Exception as e:
            print(f"Error initializing collections and indexes: {str(e)}")
            raise

    def insert_one(self, collection, document):
        """Insert a document into a collection."""
        print(f"Inserting document into {collection}:")
        for key, value in document.items():
            print(f"  {key}: {type(value)}")
        
        if '_id' not in document:
            document['created_at'] = datetime.utcnow()
            document['updated_at'] = datetime.utcnow()
        try:
            result = self.db[collection].insert_one(document)
            print(f"Successfully inserted document with id: {result.inserted_id}")
            return str(result.inserted_id)
        except Exception as e:
            print(f"Error inserting document: {str(e)}")
            raise

    def find_one(self, collection, query):
        """Find a single document matching the query."""
        print(f"Finding document in {collection} with query: {query}")
        try:
            result = self.db[collection].find_one(query)
            if result:
                print(f"Found document:")
                for key, value in result.items():
                    print(f"  {key}: {type(value)}")
            else:
                print("No document found")
            return result
        except Exception as e:
            print(f"Error finding document: {str(e)}")
            raise

    def find_many(self, collection, query, sort=None, limit=None):
        """Find multiple documents matching the query."""
        print(f"Finding multiple documents in {collection} with query: {query}")
        try:
            cursor = self.db[collection].find(query)
            if sort:
                cursor = cursor.sort(sort)
            if limit:
                cursor = cursor.limit(limit)
            result = list(cursor)
            print(f"Found {len(result)} documents")
            return result
        except Exception as e:
            print(f"Error finding documents: {str(e)}")
            raise

    def update_one(self, collection, query, update_data):
        """Update a single document matching the query."""
        print(f"Updating document in {collection} with query: {query}")
        print("Update data:")
        for key, value in update_data.items():
            print(f"  {key}: {type(value)}")
        
        update_data['updated_at'] = datetime.utcnow()
        try:
            result = self.db[collection].update_one(
                query,
                {'$set': update_data}
            )
            print(f"Modified {result.modified_count} documents")
            return result.modified_count > 0
        except Exception as e:
            print(f"Error updating document: {str(e)}")
            raise

    def delete_one(self, collection, query):
        """Delete a single document matching the query."""
        print(f"Deleting document in {collection} with query: {query}")
        try:
            result = self.db[collection].delete_one(query)
            print(f"Deleted {result.deleted_count} documents")
            return result.deleted_count > 0
        except Exception as e:
            print(f"Error deleting document: {str(e)}")
            raise

    # Transaction specific methods
    def create_transaction(self, user_id, plan_id, amount, invoice_id):
        """Create a new transaction record."""
        print(f"Creating transaction for user {user_id} with plan {plan_id} and amount {amount}")
        transaction = {
            'user_id': user_id,
            'plan_id': plan_id,
            'amount': amount,
            'invoice_id': invoice_id,
            'status': 'pending',
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        return self.insert_one('transactions', transaction)

    def update_transaction_status(self, invoice_id, status, payment_data=None):
        """Update transaction status and payment data."""
        print(f"Updating transaction status for invoice {invoice_id} to {status}")
        update_data = {
            'status': status,
            'updated_at': datetime.utcnow()
        }
        if payment_data:
            update_data['payment_data'] = payment_data
        
        return self.update_one(
            'transactions',
            {'invoice_id': invoice_id},
            update_data
        )

    def get_user_transactions(self, user_id, limit=None):
        """Get user's transactions."""
        print(f"Getting transactions for user {user_id}")
        query = {'user_id': user_id}
        try:
            cursor = self.db.transactions.find(query).sort('created_at', -1)
            if limit:
                cursor = cursor.limit(limit)
            result = list(cursor)
            print(f"Found {len(result)} transactions")
            return result
        except Exception as e:
            print(f"Error getting transactions: {str(e)}")
            raise

    # Subscription specific methods
    def get_user_subscription(self, user_id):
        """Get user's current subscription."""
        print(f"Getting subscription for user {user_id}")
        return self.find_one('subscriptions', {'user_id': user_id})

    def update_user_subscription(self, user_id, plan_id, end_date):
        """Update user's subscription."""
        print(f"Updating subscription for user {user_id} to plan {plan_id} with end date {end_date}")
        subscription = {
            'user_id': user_id,
            'plan_id': plan_id,
            'end_date': end_date,
            'status': 'active'
        }
        
        existing = self.get_user_subscription(user_id)
        if existing:
            return self.update_one('subscriptions', {'user_id': user_id}, subscription)
        else:
            return self.insert_one('subscriptions', subscription)

    # Credit specific methods
    def get_user_credits(self, user_id):
        """Get user's current credits."""
        print(f"Getting credits for user {user_id}")
        return self.find_one('credits', {'user_id': user_id})

    def update_user_credits(self, user_id, amount):
        """Update user's credits."""
        print(f"Updating credits for user {user_id} by {amount}")
        credits = self.get_user_credits(user_id)
        if credits:
            new_amount = credits.get('amount', 0) + amount
            return self.update_one(
                'credits',
                {'user_id': user_id},
                {'amount': new_amount}
            )
        else:
            return self.insert_one('credits', {
                'user_id': user_id,
                'amount': amount
            })

    # Dashboard specific methods
    def update_user_settings(self, user_id, settings):
        """Update user settings."""
        print(f"Updating settings for user {user_id}")
        try:
            result = self.db.users.update_one(
                {'_id': user_id},
                {'$set': settings}
            )
            print(f"Updated settings for user {user_id}")
            return result.modified_count > 0
        except Exception as e:
            print(f"Failed to update settings for user {user_id}: {str(e)}")
            return False

    def get_user_stats(self, user_id):
        """Get user statistics."""
        print(f"Getting statistics for user {user_id}")
        pipeline = [
            {'$match': {'user_id': user_id}},
            {'$group': {
                '_id': None,
                'videos_processed': {'$sum': 1},
                'total_processing_time': {'$sum': '$processing_time'}
            }}
        ]
        
        try:
            result = list(self.db.video_exports.aggregate(pipeline))
            if result:
                stats = result[0]
                del stats['_id']
                print(f"Found statistics for user {user_id}: {stats}")
                return stats
            print("No statistics found for user")
            return {
                'videos_processed': 0,
                'total_processing_time': 0
            }
        except Exception as e:
            print(f"Error getting statistics: {str(e)}")
            raise

    def get_notification_history(self, user_id, limit=10, skip=0):
        """Get user's notification history."""
        print(f"Getting notification history for user {user_id}")
        try:
            return list(self.db.notifications.find(
                {'user_id': user_id}
            ).sort('sent_at', -1).skip(skip).limit(limit))
        except Exception as e:
            print(f"Error getting notification history: {str(e)}")
            raise

    def update_notification_preferences(self, user_id, preferences):
        """Update user's notification preferences."""
        print(f"Updating notification preferences for user {user_id}")
        try:
            result = self.db.users.update_one(
                {'_id': user_id},
                {'$set': {'notification_preferences': preferences}}
            )
            print(f"Updated notification preferences for user {user_id}")
            return result.modified_count > 0
        except Exception as e:
            print(f"Failed to update notification preferences for user {user_id}: {str(e)}")
            return False

    def get_notification_preferences(self, user_id):
        """Get user's notification preferences."""
        print(f"Getting notification preferences for user {user_id}")
        try:
            user = self.db.users.find_one(
                {'_id': user_id},
                {'notification_preferences': 1}
            )
            if user:
                print(f"Found notification preferences for user {user_id}: {user.get('notification_preferences')}")
                return user.get('notification_preferences', {
                    'subscription_expiry': True,
                    'low_credits': True,
                    'payment_confirmation': True,
                    'export_complete': True,
                    'promotional': False,
                    'email_digest': 'daily'  # Options: 'daily', 'weekly', 'none'
                })
            print("No notification preferences found for user")
            return {
                'subscription_expiry': True,
                'low_credits': True,
                'payment_confirmation': True,
                'export_complete': True,
                'promotional': False,
                'email_digest': 'daily'  # Options: 'daily', 'weekly', 'none'
            }
        except Exception as e:
            print(f"Error getting notification preferences: {str(e)}")
            raise

def init_db(app):
    """Initialize the database with the Flask app."""
    db = get_db()
    app.config['db'] = db
    return db

def get_db():
    """Get the database instance."""
    return Database()
