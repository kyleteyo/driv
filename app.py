import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import json
import time
from auth import authenticate_user, change_password, get_user_info
from sheets_manager import SheetsManager
from utils import calculate_currency_status, format_status_badge
from performance_config import get_cached_data, set_cached_data
# Removed api_optimizer import to fix compatibility

# Initialize session state with persistence
def init_session_state():
    """Initialize session state with persistent login"""
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'username' not in st.session_state:
        st.session_state.username = ""
    if 'sheets_manager' not in st.session_state:
        st.session_state.sheets_manager = None
    if 'session_initialized' not in st.session_state:
        st.session_state.session_initialized = True

# Check for stored session on app start
def check_stored_session():
    """Check if user has a stored session and restore it"""
    # This will be handled by the browser storage script
    pass

init_session_state()

# Performance optimization: Cache Google Sheets connection
@st.cache_resource
def get_sheets_manager():
    """Get cached sheets manager instance"""
    try:
        return SheetsManager()
    except Exception as e:
        st.error(f"Failed to connect to Google Sheets: {str(e)}")
        return None

def login_page():
    """Display login page"""
    st.title("🪖 MSC DRIVr")
    st.subheader("Login Required")
    
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit_button = st.form_submit_button("Login")
        
        if submit_button:
            if authenticate_user(username, password):
                st.session_state.logged_in = True
                st.session_state.username = username
                # Store session in browser storage
                st.components.v1.html(f"""
                <script>
                sessionStorage.setItem('msc_drivr_logged_in', 'true');
                sessionStorage.setItem('msc_drivr_username', '{username}');
                </script>
                """, height=0)
                st.success("Login successful!")
                st.rerun()
            else:
                st.error("Invalid username or password")

def main_app():
    """Main application interface"""
    # Header
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title("🪖 MSC DRIVr")
    with col2:
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.session_state.username = ""
            # Clear session from browser storage
            st.components.v1.html("""
            <script>
            sessionStorage.removeItem('msc_drivr_logged_in');
            sessionStorage.removeItem('msc_drivr_username');
            </script>
            """, height=0)
            st.rerun()
    
    # Initialize sheets manager with caching
    sheets_manager = get_sheets_manager()
    if sheets_manager is None:
        st.info("Please ensure Google Sheets API credentials are properly configured.")
        return
    
    # Get user info and display welcome message
    user_qualifications = sheets_manager.check_user_qualifications(st.session_state.username)
    full_name = user_qualifications.get('full_name', st.session_state.username)
    rank = user_qualifications.get('rank', '')
    
    # Check if user is main admin for special interface
    is_main_admin = st.session_state.username == 'admin'
    
    if is_main_admin:
        st.markdown("## Admin Dashboard")
    else:
        if full_name and rank:
            st.write(f"Welcome, **{rank} {full_name}**")
        elif full_name:
            st.write(f"Welcome, **{full_name}**")
        else:
            st.write(f"Welcome, **{st.session_state.username}**")
    
    if is_main_admin:
        # Main admin interface - focused on management with persistent tab state
        
        # Initialize active tab if not set
        if 'admin_active_tab' not in st.session_state:
            st.session_state.admin_active_tab = 0
        
        # Create tab buttons for better state control
        col1, col2 = st.columns(2)
        with col1:
            if st.button("👥 Team Overview", key="team_tab", use_container_width=True, 
                        type="primary" if st.session_state.admin_active_tab == 0 else "secondary"):
                st.session_state.admin_active_tab = 0
                st.rerun()
        with col2:
            if st.button("👤 Account Management", key="account_tab", use_container_width=True,
                        type="primary" if st.session_state.admin_active_tab == 1 else "secondary"):
                st.session_state.admin_active_tab = 1
                st.rerun()
        
        st.markdown("---")
        
        # Show content based on active tab
        if st.session_state.admin_active_tab == 0:
            admin_team_dashboard(sheets_manager)
        else:
            account_management_tab(sheets_manager)
    else:
        # Regular user interface
        tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "📝 Log Mileage", "🎯 Currency Status", "🔐 Change Password"])
        
        with tab1:
            dashboard_tab(sheets_manager)
        
        with tab2:
            log_mileage_tab(sheets_manager)
        
        with tab3:
            currency_status_tab(sheets_manager)
        
        with tab4:
            change_password_tab()

