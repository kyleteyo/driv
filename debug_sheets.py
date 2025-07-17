#!/usr/bin/env python3
"""
Debug script to check Google Sheets structure and data
"""

import streamlit as st
from sheets_manager import SheetsManager
import json

def debug_sheets():
    """Debug Google Sheets data structure"""
    try:
        sheets_manager = SheetsManager()
        
        print("=== DEBUG: TERREX TRACKER ===")
        try:
            terrex_records = sheets_manager.terrex_worksheet.get_all_records()
            print(f"Total Terrex records: {len(terrex_records)}")
            
            if terrex_records:
                print("\nFirst Terrex record structure:")
                print(json.dumps(terrex_records[0], indent=2))
                
                print("\nFirst 5 Terrex usernames and names:")
                for i, record in enumerate(terrex_records[:5]):
                    username = record.get('Username', 'NO_USERNAME')
                    name = record.get('Name', 'NO_NAME')
                    rank = record.get('Rank', 'NO_RANK')
                    print(f"{i+1}. Username: '{username}' | Name: '{name}' | Rank: '{rank}'")
                    
        except Exception as e:
            print(f"Error getting Terrex records: {e}")
            
            # Try raw values approach
            try:
                print("Trying raw values approach for Terrex...")
                terrex_values = sheets_manager.terrex_worksheet.get_all_values()
                if terrex_values:
                    print(f"Headers: {terrex_values[0]}")
                    if len(terrex_values) > 1:
                        print(f"First data row: {terrex_values[1]}")
            except Exception as e2:
                print(f"Raw values also failed: {e2}")
        
        print("\n=== DEBUG: BELREX TRACKER ===")
        try:
            belrex_records = sheets_manager.belrex_worksheet.get_all_records()
            print(f"Total Belrex records: {len(belrex_records)}")
            
            if belrex_records:
                print("\nFirst Belrex record structure:")
                print(json.dumps(belrex_records[0], indent=2))
                
                print("\nFirst 5 Belrex usernames and names:")
                for i, record in enumerate(belrex_records[:5]):
                    username = record.get('Username', 'NO_USERNAME')
                    name = record.get('Name', 'NO_NAME')
                    rank = record.get('Rank', 'NO_RANK')
                    print(f"{i+1}. Username: '{username}' | Name: '{name}' | Rank: '{rank}'")
                    
        except Exception as e:
            print(f"Error getting Belrex records: {e}")
            
            # Try raw values approach
            try:
                print("Trying raw values approach for Belrex...")
                belrex_values = sheets_manager.belrex_worksheet.get_all_values()
                if belrex_values:
                    print(f"Headers: {belrex_values[0]}")
                    if len(belrex_values) > 1:
                        print(f"First data row: {belrex_values[1]}")
            except Exception as e2:
                print(f"Raw values also failed: {e2}")
        
        print("\n=== TEST SPECIFIC USER ===")
        test_users = ['admin', 'trooper1', 'cabre', 'branw']  # Mix of admin and regular users
        
        for username in test_users:
            print(f"\nTesting user: {username}")
            try:
                qualifications = sheets_manager.check_user_qualifications(username)
                print(f"  Qualifications: {qualifications}")
                
                tracker_data = sheets_manager.get_user_tracker_data(username)
                print(f"  Tracker data: {tracker_data}")
                
            except Exception as e:
                print(f"  Error: {e}")
        
    except Exception as e:
        print(f"Failed to initialize sheets manager: {e}")

if __name__ == "__main__":
    debug_sheets()