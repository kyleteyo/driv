import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import json
import time
from auth import authenticate_user, change_password, get_user_info
from sheets_manager import SheetsManager
from utils import calculate_currency_status, format_status_badge
from optimization import session_cache, clear_session_cache, lazy_load_data, optimize_dataframe

# Performance optimization - Streamlit configuration
if "app_configured" not in st.session_state:
    st.set_page_config(
        page_title="MSC DRIVr",
        page_icon="./msc_logo.png",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    # High-load performance configuration for 90+ concurrent users
    st._config.set_option('browser.gatherUsageStats', False)
    st._config.set_option('server.maxUploadSize', 5)  # 5MB limit
    st._config.set_option('server.maxMessageSize', 200)  # 200MB message limit
    st._config.set_option('server.enableCORS', True)
    st._config.set_option('server.enableXsrfProtection', True)
    
    # Session persistence settings
    st._config.set_option('server.sessionTimeout', 7200)  # 2 hours timeout
    st._config.set_option('server.enableStaticServing', True)
    
    st.session_state.app_configured = True

# High-load performance functions
def configure_high_load_performance():
    """Configure app for 90+ concurrent users"""
    from collections import defaultdict
    
    # Initialize rate limiting and monitoring
    if 'rate_limits' not in st.session_state:
        st.session_state.rate_limits = defaultdict(list)
    
    if 'load_monitor' not in st.session_state:
        st.session_state.load_monitor = {
            'request_times': [],
            'active_users': set(),
            'last_check': time.time(),
            'high_load_mode': False
        }
    
    # Check if we should enable high load mode
    check_and_enable_high_load_mode()
    
    # Aggressive memory cleanup
    cleanup_session_memory()

def check_and_enable_high_load_mode():
    """Automatically detect high load and enable protection"""
    import time
    current_time = time.time()
    
    # Track this user as active
    if 'username' in st.session_state:
        st.session_state.load_monitor['active_users'].add(st.session_state['username'])
    
    # Clean old active users (remove after 5 minutes of inactivity)
    if current_time - st.session_state.load_monitor['last_check'] > 30:  # Check every 30 seconds
        # Count recent requests across all users
        total_recent_requests = 0
        for user_requests in st.session_state.rate_limits.values():
            recent_requests = [req for req in user_requests if current_time - req < 300]  # Last 5 minutes
            total_recent_requests += len(recent_requests)
        
        # Count concurrent users (active in last 5 minutes)
        concurrent_users = len(st.session_state.load_monitor['active_users'])
        
        # Enable high load mode if:
        # - More than 50 concurrent users OR
        # - More than 200 requests in last 5 minutes OR
        # - Average response time getting slow
        should_enable = (
            concurrent_users > 50 or 
            total_recent_requests > 200
        )
        
        if should_enable and not st.session_state.load_monitor['high_load_mode']:
            st.session_state.load_monitor['high_load_mode'] = True
            st.session_state.high_load_mode = True
            st.warning("⚡ High load detected - Performance protection enabled")
        
        elif not should_enable and st.session_state.load_monitor['high_load_mode']:
            st.session_state.load_monitor['high_load_mode'] = False
            st.session_state.high_load_mode = False
            st.success("✅ Load normalized - Full performance restored")
        
        st.session_state.load_monitor['last_check'] = current_time

def check_rate_limit(user_id):
    """Prevent system overload with rate limiting"""
    import time
    current_time = time.time()
    
    if 'rate_limits' not in st.session_state:
        st.session_state.rate_limits = defaultdict(list)
    
    user_requests = st.session_state.rate_limits[user_id]
    
    # Remove old requests (1 minute window)
    user_requests[:] = [req_time for req_time in user_requests 
                       if current_time - req_time < 60]
    
    # Allow max 20 requests per minute per user (much more reasonable)
    if len(user_requests) >= 20:
        st.warning("⏳ Please wait a moment before making another request.")
        return False
    
    user_requests.append(current_time)
    return True

def cleanup_session_memory():
    """Aggressive memory cleanup for high-load scenarios"""
    import sys
    
    # Clean expired session cache
    if 'session_cache' in st.session_state:
        current_time = time.time()
        cache = st.session_state.session_cache
        
        expired_keys = [
            key for key, data in cache.items()
            if current_time - data.get('timestamp', 0) > 120  # 2 minutes
        ]
        
        for key in expired_keys:
            del cache[key]
    
    # Limit session state size to 512MB
    session_size = sys.getsizeof(st.session_state)
    if session_size > 512 * 1024 * 1024:
        # Remove large data structures
        keys_to_remove = []
        for key, value in st.session_state.items():
            if sys.getsizeof(value) > 100000:  # 100KB items
                keys_to_remove.append(key)
        
        for key in keys_to_remove[:5]:  # Remove up to 5 large items
            if key not in ['logged_in', 'username', 'current_page']:
                del st.session_state[key]

# Initialize high-load performance configuration
configure_high_load_performance()

# CRITICAL: Safely initialize missing users without overwriting existing passwords
def safe_user_initialization():
    """Ensure all users from Google Sheets exist without overwriting passwords"""
    try:
        from auth import safe_initialize_missing_users
        safe_initialize_missing_users()
    except Exception as e:
        print(f"User initialization error: {e}")

# Call safe initialization once per app startup
if 'users_initialized' not in st.session_state:
    safe_user_initialization()
    st.session_state.users_initialized = True



# Add custom CSS for permanent sidebar on laptops
st.markdown("""
<style>
    /* Force sidebar to stay open on laptops and desktops */
    @media (min-width: 768px) {
        /* Sidebar container */
        section[data-testid="stSidebar"] {
            width: 320px !important;
            min-width: 320px !important;
            transform: translateX(0px) !important;
            visibility: visible !important;
        }
        
        /* Sidebar content */
        .css-1d391kg, .css-6qob1r, .st-emotion-cache-6qob1r {
            width: 320px !important;
            min-width: 320px !important;
        }
        
        /* Main content area adjustment */
        .main .block-container, .css-1lcbmhc {
            margin-left: 340px !important;
            max-width: calc(100% - 360px) !important;
        }
        
        /* Hide collapse button */
        button[data-testid="collapsedControl"] {
            display: none !important;
        }
        
        /* Override any auto-hide behavior */
        .css-79elbk, .css-1kyxreq {
            display: none !important;
        }
    }
</style>
""", unsafe_allow_html=True)

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
    """Display login page with background logo"""
    
    # Use base64 encoded background image approach
    import base64
    
    try:
        with open("msc_logo.png", "rb") as img_file:
            img_data = base64.b64encode(img_file.read()).decode()
            logo_data_url = f"data:image/png;base64,{img_data}"
    except:
        logo_data_url = ""
    
    # Apply page-wide background with proper CSS
    st.markdown(f"""
    <style>
    /* Target the main container for background */
    div[data-testid="stAppViewContainer"] {{
        background-image: url('{logo_data_url}');
        background-repeat: no-repeat;
        background-position: center center;
        background-size: 400px;
        background-attachment: fixed;
    }}
    
    /* Make background semi-transparent */
    div[data-testid="stAppViewContainer"]::before {{
        content: '';
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-image: url('{logo_data_url}');
        background-repeat: no-repeat;
        background-position: center center;
        background-size: 400px;
        opacity: 0.1;
        z-index: -1;
        pointer-events: none;
    }}
    
    .login-title {{
        text-align: center;
        font-size: 3rem;
        font-weight: bold;
        color: #2C5530;
        margin-bottom: 30px;
        text-shadow: 2px 2px 4px rgba(255,255,255,0.9);
        margin-top: 0;
    }}
    
    /* Center the main content container consistently */
    .main .block-container {{
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        min-height: 95vh;
        padding: 2rem 1rem;
        max-width: 500px;
        margin: 0 auto;
    }}
    </style>
    
    <h1 class="login-title">MSC DRIVr</h1>
    """, unsafe_allow_html=True)
    
    # Simple login form without extra containers
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit_button = st.form_submit_button("Login")
        
        remember_me = st.checkbox("Keep me logged in", value=True)
        
        if submit_button:
            if authenticate_user(username, password):
                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.login_time = time.time()
                
                if remember_me:
                    # Create session token for persistence
                    session_token = generate_session_token(username)
                    # Store in browser localStorage for persistence across tabs/sessions
                    st.components.v1.html(f"""
                    <script>
                    localStorage.setItem('msc_drivr_logged_in', 'true');
                    localStorage.setItem('msc_drivr_username', '{username}');
                    localStorage.setItem('msc_drivr_session_token', '{session_token}');
                    localStorage.setItem('msc_drivr_login_time', '{int(time.time())}');
                    </script>
                    """, height=0)
                else:
                    # Use session storage (expires when tab closes)
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
    """Main application interface with sidebar navigation"""
    # Configure sidebar
    with st.sidebar:
        st.title("🪖 MSC DRIVr")
        
        # User welcome message
        sheets_manager = get_sheets_manager()
        if sheets_manager:
            user_qualifications = sheets_manager.check_user_qualifications(st.session_state.username)
            full_name = user_qualifications.get('full_name', st.session_state.username)
            rank = user_qualifications.get('rank', '')
            
            if full_name and rank:
                st.write(f"**{rank} {full_name}**")
            elif full_name:
                st.write(f"**{full_name}**")
            else:
                st.write(f"**{st.session_state.username}**")
        
        st.markdown("---")
        
        # Navigation menu
        if 'current_page' not in st.session_state:
            st.session_state.current_page = "Dashboard"
        
        # Navigation menu - plain text style
        st.write("**Navigation**")
        
        # Dashboard
        if st.session_state.current_page == "Dashboard":
            st.write("→ 🏠 Dashboard")
        else:
            if st.button("🏠 Dashboard", key="nav_dashboard"):
                st.session_state.current_page = "Dashboard"
                st.rerun()
        
        # My Mileage
        if st.session_state.current_page == "My Mileage":
            st.write("→ 📊 My Mileage")
        else:
            if st.button("📊 My Mileage", key="nav_mileage"):
                st.session_state.current_page = "My Mileage"
                st.rerun()
        
        # Safety Portal
        if st.session_state.current_page == "Safety Portal":
            st.write("→ 🛡️ Safety Portal")
        else:
            if st.button("🛡️ Safety Portal", key="nav_safety"):
                st.session_state.current_page = "Safety Portal"
                st.rerun()
        
        # Fitness Tracker
        if st.session_state.current_page == "Fitness Tracker":
            st.write("→ 💪 Fitness Tracker")
        else:
            if st.button("💪 Fitness Tracker", key="nav_fitness"):
                st.session_state.current_page = "Fitness Tracker"
                st.rerun()
        
        # Admin features (if applicable)
        if sheets_manager and sheets_manager.is_admin_user(st.session_state.username):
            st.markdown("---")
            st.write("**Admin Features**")
            
            # Team Overview
            if st.session_state.current_page == "Team Overview":
                st.write("→ 👥 Team Overview")
            else:
                if st.button("👥 Team Overview", key="nav_team"):
                    st.session_state.current_page = "Team Overview"
                    st.rerun()
            
            # Account Management
            if st.session_state.current_page == "Account Management":
                st.write("→ 👤 Account Management")
            else:
                if st.button("👤 Account Management", key="nav_accounts"):
                    st.session_state.current_page = "Account Management"
                    st.rerun()
        
        # Commander features (if applicable)
        elif sheets_manager and sheets_manager.is_commander_user(st.session_state.username):
            st.markdown("---")
            st.write("**Commander Features**")
            
            # Team Overview for commanders
            if st.session_state.current_page == "Team Overview":
                st.write("→ 👥 Team Overview")
            else:
                if st.button("👥 Team Overview", key="nav_team_cmd"):
                    st.session_state.current_page = "Team Overview"
                    st.rerun()
            

        
        st.markdown("---")
        
        # Change Password
        if st.session_state.current_page == "Change Password":
            st.write("→ 🔐 Change Password")
        else:
            if st.button("🔐 Change Password", key="nav_password"):
                st.session_state.current_page = "Change Password"
                st.rerun()
        
        # Logout button at bottom
        if st.button("🚪 Logout", key="logout_btn"):
            # Clear browser storage on logout
            st.components.v1.html("""
            <script>
            localStorage.removeItem('msc_drivr_logged_in');
            localStorage.removeItem('msc_drivr_username');
            localStorage.removeItem('msc_drivr_session_token');
            localStorage.removeItem('msc_drivr_login_time');
            sessionStorage.clear();
            </script>
            """, height=0)
            
            # Clear session state
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
    
    # Initialize sheets manager with caching
    sheets_manager = get_sheets_manager()
    if sheets_manager is None:
        st.error("Please ensure Google Sheets API credentials are properly configured.")
        return
    
    # Main content area - display content based on current page
    if st.session_state.current_page == "Dashboard":
        dashboard_landing_page(sheets_manager)
    elif st.session_state.current_page == "My Mileage":
        my_mileage_page(sheets_manager)
    elif st.session_state.current_page == "Safety Portal":
        safety_portal_page(sheets_manager)
    elif st.session_state.current_page == "Fitness Tracker":
        fitness_tracker_page(sheets_manager)
    elif st.session_state.current_page == "Team Overview":
        admin_team_dashboard(sheets_manager)
    elif st.session_state.current_page == "Account Management":
        account_management_tab(sheets_manager)

    elif st.session_state.current_page == "Change Password":
        change_password_tab()
    else:
        # Default to My Mileage if no valid page selected
        my_mileage_page(sheets_manager)

def dashboard_landing_page(sheets_manager):
    """Simple horizontal navigation bar for main modules"""
    st.title("🏠 MSC DRIVr")
    
    # Create horizontal navigation bar
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🚗 My Mileage", key="goto_mileage", use_container_width=True):
            st.session_state.current_page = "My Mileage"
            st.rerun()
    
    with col2:
        if st.button("🛡️ Safety Portal", key="goto_safety", use_container_width=True):
            st.session_state.current_page = "Safety Portal"
            st.rerun()
    
    with col3:
        if st.button("💪 Fitness Tracker", key="goto_fitness", use_container_width=True):
            st.session_state.current_page = "Fitness Tracker"
            st.rerun()

def fitness_tracker_page(sheets_manager):
    """Strength & Power fitness tracking system"""
    st.title("💪 Fitness Tracker")
    st.markdown("### Strength & Power Training")
    
    # Create horizontal tabs for fitness features
    tab1, tab2, tab3 = st.tabs(["📊 Log Workout", "📈 My Progress", "📋 Training Plans"])
    
    with tab1:
        log_strength_workout(sheets_manager)
    
    with tab2:
        view_fitness_progress(sheets_manager)
    
    with tab3:
        view_training_plans(sheets_manager)

def log_strength_workout(sheets_manager):
    """Log Strength & Power workout session"""
    st.markdown("#### Log Your Strength & Power Session")
    
    # Session selection
    session_number = st.selectbox(
        "Select Session Number",
        options=list(range(1, 17)),
        help="Choose your S&P session number (1-16)"
    )
    
    if st.button("Load Session Exercises"):
        try:
            # Get exercises for selected session
            exercises = get_session_exercises(sheets_manager, session_number)
            
            if exercises:
                st.session_state.current_exercises = exercises
                st.session_state.session_number = session_number
                st.success(f"Loaded {len(exercises)} exercises for Session {session_number}")
            else:
                st.warning(f"No exercises found for Session {session_number}")
                
        except Exception as e:
            st.error(f"Error loading exercises: {str(e)}")
    
    # Display exercise logging form if exercises are loaded
    if 'current_exercises' in st.session_state and st.session_state.current_exercises:
        st.markdown("---")
        st.markdown(f"#### Session {st.session_state.session_number} Exercises")
        
        with st.form("workout_log_form"):
            exercise_data = []
            
            for i, exercise in enumerate(st.session_state.current_exercises):
                st.markdown(f"**{exercise['Exercise']}**")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.text(f"Sets: {exercise.get('Sets', 'N/A')}")
                with col2:
                    st.text(f"Reps: {exercise.get('Reps', 'N/A')}")
                with col3:
                    if exercise.get('Notes'):
                        st.text(f"Notes: {exercise['Notes']}")
                    else:
                        st.text("")
                
                # Get last logged data for this exercise
                last_weight, last_reps = get_last_exercise_data(sheets_manager, exercise['Exercise'])
                
                # Check if this is a bodyweight exercise
                exercise_name = exercise['Exercise'].lower()
                is_bodyweight = any(keyword in exercise_name for keyword in ['pull up', 'pull-up', 'pullup', 'push up', 'push-up', 'pushup', 'sit up', 'sit-up', 'situp'])
                
                if is_bodyweight:
                    # Bodyweight exercises - only track reps
                    actual_reps = st.text_input(
                        f"Reps Completed",
                        value=last_reps,
                        key=f"reps_{i}",
                        help="Reps completed (auto-filled from last session)"
                    )
                    weight = 0  # No weight for bodyweight exercises
                    
                else:
                    # Weighted exercises - track both weight and reps
                    col1, col2 = st.columns(2)
                    with col1:
                        weight = st.number_input(
                            f"Weight (kg)",
                            min_value=0.0,
                            step=0.5,
                            value=last_weight,
                            key=f"weight_{i}",
                            help="Weight lifted for this exercise (auto-filled from last session)"
                        )
                    with col2:
                        actual_reps = st.text_input(
                            f"Actual Reps",
                            value=last_reps,
                            key=f"reps_{i}",
                            help="Reps completed (auto-filled from last session)"
                        )
                
                exercise_data.append({
                    'exercise': exercise,
                    'weight': weight,
                    'actual_reps': actual_reps
                })
                
                st.markdown("---")
            
            # Submit button
            if st.form_submit_button("Log Workout", use_container_width=True):

                
                try:
                    log_fitness_data(sheets_manager, st.session_state.session_number, exercise_data)
                    st.success("Workout logged successfully!")
                    # Don't clear session state or rerun immediately to see debug output
                    pass
                except Exception as e:
                    st.error(f"Error logging workout: {str(e)}")

def get_session_exercises(sheets_manager, session_number):
    """Get exercises for a specific session from Strength & Power sheet"""
    try:
        # Get the reference sheet using the correct method
        if not hasattr(sheets_manager, 'spreadsheet'):
            sheets_manager.connect()
        
        try:
            sp_sheet = sheets_manager.spreadsheet.worksheet("Strength & Power")
        except:
            # Create sheet if it doesn't exist
            sp_sheet = sheets_manager.spreadsheet.add_worksheet(title="Strength & Power", rows=1000, cols=10)
            # Add sample headers
            headers = ["Session", "Exercise", "Sets", "Reps", "Notes"]
            sp_sheet.append_row(headers)
            st.warning("Created new 'Strength & Power' sheet. Please add your exercise data.")
            return []
            
        records = sp_sheet.get_all_records()
        
        # Filter exercises for the selected session
        session_exercises = [
            record for record in records 
            if record.get('Session') == session_number
        ]
        
        return session_exercises
        
    except Exception as e:
        st.error(f"Error accessing Strength & Power sheet: {str(e)}")
        return []

def log_fitness_data(sheets_manager, session_number, exercise_data):
    """Log workout data to Strength & Power Tracking sheet"""
    try:
        # Get or create tracking sheet
        if not hasattr(sheets_manager, 'spreadsheet'):
            sheets_manager.connect()
            
        try:
            tracking_sheet = sheets_manager.spreadsheet.worksheet("Strength & Power Tracking")
            # Delete existing sheet to recreate with new format
            sheets_manager.spreadsheet.del_worksheet(tracking_sheet)
            st.info("Deleted old tracking sheet to create new horizontal format")
        except:
            pass  # Sheet doesn't exist, that's fine
            
        # Create new sheet with exercise-based columns
        tracking_sheet = sheets_manager.spreadsheet.add_worksheet(title="Strength & Power Tracking", rows=1000, cols=50)
        
        # Create headers with exercises as columns
        base_headers = ["Date", "Soldier Name / ID", "Session Number"]
        
        # Get all unique exercises from the reference sheet to create comprehensive headers
        try:
            sp_sheet = sheets_manager.spreadsheet.worksheet("Strength & Power")
            all_records = sp_sheet.get_all_records()
            unique_exercises = list(set([record.get('Exercise', '') for record in all_records if record.get('Exercise')]))
            unique_exercises.sort()  # Sort alphabetically
        except:
            # Fallback to common exercises if reference sheet not available
            unique_exercises = [
                "Back Squat", "Bench Press", "Bent Over Row", "Bicep Curl", "Bulgarian Split Squat",
                "Burpees", "Chin-ups", "Dips", "Goblet Squat", "Incline Dumbbell Press",
                "Jump Squats", "Lat Pulldown", "Lateral Raise", "Lunges", "Mountain Climbers",
                "Overhead Press", "Plank", "Pull Up", "Push-ups", "Romanian Deadlift",
                "Step Up (optional)", "Sumo Deadlift", "Tricep Extension"
            ]
        
        # Create weight and reps columns for each exercise (skip weight for bodyweight exercises)
        exercise_headers = []
        for exercise in unique_exercises:
            # Check if this is a bodyweight exercise
            exercise_name_lower = exercise.lower()
            is_bodyweight = any(keyword in exercise_name_lower for keyword in ['pull up', 'pull-up', 'pullup', 'push up', 'push-up', 'pushup', 'sit up', 'sit-up', 'situp'])
            
            if is_bodyweight:
                # Only add reps column for bodyweight exercises
                exercise_headers.append(f"{exercise} (reps)")
            else:
                # Add both weight and reps columns for weighted exercises
                exercise_headers.extend([f"{exercise} (kg)", f"{exercise} (reps)"])
        
        headers = base_headers + exercise_headers
        tracking_sheet.append_row(headers)
        st.success(f"Created new tracking sheet with {len(unique_exercises)} exercise columns")
        
        # Get user info
        user_qualifications = sheets_manager.check_user_qualifications(st.session_state.username)
        full_name = user_qualifications.get('full_name', st.session_state.username)
        
        # Prepare single row with all exercises as columns
        from datetime import datetime
        current_date = datetime.now().strftime("%Y-%m-%d")
        
        # Get header row and log in single row format
        headers = tracking_sheet.row_values(1)
        # Create single row with all exercises as columns
        row_data = [""] * len(headers)
        row_data[0] = current_date      # Date
        row_data[1] = full_name         # Soldier Name / ID  
        row_data[2] = session_number    # Session Number
        
        # Fill in exercise data using exercise-specific weight and reps columns
        exercises_logged = 0
        for data in exercise_data:
            if data['weight'] > 0 or data['actual_reps']:  # Log if either weight or reps entered
                exercise_name = data['exercise'].get('Exercise', '')
                weight_col = f"{exercise_name} (kg)"
                reps_col = f"{exercise_name} (reps)"
                
                try:
                    # Check if this is a bodyweight exercise
                    exercise_name_lower = exercise_name.lower()
                    is_bodyweight = any(keyword in exercise_name_lower for keyword in ['pull up', 'pull-up', 'pullup', 'push up', 'push-up', 'pushup', 'sit up', 'sit-up', 'situp'])
                    
                    # Set weight if entered (skip for bodyweight exercises)
                    if not is_bodyweight and data['weight'] > 0 and weight_col in headers:
                        weight_idx = headers.index(weight_col)
                        row_data[weight_idx] = data['weight']
                    
                    # Set reps if entered
                    if data['actual_reps'] and reps_col in headers:
                        reps_idx = headers.index(reps_col)
                        row_data[reps_idx] = data['actual_reps']
                        exercises_logged += 1  # Count exercise as logged if reps are entered
                    elif not is_bodyweight and data['weight'] > 0:
                        exercises_logged += 1  # Count weighted exercise if weight is entered
                        
                except ValueError:
                    continue
        
        if exercises_logged > 0:
            tracking_sheet.append_row(row_data)
            st.success(f"Logged session {session_number} with {exercises_logged} exercises!")
            # Clear session state and refresh to show updated data
            if 'current_exercises' in st.session_state:
                del st.session_state.current_exercises
            if 'session_number' in st.session_state:
                del st.session_state.session_number
            st.rerun()
        else:
            st.warning("No exercise data entered to log")
            
    except Exception as e:
        raise Exception(f"Failed to log workout data: {str(e)}")

def view_fitness_progress(sheets_manager):
    """View personal fitness progress and history"""
    st.markdown("#### Your Progress")
    
    try:
        # Get tracking data
        if not hasattr(sheets_manager, 'spreadsheet'):
            sheets_manager.connect()
            
        try:
            tracking_sheet = sheets_manager.spreadsheet.worksheet("Strength & Power Tracking")
            records = tracking_sheet.get_all_records()
        except:
            st.info("No workout tracking data found. Start logging workouts to see progress!")
            return
        
        # Get user info for filtering
        user_qualifications = sheets_manager.check_user_qualifications(st.session_state.username)
        full_name = user_qualifications.get('full_name', st.session_state.username)
        
        # Filter user's records
        user_records = [
            record for record in records 
            if record.get('Soldier Name / ID') == full_name
        ]
        
        if user_records:
            # Display recent workouts
            st.markdown("##### Recent Workouts")
            
            # Sort records by date to get most recent first
            user_records_sorted = sorted(user_records, key=lambda x: x.get('Date', ''), reverse=True)
            recent_sessions = user_records_sorted[:5]  # Show last 5 sessions
            
            for record in recent_sessions:
                session_num = record.get('Session Number', 'Unknown')
                date = record.get('Date', 'Unknown Date')
                
                with st.expander(f"Session {session_num} - {date}"):
                    # Get all exercise columns and display their values
                    exercise_count = 0
                    displayed_exercises = set()  # Track which exercises we've already displayed
                    
                    for key, value in record.items():
                        if '(kg)' in key or '(reps)' in key:
                            if value and str(value).strip():  # Only show exercises with data
                                exercise_name = key.replace(' (kg)', '').replace(' (reps)', '')
                                
                                if exercise_name in displayed_exercises:
                                    continue  # Skip if already displayed
                                    
                                if '(kg)' in key:
                                    # Weighted exercise - check for both weight and reps
                                    reps_key = f"{exercise_name} (reps)"
                                    reps_value = record.get(reps_key, '')
                                    if reps_value:
                                        st.write(f"**{exercise_name}**: {value}kg x {reps_value} reps")
                                    else:
                                        st.write(f"**{exercise_name}**: {value}kg")
                                    exercise_count += 1
                                    displayed_exercises.add(exercise_name)
                                    
                                elif '(reps)' in key:
                                    # Check if this is a bodyweight exercise (no corresponding kg column)
                                    weight_key = f"{exercise_name} (kg)"
                                    if weight_key not in record:
                                        # This is a bodyweight exercise
                                        st.write(f"**{exercise_name}**: {value} reps")
                                        exercise_count += 1
                                        displayed_exercises.add(exercise_name)
                    
                    if exercise_count == 0:
                        st.info("No exercise data recorded for this session")
            
            # Exercise progress
            st.markdown("##### Exercise Progress")
            
            # Get all unique exercises from column headers (both weighted and bodyweight)
            if user_records:
                sample_record = user_records[0]
                exercise_names = []
                for key in sample_record.keys():
                    if '(kg)' in key:
                        exercise_name = key.replace(' (kg)', '')
                        exercise_names.append(exercise_name)
                    elif '(reps)' in key:
                        exercise_name = key.replace(' (reps)', '')
                        weight_key = f"{exercise_name} (kg)"
                        if weight_key not in sample_record.keys():
                            # This is a bodyweight exercise (reps column without corresponding kg column)
                            exercise_names.append(exercise_name)
                
                # Remove duplicates and sort
                exercise_names = sorted(list(set(exercise_names)))
                
                if exercise_names:
                    selected_exercise = st.selectbox("Select Exercise", exercise_names)
                    
                    if selected_exercise:
                        # Check if this is a bodyweight exercise
                        exercise_name_lower = selected_exercise.lower()
                        is_bodyweight = any(keyword in exercise_name_lower for keyword in ['pull up', 'pull-up', 'pullup', 'push up', 'push-up', 'pushup', 'sit up', 'sit-up', 'situp'])
                        
                        weight_col = f"{selected_exercise} (kg)"
                        reps_col = f"{selected_exercise} (reps)"
                        
                        # Prepare chart data for weight progression
                        chart_data = []
                        for record in user_records_sorted:
                            date = record.get('Date', '')
                            weight = record.get(weight_col, '') if not is_bodyweight else ''
                            reps = record.get(reps_col, '')
                            
                            if date and (weight or reps):
                                try:
                                    weight_val = float(weight) if weight and not is_bodyweight else 0
                                    chart_data.append({
                                        'Date': date,
                                        'Weight (kg)': weight_val,
                                        'Reps': reps if reps else 0
                                    })
                                except (ValueError, TypeError):
                                    continue
                        
                        if chart_data:
                            # Display weight progression chart (only for weighted exercises)
                            if not is_bodyweight and any(item['Weight (kg)'] > 0 for item in chart_data):
                                st.markdown(f"**Weight Progression for {selected_exercise}**")
                                import pandas as pd
                                df = pd.DataFrame(chart_data)
                                df = df[df['Weight (kg)'] > 0]  # Only show entries with weight data
                                if not df.empty:
                                    st.line_chart(df.set_index('Date')[['Weight (kg)']])
                            
                            # Display recent performance table
                            st.markdown(f"**Recent Performance for {selected_exercise}**")
                            performance_data = []
                            for item in chart_data[:10]:  # Show last 10 sessions
                                if item['Weight (kg)'] > 0 or item['Reps']:
                                    if is_bodyweight:
                                        # Only show reps for bodyweight exercises
                                        performance_data.append({
                                            'Date': item['Date'],
                                            'Reps': item['Reps'] if item['Reps'] else '-'
                                        })
                                    else:
                                        # Show both weight and reps for weighted exercises
                                        performance_data.append({
                                            'Date': item['Date'],
                                            'Weight (kg)': f"{item['Weight (kg)']}kg" if item['Weight (kg)'] > 0 else '-',
                                            'Reps': item['Reps'] if item['Reps'] else '-'
                                        })
                            
                            if performance_data:
                                import pandas as pd
                                df_performance = pd.DataFrame(performance_data)
                                st.dataframe(df_performance, hide_index=True)
                            else:
                                st.info("No performance data recorded for this exercise yet.")
                        else:
                            st.info("No data recorded for this exercise yet.")
                else:
                    st.info("No exercises found in your workout history.")
        else:
            st.info("No workout data found. Start logging your workouts to see progress!")
            
    except Exception as e:
        st.error(f"Error loading progress data: {str(e)}")

def view_training_plans(sheets_manager):
    """View available training plans and session details with latest workout data"""
    st.markdown("#### Training Plans & Session Reference")
    
    try:
        # Get reference data
        if not hasattr(sheets_manager, 'spreadsheet'):
            sheets_manager.connect()
            
        try:
            sp_sheet = sheets_manager.spreadsheet.worksheet("Strength & Power")
            records = sp_sheet.get_all_records()
        except:
            st.info("No 'Strength & Power' sheet found. Please create this sheet with your exercise data.")
            return
        
        # Get user's tracking data
        user_qualifications = sheets_manager.check_user_qualifications(st.session_state.username)
        full_name = user_qualifications.get('full_name', st.session_state.username)
        
        try:
            tracking_sheet = sheets_manager.spreadsheet.worksheet("Strength & Power Tracking")
            tracking_records = tracking_sheet.get_all_records()
            user_tracking = [r for r in tracking_records if r.get('Soldier Name / ID') == full_name]
        except:
            user_tracking = []
        
        # Group records by session
        sessions = {}
        for record in records:
            session_num = record.get('Session')
            if session_num:
                if session_num not in sessions:
                    sessions[session_num] = []
                sessions[session_num].append(record)
        
        st.markdown("##### Session Overview")
        for session_num in sorted(sessions.keys()):
            session_exercises = sessions[session_num]
            
            # Find the latest workout for this session
            session_workouts = [r for r in user_tracking if r.get('Session Number') == session_num]
            latest_workout = session_workouts[-1] if session_workouts else None
            
            # Create expander title with workout status
            if latest_workout:
                workout_date = latest_workout.get('Date', 'Unknown Date')
                expander_title = f"Session {session_num} ({len(session_exercises)} exercises) - Last completed: {workout_date}"
            else:
                expander_title = f"Session {session_num} ({len(session_exercises)} exercises) - Not completed yet"
            
            with st.expander(expander_title):
                for exercise in session_exercises:
                    exercise_name = exercise.get('Exercise', 'Unknown')
                    
                    # Create columns for layout
                    col1, col2, col3, col4 = st.columns([3, 1, 1, 2])
                    
                    with col1:
                        st.write(f"**{exercise_name}**")
                    with col2:
                        st.write(f"Sets: {exercise.get('Sets', 'N/A')}")
                    with col3:
                        st.write(f"Reps: {exercise.get('Reps', 'N/A')}")
                    with col4:
                        # Show latest performance for this exercise
                        if latest_workout:
                            weight_col = f"{exercise_name} (kg)"
                            reps_col = f"{exercise_name} (reps)"
                            
                            last_weight = latest_workout.get(weight_col, '')
                            last_reps = latest_workout.get(reps_col, '')
                            
                            # Check if this is a bodyweight exercise
                            exercise_name_lower = exercise_name.lower()
                            is_bodyweight = any(keyword in exercise_name_lower for keyword in ['pull up', 'pull-up', 'pullup', 'push up', 'push-up', 'pushup', 'sit up', 'sit-up', 'situp'])
                            
                            if last_weight or last_reps:
                                performance_text = ""
                                if not is_bodyweight and last_weight:
                                    performance_text += f"{last_weight}kg"
                                if last_reps:
                                    if performance_text:
                                        performance_text += f" x {last_reps}"
                                    else:
                                        performance_text = f"{last_reps} reps"
                                st.write(f"Last: {performance_text}")
                            else:
                                st.write("Last: Not logged")
                        else:
                            st.write("Last: No data")
                    
                    if exercise.get('Notes'):
                        st.caption(f"Notes: {exercise['Notes']}")
                    st.markdown("---")
        
    except Exception as e:
        st.error(f"Error loading training plans: {str(e)}")
        st.info("Make sure the 'Strength & Power' sheet exists with session data.")

def get_last_exercise_data(sheets_manager, exercise_name):
    """Get the last logged weight and reps for a specific exercise"""
    try:
        # Get user info for filtering
        user_qualifications = sheets_manager.check_user_qualifications(st.session_state.username)
        full_name = user_qualifications.get('full_name', st.session_state.username)
        
        # Get tracking data
        if not hasattr(sheets_manager, 'spreadsheet'):
            sheets_manager.connect()
            
        try:
            tracking_sheet = sheets_manager.spreadsheet.worksheet("Strength & Power Tracking")
            records = tracking_sheet.get_all_records()
            
        except:
            return 0.0, ""  # No tracking data available
        
        # Filter user's records using new column format
        user_records = [
            record for record in records 
            if record.get('Soldier Name / ID') == full_name
        ]
        
        if user_records:
            # Get the most recent record (last in the list)
            last_record = user_records[-1]
            
            # Check if this is a bodyweight exercise
            exercise_name_lower = exercise_name.lower()
            is_bodyweight = any(keyword in exercise_name_lower for keyword in ['pull up', 'pull-up', 'pullup', 'push up', 'push-up', 'pushup', 'sit up', 'sit-up', 'situp'])
            
            # Look for exercise-specific weight and reps columns
            weight_col = f"{exercise_name} (kg)"
            reps_col = f"{exercise_name} (reps)"
            
            try:
                # For bodyweight exercises, don't look for weight
                if is_bodyweight:
                    last_weight = 0.0
                else:
                    last_weight = float(last_record.get(weight_col, 0)) if last_record.get(weight_col) else 0.0
                
                last_reps = str(last_record.get(reps_col, '')) if last_record.get(reps_col) else ""
                return last_weight, last_reps
            except (ValueError, TypeError):
                return 0.0, ""
        else:
            return 0.0, ""  # No previous data for this exercise
            
    except Exception as e:
        # Debug: Show error details
        st.error(f"Debug error in get_last_exercise_data: {str(e)}")
        return 0.0, ""

def my_mileage_page(sheets_manager):
    """Mileage tracking page with horizontal sub-menu tabs"""
    st.title("📊 My Mileage")
    
    # Create horizontal tabs for Dashboard and Log Mileage
    tab1, tab2 = st.tabs(["📊 Dashboard", "📝 Log Mileage"])
    
    with tab1:
        dashboard_tab(sheets_manager)
    
    with tab2:
        log_mileage_tab(sheets_manager)

def safety_portal_page(sheets_manager):
    """Safety Portal page with horizontal tabs"""
    st.title("🛡️ Safety Portal")
    
    # Create horizontal tabs for the three safety sections
    tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "📸 Submit Infographic", "📝 Submit Safety Pointer"])
    
    with tab1:
        safety_dashboard_tab(sheets_manager)
    
    with tab2:
        safety_infographic_tab(sheets_manager)
    
    with tab3:
        safety_pointer_tab(sheets_manager)