def dashboard_tab(sheets_manager):
    """Dashboard overview"""
    
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
        # Get user qualifications
        qualifications = sheets_manager.check_user_qualifications(st.session_state.username)
        
        # Get user's tracker data
        tracker_data = sheets_manager.get_user_tracker_data(st.session_state.username)
        
        # Currency status display - most important information
        
        # Check qualifications and display currency status prominently
        qualified_vehicles = []
        if qualifications['terrex']:
            qualified_vehicles.append('terrex')
        if qualifications['belrex']:
            qualified_vehicles.append('belrex')
        
        if len(qualified_vehicles) == 0:
            st.error("❌ You are not qualified for any vehicle type.")
            return
        
        # Show currency status for each qualified vehicle with prominent styling
        for vehicle in qualified_vehicles:
            if vehicle == 'terrex' and tracker_data['terrex']:
                terrex_data = tracker_data['terrex']
                currency_status = terrex_data.get('Currency Maintained', 'N/A')
                distance = float(terrex_data.get('Distance in Last 3 Months', 0) or 0)
                expiry_date = terrex_data.get('Lapsing Date', 'N/A')
                
                # Large, prominent status display
                if currency_status.upper() == 'YES':
                    st.markdown("""
                    <div class="status-current">
                        <h2>🚛 TERREX - ✅ CURRENT</h2>
                        <p><strong>{:.1f} KM</strong> driven in last 3 months (Min: 2.0 KM)</p>
                        <p>Currency expires: <strong>{}</strong></p>
                    </div>
                    """.format(distance, expiry_date), unsafe_allow_html=True)
                elif currency_status.upper() == 'NO':
                    st.markdown("""
                    <div class="status-expired">
                        <h2>🚛 TERREX - ❌ NOT CURRENT</h2>
                        <p><strong>{:.1f} KM</strong> driven in last 3 months (Min: 2.0 KM required)</p>
                        <p><strong>ACTION REQUIRED:</strong> Log mileage to maintain currency</p>
                    </div>
                    """.format(distance), unsafe_allow_html=True)
                else:
                    st.markdown("""
                    <div class="status-expiring">
                        <h2>🚛 TERREX - ⚠️ STATUS UNKNOWN</h2>
                        <p>Unable to determine currency status</p>
                    </div>
                    """, unsafe_allow_html=True)
            
            elif vehicle == 'belrex' and tracker_data['belrex']:
                belrex_data = tracker_data['belrex']
                currency_status = belrex_data.get('Currency Maintained', 'N/A')
                distance = float(belrex_data.get('Distance in Last 3 Months', 0) or 0)
                expiry_date = belrex_data.get('Lapsing Date', 'N/A')
                
                # Large, prominent status display
                if currency_status.upper() == 'YES':
                    st.markdown("""
                    <div class="status-current">
                        <h2>🚗 BELREX - ✅ CURRENT</h2>
                        <p><strong>{:.1f} KM</strong> driven in last 3 months (Min: 2.0 KM)</p>
                        <p>Currency expires: <strong>{}</strong></p>
                    </div>
                    """.format(distance, expiry_date), unsafe_allow_html=True)
                elif currency_status.upper() == 'NO':
                    st.markdown("""
                    <div class="status-expired">
                        <h2>🚗 BELREX - ❌ NOT CURRENT</h2>
                        <p><strong>{:.1f} KM</strong> driven in last 3 months (Min: 2.0 KM required)</p>
                        <p><strong>ACTION REQUIRED:</strong> Log mileage to maintain currency</p>
                    </div>
                    """.format(distance), unsafe_allow_html=True)
                else:
                    st.markdown("""
                    <div class="status-expiring">
                        <h2>🚗 BELREX - ⚠️ STATUS UNKNOWN</h2>
                        <p>Unable to determine currency status</p>
                    </div>
                    """, unsafe_allow_html=True)
            
            elif vehicle == 'terrex':
                st.markdown("""
                <div class="status-expiring">
                    <h2>🚛 TERREX - ⚠️ NO DATA</h2>
                    <p>No mileage data found. Start logging to track your currency.</p>
                </div>
                """, unsafe_allow_html=True)
            
            elif vehicle == 'belrex':
                st.markdown("""
                <div class="status-expiring">
                    <h2>🚗 BELREX - ⚠️ NO DATA</h2>
                    <p>No mileage data found. Start logging to track your currency.</p>
                </div>
                """, unsafe_allow_html=True)
        
        
        # Show recent entries only if data exists and user wants to see it
        user_data = sheets_manager.get_user_data(st.session_state.username)
        if not user_data.empty:
            with st.expander("📋 Recent Mileage Logs (Last 5)", expanded=False):
                recent_data = user_data.tail(5)[['Date_of_Drive', 'Vehicle_Type', 'Vehicle_No_MID', 'Distance_Driven_KM']].copy()
                recent_data['Date_of_Drive'] = recent_data['Date_of_Drive'].dt.strftime("%Y-%m-%d")
                recent_data.columns = ['Date', 'Vehicle Type', 'Vehicle No.', 'Distance (KM)']
                st.dataframe(recent_data, use_container_width=True)
        
    except Exception as e:
        st.error(f"Error loading dashboard data: {str(e)}")

