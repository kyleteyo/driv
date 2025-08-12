#!/usr/bin/env python3
"""
Password Backup and Restoration Utility for MSC DRIVr

This script helps preserve user passwords when updating the application.
It creates backups of the credentials.json file and can restore them.
"""

import json
import os
import shutil
from datetime import datetime

def backup_passwords(backup_name=None):
    """Create a backup of current passwords"""
    if not os.path.exists('credentials.json'):
        print("No credentials.json file found!")
        return False
    
    if backup_name is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"credentials_backup_{timestamp}.json"
    
    try:
        shutil.copy2('credentials.json', backup_name)
        print(f"✅ Password backup created: {backup_name}")
        return True
    except Exception as e:
        print(f"❌ Backup failed: {e}")
        return False

def restore_passwords(backup_file):
    """Restore passwords from backup file"""
    if not os.path.exists(backup_file):
        print(f"Backup file not found: {backup_file}")
        return False
    
    try:
        # Validate the backup file
        with open(backup_file, 'r') as f:
            backup_data = json.load(f)
        
        # Create a backup of current file before restoring
        if os.path.exists('credentials.json'):
            backup_passwords("credentials_before_restore.json")
        
        # Restore the backup
        shutil.copy2(backup_file, 'credentials.json')
        print(f"✅ Passwords restored from: {backup_file}")
        print(f"📊 Restored {len(backup_data)} user accounts")
        return True
        
    except Exception as e:
        print(f"❌ Restore failed: {e}")
        return False

def merge_passwords(production_backup, development_file='credentials.json'):
    """Merge production passwords with development user list"""
    try:
        # Load production passwords
        with open(production_backup, 'r') as f:
            production_data = json.load(f)
        
        # Load development users (if exists)
        dev_data = {}
        if os.path.exists(development_file):
            with open(development_file, 'r') as f:
                dev_data = json.load(f)
        
        # Merge: production passwords take priority, new dev users get default
        merged_data = {}
        
        # First, add all production users with their existing passwords
        for username, password_data in production_data.items():
            merged_data[username] = password_data
            
        # Then, add any new development users that don't exist in production
        for username, password_data in dev_data.items():
            if username not in merged_data:
                merged_data[username] = password_data
                print(f"➕ Added new user: {username}")
        
        # Save merged file
        backup_passwords("credentials_before_merge.json")
        with open('credentials.json', 'w') as f:
            json.dump(merged_data, f, indent=2)
        
        print(f"✅ Merged passwords successfully")
        print(f"📊 Total users: {len(merged_data)}")
        print(f"📊 From production: {len(production_data)}")
        print(f"📊 New users: {len(merged_data) - len(production_data)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Merge failed: {e}")
        return False

def list_backups():
    """List all available password backup files"""
    backup_files = [f for f in os.listdir('.') if f.startswith('credentials_backup_') and f.endswith('.json')]
    
    if not backup_files:
        print("No backup files found")
        return []
    
    print("Available password backups:")
    for backup_file in sorted(backup_files):
        try:
            with open(backup_file, 'r') as f:
                data = json.load(f)
            file_size = os.path.getsize(backup_file)
            print(f"  📁 {backup_file} ({len(data)} users, {file_size} bytes)")
        except:
            print(f"  ❌ {backup_file} (corrupted)")
    
    return backup_files

if __name__ == "__main__":
    print("MSC DRIVr Password Backup Utility")
    print("=" * 40)
    
    while True:
        print("\nOptions:")
        print("1. Create backup")
        print("2. Restore from backup")
        print("3. List backups")
        print("4. Merge production with development")
        print("5. Exit")
        
        choice = input("\nSelect option (1-5): ").strip()
        
        if choice == '1':
            backup_passwords()
        elif choice == '2':
            list_backups()
            backup_file = input("Enter backup filename: ").strip()
            if backup_file:
                restore_passwords(backup_file)
        elif choice == '3':
            list_backups()
        elif choice == '4':
            prod_file = input("Enter production backup filename: ").strip()
            if prod_file:
                merge_passwords(prod_file)
        elif choice == '5':
            break
        else:
            print("Invalid option")