def safety_dashboard_tab(sheets_manager):
    """Safety Portal Dashboard - displays submitted content"""
    
    # Create selectbox for view selection
    view_option = st.selectbox(
        "Select View:",
        ["📸 Infographics", "📝 Safety Pointers"],
        index=0,
        label_visibility="collapsed"
    )
    
    st.markdown("---")
    
    # Display content based on selection
    if view_option == "📸 Infographics":
        display_safety_infographics(sheets_manager)
    elif view_option == "📝 Safety Pointers":
        display_safety_pointers(sheets_manager)

def display_safety_infographics(sheets_manager):
    """Display safety infographics from Google Sheets"""
    try:
        # Try to get infographics data from Google Sheets
        infographics_data = sheets_manager.get_safety_infographics() if hasattr(sheets_manager, 'get_safety_infographics') else []
        
        if infographics_data and len(infographics_data) > 0:
            st.markdown("#### 📸 Safety Infographics")
            
            # Display infographics in card format
            for i, infographic in enumerate(infographics_data[:6]):  # Show latest 6
                with st.container():
                    # Get the correct fields based on actual data structure
                    title = infographic.get('Title', 'Safety Infographic')
                    image_url = infographic.get('File_Type', '')  # Actual image URL is in File_Type
                    submitter_username = infographic.get('Submitter', 'Unknown')  # This appears to be a timestamp
                    original_filename = infographic.get('Date', 'N/A')  # Original filename is in Date field
                    
                    # Extract username from title and get full name/rank
                    username = title  # Title contains the username
                    try:
                        # Get full name and rank from sheets manager
                        user_info = sheets_manager.check_user_qualifications(username)
                        if user_info:
                            # Build display name with available information
                            rank = user_info.get('rank', '')
                            full_name = user_info.get('full_name', '')
                            
                            if rank and full_name:
                                submitter_display = f"{rank} {full_name}"
                            elif full_name:
                                submitter_display = full_name
                            elif rank:
                                submitter_display = f"{rank} {username}"
                            else:
                                submitter_display = username
                        else:
                            submitter_display = username
                    except Exception:
                        submitter_display = username
                    
                    # Use timestamp as date
                    date_display = submitter_username
                    
                    # Format timestamp for display
                    try:
                        if len(date_display.split()) > 1:
                            date_only = date_display.split()[0]  # Get just the date part
                        else:
                            date_only = date_display
                    except:
                        date_only = date_display
                    
                    # Show image with title and submitter info
                    if image_url and image_url not in ['METADATA_ONLY', 'UPLOAD_FAILED', 'R2_NOT_CONFIGURED', '']:
                        # Validate URL format
                        if image_url.startswith(('http://', 'https://')):
                            try:
                                # Don't display title separately since it's just the username
                                st.image(image_url, use_container_width=True, caption=None)
                                st.markdown(f"""
                                <div style="text-align: center; margin-top: 10px;">
                                    <p style="margin: 2px 0; color: #666; font-size: 0.9em;"><strong>Uploaded by:</strong> {submitter_display}</p>
                                    <p style="margin: 2px 0; color: #666; font-size: 0.9em;">{date_only}</p>
                                </div>
                                """, unsafe_allow_html=True)
                            except Exception as img_error:
                                st.error(f"📷 Image could not load: {str(img_error)}")
                                st.caption(f"URL: {image_url}")
                        else:
                            # Invalid URL format - show metadata only
                            st.markdown(f"**{title if title != 'Safety Infographic' else 'Safety Submission'}**")
                            st.info(f"📷 Image file: {original_filename}")
                            st.markdown(f"""
                            <div style="text-align: center; margin-top: 10px;">
                                <p style="margin: 2px 0; color: #666; font-size: 0.9em;"><strong>Uploaded by:</strong> {submitter_display}</p>
                                <p style="margin: 2px 0; color: #666; font-size: 0.9em;">{date_only}</p>
                            </div>
                            """, unsafe_allow_html=True)
                    else:
                        st.markdown("📷 *Metadata only - no image available*")
                        if image_url:
                            st.caption(f"Status: {image_url}")
                        st.markdown(f"**Submitted by:** {submitter_display} | **Date:** {date_only}")
                    
                    st.markdown("---")
        else:
            st.info("📸 No safety infographics submitted yet. Be the first to share!")
            st.markdown("*Use the 'Submit Infographic' tab to upload safety-related images.*")
            
    except Exception as e:
        st.warning(f"⚠️ Unable to load infographics data: {str(e)}")
        st.markdown("**Debug info:** Check if Safety_Infographics worksheet exists in Google Sheets")
        
        # Debug: Show what data we have
        try:
            debug_data = sheets_manager.get_safety_infographics()
            if debug_data:
                st.write("**Debug - Found data:**")
                for item in debug_data[:2]:  # Show first 2 items
                    st.json(item)
        except:
            st.write("**Debug:** Could not retrieve any data")

