import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import json
from auth import authenticate_user
from sheets_manager import SheetsManager
from utils import calculate_currency_status, format_status_badge

# Initialize session state
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'username' not in st.session_state:
    st.session_state.username = ""

def login_page():
    """Display login page"""
    st.title("🪖 MSC Mileage Tracker")
    st.subheader("Login Required")
    
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit_button = st.form_submit_button("Login")
        
        if submit_button:
            if authenticate_user(username, password):
                st.session_state.logged_in = True
                st.session_state.username = username
                st.success("Login successful!")
                st.rerun()
            else:
                st.error("Invalid username or password")

def main_app():
    """Main application interface"""
    # Header
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title("🪖 MSC Mileage Tracker")
    with col2:
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.rerun()
    
    # Initialize sheets manager
    try:
        sheets_manager = SheetsManager()
    except Exception as e:
        st.error(f"Failed to connect to Google Sheets: {str(e)}")
        st.info("Please ensure Google Sheets API credentials are properly configured.")
        return
    
    # Get user info and display welcome message
    user_qualifications = sheets_manager.check_user_qualifications(st.session_state.username)
    full_name = user_qualifications.get('full_name', st.session_state.username)
    rank = user_qualifications.get('rank', '')
    
    if full_name and rank:
        st.write(f"Welcome, **{rank} {full_name}**")
    elif full_name:
        st.write(f"Welcome, **{full_name}**")
    else:
        st.write(f"Welcome, **{st.session_state.username}**")
    
    # Check if user is main admin for special interface
    is_main_admin = st.session_state.username == 'admin'
    
    if is_main_admin:
        # Main admin interface - focused on management
        tab1, tab2 = st.tabs(["👥 Team Overview", "👤 Account Management"])
        
        with tab1:
            admin_team_dashboard(sheets_manager)
        
        with tab2:
            account_management_tab(sheets_manager)
    else:
        # Regular user interface
        tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "📝 Log Mileage", "🎯 Currency Status"])
        
        with tab1:
            dashboard_tab(sheets_manager)
        
        with tab2:
            log_mileage_tab(sheets_manager)
        
        with tab3:
            currency_status_tab(sheets_manager)

