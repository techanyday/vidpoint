"""Database interface for VidPoint."""
import json
import os
from typing import Optional, Dict, List
from datetime import datetime
from .user import User

class Database:
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.users_file = os.path.join(data_dir, "users.json")
        self._ensure_data_dir()
        self._load_users()
    
    def _ensure_data_dir(self) -> None:
        """Ensure the data directory exists."""
        os.makedirs(self.data_dir, exist_ok=True)
        if not os.path.exists(self.users_file):
            with open(self.users_file, "w") as f:
                json.dump({}, f)
    
    def _load_users(self) -> None:
        """Load users from the JSON file."""
        with open(self.users_file, "r") as f:
            self.users = json.load(f)
    
    def _save_users(self) -> None:
        """Save users to the JSON file."""
        with open(self.users_file, "w") as f:
            json.dump(self.users, f, indent=2)
    
    def create_user(self, email: str, password: str, plan: str = "free") -> Optional[User]:
        """Create a new user."""
        if email in self.users:
            return None
            
        user = User(email, password, plan)
        self.users[email] = user.to_dict()
        self._save_users()
        return user
    
    def get_user(self, email: str) -> Optional[User]:
        """Get a user by email."""
        user_data = self.users.get(email)
        if not user_data:
            return None
            
        user = User(email, "")  # Password hash is already stored
        user.password_hash = user_data["password_hash"]
        user.plan = user_data["plan"]
        user.summaries_used = user_data["summaries_used"]
        user.extra_credits = user_data["extra_credits"]
        user.last_reset = datetime.fromisoformat(user_data["last_reset"])
        user.team_members = user_data.get("team_members", [])
        return user
    
    def update_user(self, user: User) -> None:
        """Update a user's information."""
        self.users[user.email] = user.to_dict()
        self._save_users()
    
    def delete_user(self, email: str) -> bool:
        """Delete a user."""
        if email in self.users:
            del self.users[email]
            self._save_users()
            return True
        return False
