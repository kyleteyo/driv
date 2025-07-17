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

def authenticate_user(username, password, skip_password=False):
    """Authenticate user with username and password"""
    credentials = load_credentials()
    
    if username not in credentials:
        return False
    
    # For session restoration, skip password check
    if skip_password:
        return True
    
    hashed_password = hash_password(password)
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

def change_password(username, old_password, new_password):
    """Change user password"""
    credentials = load_credentials()
    
    # Verify current password
    if not authenticate_user(username, old_password):
        return False, "Current password is incorrect"
    
    if len(new_password) < 6:
        return False, "New password must be at least 6 characters long"
    
    # Update password
    user_details = credentials[username]
    
    # Handle both old format (string) and new format (dict)
    if isinstance(user_details, dict):
        credentials[username]['password'] = hash_password(new_password)
    else:
        # Legacy format - convert to new format
        credentials[username] = {
            'password': hash_password(new_password),
            'is_admin': username in ['admin', 'trooper1', 'trooper2', 'commander']
        }
    
    # Save updated credentials
    try:
        with open('credentials.json', 'w') as f:
            json.dump(credentials, f, indent=2)
        return True, "Password changed successfully"
    except Exception as e:
        return False, f"Failed to save new password: {str(e)}"

def get_user_info(username):
    """Get user information"""
    credentials = load_credentials()
    if username not in credentials:
        return None
    
    user_details = credentials[username]
    if isinstance(user_details, dict):
        return {
            'username': username,
            'is_admin': user_details.get('is_admin', False)
        }
    else:
        # Legacy format
        return {
            'username': username,
            'is_admin': username in ['admin', 'trooper1', 'trooper2', 'commander']
        }
