from datetime import datetime
from .database import Database
import bcrypt

class User:
    def __init__(self, id=None, email=None, name=None, google_id=None, profile_picture=None,
                 subscription_plan='free', subscription_end=None, summaries_remaining=3,
                 created_at=None, updated_at=None, password_hash=None):
        self.id = id
        self.email = email
        self.name = name
        self.google_id = google_id
        self.profile_picture = profile_picture
        self.subscription_plan = subscription_plan
        self.subscription_end = subscription_end
        self.summaries_remaining = summaries_remaining
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()
        self.password_hash = password_hash
        self._db = Database()

    def set_password(self, password):
        """Hash and set the user's password"""
        if not password:
            raise ValueError("Password cannot be empty")
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        self.save()

    def check_password(self, password):
        """Check if the provided password matches the stored hash"""
        if not self.password_hash:
            return False
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash)

    @classmethod
    def get_by_email(cls, email):
        db = Database()
        user_data = db.find_one('users', {'email': email})
        if user_data:
            return cls(**user_data)
        return None

    @classmethod
    def get_by_id(cls, user_id):
        db = Database()
        user_data = db.find_one('users', {'_id': user_id})
        if user_data:
            return cls(**user_data)
        return None

    @classmethod
    def create(cls, email, name=None, google_id=None, profile_picture=None):
        user = cls(
            email=email,
            name=name,
            google_id=google_id,
            profile_picture=profile_picture
        )
        user.save()
        return user

    def save(self):
        self.updated_at = datetime.utcnow()
        user_data = {
            'email': self.email,
            'name': self.name,
            'google_id': self.google_id,
            'profile_picture': self.profile_picture,
            'subscription_plan': self.subscription_plan,
            'subscription_end': self.subscription_end,
            'summaries_remaining': self.summaries_remaining,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'password_hash': self.password_hash
        }
        
        if self.id:
            self._db.update_one('users', {'_id': self.id}, user_data)
        else:
            self.id = self._db.insert_one('users', user_data)

    def update(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.save()

    def can_process_video(self):
        """Check if user can process a new video based on their subscription"""
        if self.summaries_remaining <= 0:
            return False
        if self.subscription_end and datetime.utcnow() > self.subscription_end:
            return False
        return True

    def decrement_summaries(self):
        """Decrement the number of remaining summaries"""
        if self.summaries_remaining > 0:
            self.summaries_remaining -= 1
            self.save()
            return True
        return False

    def add_summaries(self, amount):
        """Add more summaries to the user's account"""
        self.summaries_remaining += amount
        self.save()

    def update_subscription(self, plan, end_date=None):
        """Update user's subscription plan and end date"""
        self.subscription_plan = plan
        self.subscription_end = end_date
        
        # Reset summaries based on plan
        if plan == 'free':
            self.summaries_remaining = 3
        elif plan == 'starter':
            self.summaries_remaining = 50
        elif plan == 'pro':
            self.summaries_remaining = 1000
            
        self.save()