def dashboard_tab(sheets_manager):
    """Dashboard overview"""
    st.header("Dashboard Overview")
    
    try:
        # Check if user is admin
        is_admin = sheets_manager.is_admin_user(st.session_state.username)
        
        if is_admin:
            # Admin dashboard with Individual/Team options
            view_option = st.selectbox(
                "Select View:",
                ["Individual", "Team Overview"],
                key="admin_view_selector"
            )
            
            if view_option == "Team Overview":
                admin_team_dashboard(sheets_manager)
                return
            else:
                st.subheader("📊 Individual View")
        
        # Individual dashboard (for both admin and regular users)
        # Get user's mileage data
        user_data = sheets_manager.get_user_data(st.session_state.username)
        
        if user_data.empty:
            st.info("No mileage logs found. Start by logging your first mileage entry!")
            if not is_admin:
                return
        
        # Get user's tracker data
        tracker_data = sheets_manager.get_user_tracker_data(st.session_state.username)
        
        # Display key metrics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                label="Total Entries",
                value=len(user_data)
            )
        
        with col2:
            latest_entry = user_data.iloc[-1]
            st.metric(
                label="Last Logged",
                value=latest_entry['Date_of_Drive'].strftime("%Y-%m-%d")
            )
        
        with col3:
            total_distance = user_data['Distance_Driven_KM'].sum()
            st.metric(
                label="Total Distance",
                value=f"{total_distance:.1f} KM"
            )
        
        # Get user qualifications
        qualifications = sheets_manager.check_user_qualifications(st.session_state.username)
        
        # Currency status for each vehicle type
        st.subheader("Currency Status")
        
        # Display status for qualified vehicles only
        qualified_vehicles = []
        if qualifications['terrex']:
            qualified_vehicles.append('terrex')
        if qualifications['belrex']:
            qualified_vehicles.append('belrex')
        
        if len(qualified_vehicles) == 0:
            st.error("❌ You are not qualified for any vehicle type.")
            return
        
        if len(qualified_vehicles) == 1:
            # Single column for one vehicle
            vehicle = qualified_vehicles[0]
            if vehicle == 'terrex' and tracker_data['terrex']:
                st.markdown("**Terrex Currency**")
                terrex_data = tracker_data['terrex']
                currency_status = terrex_data.get('Currency Maintained', 'N/A')
                
                if currency_status.upper() == 'YES':
                    distance = float(terrex_data.get('Distance in Last 3 Months', 0) or 0)
                    st.success(f"✅ CURRENT - {distance:.1f} KM in last 3 months")
                elif currency_status.upper() == 'NO':
                    distance = float(terrex_data.get('Distance in Last 3 Months', 0) or 0)
                    st.error(f"❌ NOT CURRENT - {distance:.1f} KM in last 3 months")
                else:
                    st.info("⚠️ Status unknown")
                
                expiry_date = terrex_data.get('Lapsing Date', 'N/A')
                if expiry_date != 'N/A':
                    st.write(f"Expiry: {expiry_date}")
            elif vehicle == 'belrex' and tracker_data['belrex']:
                st.markdown("**Belrex Currency**")
                belrex_data = tracker_data['belrex']
                currency_status = belrex_data.get('Currency Maintained', 'N/A')
                
                if currency_status.upper() == 'YES':
                    distance = float(belrex_data.get('Distance in Last 3 Months', 0) or 0)
                    st.success(f"✅ CURRENT - {distance:.1f} KM in last 3 months")
                elif currency_status.upper() == 'NO':
                    distance = float(belrex_data.get('Distance in Last 3 Months', 0) or 0)
                    st.error(f"❌ NOT CURRENT - {distance:.1f} KM in last 3 months")
                else:
                    st.info("⚠️ Status unknown")
                
                expiry_date = belrex_data.get('Lapsing Date', 'N/A')
                if expiry_date != 'N/A':
                    st.write(f"Expiry: {expiry_date}")
        else:
            # Two columns for dual qualification
            col1, col2 = st.columns(2)
            with col1:
                if tracker_data['terrex']:
                    st.markdown("**Terrex Currency**")
                    terrex_data = tracker_data['terrex']
                    currency_status = terrex_data.get('Currency Maintained', 'N/A')
                    
                    if currency_status.upper() == 'YES':
                        distance = float(terrex_data.get('Distance in Last 3 Months', 0) or 0)
                        st.success(f"✅ CURRENT - {distance:.1f} KM in last 3 months")
                    elif currency_status.upper() == 'NO':
                        distance = float(terrex_data.get('Distance in Last 3 Months', 0) or 0)
                        st.error(f"❌ NOT CURRENT - {distance:.1f} KM in last 3 months")
                    else:
                        st.info("⚠️ Status unknown")
                    
                    expiry_date = terrex_data.get('Lapsing Date', 'N/A')
                    if expiry_date != 'N/A':
                        st.write(f"Expiry: {expiry_date}")
                else:
                    st.info("No Terrex data yet")
            
            with col2:
                if tracker_data['belrex']:
                    st.markdown("**Belrex Currency**")
                    belrex_data = tracker_data['belrex']
                    currency_status = belrex_data.get('Currency Maintained', 'N/A')
                    
                    if currency_status.upper() == 'YES':
                        distance = float(belrex_data.get('Distance in Last 3 Months', 0) or 0)
                        st.success(f"✅ CURRENT - {distance:.1f} KM in last 3 months")
                    elif currency_status.upper() == 'NO':
                        distance = float(belrex_data.get('Distance in Last 3 Months', 0) or 0)
                        st.error(f"❌ NOT CURRENT - {distance:.1f} KM in last 3 months")
                    else:
                        st.info("⚠️ Status unknown")
                    
                    expiry_date = belrex_data.get('Lapsing Date', 'N/A')
                    if expiry_date != 'N/A':
                        st.write(f"Expiry: {expiry_date}")
                else:
                    st.info("No Belrex data yet")
        
        # Recent entries
        st.subheader("Recent Mileage Logs")
        recent_data = user_data.tail(5)[['Date_of_Drive', 'Vehicle_Type', 'Vehicle_No_MID', 'Distance_Driven_KM']].copy()
        recent_data['Date_of_Drive'] = recent_data['Date_of_Drive'].dt.strftime("%Y-%m-%d")
        recent_data.columns = ['Date', 'Vehicle Type', 'Vehicle No.', 'Distance (KM)']
        st.dataframe(recent_data, use_container_width=True)
        
    except Exception as e:
        st.error(f"Error loading dashboard data: {str(e)}")

