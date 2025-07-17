import json
import hashlib
import os

def load_credentials():
    """Load user credentials from JSON file"""
    try:
        with open('credentials.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        # Return default credentials if file doesn't exist
        return {
            "admin": "5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8",  # "password"
            "trooper1": "ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f",  # "secret123"
            "trooper2": "5994471abb01112afcc18159f6cc74b4f511b99806da59b3caf5a9c173cacfc5"   # "service456"
        }

def hash_password(password):
    """Hash password using SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()

def authenticate_user(username, password):
    """Authenticate user with username and password"""
    credentials = load_credentials()
    hashed_password = hash_password(password)
    
    if username not in credentials:
        return False
    
    user_details = credentials[username]
    
    # Handle both old format (string) and new format (dict)
    if isinstance(user_details, dict):
        return user_details.get('password') == hashed_password
    else:
        # Legacy format - password hash directly stored
        return user_details == hashed_password

def create_user(username, password):
    """Create a new user (for administrative purposes)"""
    credentials = load_credentials()
    credentials[username] = hash_password(password)
    
    with open('credentials.json', 'w') as f:
        json.dump(credentials, f, indent=2)
    
    return True
