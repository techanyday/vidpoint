"""User model and management for VidPoint."""
from datetime import datetime, timezone
from typing import Optional, Dict
import jwt
from werkzeug.security import generate_password_hash, check_password_hash
from config.pricing import PRICING_PLANS

class User:
    def __init__(self, email: str, password: str, plan: str = "free"):
        self.email = email
        self.password_hash = generate_password_hash(password)
        self.plan = plan
        self.summaries_used = 0
        self.extra_credits = 0
        self.last_reset = datetime.now(timezone.utc)
        self.team_members = [] if plan == "pro" else None
        
    def check_password(self, password: str) -> bool:
        """Check if the provided password matches the hash."""
        return check_password_hash(self.password_hash, password)
    
    def can_process_video(self) -> tuple[bool, str]:
        """Check if user can process another video."""
        # Reset counter if it's a new month
        now = datetime.now(timezone.utc)
        if now.month != self.last_reset.month or now.year != self.last_reset.year:
            self.summaries_used = 0
            self.last_reset = now
        
        # Get plan limits
        plan_info = PRICING_PLANS[self.plan]
        total_available = plan_info["monthly_summaries"] + self.extra_credits
        
        if self.summaries_used >= total_available:
            return False, f"Monthly limit reached ({total_available} summaries). Please upgrade your plan or purchase extra credits."
            
        return True, ""
    
    def process_video(self) -> None:
        """Record a video processing usage."""
        self.summaries_used += 1
    
    def add_credits(self, amount: int) -> None:
        """Add extra processing credits."""
        self.extra_credits += amount
    
    def get_token(self, secret_key: str) -> str:
        """Generate a JWT token for the user."""
        return jwt.encode(
            {
                "email": self.email,
                "plan": self.plan,
                "exp": datetime.now(timezone.utc).timestamp() + 86400  # 24 hours
            },
            secret_key,
            algorithm="HS256"
        )
    
    @staticmethod
    def verify_token(token: str, secret_key: str) -> Optional[Dict]:
        """Verify a JWT token and return the payload."""
        try:
            return jwt.decode(token, secret_key, algorithms=["HS256"])
        except jwt.InvalidTokenError:
            return None
    
    def to_dict(self) -> Dict:
        """Convert user to dictionary for storage."""
        return {
            "email": self.email,
            "password_hash": self.password_hash,
            "plan": self.plan,
            "summaries_used": self.summaries_used,
            "extra_credits": self.extra_credits,
            "last_reset": self.last_reset.isoformat(),
            "team_members": self.team_members
        }
