"""Database interface for VidPoint."""
import json
import os
import time
import certifi
from pymongo import MongoClient, server_api
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from datetime import datetime
from typing import Optional, Dict, List

class Database:
    _instance = None
    MAX_RETRY_ATTEMPTS = 3
    RETRY_DELAY_SECONDS = 5

    @classmethod
    def _connect_with_retry(cls, uri: str) -> MongoClient:
        """Attempt to connect to MongoDB with retries."""
        last_error = None
        
        for attempt in range(cls.MAX_RETRY_ATTEMPTS):
            try:
                print(f"MongoDB connection attempt {attempt + 1}/{cls.MAX_RETRY_ATTEMPTS}")
                
                # Configure MongoDB client with retries and timeouts
                client = MongoClient(
                    uri,
                    tlsCAFile=certifi.where(),
                    serverSelectionTimeoutMS=5000,
                    connectTimeoutMS=5000,
                    socketTimeoutMS=10000,
                    maxPoolSize=1,
                    retryWrites=True
                )
                
                # Test connection with a light command
                client.admin.command('ping')
                print("Successfully connected to MongoDB")
                return client
                
            except (ConnectionFailure, ServerSelectionTimeoutError) as e:
                last_error = e
                print(f"Connection attempt {attempt + 1} failed: {str(e)}")
                if attempt < cls.MAX_RETRY_ATTEMPTS - 1:
                    print(f"Retrying in {cls.RETRY_DELAY_SECONDS} seconds...")
                    time.sleep(cls.RETRY_DELAY_SECONDS)
                    
        raise ConnectionFailure(f"Failed to connect after {cls.MAX_RETRY_ATTEMPTS} attempts. Last error: {str(last_error)}")

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Database, cls).__new__(cls)
            
            # Initialize MongoDB connection
            mongodb_uri = os.environ.get('MONGODB_URI')
            if not mongodb_uri:
                mongodb_uri = 'mongodb://localhost:27017/vidpoint'
                print("Warning: Using localhost MongoDB. Set MONGODB_URI for production.")
            
            # Convert srv URI to direct connection if needed
            if mongodb_uri.startswith('mongodb+srv://'):
                print("Converting srv URI to direct connection...")
                parts = mongodb_uri.replace('mongodb+srv://', '').split('@')
                if len(parts) == 2:
                    auth, host = parts
                    cluster = host.split('/')[0]
                    rest = '/'.join(host.split('/')[1:])
                    mongodb_uri = f'mongodb://{auth}@{cluster}:27017/{rest}'
            
            try:
                # Connect with retry mechanism
                client = cls._connect_with_retry(mongodb_uri)
                cls._instance.client = client
                cls._instance.db = client.get_database()
                print(f"Using database: {cls._instance.db.name}")
                
                # Initialize database and collections
                cls._instance._init_database()
            except Exception as e:
                print(f"Error initializing database: {str(e)}")
                raise
                
        return cls._instance

    def _init_database(self):
        """Initialize database and collections with indexes."""
        try:
            # Create collections if they don't exist
            if 'users' not in self.db.list_collection_names():
                print("Creating users collection")
                self.db.create_collection('users')
                # Create indexes
                self.db.users.create_index('email', unique=True)
                print("Created index on users.email")

            if 'transactions' not in self.db.list_collection_names():
                print("Creating transactions collection")
                self.db.create_collection('transactions')
                # Create indexes
                self.db.transactions.create_index('user_id')
                self.db.transactions.create_index('invoice_id', unique=True)
                print("Created indexes on transactions collection")

            if 'notifications' not in self.db.list_collection_names():
                print("Creating notifications collection")
                self.db.create_collection('notifications')
                # Create indexes
                self.db.notifications.create_index('user_id')
                self.db.notifications.create_index('sent_at')
                print("Created indexes on notifications collection")

            if 'subscriptions' not in self.db.list_collection_names():
                print("Creating subscriptions collection")
                self.db.create_collection('subscriptions')
                # Create indexes
                self.db.subscriptions.create_index('user_id', unique=True)
                print("Created index on subscriptions.user_id")

            if 'credits' not in self.db.list_collection_names():
                print("Creating credits collection")
                self.db.create_collection('credits')
                # Create indexes
                self.db.credits.create_index('user_id', unique=True)
                print("Created index on credits.user_id")

            if 'video_exports' not in self.db.list_collection_names():
                print("Creating video_exports collection")
                self.db.create_collection('video_exports')
                # Create indexes
                self.db.video_exports.create_index('user_id')
                self.db.video_exports.create_index('created_at')
                print("Created indexes on video_exports collection")

            print("Database initialization complete")
        except Exception as e:
            print(f"Error initializing database: {str(e)}")
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

def get_db():
    """Get the database instance."""
    return Database()
