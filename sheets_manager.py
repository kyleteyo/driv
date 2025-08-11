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
            
        # Setup User Management worksheet - preserve existing data
        try:
            self.user_management_worksheet = self.spreadsheet.worksheet('User_Management')
        except gspread.WorksheetNotFound:
            # Create User_Management worksheet only if it doesn't exist
            self.user_management_worksheet = self.spreadsheet.add_worksheet(title='User_Management', rows=1000, cols=3)
            headers = ['Username', 'Is_Commander', 'Is_Admin']
            self.user_management_worksheet.append_row(headers)
            
            # Add default accounts with simplified structure
            default_accounts = [
                ['trooper1', 'FALSE', 'FALSE'],
                ['trooper2', 'FALSE', 'FALSE'],
                ['commander', 'TRUE', 'FALSE']
            ]
            for account_row in default_accounts:
                self.user_management_worksheet.append_row(account_row)
    
    @st.cache_data(ttl=900, show_spinner=False)  # 15 minute cache for qualifications (balanced performance)
    def check_user_qualifications(_self, username):
        """Check if user is qualified for Terrex and/or Belrex based on presence in tracker sheets"""
        qualifications = {'terrex': False, 'belrex': False, 'full_name': '', 'rank': '', 'is_admin': False}
        
        # Check if user is admin and commander from User Management sheet
        user_management = _self.get_user_management_info(username)
        is_admin = user_management.get('is_admin', False)
        is_commander = user_management.get('is_commander', False)
        qualifications['is_admin'] = is_admin
        qualifications['is_commander'] = is_commander
        
        # Special handling for built-in accounts
        if username == 'admin':
            # Admin gets full qualification and display names
            qualifications['terrex'] = True
            qualifications['belrex'] = True
            qualifications['full_name'] = 'ADMIN'
            qualifications['rank'] = 'ADMIN'
            return qualifications
        elif username in ['trooper1', 'trooper2', 'commander']:
            # Test accounts get full qualification and display names
            qualifications['terrex'] = True
            qualifications['belrex'] = True
            qualifications['full_name'] = username.upper()
            qualifications['rank'] = 'CDR' if username == 'commander' else 'TPR'
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
    
    def get_safety_infographics(self):
        """Get safety infographics submissions from Google Sheets"""
        try:
            # Try to access safety infographics sheet
            try:
                safety_sheet = self.gc.open_by_key(self.sheet_id).worksheet('Safety_Infographics')
            except:
                # Sheet doesn't exist yet, return empty list
                return []
            
            records = safety_sheet.get_all_records()
            return records
        except Exception as e:
            print(f"Error getting safety infographics: {e}")
            return []
    
    def get_safety_pointers(self):
        """Get safety pointers submissions from Google Sheets"""
        try:
            # Try to access safety pointers sheet
            try:
                safety_sheet = self.gc.open_by_key(self.sheet_id).worksheet('Safety_Pointers')
            except:
                # Sheet doesn't exist yet, return empty list
                return []
            
            records = safety_sheet.get_all_records()
            return records
        except Exception as e:
            print(f"Error getting safety pointers: {e}")
            return []
    
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
    
    def get_safety_infographics(self):
        """Get safety infographics submissions sorted by newest first"""
        try:
            # Try to access safety infographics sheet
            try:
                safety_sheet = self.spreadsheet.worksheet('Safety_Infographics')
                
                # Define expected headers to handle duplicates
                expected_headers = ['Title', 'Image_URL', 'Submitter', 'Date', 'Storage_Size', 'File_Type']
                
                try:
                    records = safety_sheet.get_all_records(expected_headers=expected_headers)
                except:
                    # Fallback: get all values and create records manually
                    all_values = safety_sheet.get_all_values()
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
                
                # Sort by date (newest first) if records exist
                if records:
                    try:
                        records = sorted(records, key=lambda x: x.get('Date', ''), reverse=True)
                    except Exception as sort_error:
                        print(f"Warning: Could not sort infographics by date: {sort_error}")
                        records = list(reversed(records))
                
                return records
            except Exception as sheet_error:
                print(f"Safety_Infographics sheet not found: {sheet_error}")
                return []
            
        except Exception as e:
            print(f"Error getting safety infographics: {e}")
            return []
    
    def get_safety_pointers(self):
        """Get safety pointers submissions sorted by newest first"""
        try:
            # Try to access safety pointers sheet
            try:
                safety_sheet = self.spreadsheet.worksheet('Safety_Pointers')
                records = safety_sheet.get_all_records()
                
                # Sort by submission date (newest first) if records exist
                if records:
                    try:
                        # Sort by Submission_Date in descending order (newest first)
                        records = sorted(records, key=lambda x: x.get('Submission_Date', ''), reverse=True)
                    except Exception as sort_error:
                        print(f"Warning: Could not sort safety pointers by date: {sort_error}")
                        # Return records in reverse order as fallback (newest at top)
                        records = list(reversed(records))
                
                return records
            except Exception as sheet_error:
                print(f"Safety_Pointers sheet not found: {sheet_error}")
                return []
            
        except Exception as e:
            print(f"Error getting safety pointers: {e}")
            return []

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
    
    @st.cache_data(ttl=900, show_spinner=False)  # 15 minute cache for personnel status (faster updates)
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
    
    def get_user_full_name(self, username):
        """Get user's full name with rank from tracker sheets"""
        try:
            all_names = self.get_all_personnel_names()
            return all_names.get(username, username)
        except Exception as e:
            return username
    
    @st.cache_data(ttl=300, show_spinner=False)  # 5 minute cache for user management (balanced)
    def get_user_management_info(_self, username):
        """Get user management information from User_Management worksheet"""
        try:
            user_management_data = _self.user_management_worksheet.get_all_records()
            for user_record in user_management_data:
                if user_record.get('Username', '').lower() == username.lower():
                    return {
                        'is_admin': user_record.get('Is_Admin', '').upper() == 'TRUE',
                        'is_commander': user_record.get('Is_Commander', '').upper() == 'TRUE'
                    }
        except Exception as e:
            print(f"Error getting user management info: {e}")
            
        # Fallback to default accounts if not found in sheet
        # Only admin has admin privileges, others are troopers or commanders
        if username == 'admin':
            return {
                'is_admin': True,
                'is_commander': False
            }
        elif username == 'commander':
            return {
                'is_admin': False,
                'is_commander': True
            }
        elif username in ['trooper1', 'trooper2']:
            return {
                'is_admin': False,
                'is_commander': False
            }
            
        return {'is_admin': False, 'is_commander': False}
    
    def is_admin_user(self, username):
        """Check if user is an admin (has administrative privileges)"""
        user_info = self.get_user_management_info(username)
        return user_info.get('is_admin', False)
    
    def is_commander_user(self, username):
        """Check if user is a commander (has commander privileges)"""
        user_info = self.get_user_management_info(username)
        return user_info.get('is_commander', False)
    
    def update_user_permissions(self, username, is_admin=None, is_commander=None):
        """Update user permissions in User_Management worksheet"""
        try:
            # Clear cache when updating permissions for immediate effect
            st.cache_data.clear()
            user_management_data = self.user_management_worksheet.get_all_records()
            user_found = False
            
            # Look for existing user
            for i, user_record in enumerate(user_management_data):
                if user_record.get('Username', '').lower() == username.lower():
                    # Update existing user
                    row_index = i + 2  # +2 because sheet is 1-indexed and has header
                    
                    if is_admin is not None:
                        self.user_management_worksheet.update_cell(row_index, 3, 'TRUE' if is_admin else 'FALSE')
                    if is_commander is not None:
                        self.user_management_worksheet.update_cell(row_index, 2, 'TRUE' if is_commander else 'FALSE')
                    

                    user_found = True
                    break
            
            # If user not found, add new user
            if not user_found:
                new_row = [
                    username,
                    'TRUE' if is_commander else 'FALSE',
                    'TRUE' if is_admin else 'FALSE'
                ]
                self.user_management_worksheet.append_row(new_row)
            
            return True
            
        except Exception as e:
            print(f"Error updating user permissions: {e}")
            return False
    
    def get_all_user_permissions(self):
        """Get all user permissions from User_Management worksheet"""
        try:
            return self.user_management_worksheet.get_all_records()
        except Exception as e:
            print(f"Error getting all user permissions: {e}")
            return []
    
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