def admin_team_dashboard(sheets_manager):
    """Admin team overview dashboard"""
    st.subheader("👥 Team Overview")
    
    try:
        # Get all personnel status
        all_personnel = sheets_manager.get_all_personnel_status()
        
        if not all_personnel:
            st.warning("No personnel data found.")
            return
        
        # Convert to DataFrame for easier analysis
        import pandas as pd
        df = pd.DataFrame(all_personnel)
        
        # Summary statistics
        st.subheader("📈 Team Summary")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_personnel = len(df)
            st.metric("Total Personnel", total_personnel)
        
        with col2:
            current_count = len(df[df['currency_status'].str.upper() == 'YES'])
            st.metric("✅ Current", current_count, delta=f"{(current_count/total_personnel*100):.1f}%")
        
        with col3:
            not_current_count = len(df[df['currency_status'].str.upper() == 'NO'])
            st.metric("❌ Not Current", not_current_count, delta=f"{(not_current_count/total_personnel*100):.1f}%")
        
        with col4:
            # Count expiring soon (Days to Expiry <= 14 and currency is YES)
            try:
                df['days_to_expiry_num'] = pd.to_numeric(df['days_to_expiry'], errors='coerce')
                expiring_soon = len(df[(df['currency_status'].str.upper() == 'YES') & (df['days_to_expiry_num'] <= 14)])
            except:
                expiring_soon = 0
            st.metric("⚠️ Expiring Soon", expiring_soon)
        
        # Vehicle type breakdown
        st.subheader("🚗 Vehicle Type Breakdown")
        col1, col2 = st.columns(2)
        
        with col1:
            terrex_personnel = df[df['vehicle_type'] == 'Terrex']
            terrex_current = len(terrex_personnel[terrex_personnel['currency_status'].str.upper() == 'YES'])
            st.metric("Terrex Current", f"{terrex_current}/{len(terrex_personnel)}")
        
        with col2:
            belrex_personnel = df[df['vehicle_type'] == 'Belrex']
            belrex_current = len(belrex_personnel[belrex_personnel['currency_status'].str.upper() == 'YES'])
            st.metric("Belrex Current", f"{belrex_current}/{len(belrex_personnel)}")
        
        # Priority Actions Required
        st.subheader("🚨 Priority Actions Required")
        
        # Not current personnel
        not_current = df[df['currency_status'].str.upper() == 'NO']
        if len(not_current) > 0:
            st.error(f"**{len(not_current)} personnel need immediate currency drives:**")
            for _, person in not_current.iterrows():
                st.write(f"• **{person['rank']} {person['name']}** ({person['vehicle_type']}) - {person['distance_3_months']:.1f} KM in last 3 months")
        
        # Expiring soon personnel
        try:
            expiring = df[(df['currency_status'].str.upper() == 'YES') & (df['days_to_expiry_num'] <= 14)]
            if len(expiring) > 0:
                st.warning(f"**{len(expiring)} personnel expiring within 14 days:**")
                for _, person in expiring.iterrows():
                    days_left = person['days_to_expiry_num']
                    st.write(f"• **{person['rank']} {person['name']}** ({person['vehicle_type']}) - Expires in {days_left} days")
        except:
            pass
        
        # Platoon breakdown
        st.subheader("🏢 Platoon Status")
        
        # Group by platoon
        platoon_groups = df.groupby('platoon').agg({
            'currency_status': lambda x: (x.str.upper() == 'YES').sum(),
            'username': 'count'
        }).reset_index()
        platoon_groups.columns = ['Platoon', 'Current', 'Total']
        platoon_groups['Current_Rate'] = (platoon_groups['Current'] / platoon_groups['Total'] * 100).round(1)
        
        # Display platoon summary
        for _, platoon in platoon_groups.iterrows():
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"**{platoon['Platoon']}**: {platoon['Current']}/{platoon['Total']} current ({platoon['Current_Rate']:.1f}%)")
            with col2:
                if st.button(f"View Details", key=f"platoon_{platoon['Platoon']}"):
                    st.session_state.selected_platoon = platoon['Platoon']
        
        # Detailed platoon view
        if 'selected_platoon' in st.session_state:
            st.subheader(f"📋 {st.session_state.selected_platoon} Detailed Status")
            
            platoon_personnel = df[df['platoon'] == st.session_state.selected_platoon]
            
            # Display detailed table
            display_cols = ['rank', 'name', 'vehicle_type', 'currency_status', 'distance_3_months', 'expiry_date', 'last_drive_date']
            display_df = platoon_personnel[display_cols].copy()
            display_df.columns = ['Rank', 'Name', 'Vehicle', 'Status', '3-Month KM', 'Expiry Date', 'Last Drive']
            
            # Color code the status
            def color_status(val):
                if val == 'YES':
                    return 'background-color: #d4edda'
                elif val == 'NO':
                    return 'background-color: #f8d7da'
                return ''
            
            styled_df = display_df.style.map(color_status, subset=['Status'])
            st.dataframe(styled_df, use_container_width=True)
            
            if st.button("Close Details"):
                del st.session_state.selected_platoon
                st.rerun()
        
        # Full personnel table
        st.subheader("📊 Complete Personnel Status")
        
        # Add search/filter options
        col1, col2 = st.columns(2)
        with col1:
            search_term = st.text_input("Search by name or username:")
        with col2:
            status_filter = st.selectbox("Filter by status:", ["All", "Current", "Not Current"])
        
        # Apply filters
        filtered_df = df.copy()
        if search_term:
            filtered_df = filtered_df[
                filtered_df['name'].str.contains(search_term, case=False, na=False) |
                filtered_df['username'].str.contains(search_term, case=False, na=False)
            ]
        
        if status_filter == "Current":
            filtered_df = filtered_df[filtered_df['currency_status'].str.upper() == 'YES']
        elif status_filter == "Not Current":
            filtered_df = filtered_df[filtered_df['currency_status'].str.upper() == 'NO']
        
        # Display filtered table
        if len(filtered_df) > 0:
            display_cols = ['rank', 'name', 'platoon', 'vehicle_type', 'currency_status', 'distance_3_months', 'days_to_expiry', 'expiry_date']
            table_df = filtered_df[display_cols].copy()
            table_df.columns = ['Rank', 'Name', 'Platoon', 'Vehicle', 'Status', '3-Month KM', 'Days to Expiry', 'Expiry Date']
            
            st.dataframe(table_df, use_container_width=True)
        else:
            st.info("No personnel found matching the current filters.")
            
    except Exception as e:
        st.error(f"Error loading team dashboard: {str(e)}")

