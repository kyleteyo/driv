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

def create_user(username, password, preserve_existing=True):
    """Create a new user (for administrative purposes)"""
    credentials = load_credentials()
    
    # CRITICAL: Preserve existing passwords to prevent user lockouts
    if preserve_existing and username in credentials:
        print(f"User {username} already exists - preserving existing password")
        return True  # Don't overwrite existing users
    
    credentials[username] = hash_password(password)
    
    with open('credentials.json', 'w') as f:
        json.dump(credentials, f, indent=2)
    
    return True

def safe_initialize_missing_users():
    """Safely add missing users from Google Sheets without overwriting existing passwords"""
    try:
        from sheets_manager import SheetsManager
        sheets_manager = SheetsManager()
        
        # Get all qualified personnel from tracker
        personnel_data = []
        try:
            # Try to get data from Personnel_Tracker worksheet
            personnel_sheet = sheets_manager.spreadsheet.worksheet('Personnel_Tracker')
            personnel_records = personnel_sheet.get_all_records()
            for record in personnel_records:
                username = record.get('username', '').strip()
                if username:
                    personnel_data.append({'username': username})
        except Exception as e:
            print(f"Could not load personnel data: {e}")
            return False
        credentials = load_credentials()
        
        new_users_added = 0
        
        for person in personnel_data:
            username = person.get('username', '').strip().lower()
            if username and username not in credentials:
                # Only add truly new users with default password
                credentials[username] = "ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f"  # "secret123"
                new_users_added += 1
                print(f"Added new user: {username}")
        
        if new_users_added > 0:
            with open('credentials.json', 'w') as f:
                json.dump(credentials, f, indent=2)
            print(f"Added {new_users_added} new users while preserving existing passwords")
        
        return True
        
    except Exception as e:
        print(f"Error initializing missing users: {e}")
        return False

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