def display_safety_pointers(sheets_manager):
    """Display safety pointers from Google Sheets"""
    try:
        # Try to get safety pointers data from Google Sheets (clear any cache)
        safety_pointers_data = sheets_manager.get_safety_pointers()
        
        if safety_pointers_data and len(safety_pointers_data) > 0:
            st.markdown("#### 📝 Safety Observations & Recommendations")
            
            # Debug first to understand the actual data structure (remove after fixing)
            # with st.expander("🔧 Debug Data Structure", expanded=False):
            #     st.write("**First record structure:**")
            #     if safety_pointers_data:
            #         st.json(safety_pointers_data[0])
            
            # Display safety pointers in card format
            for i, pointer in enumerate(safety_pointers_data[:8]):  # Show latest 8
                with st.container():
                    # Based on your feedback, the actual data seems to be:
                    # - Observation field contains: "2025-08-11" (should be observation_date)
                    # - Reflection field contains: "test1" (should be observation text)
                    # - Recommendation field contains: "test2" (should be reflection)
                    # - Category field contains what should be recommendation
                    # - Submitter field contains category info
                    
                    # Let me try to map based on the actual data pattern:
                    submitter_username = pointer.get('Submitter', 'Unknown')
                    
                    # Try different mappings to see what's actually happening
                    raw_obs = pointer.get('Observation', 'N/A')
                    raw_ref = pointer.get('Reflection', 'N/A')
                    raw_rec = pointer.get('Recommendation', 'N/A')
                    raw_cat = pointer.get('Category', 'N/A')
                    raw_date = pointer.get('Observation_Date', 'N/A')
                    
                    # Now I know the exact mapping from the debug data:
                    # Observation_Date field contains: username ("cabre")
                    # Observation field contains: date ("2025-08-11") 
                    # Reflection field contains: observation text ("test1")
                    # Recommendation field contains: reflection text ("test2")
                    # Category field contains: recommendation text ("test3")
                    # Submitter field contains: category ("Near Miss")
                    
                    # Correct the mapping:
                    submitter_username = raw_date  # Username is in Observation_Date field
                    obs_date = raw_obs             # Date is in Observation field
                    observation = raw_ref          # Observation text is in Reflection field
                    reflection = raw_rec           # Reflection text is in Recommendation field
                    recommendation = raw_cat       # Recommendation text is in Category field
                    category = submitter_username  # Category is in Submitter field
                    
                    # Clean up the submitter name (remove extra text)
                    if submitter_username and submitter_username != 'N/A':
                        submitter_username = submitter_username.strip()
                    
                    # Set category color based on category
                    category_color = {
                        'Near Miss': '#f39c12',
                        'Accident': '#e74c3c', 
                        'Potential Accident': '#e67e22'
                    }.get(category, '#3498db')
                    
                    # Get full name and rank for the submitter
                    try:
                        submitter_info = sheets_manager.get_user_full_name(submitter_username)
                        if submitter_info and submitter_info != submitter_username:
                            submitter_display = submitter_info  # This includes rank and name like "CPT JOHN DOE"
                        else:
                            # Fallback to username if name lookup fails
                            submitter_display = f"User: {submitter_username}"
                    except Exception as e:
                        submitter_display = f"User: {submitter_username}"
                    
                    # Format date to show only date part
                    try:
                        if len(obs_date.split()) > 1:
                            date_only = obs_date.split()[0]  # Get just the date part
                        else:
                            date_only = obs_date
                    except:
                        date_only = obs_date
                    
                    st.markdown(f"""
                    <div style="border: 1px solid #ddd; border-radius: 8px; padding: 15px; margin: 10px 0; background-color: #f8f9fa; border-left: 4px solid {category_color};">
                        <h4 style="color: #2C5530; margin: 0 0 12px 0;">📝 {category}</h4>
                        <div style="margin-bottom: 8px;">
                            <p style="margin: 3px 0; color: #333;"><strong>Observation:</strong> {observation}</p>
                        </div>
                        <div style="margin-bottom: 8px;">
                            <p style="margin: 3px 0; color: #333;"><strong>Reflection:</strong> {reflection}</p>
                        </div>
                        <div style="margin-bottom: 12px;">
                            <p style="margin: 3px 0; color: #333;"><strong>Recommendation:</strong> {recommendation}</p>
                        </div>
                        <p style="margin: 5px 0; color: #666; font-size: 0.9em;"><strong>Submitted by:</strong> {submitter_display}</p>
                        <p style="margin: 5px 0; color: #666; font-size: 0.9em;">{date_only}</p>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.info("📝 No safety pointers submitted yet. Help improve our safety culture!")
            st.markdown("*Use the 'Submit Safety Pointer' tab to share observations and recommendations.*")
            
    except Exception as e:
        st.error(f"⚠️ Error loading safety pointers: {str(e)}")
        st.markdown("**Debug info:** Check if Safety_Pointers worksheet exists in Google Sheets")
        
        # Try to show debug info
        try:
            debug_data = sheets_manager.get_safety_pointers()
            if debug_data:
                st.write("**Debug - Found safety pointers data:**")
                for item in debug_data[:2]:
                    st.json(item)
            else:
                st.write("**Debug:** No safety pointers data found")
        except Exception as debug_error:
            st.write(f"**Debug error:** {str(debug_error)}")

def safety_infographic_tab(sheets_manager):
    """Safety infographic submission tab with Cloudflare R2 storage"""
    
    st.markdown("Upload safety-related images and infographics to share with the team.")
    
    # Initialize R2 manager
    try:
        from cloudflare_r2 import CloudflareR2Manager, get_r2_setup_instructions
        r2_manager = CloudflareR2Manager()
        
        # R2 configured but no status display needed
    except ImportError:
        r2_manager = None
        st.info("📁 Cloudflare R2 integration available - install boto3 to enable cloud storage")
    
    with st.form("infographic_form"):
        # Image upload
        uploaded_file = st.file_uploader(
            "Upload Safety Infographic:",
            type=['jpg', 'jpeg', 'png', 'gif', 'webp'],
            help="Supported formats: JPG, JPEG, PNG, GIF, WebP (max 10MB)"
        )
        
        # Preview uploaded image
        if uploaded_file:
            st.markdown("**Preview:**")
            st.image(uploaded_file, caption=f"{uploaded_file.name}", use_container_width=True)
        
        submit_button = st.form_submit_button("📤 Submit Safety Infographic", type="primary")
        
        if submit_button:
            if not uploaded_file:
                st.error("Please upload an image file.")
            else:
                try:
                    # Prepare submission data
                    submission_data = {
                        'submitter': st.session_state.username,
                        'title': f"Safety Infographic by {st.session_state.username}",
                        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'original_filename': uploaded_file.name,
                        'file_size': uploaded_file.size
                    }
                    
                    # Try to upload to R2 if configured
                    image_url = None
                    if r2_manager and r2_manager.is_configured():
                        with st.spinner("📤 Uploading to Cloudflare R2..."):
                            upload_result = r2_manager.upload_infographic(
                                uploaded_file, 
                                st.session_state.username,
                                None  # No title needed
                            )
                        
                        if upload_result['success']:
                            image_url = upload_result['url']
                            submission_data['image_url'] = image_url
                            submission_data['optimized_size'] = upload_result['size']
                            submission_data['dimensions'] = upload_result['dimensions']
                            st.success(f"✅ {upload_result['message']}")
                            st.info(f"🔗 Public URL: {image_url}")
                        else:
                            st.warning(f"⚠️ R2 upload failed: {upload_result['error']}")
                            st.info("📝 Continuing with metadata-only submission...")
                            submission_data['image_url'] = "UPLOAD_FAILED"
                    else:
                        submission_data['image_url'] = "METADATA_ONLY"
                        st.info("📝 Saving submission metadata to Google Sheets (R2 storage not configured)")
                    
                    # Save to Google Sheets
                    try:
                        # Try to get or create Safety_Infographics worksheet
                        try:
                            safety_sheet = sheets_manager.spreadsheet.worksheet('Safety_Infographics')
                        except:
                            # Create sheet if it doesn't exist
                            safety_sheet = sheets_manager.spreadsheet.add_worksheet(title='Safety_Infographics', rows=1000, cols=10)
                            
                            # Add headers
                            headers = ['Submitter', 'Title', 'Date', 'Original_Filename', 'File_Size', 'Image_URL', 'Optimized_Size', 'Dimensions', 'Tags']
                            safety_sheet.append_row(headers)
                        
                        # Append the submission data
                        row_data = [
                            submission_data['submitter'],
                            submission_data['title'],
                            submission_data['date'],
                            submission_data['original_filename'],
                            str(submission_data['file_size']),
                            submission_data.get('image_url', ''),
                            str(submission_data.get('optimized_size', '')),
                            str(submission_data.get('dimensions', '')),
                            ''  # Tags placeholder
                        ]
                        safety_sheet.append_row(row_data)
                        
                        st.success("✅ Safety infographic submitted successfully!")
                        st.balloons()
                        
                        # Show submission summary
                        with st.expander("📋 Submission Details"):
                            st.write(f"**Title:** {submission_data['title']}")
                            st.write(f"**Submitted by:** {submission_data['submitter']}")
                            st.write(f"**Date:** {submission_data['date']}")
                            if image_url and image_url not in ["METADATA_ONLY", "UPLOAD_FAILED"]:
                                st.write(f"**Storage:** Cloudflare R2")
                                st.write(f"**URL:** {image_url}")
                            else:
                                st.write(f"**Storage:** Google Sheets metadata only")
                                st.info("💡 To enable cloud image storage, set up Cloudflare R2 credentials")
                        
                    except Exception as e:
                        st.error(f"❌ Error saving to Google Sheets: {str(e)}")
                        st.info("The image was uploaded to R2 but metadata couldn't be saved to sheets.")
                    
                except Exception as e:
                    st.error(f"❌ Error processing submission: {str(e)}")

def safety_pointer_tab(sheets_manager):
    """Safety pointer submission tab"""
    
    st.markdown("Submit safety observations and recommendations to improve workplace safety.")
    
    with st.form("safety_pointer_form"):
        # Date of Observation
        observation_date = st.date_input(
            "Date of Observation:",
            value=datetime.now().date(),
            help="When did you observe this safety issue or situation?"
        )
        
        # Observation
        observation = st.text_area(
            "Observation:",
            placeholder="Describe what you observed (situation, behavior, conditions, etc.)",
            height=100
        )
        
        # Reflection
        reflection = st.text_area(
            "Reflection:",
            placeholder="What are your thoughts on this observation? Why is it significant?",
            height=100
        )
        
        # Recommendation
        recommendation = st.text_area(
            "Recommendation:",
            placeholder="What actions do you recommend to address this observation?",
            height=100
        )
        
        # Category dropdown
        category = st.selectbox(
            "Category:",
            ["Near Miss", "Accident", "Potential Accident"],
            help="Select the most appropriate category for this observation"
        )
        
        submit_button = st.form_submit_button("Submit Safety Pointer", type="primary")
        
        if submit_button:
            if not observation.strip():
                st.error("Please enter your observation.")
            elif not reflection.strip():
                st.error("Please enter your reflection.")
            elif not recommendation.strip():
                st.error("Please enter your recommendation.")
            else:
                try:
                    # Process the submission
                    submission_data = {
                        'submitter': st.session_state.username,
                        'observation_date': observation_date.strftime('%Y-%m-%d'),
                        'observation': observation.strip(),
                        'reflection': reflection.strip(),
                        'recommendation': recommendation.strip(),
                        'category': category,
                        'submission_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                    
                    # Save to Google Sheets
                    try:
                        # Try to get or create Safety_Pointers worksheet
                        try:
                            safety_pointers_sheet = sheets_manager.spreadsheet.worksheet('Safety_Pointers')
                            # Get existing headers to ensure correct order
                            existing_headers = safety_pointers_sheet.row_values(1)
                        except:
                            # Create sheet if it doesn't exist
                            safety_pointers_sheet = sheets_manager.spreadsheet.add_worksheet(title='Safety_Pointers', rows=1000, cols=8)
                            
                            # Add headers in the correct order
                            headers = ['Submitter', 'Observation_Date', 'Observation', 'Reflection', 'Recommendation', 'Category', 'Submission_Date']
                            safety_pointers_sheet.append_row(headers)
                            existing_headers = headers
                        
                        # Check if headers match expected format and correct order
                        expected_headers = ['Submitter', 'Observation_Date', 'Observation', 'Reflection', 'Recommendation', 'Category', 'Submission_Date']
                        
                        if existing_headers != expected_headers:
                            # Headers are wrong, update them
                            safety_pointers_sheet.update('A1:G1', [expected_headers])
                        
                        # Based on debug data, the actual order being written is wrong
                        # The headers are: ['Submitter', 'Observation_Date', 'Observation', 'Reflection', 'Recommendation', 'Category', 'Submission_Date']
                        # But data is being written as: [category, observation_date, observation, reflection, recommendation, submitter, submission_date]
                        # Let me fix this to write in the correct order matching headers
                        
                        row_data = [
                            submission_data['submitter'],          # Submitter (was going to Category position)
                            submission_data['observation_date'],   # Observation_Date (was going to Submitter position)
                            submission_data['observation'],       # Observation (was correct)
                            submission_data['reflection'],        # Reflection (was correct)
                            submission_data['recommendation'],    # Recommendation (was correct)
                            submission_data['category'],          # Category (was going to Observation_Date position)
                            submission_data['submission_date']    # Submission_Date (was correct)
                        ]
                        
                        safety_pointers_sheet.append_row(row_data)
                        
                        st.success("✅ Safety pointer submitted successfully!")
                        st.info("📝 Your safety observation has been logged and will help improve workplace safety.")
                        
                        # Clear the form by rerunning (user will see success message)
                        
                    except Exception as sheets_error:
                        st.error(f"❌ Error saving to Google Sheets: {str(sheets_error)}")
                        st.info("📝 Your submission was processed but may not have been saved. Please try again.")
                    
                except Exception as e:
                    st.error(f"❌ Error submitting safety pointer: {str(e)}")

def dashboard_tab(sheets_manager):
    """Dashboard overview"""
    
    try:
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
    
    # Add CSS styles for dashboard
    st.markdown("""
    <style>
        /* Enhanced Metric Cards - All same height */
        .metric-card-current, .metric-card-expired, .metric-card-expiring, .metric-card-vehicles {
            padding: 15px 10px;
            border-radius: 12px;
            text-align: center;
            margin: 0;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            height: 160px;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            overflow: visible;
            box-sizing: border-box;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
            position: relative;
            width: 100%;
        }
        
        /* Hover effects for cards */
        .metric-card-current:hover, .metric-card-expired:hover, .metric-card-expiring:hover, .metric-card-vehicles:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 16px rgba(0,0,0,0.2);
        }
        
        /* Optimized text sizing for metric cards to prevent cutoff */
        .metric-card-current h2, .metric-card-expired h2, .metric-card-expiring h2, .metric-card-vehicles h2 {
            margin: 5px 0;
            font-size: clamp(1.4rem, 3vw, 1.8rem);
            line-height: 1.1;
            font-weight: 700;
            text-shadow: 0 1px 2px rgba(0,0,0,0.1);
        }
        
        .metric-card-current p, .metric-card-expired p, .metric-card-expiring p, .metric-card-vehicles p {
            margin: 4px 0;
            font-size: clamp(0.85rem, 2vw, 1rem);
            line-height: 1.2;
            font-weight: 600;
        }
        
        .metric-card-current small, .metric-card-expired small, .metric-card-expiring small, .metric-card-vehicles small {
            margin: 3px 0;
            font-size: clamp(0.7rem, 1.5vw, 0.8rem);
            line-height: 1.1;
            opacity: 0.8;
        }
        
        /* Container for metric cards grid - ensures equal heights */
        .metrics-container {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            grid-template-rows: 1fr;
            gap: 15px;
            margin: 20px 0;
            width: 100%;
            align-items: stretch;
        }
        
        /* Individual metric card wrapper - ensures cards fill full height */
        .metric-wrapper {
            width: 100%;
            height: 100%;
            box-sizing: border-box;
            display: flex;
            align-items: stretch;
        }
        
        .metric-wrapper > div {
            flex: 1;
        }
        
        /* Responsive grid for smaller screens */
        @media (max-width: 768px) {
            .metrics-container {
                grid-template-columns: repeat(2, 1fr);
                gap: 10px;
            }
        }
        
        @media (max-width: 480px) {
            .metrics-container {
                grid-template-columns: 1fr;
                gap: 8px;
            }
        }
        
        .metric-card-current {
            background: linear-gradient(135deg, #d4edda, #c3e6cb);
            color: #155724;
            border-left: 5px solid #28a745;
        }
        .metric-card-expired {
            background: linear-gradient(135deg, #f8d7da, #f1b0b7);
            color: #721c24;
            border-left: 5px solid #dc3545;
        }
        .metric-card-expiring {
            background: linear-gradient(135deg, #fff3cd, #ffeaa7);
            color: #856404;
            border-left: 5px solid #ffc107;
        }
        .metric-card-vehicles {
            background: linear-gradient(135deg, #e2e3e5, #d1d3d4);
            color: #383d41;
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
        

    </style>
    """, unsafe_allow_html=True)
    
    # Header with refresh button
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("🔄 Refresh", help="Get latest data"):
            # Clear all relevant caches for immediate updates
            clear_session_cache()
            st.cache_data.clear()
            st.cache_resource.clear()
            st.success("Data refreshed!")
            st.rerun()
    
    with col2:
        st.markdown("""
        <h1 style="text-align: center; margin-bottom: 30px; color: #2c3e50;">Team Overview</h1>
        """, unsafe_allow_html=True)
    
    # Create tabs for different team overviews
    tab1, tab2 = st.tabs(["🚗 Mileage Status", "💪 Fitness Progress"])
    
    with tab1:
        mileage_team_overview(sheets_manager)
    
    with tab2:
        fitness_team_overview(sheets_manager)

def mileage_team_overview(sheets_manager):
    """Team overview for mileage/vehicle currency"""
    try:
        # Get all personnel status with session caching for faster loading
        @session_cache(ttl=600)  # 10 minute session cache
        def get_cached_personnel_status():
            return sheets_manager.get_all_personnel_status()
        
        all_personnel = get_cached_personnel_status()
        
        if not all_personnel:
            st.warning("No personnel data found.")
            return
        
        # Convert to DataFrame for easier analysis with optimization
        import pandas as pd
        df = pd.DataFrame(all_personnel)
        df = optimize_dataframe(df)  # Optimize memory usage
        
        # Key Metrics Section
        st.subheader("📊 Overall Status")
        
        total_personnel = len(df)
        current_count = len(df[df['currency_status'].str.upper() == 'YES'])
        not_current_count = len(df[df['currency_status'].str.upper() == 'NO'])
        
        try:
            df['days_to_expiry_num'] = pd.to_numeric(df['days_to_expiry'], errors='coerce')
            expiring_soon = len(df[(df['currency_status'].str.upper() == 'YES') & (df['days_to_expiry_num'] <= 14)])
        except:
            expiring_soon = 0
        
        # Vehicle breakdown
        terrex_personnel = df[df['vehicle_type'] == 'Terrex']
        belrex_personnel = df[df['vehicle_type'] == 'Belrex']
        terrex_current = len(terrex_personnel[terrex_personnel['currency_status'].str.upper() == 'YES'])
        belrex_current = len(belrex_personnel[belrex_personnel['currency_status'].str.upper() == 'YES'])
        
        # Display metrics in improved grid layout
        st.markdown("""
        <div class="metrics-container">
        """, unsafe_allow_html=True)
        
        col1, col2, col3, col4 = st.columns(4, gap="medium")
        
        with col1:
            current_rate = (current_count/total_personnel*100) if total_personnel > 0 else 0
            st.markdown(f"""
            <div class="metric-wrapper">
                <div class="metric-card-current">
                    <h2>✅ {current_count}</h2>
                    <p>Current Personnel</p>
                    <small>{current_rate:.1f}% of {total_personnel}</small>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            not_current_rate = (not_current_count/total_personnel*100) if total_personnel > 0 else 0
            st.markdown(f"""
            <div class="metric-wrapper">
                <div class="metric-card-expired">
                    <h2>❌ {not_current_count}</h2>
                    <p>Not Current</p>
                    <small>{not_current_rate:.1f}% need drives</small>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div class="metric-wrapper">
                <div class="metric-card-expiring">
                    <h2>⚠️ {expiring_soon}</h2>
                    <p>Expiring Soon</p>
                    <small>Within 14 days</small>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        with col4:
            st.markdown(f"""
            <div class="metric-wrapper">
                <div class="metric-card-vehicles">
                    <h2>🚛 {terrex_current}/{len(terrex_personnel)}</h2>
                    <p>🚗 {belrex_current}/{len(belrex_personnel)}</p>
                    <small>Current/Total by Vehicle</small>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Critical Actions Section
        st.subheader("🚨 Priority Actions")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Immediate Action Required")
            not_current = df[df['currency_status'].str.upper() == 'NO']
            if len(not_current) > 0:
                for _, person in not_current.head(8).iterrows():  # Limit for better display
                    st.markdown(f"""
                    <div class="action-item-critical">
                        <strong>{person['rank']} {person['name']}</strong><br>
                        <small>{person['vehicle_type']} • {person['distance_3_months']:.1f} KM (3mo)</small>
                    </div>
                    """, unsafe_allow_html=True)
                if len(not_current) > 8:
                    st.info(f"... and {len(not_current) - 8} more personnel need drives")
            else:
                st.success("All personnel are current!")
        
        with col2:
            st.markdown("#### Expiring Within 14 Days")
            try:
                expiring = df[(df['currency_status'].str.upper() == 'YES') & (df['days_to_expiry_num'] <= 14)]
                if len(expiring) > 0:
                    for _, person in expiring.head(8).iterrows():
                        days_left = int(person['days_to_expiry_num']) if pd.notna(person['days_to_expiry_num']) else 0
                        st.markdown(f"""
                        <div class="action-item-warning">
                            <strong>{person['rank']} {person['name']}</strong><br>
                            <small>{person['vehicle_type']} • Expires in {days_left} days</small>
                        </div>
                        """, unsafe_allow_html=True)
                    if len(expiring) > 8:
                        st.info(f"... and {len(expiring) - 8} more expiring soon")
                else:
                    st.success("No immediate expirations")
            except:
                st.info("No expiration data available")
        
        st.markdown("---")
        
        # Platoon Status Section
        st.subheader("🏢 Platoon Overview")
        
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
                
                # Ensure 'Days to Expiry' column is treated as string to avoid Arrow serialization errors
                display_df['Days to Expiry'] = display_df['Days to Expiry'].astype(str)
                
                st.dataframe(display_df, use_container_width=True, height=200)
        
        # Personnel Search Section
        st.subheader("🔍 Personnel Search")
        
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
        
        # Display filtered results
        if len(filtered_df) > 0:
            st.markdown(f"**Found {len(filtered_df)} personnel**")
            
            display_cols = ['rank', 'name', 'platoon', 'vehicle_type', 'currency_status', 'distance_3_months', 'days_to_expiry']
            table_df = filtered_df[display_cols].copy()
            table_df.columns = ['Rank', 'Name', 'Platoon', 'Vehicle', 'Status', '3-Month KM', 'Days to Expiry']
            
            # Clean up data types for display
            table_df['Days to Expiry'] = table_df['Days to Expiry'].astype(str)
            table_df['3-Month KM'] = pd.to_numeric(table_df['3-Month KM'], errors='coerce').fillna(0).round(1)
            
            st.dataframe(table_df, use_container_width=True, height=400)
        else:
            st.info("No personnel found matching the current filters.")
            
    except Exception as e:
        st.error(f"Error loading team dashboard: {str(e)}")

def fitness_team_overview(sheets_manager):
    """Team overview for fitness progress"""
    try:
        st.subheader("💪 Strength & Power Programme Overview")
        
        # Get fitness data from all personnel
        @session_cache(ttl=600)  # 10 minute session cache
        def get_cached_fitness_data():
            return get_all_fitness_data(sheets_manager)
        
        fitness_data = get_cached_fitness_data()
        
        if not fitness_data:
            st.warning("No S&P programme data found.")
            return
        
        # Convert to DataFrame for analysis
        import pandas as pd
        df = pd.DataFrame(fitness_data)
        df = optimize_dataframe(df)
        
        # S&P Progress Overview Section
        st.subheader("📊 S&P Progress Overview")
        
        total_personnel = len(df)
        active_personnel = len(df[df['recent_workouts'] > 0])
        improving_personnel = len(df[df['progress_trend'] == 'improving']) if 'progress_trend' in df.columns else 0
        avg_sessions = df['recent_workouts'].mean() if total_personnel > 0 else 0
        
        # Display progress metrics in improved grid layout
        st.markdown("""
        <div class="metrics-container">
        """, unsafe_allow_html=True)
        
        col1, col2, col3, col4 = st.columns(4, gap="medium")
        
        with col1:
            active_rate = (active_personnel/total_personnel*100) if total_personnel > 0 else 0
            st.markdown(f"""
            <div class="metric-wrapper">
                <div class="metric-card-current">
                    <h2>💪 {active_personnel}</h2>
                    <p>Active Training</p>
                    <small>{active_rate:.1f}% of {total_personnel}</small>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            if 'progress_trend' in df.columns:
                improving_rate = (improving_personnel/total_personnel*100) if total_personnel > 0 else 0
                st.markdown(f"""
                <div class="metric-wrapper">
                    <div class="metric-card-current">
                        <h2>📈 {improving_personnel}</h2>
                        <p>Showing Progress</p>
                        <small>{improving_rate:.1f}% improving</small>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                total_sessions = df['recent_workouts'].sum()
                st.markdown(f"""
                <div class="metric-wrapper">
                    <div class="metric-card-expiring">
                        <h2>🏋️ {total_sessions}</h2>
                        <p>Total Sessions</p>
                        <small>Team effort</small>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        
        with col3:
            if 'avg_weight_increase' in df.columns:
                avg_weight_increase = df['avg_weight_increase'].mean()
                st.markdown(f"""
                <div class="metric-wrapper">
                    <div class="metric-card-vehicles">
                        <h2>⬆️ {avg_weight_increase:.1f}kg</h2>
                        <p>Avg Weight Gain</p>
                        <small>Last 30 days</small>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="metric-wrapper">
                    <div class="metric-card-expiring">
                        <h2>📊 {avg_sessions:.1f}</h2>
                        <p>Avg Sessions</p>
                        <small>Last 30 days</small>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        
        with col4:
            if 'personal_records' in df.columns:
                total_prs = df['personal_records'].sum()
                st.markdown(f"""
                <div class="metric-wrapper">
                    <div class="metric-card-current">
                        <h2>🏆 {total_prs}</h2>
                        <p>Personal Records</p>
                        <small>This month</small>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                total_sessions = df['recent_workouts'].sum()
                st.markdown(f"""
                <div class="metric-wrapper">
                    <div class="metric-card-vehicles">
                        <h2>🏋️ {total_sessions}</h2>
                        <p>Total Sessions</p>
                        <small>Programme progress</small>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Progress Highlights
        st.subheader("🎯 Progress Highlights")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Strength Gainers")
            if 'max_weight_lifted' in df.columns:
                strength_gainers = df.nlargest(8, 'max_weight_lifted')
                if len(strength_gainers) > 0:
                    for _, person in strength_gainers.iterrows():
                        if person['max_weight_lifted'] > 0:
                            progress_indicator = ""
                            if 'weight_increase' in df.columns and person['weight_increase'] > 0:
                                progress_indicator = f" (+{person['weight_increase']:.1f}kg)"
                            st.markdown(f"""
                            <div class="action-item-warning" style="background-color: #d4edda; color: #155724; border-left: 4px solid #28a745;">
                                <strong>{person['rank']} {person['name']}</strong><br>
                                <small>Max: {person['max_weight_lifted']:.1f}kg{progress_indicator}</small>
                            </div>
                            """, unsafe_allow_html=True)
                else:
                    st.info("No strength data available")
            else:
                # Fallback to session count
                top_performers = df.nlargest(8, 'recent_workouts')
                if len(top_performers) > 0:
                    for _, person in top_performers.iterrows():
                        if person['recent_workouts'] > 0:
                            st.markdown(f"""
                            <div class="action-item-warning" style="background-color: #d1ecf1; color: #0c5460; border-left: 4px solid #17a2b8;">
                                <strong>{person['rank']} {person['name']}</strong><br>
                                <small>{person['recent_workouts']} sessions completed</small>
                            </div>
                            """, unsafe_allow_html=True)
                else:
                    st.info("No session data available")
        
        with col2:
            st.markdown("#### Personal Records")
            if 'recent_prs' in df.columns:
                pr_leaders = df.nlargest(8, 'recent_prs')
                if len(pr_leaders) > 0:
                    for _, person in pr_leaders.iterrows():
                        if person['recent_prs'] > 0:
                            st.markdown(f"""
                            <div class="action-item-warning" style="background-color: #fff3cd; color: #856404; border-left: 4px solid #ffc107;">
                                <strong>{person['rank']} {person['name']}</strong><br>
                                <small>{person['recent_prs']} PRs this month</small>
                            </div>
                            """, unsafe_allow_html=True)
                else:
                    st.info("No recent personal records")
            else:
                # Show personnel needing attention
                st.markdown("#### Needs Support")
                inactive = df[df['recent_workouts'] == 0]
                if len(inactive) > 0:
                    for _, person in inactive.head(8).iterrows():
                        st.markdown(f"""
                        <div class="action-item-critical">
                            <strong>{person['rank']} {person['name']}</strong><br>
                            <small>No recent training sessions</small>
                        </div>
                        """, unsafe_allow_html=True)
                    if len(inactive) > 8:
                        st.info(f"... and {len(inactive) - 8} more need support")
                else:
                    st.success("Everyone is actively training!")
        
        st.markdown("---")
        
        # Platoon Progress Breakdown
        st.subheader("🏢 Platoon Progress Breakdown")
        
        # Group by platoon
        if 'platoon' in df.columns:
            agg_dict = {
                'recent_workouts': ['count', 'sum', 'mean'],
                'username': 'count'
            }
            if 'max_weight_lifted' in df.columns:
                agg_dict['max_weight_lifted'] = 'mean'
            if 'recent_prs' in df.columns:
                agg_dict['recent_prs'] = 'sum'
                
            platoon_groups = df.groupby('platoon').agg(agg_dict).reset_index()
            
            # Flatten column names
            platoon_groups.columns = ['Platoon', 'Active_Count', 'Total_Sessions', 'Avg_Sessions', 'Total_Personnel'] + \
                                   (['Avg_Max_Weight'] if 'max_weight_lifted' in df.columns else []) + \
                                   (['Total_PRs'] if 'recent_prs' in df.columns else [])
            
            # Display each platoon
            for _, platoon in platoon_groups.iterrows():
                avg_sessions = platoon['Avg_Sessions']
                active_rate = (platoon['Active_Count'] / platoon['Total_Personnel'] * 100) if platoon['Total_Personnel'] > 0 else 0
                
                # Determine progress status
                if avg_sessions >= 8:
                    status_emoji = "🔥"
                    status_text = "Excellent Progress"
                elif avg_sessions >= 4:
                    status_emoji = "💪"
                    status_text = "Good Progress"
                else:
                    status_emoji = "📈"
                    status_text = "Building Momentum"
                
                # Add progress indicators if available
                progress_info = f"{platoon['Total_Sessions']} total sessions ({avg_sessions:.1f} avg)"
                if 'Avg_Max_Weight' in platoon_groups.columns:
                    progress_info += f" | Avg Max: {platoon['Avg_Max_Weight']:.1f}kg"
                if 'Total_PRs' in platoon_groups.columns:
                    progress_info += f" | {platoon['Total_PRs']} PRs"
                
                with st.expander(f"{status_emoji} **{platoon['Platoon']}** - {progress_info} - {status_text}", expanded=False):
                    # Get personnel for this platoon
                    platoon_personnel = df[df['platoon'] == platoon['Platoon']]
                    
                    # Quick stats
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Personnel", len(platoon_personnel))
                    with col2:
                        active_count = len(platoon_personnel[platoon_personnel['recent_workouts'] > 0])
                        st.metric("Active", active_count)
                    with col3:
                        st.metric("Total Sessions", int(platoon['Total_Sessions']))
                    with col4:
                        if 'Total_PRs' in platoon_groups.columns:
                            st.metric("Personal Records", int(platoon['Total_PRs']))
                        else:
                            st.metric("Avg Sessions", f"{avg_sessions:.1f}")
                    
                    # Personnel table for this platoon with progress focus
                    st.markdown("**📋 Platoon Progress Status:**")
                    display_cols = ['rank', 'name', 'recent_workouts', 'last_workout_date']
                    if 'max_weight_lifted' in platoon_personnel.columns:
                        display_cols.append('max_weight_lifted')
                    if 'recent_prs' in platoon_personnel.columns:
                        display_cols.append('recent_prs')
                    
                    available_cols = [col for col in display_cols if col in platoon_personnel.columns]
                    if available_cols:
                        display_df = platoon_personnel[available_cols].copy()
                        col_names = ['Rank', 'Name', '30-Day Sessions', 'Last Session']
                        if 'max_weight_lifted' in available_cols:
                            col_names.append('Max Weight')
                        if 'recent_prs' in available_cols:
                            col_names.append('Recent PRs')
                        display_df.columns = col_names[:len(available_cols)]
                        display_df = display_df.sort_values('30-Day Sessions', ascending=False)
                        st.dataframe(display_df, use_container_width=True, height=200)
        
        # Personnel Progress Search
        st.subheader("🔍 Progress Search")
        
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            search_term = st.text_input("Search by name:", placeholder="Type name to search...", key="fitness_search")
        with col2:
            progress_filter = st.selectbox("Progress Status:", ["All", "Active", "High Performers", "Need Support"], key="fitness_progress")
        with col3:
            min_sessions = st.number_input("Min Sessions:", min_value=0, value=0, key="fitness_min_sessions")
        
        # Apply filters
        filtered_df = df.copy()
        if search_term:
            filtered_df = filtered_df[
                filtered_df['name'].str.contains(search_term, case=False, na=False) |
                filtered_df['username'].str.contains(search_term, case=False, na=False)
            ]
        
        if progress_filter == "Active":
            filtered_df = filtered_df[filtered_df['recent_workouts'] > 0]
        elif progress_filter == "High Performers":
            # Top 25% by session count
            threshold = filtered_df['recent_workouts'].quantile(0.75) if len(filtered_df) > 0 else 0
            filtered_df = filtered_df[filtered_df['recent_workouts'] >= threshold]
        elif progress_filter == "Need Support":
            filtered_df = filtered_df[filtered_df['recent_workouts'] == 0]
        
        if min_sessions > 0:
            filtered_df = filtered_df[filtered_df['recent_workouts'] >= min_sessions]
        
        # Display filtered results
        if len(filtered_df) > 0:
            st.markdown(f"**Found {len(filtered_df)} personnel**")
            
            display_cols = ['rank', 'name', 'platoon', 'recent_workouts', 'last_workout_date']
            if 'max_weight_lifted' in filtered_df.columns:
                display_cols.append('max_weight_lifted')
            if 'recent_prs' in filtered_df.columns:
                display_cols.append('recent_prs')
            
            available_cols = [col for col in display_cols if col in filtered_df.columns]
            if available_cols:
                table_df = filtered_df[available_cols].copy()
                col_names = ['Rank', 'Name', 'Platoon', '30-Day Sessions', 'Last Session']
                if 'max_weight_lifted' in available_cols:
                    col_names.append('Max Weight (kg)')
                if 'recent_prs' in available_cols:
                    col_names.append('Recent PRs')
                table_df.columns = col_names[:len(available_cols)]
                table_df = table_df.sort_values('30-Day Sessions', ascending=False)
                st.dataframe(table_df, use_container_width=True)
        else:
            st.info("No personnel found matching the criteria.")
            
    except Exception as e:
        st.error(f"Error loading fitness team overview: {str(e)}")

def get_all_fitness_data(sheets_manager):
    """Get fitness data for all personnel with progress tracking"""
    try:
        # Get fitness worksheet
        try:
            fitness_sheet = sheets_manager.spreadsheet.worksheet('Fitness_Tracker')
            fitness_records = fitness_sheet.get_all_records()
        except:
            return []
        
        # Get personnel qualifications for names and ranks
        personnel_data = []
        
        # Group fitness data by username and calculate stats
        from collections import defaultdict
        user_workouts = defaultdict(list)
        
        for record in fitness_records:
            username = record.get('Username', '').strip()
            if username:
                user_workouts[username].append(record)
        
        # Calculate fitness metrics for each user
        for username, workouts in user_workouts.items():
            # Get user qualifications for rank and name
            user_quals = sheets_manager.check_user_qualifications(username)
            
            # Calculate recent workouts (last 30 days)
            from datetime import datetime, timedelta
            thirty_days_ago = datetime.now() - timedelta(days=30)
            recent_workouts = 0
            last_workout_date = "Never"
            max_weight_lifted = 0
            recent_prs = 0
            weight_progression = []
            
            for workout in workouts:
                try:
                    workout_date_str = workout.get('Date', '')
                    if workout_date_str:
                        workout_date = datetime.strptime(workout_date_str, '%Y-%m-%d')
                        
                        # Track recent activity
                        if workout_date >= thirty_days_ago:
                            recent_workouts += 1
                            
                            # Track weight progression
                            try:
                                weight = float(workout.get('Weight', 0) or 0)
                                if weight > 0:
                                    weight_progression.append(weight)
                                    max_weight_lifted = max(max_weight_lifted, weight)
                            except:
                                pass
                            
                            # Count personal records (simplified: any workout with weight > previous max)
                            if weight > max_weight_lifted * 0.95:  # Within 5% counts as potential PR
                                recent_prs += 1
                        
                        # Track most recent workout
                        if last_workout_date == "Never" or workout_date > datetime.strptime(last_workout_date, '%Y-%m-%d'):
                            last_workout_date = workout_date_str
                except:
                    continue
            
            # Calculate weight increase trend
            weight_increase = 0
            progress_trend = 'stable'
            if len(weight_progression) >= 2:
                weight_increase = weight_progression[-1] - weight_progression[0]
                if weight_increase > 2:
                    progress_trend = 'improving'
                elif weight_increase < -2:
                    progress_trend = 'declining'
            
            personnel_data.append({
                'username': username,
                'name': user_quals.get('full_name', username),
                'rank': user_quals.get('rank', ''),
                'platoon': user_quals.get('platoon', 'Unknown'),
                'recent_workouts': recent_workouts,
                'total_workouts': len(workouts),
                'last_workout_date': last_workout_date,
                'max_weight_lifted': max_weight_lifted,
                'recent_prs': recent_prs,
                'weight_increase': weight_increase,
                'progress_trend': progress_trend,
                'avg_weight_increase': weight_increase,
                'personal_records': recent_prs
            })
        
        return personnel_data
        
    except Exception as e:
        print(f"Error getting fitness data: {e}")
        return []

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
                format="%.1f",
                value=None,
                placeholder="Enter starting mileage"
            )
        
        with col4:
            final_mileage = st.number_input(
                "Final Mileage (KM)",
                min_value=0.0,
                max_value=999999.0,
                step=0.1,
                format="%.1f",
                value=None,
                placeholder="Enter ending mileage"
            )
        
        # Calculate distance automatically
        if initial_mileage is not None and final_mileage is not None:
            if final_mileage > initial_mileage:
                distance_driven = final_mileage - initial_mileage
                st.info(f"Distance Driven: {distance_driven:.1f} KM")
            else:
                distance_driven = 0.0
                st.error("Final mileage must be greater than initial mileage")
        else:
            distance_driven = 0.0
            if initial_mileage is not None and final_mileage is not None:
                st.info("Enter both initial and final mileage to calculate distance")
        
        submit_button = st.form_submit_button("Log Mileage", type="primary")
        
        if submit_button:
            # Validation
            if not vehicle_no.strip():
                st.error("Please enter a vehicle number (MID)")
                return
            
            if initial_mileage is None:
                st.error("Please enter initial mileage")
                return
                
            if final_mileage is None:
                st.error("Please enter final mileage")
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

def restore_session():
    """Restore user session from browser storage if available"""
    # Check if there's a stored session
    if not st.session_state.get('logged_in', False):
        # Add JavaScript to check localStorage and return values
        session_check = st.components.v1.html("""
        <script>
        const loggedIn = localStorage.getItem('msc_drivr_logged_in');
        const username = localStorage.getItem('msc_drivr_username');
        const sessionToken = localStorage.getItem('msc_drivr_session_token');
        const loginTime = localStorage.getItem('msc_drivr_login_time');
        
        // Check if session is still valid (2 hours = 7200 seconds)
        const currentTime = Math.floor(Date.now() / 1000);
        const sessionValid = loginTime && (currentTime - parseInt(loginTime)) < 7200;
        
        if (loggedIn === 'true' && username && sessionToken && sessionValid) {
            // Return session data to Python
            const params = new URLSearchParams(window.location.search);
            if (!params.get('restored_user')) {
                params.set('restored_user', username);
                params.set('restored_token', sessionToken);
                window.location.search = params.toString();
            }
        }
        </script>
        """, height=0)
        
        # Check URL parameters for restored session
        query_params = st.query_params
        if 'restored_user' in query_params and 'restored_token' in query_params:
            username = query_params['restored_user']
            session_token = query_params['restored_token']
            
            # Validate session token
            if validate_session_token(username, session_token):
                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.login_time = time.time()
                
                # Clear URL parameters after successful restore
                st.query_params.clear()
                st.success(f"Welcome back, {username}!")
                return True
    
    return False

def validate_session_token(username, token):
    """Simple session token validation"""
    # Basic validation - in production, use proper JWT or secure tokens
    expected_token = hashlib.sha256(f"{username}_session_salt".encode()).hexdigest()[:16]
    return token == expected_token

def generate_session_token(username):
    """Generate a simple session token"""
    return hashlib.sha256(f"{username}_session_salt".encode()).hexdigest()[:16]

def main():
    """Main application controller with session persistence"""
    # Initialize session state
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    
    # Try to restore session first
    restore_session()
    
    # Smart high-load protection: Automatically detects and responds to high load
    if st.session_state.logged_in:
        username = st.session_state.get('username', 'unknown')
        
        # Check if we're in high load mode and apply rate limiting only then
        if st.session_state.get('high_load_mode', False):
            if not check_rate_limit(username):
                st.error("🚫 System under high load. Please wait 30 seconds and refresh.")
                st.info("💡 Try again in a moment - protection will automatically disable when load decreases.")
                st.stop()
    
    # Periodic memory cleanup every request
    cleanup_session_memory()
    
    # Check if user is logged in
    if not st.session_state.logged_in:
        login_page()
    else:
        try:
            main_app()
        except Exception as e:
            st.error(f"Application error: {str(e)}")
            st.info("Please refresh the page. If the problem persists, try again in a few minutes.")
            # Clear problematic session state
            if 'sheets_manager' in st.session_state:
                del st.session_state['sheets_manager']

if __name__ == "__main__":
    main()