def log_mileage_tab(sheets_manager):
    """Mileage logging interface"""
    st.header("Log Vehicle Mileage")
    
    # Check user qualifications first
    try:
        qualifications = sheets_manager.check_user_qualifications(st.session_state.username)
        
        if not qualifications['terrex'] and not qualifications['belrex']:
            st.error("❌ You are not qualified for any vehicle type. Please contact your administrator.")
            return
            
    except Exception as e:
        st.error(f"Failed to check qualifications: {str(e)}")
        return
    
    with st.form("mileage_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            operation_date = st.date_input(
                "Date of Drive",
                value=datetime.now().date(),
                max_value=datetime.now().date()
            )
        
        with col2:
            # Dynamic vehicle type selection based on qualifications
            vehicle_options = []
            if qualifications['terrex']:
                vehicle_options.append("Terrex")
            if qualifications['belrex']:
                vehicle_options.append("Belrex")
            
            if len(vehicle_options) == 1:
                vehicle_type = st.selectbox(
                    "Vehicle Type",
                    options=vehicle_options,
                    disabled=True
                )
                st.info(f"You are only qualified for {vehicle_options[0]}")
            else:
                vehicle_type = st.selectbox(
                    "Vehicle Type",
                    options=vehicle_options
                )
        
        vehicle_no = st.text_input(
            "Vehicle No. (MID)",
            placeholder="Enter vehicle identification number"
        )
        
        col3, col4 = st.columns(2)
        
        with col3:
            initial_mileage = st.number_input(
                "Initial Mileage (KM)",
                min_value=0.0,
                max_value=999999.0,
                step=0.1,
                format="%.1f"
            )
        
        with col4:
            final_mileage = st.number_input(
                "Final Mileage (KM)",
                min_value=0.0,
                max_value=999999.0,
                step=0.1,
                format="%.1f"
            )
        
        # Calculate distance automatically
        if final_mileage > initial_mileage:
            distance_driven = final_mileage - initial_mileage
            st.info(f"Distance Driven: {distance_driven:.1f} KM")
        else:
            distance_driven = 0.0
            if final_mileage != 0.0 and initial_mileage != 0.0:
                st.error("Final mileage must be greater than initial mileage")
        
        submit_button = st.form_submit_button("Log Mileage", type="primary")
        
        if submit_button:
            # Validation
            if not vehicle_no.strip():
                st.error("Please enter a vehicle number (MID)")
                return
            
            if final_mileage <= initial_mileage:
                st.error("Final mileage must be greater than initial mileage")
                return
            
            if distance_driven <= 0:
                st.error("Distance driven must be greater than 0")
                return
            
            try:
                # Prepare data
                log_data = {
                    'Username': st.session_state.username,
                    'Date_of_Drive': operation_date.strftime("%Y-%m-%d"),
                    'Vehicle_No_MID': vehicle_no.strip(),
                    'Initial_Mileage_KM': initial_mileage,
                    'Final_Mileage_KM': final_mileage,
                    'Distance_Driven_KM': distance_driven,
                    'Vehicle_Type': vehicle_type,
                    'Timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                
                # Save to Google Sheets
                sheets_manager.add_mileage_log(log_data)
                
                st.success(f"✅ Mileage logged successfully!")
                st.info(f"**Date:** {operation_date.strftime('%Y-%m-%d')} | **Vehicle:** {vehicle_type} ({vehicle_no}) | **Distance:** {distance_driven:.1f} KM")
                
            except Exception as e:
                st.error(f"Failed to log mileage: {str(e)}")

def currency_status_tab(sheets_manager):
    """Currency status tracking"""
    st.header("Currency Status")
    
    try:
        # Check user qualifications first
        qualifications = sheets_manager.check_user_qualifications(st.session_state.username)
        
        if not qualifications['terrex'] and not qualifications['belrex']:
            st.error("❌ You are not qualified for any vehicle type. Please contact your administrator.")
            return
        
        # Get user's tracker data (currency status comes from tracker sheets, not mileage logs)
        tracker_data = sheets_manager.get_user_tracker_data(st.session_state.username)
        
        # Display status for each vehicle type
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🚗 Terrex Status")
            if qualifications['terrex']:
                if tracker_data['terrex']:
                    terrex_data = tracker_data['terrex']
                    currency_status = terrex_data.get('Currency Maintained', 'N/A')
                    distance_3_months = float(terrex_data.get('Distance in Last 3 Months', 0) or 0)
                    
                    if currency_status.upper() == 'YES':
                        st.success("✅ CURRENT")
                        st.write(f"**3-Month Distance:** {distance_3_months:.1f} KM")
                    elif currency_status.upper() == 'NO':
                        st.error("❌ NOT CURRENT")
                        st.write(f"**3-Month Distance:** {distance_3_months:.1f} KM")
                        st.write("**Required:** 2.0 KM minimum")
                    else:
                        st.info("⚠️ Status unknown")
                    
                    expiry_date = terrex_data.get('Lapsing Date', 'N/A')
                    if expiry_date != 'N/A':
                        st.write(f"**Expiry Date:** {expiry_date}")
                    
                    last_drive = terrex_data.get('Last Driven Date', 'N/A')
                    if last_drive != 'N/A':
                        st.write(f"**Last Drive:** {last_drive}")
                else:
                    st.info("No Terrex driving data available yet")
            else:
                st.info("❌ Not qualified for Terrex")
        
        with col2:
            st.subheader("🚛 Belrex Status")
            if qualifications['belrex']:
                if tracker_data['belrex']:
                    belrex_data = tracker_data['belrex']
                    currency_status = belrex_data.get('Currency Maintained', 'N/A')
                    distance_3_months = float(belrex_data.get('Distance in Last 3 Months', 0) or 0)
                    
                    if currency_status.upper() == 'YES':
                        st.success("✅ CURRENT")
                        st.write(f"**3-Month Distance:** {distance_3_months:.1f} KM")
                    elif currency_status.upper() == 'NO':
                        st.error("❌ NOT CURRENT")
                        st.write(f"**3-Month Distance:** {distance_3_months:.1f} KM")
                        st.write("**Required:** 2.0 KM minimum")
                    else:
                        st.info("⚠️ Status unknown")
                    
                    expiry_date = belrex_data.get('Lapsing Date', 'N/A')
                    if expiry_date != 'N/A':
                        st.write(f"**Expiry Date:** {expiry_date}")
                    
                    last_drive = belrex_data.get('Last Driven Date', 'N/A')
                    if last_drive != 'N/A':
                        st.write(f"**Last Drive:** {last_drive}")
                else:
                    st.info("No Belrex driving data available yet")
            else:
                st.info("❌ Not qualified for Belrex")
        
        # Currency rules explanation
        st.info("""
        **Currency Rules:**
        - ✅ **Current:** 2.0 KM or more driven in the last 3 months
        - ❌ **Not Current:** Less than 2.0 KM driven in the last 3 months
        - **Expiry:** Currency expires 3 months after last 2.0 KM cumulative drive
        """)
        
        # Historical data
        st.subheader("Mileage History")
        
        # Get user's mileage logs
        user_data = sheets_manager.get_user_data(st.session_state.username)
        
        if not user_data.empty:
            # Display all user data
            display_data = user_data[['Date_of_Drive', 'Vehicle_Type', 'Vehicle_No_MID', 'Distance_Driven_KM']].copy()
            display_data['Date_of_Drive'] = display_data['Date_of_Drive'].dt.strftime("%Y-%m-%d")
            display_data.columns = ['Date', 'Vehicle Type', 'Vehicle No.', 'Distance (KM)']
            display_data = display_data.sort_values('Date', ascending=False)
            
            st.dataframe(display_data, use_container_width=True)
            
            # Summary statistics
            st.subheader("Summary Statistics")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Total Distance", f"{user_data['Distance_Driven_KM'].sum():.1f} KM")
            
            with col2:
                st.metric("Average Distance", f"{user_data['Distance_Driven_KM'].mean():.1f} KM")
            
            with col3:
                terrex_count = len(user_data[user_data['Vehicle_Type'] == 'Terrex'])
                belrex_count = len(user_data[user_data['Vehicle_Type'] == 'Belrex'])
                st.metric("Terrex/Belrex Logs", f"{terrex_count}/{belrex_count}")
        else:
            st.info("No mileage logs found in the app yet. Start logging your drives!")
        
    except Exception as e:
        st.error(f"Error loading currency status: {str(e)}")

def account_management_tab(sheets_manager):
    """Account management for main admin"""
    st.header("👤 Account Management")
    
    try:
        # Load current credentials
        import json
        try:
            with open('credentials.json', 'r') as f:
                credentials = json.load(f)
        except FileNotFoundError:
            st.error("Credentials file not found.")
            return
        
        st.info("💡 **Note**: New accounts are added directly to the Google Sheets. Use this interface to manage existing accounts.")
        
        st.divider()
        
        # Existing accounts management
        st.subheader("📋 Existing Accounts")
        
        # Filter accounts (exclude main admin from list)
        manageable_accounts = {k: v for k, v in credentials.items() if k != 'admin'}
        
        if not manageable_accounts:
            st.info("No user accounts found. Create the first account above.")
            return
        
        # Display accounts in a table format
        account_data = []
        for username, details in manageable_accounts.items():
            # Handle different credential formats (old vs new)
            if isinstance(details, dict):
                is_admin = details.get('is_admin', username in ['trooper1', 'trooper2', 'commander'])
                created_by = details.get('created_by', 'Legacy')
                created_date = details.get('created_date', 'Unknown')
            else:
                # Old format - just password hash
                is_admin = username in ['trooper1', 'trooper2', 'commander']
                created_by = 'Legacy'
                created_date = 'Unknown'
            
            account_data.append({
                'Username': username,
                'Type': 'Admin' if is_admin else 'Regular',
                'Created By': created_by,
                'Created Date': created_date,
                'Actions': username
            })
        
        df = pd.DataFrame(account_data)
        
        # Display table
        st.dataframe(df[['Username', 'Type', 'Created By', 'Created Date']], use_container_width=True)
        
        st.divider()
        
        # Account modification section
        st.subheader("✏️ Modify Account")
        
        col1, col2 = st.columns(2)
        
        with col1:
            selected_user = st.selectbox(
                "Select account to modify:",
                options=[''] + list(manageable_accounts.keys()),
                key="modify_user_select"
            )
        
        if selected_user:
            current_details = manageable_accounts[selected_user]
            if isinstance(current_details, dict):
                current_is_admin = current_details.get('is_admin', selected_user in ['trooper1', 'trooper2', 'commander'])
            else:
                current_is_admin = selected_user in ['trooper1', 'trooper2', 'commander']
            
            with col2:
                new_admin_status = st.checkbox(
                    "Admin Privileges", 
                    value=current_is_admin,
                    key="modify_admin_status"
                )
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("Update Privileges", key="update_privileges"):
                    # Update the credentials
                    if isinstance(credentials[selected_user], dict):
                        credentials[selected_user]['is_admin'] = new_admin_status
                        credentials[selected_user]['modified_by'] = st.session_state.username
                        credentials[selected_user]['modified_date'] = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
                    else:
                        # Convert old format to new format
                        credentials[selected_user] = {
                            "password": credentials[selected_user],
                            "is_admin": new_admin_status,
                            "created_by": "Legacy",
                            "modified_by": st.session_state.username,
                            "modified_date": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
                    
                    # Save updated credentials
                    with open('credentials.json', 'w') as f:
                        json.dump(credentials, f, indent=2)
                    
                    status_change = "granted" if new_admin_status else "revoked"
                    st.success(f"✅ Admin privileges {status_change} for '{selected_user}'")
                    st.rerun()
            
            with col2:
                new_password = st.text_input("New Password (optional):", type="password", key="new_pass_input")
                if st.button("Reset Password", key="reset_password") and new_password:
                    import hashlib
                    hashed_password = hashlib.sha256(new_password.encode()).hexdigest()
                    
                    if isinstance(credentials[selected_user], dict):
                        credentials[selected_user]['password'] = hashed_password
                        credentials[selected_user]['modified_by'] = st.session_state.username
                        credentials[selected_user]['modified_date'] = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
                    else:
                        credentials[selected_user] = {
                            "password": hashed_password,
                            "is_admin": selected_user in ['trooper1', 'trooper2', 'commander'],
                            "created_by": "Legacy",
                            "modified_by": st.session_state.username,
                            "modified_date": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
                    
                    # Save updated credentials
                    with open('credentials.json', 'w') as f:
                        json.dump(credentials, f, indent=2)
                    
                    st.success(f"✅ Password reset for '{selected_user}'")
                    st.rerun()
            
            with col3:
                if st.button("🗑️ Delete Account", key="delete_account", type="secondary"):
                    if selected_user in ['trooper1', 'trooper2', 'commander']:
                        st.error("Cannot delete built-in admin accounts.")
                    else:
                        # Confirm deletion
                        if st.button("⚠️ Confirm Delete", key="confirm_delete", type="secondary"):
                            del credentials[selected_user]
                            
                            # Save updated credentials
                            with open('credentials.json', 'w') as f:
                                json.dump(credentials, f, indent=2)
                            
                            st.success(f"✅ Account '{selected_user}' deleted")
                            st.rerun()
        
        # Statistics
        st.divider()
        st.subheader("📊 Account Statistics")
        
        col1, col2, col3 = st.columns(3)
        
        total_accounts = len(manageable_accounts)
        admin_accounts = sum(1 for details in manageable_accounts.values() 
                           if (isinstance(details, dict) and details.get('is_admin', False)) or 
                              (isinstance(details, str) and any(acc in manageable_accounts for acc in ['trooper1', 'trooper2', 'commander'])))
        regular_accounts = total_accounts - admin_accounts
        
        with col1:
            st.metric("Total Accounts", total_accounts)
        with col2:
            st.metric("Admin Accounts", admin_accounts)
        with col3:
            st.metric("Regular Accounts", regular_accounts)
            
    except Exception as e:
        st.error(f"Error in account management: {str(e)}")

def main():
    """Main application entry point"""
    st.set_page_config(
        page_title="MSC Mileage Tracker",
        page_icon="🪖",
        layout="wide",
        initial_sidebar_state="collapsed"
    )
    
    # Custom CSS for military styling
    st.markdown("""
    <style>
        .status-current {
            background-color: #d4edda;
            color: #155724;
            padding: 10px;
            border-radius: 5px;
            border-left: 5px solid #28a745;
            margin: 10px 0;
        }
        .status-expiring {
            background-color: #fff3cd;
            color: #856404;
            padding: 10px;
            border-radius: 5px;
            border-left: 5px solid #ffc107;
            margin: 10px 0;
        }
        .status-expired {
            background-color: #f8d7da;
            color: #721c24;
            padding: 10px;
            border-radius: 5px;
            border-left: 5px solid #dc3545;
            margin: 10px 0;
        }
    </style>
    """, unsafe_allow_html=True)
    
    if not st.session_state.logged_in:
        login_page()
    else:
        main_app()

if __name__ == "__main__":
    main()
