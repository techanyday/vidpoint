"""Database interface for VidPoint."""
import json
import os
from pymongo import MongoClient
from datetime import datetime
from typing import Optional, Dict, List

class Database:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Database, cls).__new__(cls)
            # Initialize MongoDB connection
            mongodb_uri = os.environ.get('MONGODB_URI', 'mongodb://localhost:27017')
            client = MongoClient(mongodb_uri)
            cls._instance.db = client.vidpoint
        return cls._instance

    def insert_one(self, collection, document):
        """Insert a document into a collection."""
        if '_id' not in document:
            document['created_at'] = datetime.utcnow()
            document['updated_at'] = datetime.utcnow()
        result = self.db[collection].insert_one(document)
        return str(result.inserted_id)

    def find_one(self, collection, query):
        """Find a single document matching the query."""
        return self.db[collection].find_one(query)

    def find_many(self, collection, query, sort=None, limit=None):
        """Find multiple documents matching the query."""
        cursor = self.db[collection].find(query)
        if sort:
            cursor = cursor.sort(sort)
        if limit:
            cursor = cursor.limit(limit)
        return list(cursor)

    def update_one(self, collection, query, update_data):
        """Update a single document matching the query."""
        update_data['updated_at'] = datetime.utcnow()
        result = self.db[collection].update_one(
            query,
            {'$set': update_data}
        )
        return result.modified_count > 0

    def delete_one(self, collection, query):
        """Delete a single document matching the query."""
        result = self.db[collection].delete_one(query)
        return result.deleted_count > 0

    # Transaction specific methods
    def create_transaction(self, user_id, plan_id, amount, invoice_id):
        """Create a new transaction record."""
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

    def get_user_transactions(self, user_id, limit=10):
        """Get user's transaction history."""
        return self.find_many(
            'transactions',
            {'user_id': user_id},
            sort=[('created_at', -1)],
            limit=limit
        )

    # Subscription specific methods
    def get_user_subscription(self, user_id):
        """Get user's current subscription."""
        return self.find_one('subscriptions', {'user_id': user_id})

    def update_user_subscription(self, user_id, plan_id, end_date):
        """Update user's subscription."""
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
        return self.find_one('credits', {'user_id': user_id})

    def update_user_credits(self, user_id, amount):
        """Update user's credits."""
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
