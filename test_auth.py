from flask import Flask, request, jsonify, session
from models.user import User
from models.database import Database
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'your-secret-key')

# Initialize database
db = Database()

@app.route('/register', methods=['POST'])
def register():
    """Register a new user."""
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        name = data.get('name')
        
        print(f"Registering user with email: {email}")
        
        if not email or not password:
            return jsonify({"error": "Email and password required"}), 400
            
        # Check if user already exists
        existing_user = User.get_by_email(email)
        if existing_user:
            return jsonify({"error": "Email already registered"}), 400
            
        # Create new user
        user = User.create(email=email, name=name)
        user.set_password(password)
        user.save()  # Save after setting password
            
        session["user_email"] = email
        return jsonify({
            "message": "Registration successful",
            "user": {
                "email": user.email,
                "name": user.name,
                "subscription_plan": user.subscription_plan
            }
        })
        
    except Exception as e:
        print(f"Registration error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/login', methods=['POST'])
def login():
    """Log in a user."""
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({"error": "Email and password required"}), 400
            
        print(f"Attempting login for email: {email}")
        user = User.get_by_email(email)
        print(f"Found user: {user.__dict__ if user else None}")
        
        if not user:
            return jsonify({"error": "Invalid email or password"}), 401
            
        if not user.check_password(password):
            print("Password check failed")
            return jsonify({"error": "Invalid email or password"}), 401
            
        session["user_email"] = email
        return jsonify({
            "message": "Login successful",
            "user": {
                "email": user.email,
                "name": user.name,
                "subscription_plan": user.subscription_plan
            }
        })
        
    except Exception as e:
        print(f"Login error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/logout')
def logout():
    """Log out the current user."""
    session.pop("user_email", None)
    return jsonify({"message": "Logged out"})

if __name__ == '__main__':
    app.run(debug=True, port=8080)