def admin_team_dashboard(sheets_manager):
    """Revamped admin team overview dashboard"""
    try:
        # Get all personnel status
        all_personnel = sheets_manager.get_all_personnel_status()
        
        if not all_personnel:
            st.warning("No personnel data found.")
            return
        
        # Convert to DataFrame for easier analysis
        import pandas as pd
        df = pd.DataFrame(all_personnel)
        
        # Key Metrics Cards - Most Important Information First
        col1, col2, col3, col4 = st.columns(4)
        
        total_personnel = len(df)
        current_count = len(df[df['currency_status'].str.upper() == 'YES'])
        not_current_count = len(df[df['currency_status'].str.upper() == 'NO'])
        
        try:
            df['days_to_expiry_num'] = pd.to_numeric(df['days_to_expiry'], errors='coerce')
            expiring_soon = len(df[(df['currency_status'].str.upper() == 'YES') & (df['days_to_expiry_num'] <= 14)])
        except:
            expiring_soon = 0
        
        with col1:
            current_rate = (current_count/total_personnel*100) if total_personnel > 0 else 0
            st.markdown(f"""
            <div class="metric-card-current">
                <h2>✅ {current_count}</h2>
                <p>Current Personnel</p>
                <small>{current_rate:.1f}% of {total_personnel}</small>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            not_current_rate = (not_current_count/total_personnel*100) if total_personnel > 0 else 0
            st.markdown(f"""
            <div class="metric-card-expired">
                <h2>❌ {not_current_count}</h2>
                <p>Not Current</p>
                <small>{not_current_rate:.1f}% need drives</small>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div class="metric-card-expiring">
                <h2>⚠️ {expiring_soon}</h2>
                <p>Expiring Soon</p>
                <small>Within 14 days</small>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            terrex_personnel = df[df['vehicle_type'] == 'Terrex']
            belrex_personnel = df[df['vehicle_type'] == 'Belrex']
            terrex_current = len(terrex_personnel[terrex_personnel['currency_status'].str.upper() == 'YES'])
            belrex_current = len(belrex_personnel[belrex_personnel['currency_status'].str.upper() == 'YES'])
            
            st.markdown(f"""
            <div class="metric-card-vehicles">
                <h3>🚛 Terrex: {terrex_current}/{len(terrex_personnel)}</h3>
                <h3>🚗 Belrex: {belrex_current}/{len(belrex_personnel)}</h3>
                <small>Current/Total</small>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Critical Actions Section - Clean and Prominent
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 🚨 Immediate Action Required")
            not_current = df[df['currency_status'].str.upper() == 'NO']
            if len(not_current) > 0:
                with st.container():
                    for _, person in not_current.head(10).iterrows():  # Limit to 10 for cleaner display
                        st.markdown(f"""
                        <div class="action-item-critical">
                            <strong>{person['rank']} {person['name']}</strong><br>
                            <small>{person['vehicle_type']} • {person['distance_3_months']:.1f} KM (3mo)</small>
                        </div>
                        """, unsafe_allow_html=True)
                    if len(not_current) > 10:
                        st.info(f"... and {len(not_current) - 10} more personnel")
            else:
                st.success("🎉 All personnel are current!")
        
        with col2:
            st.markdown("### ⏰ Expiring Within 14 Days")
            try:
                expiring = df[(df['currency_status'].str.upper() == 'YES') & (df['days_to_expiry_num'] <= 14)]
                if len(expiring) > 0:
                    with st.container():
                        for _, person in expiring.head(10).iterrows():
                            days_left = int(person['days_to_expiry_num']) if pd.notna(person['days_to_expiry_num']) else 0
                            st.markdown(f"""
                            <div class="action-item-warning">
                                <strong>{person['rank']} {person['name']}</strong><br>
                                <small>{person['vehicle_type']} • Expires in {days_left} days</small>
                            </div>
                            """, unsafe_allow_html=True)
                        if len(expiring) > 10:
                            st.info(f"... and {len(expiring) - 10} more expiring")
                else:
                    st.success("✅ No immediate expirations")
            except:
                st.info("No expiration data available")
        
        st.markdown("---")
        
        # Platoon Status - Dropdown Expand Design
        st.markdown("### 🏢 Platoon Overview")
        
        # Group by platoon
        platoon_groups = df.groupby('platoon').agg({
            'currency_status': lambda x: (x.str.upper() == 'YES').sum(),
            'username': 'count'
        }).reset_index()
        platoon_groups.columns = ['Platoon', 'Current', 'Total']
        platoon_groups['Current_Rate'] = (platoon_groups['Current'] / platoon_groups['Total'] * 100).round(1)
        
        # Display each platoon as an expandable section
        for _, platoon in platoon_groups.iterrows():
            current_rate = platoon['Current_Rate']
            status_emoji = "✅" if current_rate >= 80 else ("⚠️" if current_rate >= 60 else "❌")
            status_text = "Excellent" if current_rate >= 80 else ("Good" if current_rate >= 60 else "Needs Attention")
            
            # Create expandable section for each platoon
            with st.expander(f"{status_emoji} **{platoon['Platoon']}** - {platoon['Current']}/{platoon['Total']} Current ({current_rate:.1f}%) - {status_text}", expanded=False):
                
                # Get personnel for this platoon
                platoon_personnel = df[df['platoon'] == platoon['Platoon']]
                
                # Quick stats row
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Total Personnel", len(platoon_personnel))
                with col2:
                    current_in_platoon = len(platoon_personnel[platoon_personnel['currency_status'].str.upper() == 'YES'])
                    st.metric("Current", current_in_platoon, delta=f"{current_rate:.1f}%")
                with col3:
                    not_current_in_platoon = len(platoon_personnel[platoon_personnel['currency_status'].str.upper() == 'NO'])
                    st.metric("Not Current", not_current_in_platoon)
                with col4:
                    avg_distance = platoon_personnel['distance_3_months'].mean()
                    st.metric("Avg Distance", f"{avg_distance:.1f} KM")
                
                # Critical personnel in this platoon
                platoon_not_current = platoon_personnel[platoon_personnel['currency_status'].str.upper() == 'NO']
                if len(platoon_not_current) > 0:
                    st.markdown("**🚨 Personnel Needing Immediate Drives:**")
                    for _, person in platoon_not_current.iterrows():
                        st.markdown(f"""
                        <div class="action-item-critical" style="margin: 5px 0;">
                            <strong>{person['rank']} {person['name']}</strong> ({person['vehicle_type']}) - {person['distance_3_months']:.1f} KM in last 3 months
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.success("🎉 All personnel in this platoon are current!")
                
                # Expiring personnel in this platoon
                try:
                    platoon_expiring = platoon_personnel[(platoon_personnel['currency_status'].str.upper() == 'YES') & (platoon_personnel['days_to_expiry_num'] <= 14)]
                    if len(platoon_expiring) > 0:
                        st.markdown("**⏰ Personnel Expiring Within 14 Days:**")
                        for _, person in platoon_expiring.iterrows():
                            days_left = int(person['days_to_expiry_num']) if pd.notna(person['days_to_expiry_num']) else 0
                            st.markdown(f"""
                            <div class="action-item-warning" style="margin: 5px 0;">
                                <strong>{person['rank']} {person['name']}</strong> ({person['vehicle_type']}) - Expires in {days_left} days
                            </div>
                            """, unsafe_allow_html=True)
                except:
                    pass
                
                # Full personnel table for this platoon
                st.markdown("**📋 Complete Platoon Roster:**")
                display_cols = ['rank', 'name', 'vehicle_type', 'currency_status', 'distance_3_months', 'days_to_expiry']
                display_df = platoon_personnel[display_cols].copy()
                display_df.columns = ['Rank', 'Name', 'Vehicle', 'Status', '3-Month KM', 'Days to Expiry']
                
                st.dataframe(display_df, use_container_width=True, height=200)
        
        # Quick Personnel Search & Filter
        st.markdown("---")
        st.markdown("### 🔍 Personnel Search")
        
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            search_term = st.text_input("Search by name or username:", placeholder="Type name to search...")
        with col2:
            status_filter = st.selectbox("Status:", ["All", "Current", "Not Current"])
        with col3:
            vehicle_filter = st.selectbox("Vehicle:", ["All", "Terrex", "Belrex"])
        
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
            
        if vehicle_filter != "All":
            filtered_df = filtered_df[filtered_df['vehicle_type'] == vehicle_filter]
        
        # Filtered results table
        if len(filtered_df) > 0:
            st.markdown(f"**{len(filtered_df)} personnel found**")
            
            display_cols = ['rank', 'name', 'platoon', 'vehicle_type', 'currency_status', 'distance_3_months', 'days_to_expiry']
            table_df = filtered_df[display_cols].copy()
            table_df.columns = ['Rank', 'Name', 'Platoon', 'Vehicle', 'Status', '3-Month KM', 'Days to Expiry']
            
            st.dataframe(table_df, use_container_width=True, height=400)
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
            st.error("❌ You are not qualified for any vehicle type.")
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
                
                # Clear caches to ensure dashboard updates immediately
                sheets_manager.clear_caches()
                
                st.success(f"✅ Mileage logged successfully!")
                st.info(f"**Date:** {operation_date.strftime('%Y-%m-%d')} | **Vehicle:** {vehicle_type} ({vehicle_no}) | **Distance:** {distance_driven:.1f} KM")
                
                # Force refresh the page to show updated data
                st.rerun()
                
            except Exception as e:
                st.error(f"Failed to log mileage: {str(e)}")

def currency_status_tab(sheets_manager):
    """Currency status tracking"""
    st.header("Currency Status")
    
    try:
        # Check user qualifications first
        qualifications = sheets_manager.check_user_qualifications(st.session_state.username)
        
        if not qualifications['terrex'] and not qualifications['belrex']:
            st.error("❌ You are not qualified for any vehicle type.")
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
    """Revamped account management for main admin"""
    try:
        # Load current credentials
        import json
        try:
            with open('credentials.json', 'r') as f:
                credentials = json.load(f)
        except FileNotFoundError:
            st.error("Credentials file not found.")
            return
        
        # Filter accounts (exclude main admin from list)
        manageable_accounts = {k: v for k, v in credentials.items() if k != 'admin'}
        
        if not manageable_accounts:
            st.info("No user accounts found.")
            return
        

        
        # Account Management Sections
        tab1, tab2 = st.tabs(["Account List", "Modify Account"])
        
        with tab1:
            st.markdown("### Account Directory")
            
            # Search and filter controls
            col1, col2 = st.columns([2, 1])
            with col1:
                search_term = st.text_input("Search accounts:", placeholder="Type name or username to search...", key="account_search")
            with col2:
                filter_type = st.selectbox("Filter by type:", ["All", "Commander", "Trooper"], key="account_filter")
            
            # Get all user names efficiently - use dedicated function for ALL names (not just qualified)
            # Use session state cache to avoid repeated API calls
            if 'name_lookup_cache' not in st.session_state or time.time() - st.session_state.get('name_lookup_timestamp', 0) > 7200:
                try:
                    name_lookup = sheets_manager.get_all_personnel_names()
                    st.session_state.name_lookup_cache = name_lookup
                    st.session_state.name_lookup_timestamp = time.time()
                except Exception as e:
                    st.error(f"Error loading names: {str(e)}")
                    name_lookup = {}
            else:
                name_lookup = st.session_state.name_lookup_cache
            
            # Enhanced account display with full names
            account_data = []
            for username, details in manageable_accounts.items():
                # Get display name from lookup or fallback
                display_name = name_lookup.get(username, 'Not in tracker sheets')
                
                # Handle different credential formats
                if isinstance(details, dict):
                    is_admin = details.get('is_admin', username in ['trooper1', 'trooper2', 'commander'])
                else:
                    is_admin = username in ['trooper1', 'trooper2', 'commander']
                
                account_data.append({
                    'Username': username,
                    'Full Name': display_name,
                    'Type': 'Commander' if is_admin else 'Trooper'
                })
            
            df = pd.DataFrame(account_data)
            
            # Apply search filter (search both username and full name)
            if search_term:
                mask = (df['Username'].str.contains(search_term, case=False, na=False) |
                       df['Full Name'].str.contains(search_term, case=False, na=False))
                df = df[mask]
            
            # Apply type filter
            if filter_type != "All":
                df = df[df['Type'] == filter_type]
            
            # Display results
            if len(df) > 0:
                st.dataframe(df, use_container_width=True, height=400)
            else:
                st.info("No accounts found matching the current filters.")
        
        with tab2:
            st.markdown("### Account Modification")
            
            # Search box for finding accounts quickly
            search_modify = st.text_input("Search for account to modify:", placeholder="Type name or username...", key="modify_search")
            
            # Create options with full names for easy identification
            account_options = ['']
            account_display = {'': ''}
            
            # Get name lookup for dropdown - use cached version
            if 'name_lookup_cache' not in st.session_state or time.time() - st.session_state.get('name_lookup_timestamp', 0) > 7200:
                try:
                    name_lookup = sheets_manager.get_all_personnel_names()
                    st.session_state.name_lookup_cache = name_lookup
                    st.session_state.name_lookup_timestamp = time.time()
                except:
                    name_lookup = {}
            else:
                name_lookup = st.session_state.name_lookup_cache
            
            for username in manageable_accounts.keys():
                full_name = name_lookup.get(username, 'Name not found')
                display_text = f"{username} - {full_name}"
                account_options.append(username)
                account_display[username] = display_text
            
            # Filter options based on search
            if search_modify:
                filtered_options = ['']
                for username in manageable_accounts.keys():
                    display_text = account_display[username]
                    if (search_modify.lower() in username.lower() or 
                        search_modify.lower() in display_text.lower()):
                        filtered_options.append(username)
                account_options = filtered_options
            
            col1, col2 = st.columns([1, 2])
            
            with col1:
                selected_user = st.selectbox(
                    "Select Account:",
                    options=account_options,
                    format_func=lambda x: account_display.get(x, x),
                    key="modify_user_select"
                )
            
            if selected_user:
                current_details = manageable_accounts[selected_user]
                if isinstance(current_details, dict):
                    current_is_admin = current_details.get('is_admin', selected_user in ['trooper1', 'trooper2', 'commander'])
                else:
                    current_is_admin = selected_user in ['trooper1', 'trooper2', 'commander']
                
                # Get user's full name from the lookup - use cached version
                try:
                    if 'name_lookup_cache' in st.session_state:
                        display_name = st.session_state.name_lookup_cache.get(selected_user, 'Not in tracker sheets')
                    else:
                        name_lookup = sheets_manager.get_all_personnel_names()
                        display_name = name_lookup.get(selected_user, 'Not in tracker sheets')
                except:
                    display_name = 'Error loading name'
                
                with col2:
                    status_color = "Commander" if current_is_admin else "Trooper"
                    st.markdown(f"**Editing:** {display_name}")
                    st.markdown(f"**Username:** {selected_user}")
                    st.markdown(f"**Type:** {status_color}")
                
                st.markdown("---")
                
                # Action Cards Layout
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.markdown("#### Privileges")
                    new_admin_status = st.checkbox(
                        "Grant Commander Rights", 
                        value=current_is_admin,
                        key="modify_admin_status"
                    )
                    
                    if st.button("Update Privileges", key="update_privileges", use_container_width=True):
                        # Update credentials logic
                        if isinstance(credentials[selected_user], dict):
                            credentials[selected_user]['is_admin'] = new_admin_status
                            credentials[selected_user]['modified_by'] = st.session_state.username
                            credentials[selected_user]['modified_date'] = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
                        else:
                            credentials[selected_user] = {
                                "password": credentials[selected_user],
                                "is_admin": new_admin_status,
                                "created_by": "Legacy",
                                "modified_by": st.session_state.username,
                                "modified_date": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
                            }
                        
                        with open('credentials.json', 'w') as f:
                            json.dump(credentials, f, indent=2)
                        
                        status_change = "granted" if new_admin_status else "revoked"
                        st.success(f"Commander privileges {status_change} for '{selected_user}'")
                        st.rerun()
                
                with col2:
                    st.markdown("#### Password Reset")
                    new_password = st.text_input("New Password:", type="password", key="new_pass_input")
                    
                    if st.button("Reset Password", key="reset_password", use_container_width=True):
                        if new_password:
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
                            
                            with open('credentials.json', 'w') as f:
                                json.dump(credentials, f, indent=2)
                            
                            st.success(f"Password reset for '{selected_user}'")
                            st.rerun()
                        else:
                            st.error("Please enter a new password")
                
                with col3:
                    st.markdown("#### Account Removal")
                    if selected_user in ['trooper1', 'trooper2', 'commander']:
                        st.info("Built-in commander accounts cannot be deleted")
                    else:
                        if st.button("Delete Account", key="delete_account", type="secondary", use_container_width=True):
                            if 'confirm_delete' not in st.session_state:
                                st.session_state.confirm_delete = True
                                st.rerun()
                        
                        if getattr(st.session_state, 'confirm_delete', False):
                            st.warning("Are you sure? This action cannot be undone.")
                            col_cancel, col_confirm = st.columns(2)
                            with col_cancel:
                                if st.button("Cancel", key="cancel_delete"):
                                    st.session_state.confirm_delete = False
                                    st.rerun()
                            with col_confirm:
                                if st.button("Confirm Delete", key="confirm_delete", type="secondary"):
                                    del credentials[selected_user]
                                    with open('credentials.json', 'w') as f:
                                        json.dump(credentials, f, indent=2)
                                    st.success(f"Account '{selected_user}' deleted")
                                    st.session_state.confirm_delete = False
                                    st.rerun()
            
    except Exception as e:
        st.error(f"Error in account management: {str(e)}")

def change_password_tab():
    """Password change interface"""
    st.header("🔐 Change Password")
    
    st.info("Update your account password for security.")
    
    with st.form("change_password_form"):
        st.subheader("Password Change")
        
        current_password = st.text_input("Current Password", type="password", key="current_pwd")
        new_password = st.text_input("New Password", type="password", key="new_pwd")
        confirm_password = st.text_input("Confirm New Password", type="password", key="confirm_pwd")
        
        submit_button = st.form_submit_button("Change Password")
        
        if submit_button:
            if not current_password or not new_password or not confirm_password:
                st.error("Please fill in all fields")
            elif new_password != confirm_password:
                st.error("New passwords do not match")
            elif len(new_password) < 6:
                st.error("New password must be at least 6 characters long")
            elif current_password == new_password:
                st.error("New password must be different from current password")
            else:
                success, message = change_password(st.session_state.username, current_password, new_password)
                if success:
                    st.success(message)
                    st.balloons()
                else:
                    st.error(message)
    
    # Password requirements
    st.subheader("Password Requirements")
    st.write("• Minimum 6 characters")
    st.write("• Must be different from current password")
    st.write("• Use a strong, unique password")

def main():
    """Main application entry point"""
    st.set_page_config(
        page_title="MSC DRIVr",
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
            padding: 20px;
            border-radius: 10px;
            border-left: 8px solid #28a745;
            margin: 15px 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .status-current h2 {
            margin: 0 0 10px 0;
            font-size: 1.5rem;
        }
        .status-expiring {
            background-color: #fff3cd;
            color: #856404;
            padding: 20px;
            border-radius: 10px;
            border-left: 8px solid #ffc107;
            margin: 15px 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .status-expiring h2 {
            margin: 0 0 10px 0;
            font-size: 1.5rem;
        }
        .status-expired {
            background-color: #f8d7da;
            color: #721c24;
            padding: 20px;
            border-radius: 10px;
            border-left: 8px solid #dc3545;
            margin: 15px 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .status-expired h2 {
            margin: 0 0 10px 0;
            font-size: 1.5rem;
        }
        
        /* Team Dashboard Cards */
        .metric-card-current {
            background: linear-gradient(135deg, #d4edda, #c3e6cb);
            color: #155724;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            margin: 10px 0;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            border-left: 5px solid #28a745;
        }
        .metric-card-expired {
            background: linear-gradient(135deg, #f8d7da, #f1b0b7);
            color: #721c24;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            margin: 10px 0;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            border-left: 5px solid #dc3545;
        }
        .metric-card-expiring {
            background: linear-gradient(135deg, #fff3cd, #ffeaa7);
            color: #856404;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            margin: 10px 0;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            border-left: 5px solid #ffc107;
        }
        .metric-card-vehicles {
            background: linear-gradient(135deg, #e2e3e5, #d1d3d4);
            color: #383d41;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            margin: 10px 0;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            border-left: 5px solid #6c757d;
        }
        
        /* Action Items */
        .action-item-critical {
            background-color: #f8d7da;
            color: #721c24;
            padding: 12px;
            border-radius: 8px;
            margin: 8px 0;
            border-left: 4px solid #dc3545;
        }
        .action-item-warning {
            background-color: #fff3cd;
            color: #856404;
            padding: 12px;
            border-radius: 8px;
            margin: 8px 0;
            border-left: 4px solid #ffc107;
        }
        
        /* Platoon Cards */
        .platoon-card-current {
            background: linear-gradient(135deg, #d4edda, #c3e6cb);
            color: #155724;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
            margin: 8px 0;
            border-left: 4px solid #28a745;
        }
        .platoon-card-expiring {
            background: linear-gradient(135deg, #fff3cd, #ffeaa7);
            color: #856404;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
            margin: 8px 0;
            border-left: 4px solid #ffc107;
        }
        .platoon-card-expired {
            background: linear-gradient(135deg, #f8d7da, #f1b0b7);
            color: #721c24;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
            margin: 8px 0;
            border-left: 4px solid #dc3545;
        }
        
        /* Clean up card headers */
        .metric-card-current h2, .metric-card-expired h2, .metric-card-expiring h2 {
            margin: 0 0 8px 0;
            font-size: 2rem;
            font-weight: bold;
        }
        .metric-card-current p, .metric-card-expired p, .metric-card-expiring p {
            margin: 0 0 5px 0;
            font-size: 1rem;
            font-weight: 600;
        }
        .metric-card-current small, .metric-card-expired small, .metric-card-expiring small {
            font-size: 0.8rem;
            opacity: 0.8;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Check for stored session on page load
    if not st.session_state.logged_in:
        # Try to restore session from browser storage
        session_check = st.components.v1.html("""
        <script>
        const logged_in = sessionStorage.getItem('msc_drivr_logged_in');
        const username = sessionStorage.getItem('msc_drivr_username');
        if (logged_in === 'true' && username) {
            window.parent.postMessage({
                type: 'restore_session',
                logged_in: true,
                username: username
            }, '*');
        }
        </script>
        """, height=0)
        
        # Check if we received session restoration message
        if 'restore_session' in st.session_state and st.session_state.restore_session:
            stored_username = st.session_state.get('stored_username', '')
            if stored_username and authenticate_user(stored_username, None, skip_password=True):
                st.session_state.logged_in = True
                st.session_state.username = stored_username
                st.session_state.restore_session = False
                st.rerun()
    
    if not st.session_state.logged_in:
        login_page()
    else:
        main_app()

if __name__ == "__main__":
    main()
