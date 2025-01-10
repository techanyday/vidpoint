"""Notification scheduler for VidPoint."""
from datetime import datetime, timedelta
from models.database import get_db
from notifications.email_service import EmailService
from notifications.templates import (
    SUBSCRIPTION_EXPIRING_TEMPLATE,
    LOW_CREDITS_TEMPLATE
)
from config.pricing import CREDIT_PACKAGES
from flask import current_app, url_for

class NotificationScheduler:
    """Handles scheduling and sending of notifications."""
    
    def __init__(self):
        """Initialize notification scheduler."""
        self.db = get_db()
        self.email_service = EmailService()
        
    def check_expiring_subscriptions(self):
        """Check for subscriptions expiring soon and send notifications."""
        # Get users with subscriptions expiring in 7, 3, and 1 days
        notification_days = [7, 3, 1]
        now = datetime.now()
        
        for days in notification_days:
            target_date = now + timedelta(days=days)
            expiring_users = self.db.users.find({
                'subscription.end_date': {
                    '$gte': target_date,
                    '$lt': target_date + timedelta(days=1)
                },
                'settings.email_notifications': True
            })
            
            for user in expiring_users:
                self.send_subscription_expiry_notice(
                    user,
                    days,
                    user['subscription']
                )
    
    def check_low_credits(self):
        """Check for users with low credits and send notifications."""
        # Get users with credits below threshold (e.g., 100 credits)
        threshold = 100
        low_credit_users = self.db.users.find({
            'credits': {'$lt': threshold},
            'settings.email_notifications': True
        })
        
        for user in low_credit_users:
            self.send_low_credits_notice(user, user['credits'])
    
    def send_subscription_expiry_notice(self, user, days_left, subscription):
        """Send subscription expiry notification."""
        context = {
            'plan_name': subscription['plan_name'],
            'days_left': days_left,
            'expiry_date': subscription['end_date'],
            'renewal_url': url_for(
                'payments.checkout',
                plan=subscription['plan_name'].lower(),
                _external=True
            )
        }
        
        self.email_service.send_email(
            to_email=user['email'],
            subject=f'Your VidPoint Subscription Expires in {days_left} Days',
            template=SUBSCRIPTION_EXPIRING_TEMPLATE,
            context=context
        )
        
        # Log notification
        self.db.notifications.insert_one({
            'user_id': user['_id'],
            'type': 'subscription_expiring',
            'days_left': days_left,
            'sent_at': datetime.now()
        })
    
    def send_low_credits_notice(self, user, credits_left):
        """Send low credits notification."""
        context = {
            'credits_left': credits_left,
            'credit_packages': CREDIT_PACKAGES,
            'credits_url': url_for(
                'payments.checkout',
                plan='credits-500',
                _external=True
            )
        }
        
        self.email_service.send_email(
            to_email=user['email'],
            subject='Low Credits Alert - VidPoint',
            template=LOW_CREDITS_TEMPLATE,
            context=context
        )
        
        # Log notification
        self.db.notifications.insert_one({
            'user_id': user['_id'],
            'type': 'low_credits',
            'credits_left': credits_left,
            'sent_at': datetime.now()
        })
    
    def run_checks(self):
        """Run all notification checks."""
        try:
            self.check_expiring_subscriptions()
            self.check_low_credits()
        except Exception as e:
            current_app.logger.error(f"Error running notification checks: {str(e)}")
