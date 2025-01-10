"""Square payment integration service."""
import os
import uuid
from typing import Dict, Optional, List
from square.client import Client
from datetime import datetime

class SquarePaymentService:
    """Service for handling Square payment operations."""
    
    def __init__(self):
        """Initialize Square client."""
        self.client = Client(
            access_token=os.getenv('SQUARE_ACCESS_TOKEN'),
            environment=os.getenv('SQUARE_ENVIRONMENT', 'sandbox')
        )
        self.location_id = os.getenv('SQUARE_LOCATION_ID')
    
    def create_payment(self, 
                      amount: int,
                      source_id: str,
                      payment_type: str = 'card',
                      currency: str = 'USD',
                      customer_id: Optional[str] = None,
                      reference_id: Optional[str] = None,
                      note: Optional[str] = None) -> Dict:
        """Create a payment using Square API.
        
        Args:
            amount: Amount in smallest currency unit (e.g., cents)
            source_id: Payment source ID from Square.js
            payment_type: Type of payment ('card' or 'mobile_money')
            currency: Currency code (e.g., 'USD', 'GHS')
            customer_id: Optional Square customer ID
            reference_id: Optional reference ID for tracking
            note: Optional note for the payment
            
        Returns:
            Dict containing payment details or error
        """
        try:
            idempotency_key = str(uuid.uuid4())
            
            body = {
                "source_id": source_id,
                "idempotency_key": idempotency_key,
                "amount_money": {
                    "amount": amount,
                    "currency": currency
                },
                "autocomplete": True
            }
            
            if customer_id:
                body["customer_id"] = customer_id
            if reference_id:
                body["reference_id"] = reference_id
            if note:
                body["note"] = note
                
            # Add specific fields for mobile money
            if payment_type == 'mobile_money':
                body["payment_type"] = "MOBILE_MONEY"
            
            result = self.client.payments.create_payment(body)
            
            if result.is_success():
                return {
                    "success": True,
                    "payment_id": result.body["payment"]["id"],
                    "status": result.body["payment"]["status"],
                    "amount": result.body["payment"]["amount_money"]["amount"],
                    "currency": result.body["payment"]["amount_money"]["currency"],
                    "created_at": result.body["payment"]["created_at"],
                    "receipt_url": result.body["payment"].get("receipt_url")
                }
            else:
                return {
                    "success": False,
                    "error": result.errors
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_payment(self, payment_id: str) -> Dict:
        """Retrieve payment details."""
        try:
            result = self.client.payments.get_payment(payment_id)
            
            if result.is_success():
                return {
                    "success": True,
                    "payment": result.body["payment"]
                }
            else:
                return {
                    "success": False,
                    "error": result.errors
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def list_payments(self, 
                     begin_time: Optional[datetime] = None,
                     end_time: Optional[datetime] = None,
                     cursor: Optional[str] = None,
                     limit: int = 100) -> Dict:
        """List payments with optional filtering."""
        try:
            body = {}
            if begin_time:
                body["begin_time"] = begin_time.isoformat()
            if end_time:
                body["end_time"] = end_time.isoformat()
            if cursor:
                body["cursor"] = cursor
            body["limit"] = limit
            
            result = self.client.payments.list_payments(**body)
            
            if result.is_success():
                return {
                    "success": True,
                    "payments": result.body["payments"],
                    "cursor": result.body.get("cursor")
                }
            else:
                return {
                    "success": False,
                    "error": result.errors
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def refund_payment(self,
                      payment_id: str,
                      amount: int,
                      currency: str,
                      reason: Optional[str] = None) -> Dict:
        """Refund a payment."""
        try:
            idempotency_key = str(uuid.uuid4())
            
            body = {
                "payment_id": payment_id,
                "idempotency_key": idempotency_key,
                "amount_money": {
                    "amount": amount,
                    "currency": currency
                }
            }
            
            if reason:
                body["reason"] = reason
            
            result = self.client.refunds.refund_payment(body)
            
            if result.is_success():
                return {
                    "success": True,
                    "refund_id": result.body["refund"]["id"],
                    "status": result.body["refund"]["status"],
                    "amount": result.body["refund"]["amount_money"]["amount"],
                    "currency": result.body["refund"]["amount_money"]["currency"]
                }
            else:
                return {
                    "success": False,
                    "error": result.errors
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def create_customer(self,
                       email: str,
                       phone_number: Optional[str] = None,
                       reference_id: Optional[str] = None,
                       note: Optional[str] = None) -> Dict:
        """Create a new customer in Square."""
        try:
            idempotency_key = str(uuid.uuid4())
            
            body = {
                "idempotency_key": idempotency_key,
                "email_address": email
            }
            
            if phone_number:
                body["phone_number"] = phone_number
            if reference_id:
                body["reference_id"] = reference_id
            if note:
                body["note"] = note
            
            result = self.client.customers.create_customer(body)
            
            if result.is_success():
                return {
                    "success": True,
                    "customer_id": result.body["customer"]["id"],
                    "created_at": result.body["customer"]["created_at"]
                }
            else:
                return {
                    "success": False,
                    "error": result.errors
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
