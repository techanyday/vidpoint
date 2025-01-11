from datetime import datetime
from .database import Database
import bcrypt

class User:
    def __init__(self, _id=None, email=None, name=None, google_id=None, profile_picture=None,
                 subscription_plan='free', subscription_end=None, summaries_remaining=3,
                 created_at=None, updated_at=None, password_hash=None):
        print(f"Initializing User with password_hash type: {type(password_hash)}")
        self.id = _id  # Map MongoDB's _id to id
        self.email = email
        self.name = name
        self.google_id = google_id
        self.profile_picture = profile_picture
        self.subscription_plan = subscription_plan
        self.subscription_end = subscription_end
        self.summaries_remaining = summaries_remaining
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()
        self._db = Database()

        # Handle password hash
        if password_hash:
            print(f"Converting password_hash from {type(password_hash)}")
            if isinstance(password_hash, bytes):
                self.password_hash = password_hash.decode('utf-8')
            elif isinstance(password_hash, str):
                self.password_hash = password_hash
            else:
                print(f"Unexpected password_hash type: {type(password_hash)}")
                self.password_hash = None
            print(f"Final password_hash type: {type(self.password_hash)}")
        else:
            self.password_hash = None

    def set_password(self, password):
        """Hash and set the user's password"""
        if not password:
            raise ValueError("Password cannot be empty")
        print(f"Setting password for user {self.email}")
        
        # Generate salt and hash password
        salt = bcrypt.gensalt()
        print(f"Generated salt type: {type(salt)}")
        password_bytes = password.encode('utf-8')
        print(f"Password bytes type: {type(password_bytes)}")
        hashed = bcrypt.hashpw(password_bytes, salt)
        print(f"Generated hash type: {type(hashed)}")
        
        # Store hash as string
        self.password_hash = hashed.decode('utf-8')
        print(f"Stored hash type: {type(self.password_hash)}")

    def check_password(self, password):
        """Check if the provided password matches the stored hash"""
        if not self.password_hash:
            print("No password hash found")
            return False
            
        print(f"Checking password for user {self.email}")
        print(f"Stored hash type: {type(self.password_hash)}")
        
        try:
            # Convert password to bytes
            password_bytes = password.encode('utf-8')
            print(f"Password bytes type: {type(password_bytes)}")
            
            # Convert stored hash to bytes
            stored_hash_bytes = self.password_hash.encode('utf-8')
            print(f"Stored hash bytes type: {type(stored_hash_bytes)}")
            
            # Check password
            result = bcrypt.checkpw(password_bytes, stored_hash_bytes)
            print(f"Password check result: {result}")
            return result
            
        except Exception as e:
            print(f"Error checking password: {str(e)}")
            return False

    @classmethod
    def get_by_email(cls, email):
        db = Database()
        print(f"Looking up user by email: {email}")
        user_data = db.find_one('users', {'email': email})
        if user_data:
            print(f"Found user data: {user_data}")
            return cls(**user_data)
        print("No user found with that email")
        return None

    @classmethod
    def get_by_id(cls, user_id):
        db = Database()
        print(f"Looking up user by id: {user_id}")
        user_data = db.find_one('users', {'_id': user_id})
        if user_data:
            print(f"Found user data: {user_data}")
            return cls(**user_data)
        print("No user found with that id")
        return None

    @classmethod
    def create(cls, email, name=None, google_id=None, profile_picture=None):
        print(f"Creating new user with email: {email}")
        user = cls(
            email=email,
            name=name,
            google_id=google_id,
            profile_picture=profile_picture,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        return user

    def save(self):
        """Save user to database"""
        print(f"Saving user {self.email}")
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
        
        print(f"User data to save:")
        for key, value in user_data.items():
            print(f"  {key}: {type(value)}")
        
        if self.id:
            print(f"Updating existing user with id: {self.id}")
            self._db.update_one('users', {'_id': self.id}, user_data)
        else:
            print("Creating new user")
            self.id = self._db.insert_one('users', user_data)
            print(f"Created user with id: {self.id}")

    def update(self, **kwargs):
        """Update user attributes"""
        print(f"Updating user {self.email} with {kwargs}")
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
