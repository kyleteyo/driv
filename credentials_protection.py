"""
Credentials Protection System for MSC DRIVr

This module prevents password resets during GitHub uploads by:
1. Creating protected backups of credentials.json
2. Detecting when credentials have been reset
3. Auto-restoring from backups when needed
4. Providing manual recovery options

Usage:
- Run before GitHub upload: python credentials_protection.py backup
- Run after GitHub upload: python credentials_protection.py restore
- Check status: python credentials_protection.py check
"""

import json
import os
import shutil
from datetime import datetime
import hashlib

CREDENTIALS_FILE = "credentials.json"
BACKUP_DIR = ".credentials_backup"
PROTECTED_BACKUP = os.path.join(BACKUP_DIR, "credentials_protected.json")
TIMESTAMP_FILE = os.path.join(BACKUP_DIR, "last_backup.txt")

def create_backup():
    """Create a protected backup of credentials.json"""
    if not os.path.exists(CREDENTIALS_FILE):
        print(f"No {CREDENTIALS_FILE} found to backup")
        return False
    
    # Create backup directory
    os.makedirs(BACKUP_DIR, exist_ok=True)
    
    # Copy credentials with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    timestamped_backup = os.path.join(BACKUP_DIR, f"credentials_{timestamp}.json")
    
    shutil.copy2(CREDENTIALS_FILE, timestamped_backup)
    shutil.copy2(CREDENTIALS_FILE, PROTECTED_BACKUP)
    
    # Save backup timestamp
    with open(TIMESTAMP_FILE, 'w') as f:
        f.write(f"{timestamp}\n")
    
    print(f"✅ Credentials backed up to {BACKUP_DIR}")
    print(f"   - Protected backup: {PROTECTED_BACKUP}")
    print(f"   - Timestamped backup: {timestamped_backup}")
    return True

def restore_from_backup():
    """Restore credentials from protected backup"""
    if not os.path.exists(PROTECTED_BACKUP):
        print(f"❌ No protected backup found at {PROTECTED_BACKUP}")
        return False
    
    # Backup current credentials before restore
    if os.path.exists(CREDENTIALS_FILE):
        shutil.copy2(CREDENTIALS_FILE, f"{CREDENTIALS_FILE}.before_restore")
    
    # Restore from backup
    shutil.copy2(PROTECTED_BACKUP, CREDENTIALS_FILE)
    
    print(f"✅ Credentials restored from {PROTECTED_BACKUP}")
    return True

def check_status():
    """Check the status of credentials and backups"""
    print("=== MSC DRIVr Credentials Status ===")
    
    # Check if main file exists
    if os.path.exists(CREDENTIALS_FILE):
        with open(CREDENTIALS_FILE, 'r') as f:
            creds = json.load(f)
        print(f"✅ Main credentials file: {len(creds)} users")
    else:
        print("❌ Main credentials file missing")
        return False
    
    # Check backup status
    if os.path.exists(PROTECTED_BACKUP):
        with open(PROTECTED_BACKUP, 'r') as f:
            backup_creds = json.load(f)
        print(f"✅ Protected backup: {len(backup_creds)} users")
        
        if os.path.exists(TIMESTAMP_FILE):
            with open(TIMESTAMP_FILE, 'r') as f:
                timestamp = f.read().strip()
            print(f"📅 Last backup: {timestamp}")
    else:
        print("❌ No protected backup found")
    
    # Check for password resets (detect default passwords)
    default_hash = "ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f"  # "secret123"
    reset_users = []
    
    for username, user_data in creds.items():
        if isinstance(user_data, dict):
            password_hash = user_data.get('password', '')
        else:
            password_hash = user_data
        
        if password_hash == default_hash:
            reset_users.append(username)
    
    if reset_users:
        print(f"⚠️  Users with default passwords (may be reset): {', '.join(reset_users)}")
    else:
        print("✅ No default passwords detected")
    
    return True

def auto_detect_and_restore():
    """Automatically detect if passwords were reset and restore if needed"""
    if not check_status():
        return False
    
    with open(CREDENTIALS_FILE, 'r') as f:
        creds = json.load(f)
    
    # Count users with default password
    default_hash = "ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f"
    reset_count = 0
    
    for username, user_data in creds.items():
        if isinstance(user_data, dict):
            password_hash = user_data.get('password', '')
        else:
            password_hash = user_data
        
        if password_hash == default_hash:
            reset_count += 1
    
    # If more than 50% have default passwords, likely a reset occurred
    if reset_count > len(creds) * 0.5:
        print(f"🔍 Detected likely password reset ({reset_count}/{len(creds)} users with default passwords)")
        print("🔄 Auto-restoring from backup...")
        return restore_from_backup()
    
    return True

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python credentials_protection.py [backup|restore|check|auto]")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "backup":
        create_backup()
    elif command == "restore":
        restore_from_backup()
    elif command == "check":
        check_status()
    elif command == "auto":
        auto_detect_and_restore()
    else:
        print("Unknown command. Use: backup, restore, check, or auto")