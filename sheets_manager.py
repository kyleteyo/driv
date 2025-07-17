import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime, timedelta
import os
import json
import streamlit as st
from functools import lru_cache
# Removed api_optimizer import to fix compatibility

class SheetsManager:
    def __init__(self):
        """Initialize Google Sheets connection"""
        self.setup_credentials()
        self.connect_to_sheets()
        self.setup_worksheets()
        self._cache_timeout = 1800  # 30 minutes cache timeout
    
    def setup_credentials(self):
        """Setup Google Sheets API credentials"""
        # Define the scope
        self.scope = [
            'https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/drive'
        ]
        
        # Get credentials from environment or use default service account
        try:
            # Try to get credentials from environment variable
            creds_json = os.getenv('GOOGLE_SHEETS_CREDENTIALS')
            if creds_json:
                creds_dict = json.loads(creds_json)
                self.creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, self.scope)
            else:
                # Fallback to service account file
                self.creds = ServiceAccountCredentials.from_json_keyfile_name('service_account.json', self.scope)
        except Exception as e:
            raise Exception(f"Failed to setup Google Sheets credentials: {str(e)}. Please ensure GOOGLE_SHEETS_CREDENTIALS environment variable is set or service_account.json file exists.")
    
    def connect_to_sheets(self):
        """Connect to Google Sheets"""
        try:
            self.client = gspread.authorize(self.creds)
            
            # Get spreadsheet ID from environment or use default
            spreadsheet_id = os.getenv('GOOGLE_SHEET_ID', '1jHRQuVdQKISnjDov6EwaSRhBlvpXDodLnyXOC9BDIMQ')
            
            try:
                self.spreadsheet = self.client.open_by_key(spreadsheet_id)
            except gspread.SpreadsheetNotFound:
                # Create a new spreadsheet if not found
                self.spreadsheet = self.client.create('MSC_Mileage_Tracker')
                print(f"Created new spreadsheet: {self.spreadsheet.url}")
            except Exception as e:
                if "quota" in str(e).lower() or "403" in str(e):
                    # Try to create spreadsheet in user's drive instead
                    try:
                        self.spreadsheet = self.client.create('MSC_Mileage_Tracker')
                        print(f"Created new spreadsheet: {self.spreadsheet.url}")
                    except Exception as e2:
                        raise Exception(f"Storage quota exceeded. Please try one of these solutions:\n1. Create a new Google account with fresh storage\n2. Use an existing spreadsheet and share it with the service account\n3. Clear space in your Google Drive\n\nOriginal error: {str(e)}")
                
        except Exception as e:
            raise Exception(f"Failed to connect to Google Sheets: {str(e)}")
    
    def setup_worksheets(self):
        """Setup all required worksheets"""
        # Setup Mileage_Logs worksheet
        try:
            self.mileage_worksheet = self.spreadsheet.worksheet('Mileage_Logs')
        except gspread.WorksheetNotFound:
            self.mileage_worksheet = self.spreadsheet.add_worksheet(title='Mileage_Logs', rows=1000, cols=8)
            headers = ['Username', 'Date_of_Drive', 'Vehicle_No_MID', 'Initial_Mileage_KM', 'Final_Mileage_KM', 'Distance_Driven_KM', 'Vehicle_Type', 'Timestamp']
            self.mileage_worksheet.append_row(headers)
        
        # Setup Terrex Tracker worksheet
        try:
            self.terrex_worksheet = self.spreadsheet.worksheet('Terrex Tracker (MSP1-4)')
        except gspread.WorksheetNotFound:
            self.terrex_worksheet = self.spreadsheet.add_worksheet(title='Terrex Tracker (MSP1-4)', rows=1000, cols=6)
            headers = ['Username', 'Last_Drive_Date', 'Total_Distance_3_Months', 'Currency_Maintained', 'Currency_Expiry_Date', 'Last_Updated']
            self.terrex_worksheet.append_row(headers)
        
        # Setup Belrex Tracker worksheet
        try:
            self.belrex_worksheet = self.spreadsheet.worksheet('Belrex Tracker (MSP5)')
        except gspread.WorksheetNotFound:
            self.belrex_worksheet = self.spreadsheet.add_worksheet(title='Belrex Tracker (MSP5)', rows=1000, cols=6)
            headers = ['Username', 'Last_Drive_Date', 'Total_Distance_3_Months', 'Currency_Maintained', 'Currency_Expiry_Date', 'Last_Updated']
            self.belrex_worksheet.append_row(headers)
    
    @st.cache_data(ttl=7200, show_spinner=False)  # 2 hour cache for qualifications
    def check_user_qualifications(_self, username):
        """Check if user is qualified for Terrex and/or Belrex based on presence in tracker sheets"""
        qualifications = {'terrex': False, 'belrex': False, 'full_name': '', 'rank': '', 'is_admin': False}
        
        # Check if user is admin
        is_admin = _self.is_admin_user(username)
        qualifications['is_admin'] = is_admin
        
        # Special handling for admin/test accounts
        admin_accounts = ['admin', 'trooper1', 'trooper2', 'commander']
        if username in admin_accounts:
            # Admin accounts get full qualification and display names
            qualifications['terrex'] = True
            qualifications['belrex'] = True
            qualifications['full_name'] = username.upper()
            qualifications['rank'] = 'ADMIN' if username == 'admin' else 'TEST'
            return qualifications
        
        try:
            # Check Terrex qualifications
            try:
                terrex_records = _self.terrex_worksheet.get_all_records()
            except:
                # Handle duplicate headers by using raw values
                terrex_values = _self.terrex_worksheet.get_all_values()
                terrex_records = []
                if len(terrex_values) > 1:
                    headers = terrex_values[0]
                    for row in terrex_values[1:]:
                        record = {}
                        for i, header in enumerate(headers):
                            if i < len(row):
                                record[header] = row[i]
                        terrex_records.append(record)
            
            # Check if user exists and has qualification data
            for record in terrex_records:
                if record.get('Username') == username:
                    # Get full name and rank
                    qualifications['full_name'] = record.get('Name', '')
                    qualifications['rank'] = record.get('Rank', '')
                    
                    # Check if qualified (has qualification date and qualification)
                    qualification = record.get('Qualification', '').strip()
                    qual_date = record.get('Qualification Date', '').strip()
                    
                    if qualification and qual_date:
                        qualifications['terrex'] = True
                    break
            
            # Check Belrex qualifications
            try:
                belrex_records = _self.belrex_worksheet.get_all_records()
            except:
                # Handle duplicate headers by using raw values
                belrex_values = _self.belrex_worksheet.get_all_values()
                belrex_records = []
                if len(belrex_values) > 1:
                    headers = belrex_values[0]
                    for row in belrex_values[1:]:
                        record = {}
                        for i, header in enumerate(headers):
                            if i < len(row):
                                record[header] = row[i]
                        belrex_records.append(record)
            
            # Check if user exists and has qualification data
            for record in belrex_records:
                if record.get('Username') == username:
                    # If we don't have name yet, get it from Belrex sheet
                    if not qualifications['full_name']:
                        qualifications['full_name'] = record.get('Name', '')
                        qualifications['rank'] = record.get('Rank', '')
                    
                    # Check if qualified (has qualification date and qualification)
                    qualification = record.get('Qualification', '').strip()
                    qual_date = record.get('Qualification Date', '').strip()
                    
                    if qualification and qual_date:
                        qualifications['belrex'] = True
                    break
                
        except Exception as e:
            # If sheets don't exist or error occurs, assume no qualifications
            pass
        
        return qualifications
    
    def clear_caches(self):
        """Clear all cached data to force refresh"""
        # Clear Streamlit cache for this instance
        if hasattr(st, 'cache_data'):
            st.cache_data.clear()
        if hasattr(st, 'cache_resource'):
            st.cache_resource.clear()
        
        # Clear any internal caches
        if hasattr(self, '_cached_data'):
            self._cached_data = {}
        
        # Clear performance optimization caches
        try:
            from performance_config import clear_all_caches
            clear_all_caches()
        except ImportError:
            pass
    
    def add_mileage_log(self, log_data):
        """Add a new mileage log entry"""
        try:
            # Prepare row data for Mileage_Logs
            row = [
                log_data['Username'],
                log_data['Date_of_Drive'],
                log_data['Vehicle_No_MID'],
                log_data['Initial_Mileage_KM'],
                log_data['Final_Mileage_KM'],
                log_data['Distance_Driven_KM'],
                log_data['Vehicle_Type'],
                log_data['Timestamp']
            ]
            
            # Only append to Mileage_Logs worksheet - do not modify tracker sheets
            self.mileage_worksheet.append_row(row)
            
            # Clear relevant caches to ensure fresh data after new entry
            self._clear_related_caches()
            
            return True
            
        except Exception as e:
            raise Exception(f"Failed to add mileage log: {str(e)}")
    
    def _clear_related_caches(self):
        """Clear caches that should refresh after new mileage entries"""
        try:
            # Clear Streamlit caches for functions that depend on mileage data
            if hasattr(st, 'cache_data'):
                # Clear specific cached functions
                self.get_all_personnel_status.clear()
                self.calculate_3_month_distance.clear()
                self.calculate_expiry_date.clear()
                self.get_user_tracker_data.clear()
            
            # Clear session state caches
            cache_keys_to_clear = [
                'name_lookup_cache',
                'personnel_status_cache', 
                'team_dashboard_cache',
                'currency_status_cache'
            ]
            
            for key in cache_keys_to_clear:
                if key in st.session_state:
                    del st.session_state[key]
                    
        except Exception as e:
            pass  # Fail silently for cache clearing
    
    @st.cache_data(ttl=1800, show_spinner=False)  # 30 minutes cache for calculations  
    def calculate_3_month_distance(_self, username, vehicle_type):
        """Calculate total distance driven in the last 3 months"""
        try:
            # Get all mileage records for the user and vehicle type
            expected_headers = ['Username', 'Date_of_Drive', 'Vehicle_No_MID', 'Initial_Mileage_KM', 'Final_Mileage_KM', 'Distance_Driven_KM', 'Vehicle_Type', 'Timestamp']
            
            try:
                records = _self.mileage_worksheet.get_all_records(expected_headers=expected_headers)
            except:
                # Fallback: get all values and create records manually
                all_values = _self.mileage_worksheet.get_all_values()
                records = []
                if len(all_values) > 1:
                    for row in all_values[1:]:
                        record = {}
                        for i, header in enumerate(expected_headers):
                            if i < len(row):
                                record[header] = row[i]
                            else:
                                record[header] = ''
                        records.append(record)
            
            # Filter for user and vehicle type
            user_records = [r for r in records if r.get('Username') == username and r.get('Vehicle_Type') == vehicle_type]
            
            if not user_records:
                return 0.0
            
            # Calculate date 3 months ago
            three_months_ago = datetime.now() - timedelta(days=90)
            
            total_distance = 0.0
            for record in user_records:
                try:
                    record_date = datetime.strptime(record['Date_of_Drive'], "%Y-%m-%d")
                    if record_date >= three_months_ago:
                        total_distance += float(record.get('Distance_Driven_KM', 0))
                except (ValueError, TypeError):
                    continue
            
            return total_distance
            
        except Exception as e:
            return 0.0
    
    @st.cache_data(ttl=1800, show_spinner=False)  # 30 minutes cache for calculations
    def calculate_expiry_date(_self, username, vehicle_type):
        """Calculate currency expiry date based on last 2km drive"""
        try:
            # Get all mileage records for the user and vehicle type
            expected_headers = ['Username', 'Date_of_Drive', 'Vehicle_No_MID', 'Initial_Mileage_KM', 'Final_Mileage_KM', 'Distance_Driven_KM', 'Vehicle_Type', 'Timestamp']
            
            try:
                records = _self.mileage_worksheet.get_all_records(expected_headers=expected_headers)
            except:
                # Fallback: get all values and create records manually
                all_values = _self.mileage_worksheet.get_all_values()
                records = []
                if len(all_values) > 1:
                    for row in all_values[1:]:
                        record = {}
                        for i, header in enumerate(expected_headers):
                            if i < len(row):
                                record[header] = row[i]
                            else:
                                record[header] = ''
                        records.append(record)
            
            # Filter and sort by date
            user_records = [r for r in records if r.get('Username') == username and r.get('Vehicle_Type') == vehicle_type]
            
            if not user_records:
                return "N/A"
            
            # Sort by date descending
            user_records.sort(key=lambda x: x.get('Date_of_Drive', ''), reverse=True)
            
            # Find the date when user last drove 2km or more
            cumulative_distance = 0.0
            last_2km_date = None
            
            for record in user_records:
                try:
                    distance = float(record.get('Distance_Driven_KM', 0))
                    cumulative_distance += distance
                    
                    if cumulative_distance >= 2.0:
                        last_2km_date = datetime.strptime(record['Date_of_Drive'], "%Y-%m-%d")
                        break
                except (ValueError, TypeError):
                    continue
            
            if last_2km_date:
                # Currency expires 3 months after last 2km drive
                expiry_date = last_2km_date + timedelta(days=90)
                return expiry_date.strftime("%Y-%m-%d")
            else:
                return "N/A"
                
        except Exception as e:
            return "N/A"
    
    def get_user_data(self, username):
        """Get all mileage data for a specific user"""
        try:
            # Get all records from Mileage_Logs with expected headers to handle duplicates
            expected_headers = ['Username', 'Date_of_Drive', 'Vehicle_No_MID', 'Initial_Mileage_KM', 'Final_Mileage_KM', 'Distance_Driven_KM', 'Vehicle_Type', 'Timestamp']
            
            try:
                records = self.mileage_worksheet.get_all_records(expected_headers=expected_headers)
            except:
                # Fallback: get all values and create records manually
                all_values = self.mileage_worksheet.get_all_values()
                if len(all_values) < 2:
                    return pd.DataFrame()
                
                headers = all_values[0]
                records = []
                for row in all_values[1:]:
                    record = {}
                    for i, header in enumerate(expected_headers):
                        if i < len(row):
                            record[header] = row[i]
                        else:
                            record[header] = ''
                    records.append(record)
            
            if not records:
                return pd.DataFrame()
            
            # Convert to DataFrame
            df = pd.DataFrame(records)
            
            # Filter for specific user
            user_data = df[df['Username'] == username].copy()
            
            if user_data.empty:
                return pd.DataFrame()
            
            # Convert date column to datetime
            user_data['Date_of_Drive'] = pd.to_datetime(user_data['Date_of_Drive'], errors='coerce')
            
            # Convert numeric columns to float
            numeric_columns = ['Initial_Mileage_KM', 'Final_Mileage_KM', 'Distance_Driven_KM']
            for col in numeric_columns:
                if col in user_data.columns:
                    user_data[col] = pd.to_numeric(user_data[col], errors='coerce')
            
            # Remove rows with invalid dates
            user_data = user_data.dropna(subset=['Date_of_Drive'])
            
            # Sort by date
            user_data = user_data.sort_values('Date_of_Drive')
            
            return user_data
            
        except Exception as e:
            raise Exception(f"Failed to get user data: {str(e)}")
    
    @st.cache_data(ttl=3600, show_spinner=False)  # 1 hour cache  
    def get_all_personnel_status(_self):
        """Get currency status for all personnel across both vehicle types"""
        try:
            all_personnel = []
            
            # Get Terrex personnel
            try:
                terrex_records = _self.terrex_worksheet.get_all_records()
            except:
                terrex_values = _self.terrex_worksheet.get_all_values()
                terrex_records = []
                if len(terrex_values) > 1:
                    headers = terrex_values[0]
                    for row in terrex_values[1:]:
                        record = {}
                        for i, header in enumerate(headers):
                            if i < len(row):
                                record[header] = row[i]
                        terrex_records.append(record)
            
            for record in terrex_records:
                username = record.get('Username', '').strip()
                if not username:
                    continue
                
                # Check if qualified
                qualification = record.get('Qualification', '').strip()
                qual_date = record.get('Qualification Date', '').strip()
                
                if qualification and qual_date:
                    personnel_data = {
                        'username': username,
                        'rank': record.get('Rank', ''),
                        'name': record.get('Name', ''),
                        'platoon': record.get('Platoon', ''),
                        'sub_unit': record.get('Sub Unit', ''),
                        'vehicle_type': 'Terrex',
                        'qualification': qualification,
                        'qual_date': qual_date,
                        'currency_status': record.get('Currency Maintained', 'N/A'),
                        'distance_3_months': float(record.get('Distance in Last 3 Months', 0) or 0),
                        'last_drive_date': record.get('Last Driven Date', 'N/A'),
                        'expiry_date': record.get('Lapsing Date', 'N/A'),
                        'days_to_expiry': record.get('Days to Expiry', 'N/A')
                    }
                    all_personnel.append(personnel_data)
            
            # Get Belrex personnel
            try:
                belrex_records = _self.belrex_worksheet.get_all_records()
            except:
                belrex_values = _self.belrex_worksheet.get_all_values()
                belrex_records = []
                if len(belrex_values) > 1:
                    headers = belrex_values[0]
                    for row in belrex_values[1:]:
                        record = {}
                        for i, header in enumerate(headers):
                            if i < len(row):
                                record[header] = row[i]
                        belrex_records.append(record)
            
            for record in belrex_records:
                username = record.get('Username', '').strip()
                if not username:
                    continue
                
                # Check if qualified
                qualification = record.get('Qualification', '').strip()
                qual_date = record.get('Qualification Date', '').strip()
                
                if qualification and qual_date:
                    personnel_data = {
                        'username': username,
                        'rank': record.get('Rank', ''),
                        'name': record.get('Name', ''),
                        'platoon': record.get('Platoon', ''),
                        'sub_unit': record.get('Sub Unit', ''),
                        'vehicle_type': 'Belrex',
                        'qualification': qualification,
                        'qual_date': qual_date,
                        'currency_status': record.get('Currency Maintained', 'N/A'),
                        'distance_3_months': float(record.get('Distance in Last 3 Months', 0) or 0),
                        'last_drive_date': record.get('Last Driven Date', 'N/A'),
                        'expiry_date': record.get('Lapsing Date', 'N/A'),
                        'days_to_expiry': record.get('Days to Expiry', 'N/A')
                    }
                    all_personnel.append(personnel_data)
            
            return all_personnel
            
        except Exception as e:
            raise Exception(f"Failed to get all personnel status: {str(e)}")
    
    @st.cache_data(ttl=7200, show_spinner=False)  # 2 hour cache for all names
    def get_all_personnel_names(_self):
        """Get all personnel names from both tracker sheets (qualified and unqualified)"""
        all_names = {}
        
        try:
            # Get all Terrex personnel (regardless of qualification status)
            try:
                terrex_records = _self.terrex_worksheet.get_all_records()
            except:
                terrex_values = _self.terrex_worksheet.get_all_values()
                terrex_records = []
                if len(terrex_values) > 1:
                    headers = terrex_values[0]
                    for row in terrex_values[1:]:
                        record = {}
                        for i, header in enumerate(headers):
                            if i < len(row):
                                record[header] = row[i]
                        terrex_records.append(record)
            
            for record in terrex_records:
                username = record.get('Username', '').strip()
                name = record.get('Name', '').strip()
                rank = record.get('Rank', '').strip()
                
                if username and name:  # Only need username and name to exist
                    if rank:
                        all_names[username] = f"{rank} {name}"
                    else:
                        all_names[username] = name
            
            # Get all Belrex personnel (regardless of qualification status)
            try:
                belrex_records = _self.belrex_worksheet.get_all_records()
            except:
                belrex_values = _self.belrex_worksheet.get_all_values()
                belrex_records = []
                if len(belrex_values) > 1:
                    headers = belrex_values[0]
                    for row in belrex_values[1:]:
                        record = {}
                        for i, header in enumerate(headers):
                            if i < len(row):
                                record[header] = row[i]
                        belrex_records.append(record)
            
            for record in belrex_records:
                username = record.get('Username', '').strip()
                name = record.get('Name', '').strip()
                rank = record.get('Rank', '').strip()
                
                if username and name:  # Only need username and name to exist
                    if rank:
                        all_names[username] = f"{rank} {name}"
                    else:
                        all_names[username] = name
            
            return all_names
            
        except Exception as e:
            return {}
    
    def is_admin_user(self, username):
        """Check if user has admin privileges"""
        # Main admin always has privileges
        if username == 'admin':
            return True
        
        # Check credentials file for admin status
        try:
            import json
            with open('credentials.json', 'r') as f:
                credentials = json.load(f)
            
            user_details = credentials.get(username)
            if isinstance(user_details, dict):
                return user_details.get('is_admin', False)
            else:
                # Legacy accounts
                return username in ['trooper1', 'trooper2', 'commander']
        except:
            # Fallback to legacy list
            return username in ['trooper1', 'trooper2', 'commander']
    
    @st.cache_data(ttl=7200, show_spinner=False)  # 2 hour cache
    def get_user_tracker_data(_self, username):
        """Get user's tracker data from both Terrex and Belrex sheets"""
        tracker_data = {'terrex': None, 'belrex': None}
        
        try:
            # Get Terrex data
            try:
                terrex_records = _self.terrex_worksheet.get_all_records()
            except:
                # Handle duplicate headers by using raw values
                terrex_values = _self.terrex_worksheet.get_all_values()
                terrex_records = []
                if len(terrex_values) > 1:
                    headers = terrex_values[0]
                    for row in terrex_values[1:]:
                        record = {}
                        for i, header in enumerate(headers):
                            if i < len(row):
                                record[header] = row[i]
                        terrex_records.append(record)
            
            for record in terrex_records:
                if record.get('Username') == username:
                    tracker_data['terrex'] = record
                    break
            
            # Get Belrex data
            try:
                belrex_records = _self.belrex_worksheet.get_all_records()
            except:
                # Handle duplicate headers by using raw values
                belrex_values = _self.belrex_worksheet.get_all_values()
                belrex_records = []
                if len(belrex_values) > 1:
                    headers = belrex_values[0]
                    for row in belrex_values[1:]:
                        record = {}
                        for i, header in enumerate(headers):
                            if i < len(row):
                                record[header] = row[i]
                        belrex_records.append(record)
            
            for record in belrex_records:
                if record.get('Username') == username:
                    tracker_data['belrex'] = record
                    break
                    
        except Exception as e:
            print(f"Warning: Failed to get tracker data: {str(e)}")
        
        return tracker_data
    
    def get_all_data(self):
        """Get all mileage data"""
        try:
            expected_headers = ['Username', 'Date_of_Drive', 'Vehicle_No_MID', 'Initial_Mileage_KM', 'Final_Mileage_KM', 'Distance_Driven_KM', 'Vehicle_Type', 'Timestamp']
            
            try:
                records = self.mileage_worksheet.get_all_records(expected_headers=expected_headers)
            except:
                # Fallback: get all values and create records manually
                all_values = self.mileage_worksheet.get_all_values()
                if len(all_values) < 2:
                    return pd.DataFrame()
                
                records = []
                for row in all_values[1:]:
                    record = {}
                    for i, header in enumerate(expected_headers):
                        if i < len(row):
                            record[header] = row[i]
                        else:
                            record[header] = ''
                    records.append(record)
            
            if not records:
                return pd.DataFrame()
            
            df = pd.DataFrame(records)
            df['Date_of_Drive'] = pd.to_datetime(df['Date_of_Drive'], errors='coerce')
            
            return df.sort_values(['Username', 'Date_of_Drive'])
            
        except Exception as e:
            raise Exception(f"Failed to get all data: {str(e)}")