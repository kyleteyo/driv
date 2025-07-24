import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import json
import time
from auth import authenticate_user, change_password, get_user_info
from sheets_manager import SheetsManager
from utils import calculate_currency_status, format_status_badge
# Removed performance_config import to fix compatibility
# Removed api_optimizer import to fix compatibility
import chatbot

# Set purple theme for Streamlit Cloud deployment
st.set_page_config(
    page_title="MSC DRIVr",
    page_icon="./msc_logo.png",  # Use your custom MSC logo file
    layout="wide"
)

# Add custom CSS for purple theme
st.markdown("""
<style>
    .stButton > button {
        background-color: #8A2BE2;
        color: white;
        border: none;
    }
    .stButton > button:hover {
        background-color: #7B68EE;
        color: white;
    }
    .stSelectbox > div > div {
        background-color: #8A2BE2;
    }
    .stTextInput > div > div > input {
        border-color: #8A2BE2;
    }
    .stDateInput > div > div > input {
        border-color: #8A2BE2;
    }
    .stNumberInput > div > div > input {
        border-color: #8A2BE2;
    }
    .stTab[data-baseweb="tab"] {
        color: #8A2BE2;
    }
    .stTab[aria-selected="true"] {
        color: #8A2BE2;
        border-bottom-color: #8A2BE2;
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
            st.session_state.current_page = "My Mileage"
        
        # Navigation menu - plain text style
        st.write("**Navigation**")
        
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
        
        # MSC Safety Bot - Work in Progress (disabled for deployment)
        # if st.session_state.current_page == "Safety Bot":
        #     st.write("→ 🤖 MSC SAFETY BOT")
        # else:
        #     if st.button("🤖 MSC SAFETY BOT", key="nav_bot"):
        #         st.session_state.current_page = "Safety Bot"
        #         st.rerun()
        
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
    if st.session_state.current_page == "My Mileage":
        my_mileage_page(sheets_manager)
    elif st.session_state.current_page == "Safety Portal":
        safety_portal_page(sheets_manager)
    # elif st.session_state.current_page == "Safety Bot":
    #     safety_bot_page(sheets_manager)  # Work in progress - disabled for deployment
    elif st.session_state.current_page == "Team Overview":
        admin_team_dashboard(sheets_manager)
    elif st.session_state.current_page == "Account Management":
        account_management_tab(sheets_manager)
    elif st.session_state.current_page == "Change Password":
        change_password_tab()
    else:
        # Default to My Mileage if no valid page selected
        my_mileage_page(sheets_manager)

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

def safety_bot_page(sheets_manager):
    """MSC Safety Bot page"""
    st.title("🤖 MSC SAFETY BOT")
    st.markdown("---")
    
    # Render the chatbot interface
    chatbot.render_chatbot_interface(sheets_manager)

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
        
        # Filter out entries without valid images first
        valid_infographics = []
        for infographic in infographics_data:
            image_url = infographic.get('File_Name', '')
            if image_url and image_url not in ['METADATA_ONLY', 'UPLOAD_FAILED', 'R2_NOT_CONFIGURED', '', 'N/A']:
                valid_infographics.append(infographic)
        
        if valid_infographics and len(valid_infographics) > 0:
            st.markdown("#### 📸 Safety Infographics")
            
            # Display infographics in card format
            for i, infographic in enumerate(valid_infographics[:6]):  # Show latest 6 valid ones
                with st.container():
                    # Fix column mapping based on actual data structure
                    image_url = infographic.get('File_Name', '')  # URL is in File_Name field
                    submitter_username = infographic.get('Title', 'Unknown')  # Submitter username is in Title field
                    date = infographic.get('Image_URL', 'N/A')  # Date is in Image_URL field
                    
                    # Get full name and rank for the submitter
                    try:
                        submitter_info = sheets_manager.get_user_full_name(submitter_username)
                        submitter_display = submitter_info if submitter_info != submitter_username else submitter_username
                    except:
                        submitter_display = submitter_username
                    
                    # Format date to show only date part
                    try:
                        if len(date.split()) > 1:
                            date_only = date.split()[0]  # Get just the date part
                        else:
                            date_only = date
                    except:
                        date_only = date
                    
                    # Show image with submitter info below - skip entries without valid data
                    if image_url and image_url not in ['METADATA_ONLY', 'UPLOAD_FAILED', 'R2_NOT_CONFIGURED', '', 'N/A']:
                        # Only show entries with valid image URLs
                        try:
                            st.image(image_url, use_container_width=True)
                            st.markdown(f"""
                            <div style="text-align: center; margin-top: 10px;">
                                <p style="margin: 2px 0; color: #666; font-size: 0.9em;"><strong>Uploaded by:</strong> {submitter_display}</p>
                                <p style="margin: 2px 0; color: #666; font-size: 0.9em;">{date_only}</p>
                            </div>
                            """, unsafe_allow_html=True)
                        except Exception as img_error:
                            # Skip invalid entries silently
                            continue
                    else:
                        # Skip entries without valid images (don't show "Metadata only")
                        continue
                    
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
        # Try to get safety pointers data from Google Sheets
        safety_pointers_data = sheets_manager.get_safety_pointers()
        
        if safety_pointers_data and len(safety_pointers_data) > 0:
            st.markdown("#### 📝 Safety Observations & Recommendations")
            
            # Display safety pointers in card format
            for i, pointer in enumerate(safety_pointers_data[:8]):  # Show latest 8
                with st.container():
                    # Fix column mapping based on actual data structure from debug
                    submitter_username = pointer.get('Observation_Date', 'Unknown')  # Username in Observation_Date field
                    obs_date = pointer.get('Observation', 'N/A')  # Date in Observation field
                    observation = pointer.get('Category', 'N/A')  # Observation text in Category field  
                    reflection = pointer.get('Reflection', 'N/A')  # Reflection is correct
                    recommendation = pointer.get('Recommendation', 'N/A')  # Recommendation is correct
                    category = pointer.get('Submitter', 'Safety Observation')  # Category in Submitter field
                    
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
                            
                            # Analyze image with BLIP model
                            with st.spinner("🤖 Analyzing image content with AI..."):
                                from chatbot import MSCSafetyBot
                                bot = MSCSafetyBot()
                                image_analysis = bot.analyze_image_with_blip(image_url)
                                
                                if image_analysis and not image_analysis.startswith(("No ", "Failed", "BLIP", "Request", "Network", "Analysis")):
                                    st.success(f"🔍 AI Analysis: {image_analysis}")
                                    submission_data['ai_analysis'] = image_analysis
                                else:
                                    st.warning(f"⚠️ AI Analysis: {image_analysis}")
                                    submission_data['ai_analysis'] = image_analysis or "Analysis unavailable"
                        else:
                            st.warning(f"⚠️ R2 upload failed: {upload_result['error']}")
                            st.info("📝 Continuing with metadata-only submission...")
                            submission_data['image_url'] = "UPLOAD_FAILED"
                            submission_data['ai_analysis'] = "Upload failed - cannot analyze image"
                    else:
                        submission_data['image_url'] = "METADATA_ONLY"
                        submission_data['ai_analysis'] = "R2 storage not configured - cannot analyze image"
                        st.info("📝 Saving submission metadata to Google Sheets (R2 storage not configured)")
                    
                    # Save to Google Sheets
                    try:
                        # Try to get or create Safety_Infographics worksheet
                        try:
                            safety_sheet = sheets_manager.spreadsheet.worksheet('Safety_Infographics')
                        except:
                            # Create sheet if it doesn't exist
                            safety_sheet = sheets_manager.spreadsheet.add_worksheet(title='Safety_Infographics', rows=1000, cols=11)
                            
                            # Add headers
                            headers = ['Submitter', 'Title', 'Date', 'Original_Filename', 'File_Size', 'Image_URL', 'Optimized_Size', 'Dimensions', 'Tags', 'AI_Analysis']
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
                            '',  # Tags placeholder
                            submission_data.get('ai_analysis', '')  # AI analysis from BLIP
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
                                if submission_data.get('ai_analysis'):
                                    st.write(f"**AI Analysis:** {submission_data['ai_analysis']}")
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
                        except:
                            # Create sheet if it doesn't exist
                            safety_pointers_sheet = sheets_manager.spreadsheet.add_worksheet(title='Safety_Pointers', rows=1000, cols=8)
                            
                            # Add headers
                            headers = ['Submitter', 'Observation_Date', 'Observation', 'Reflection', 'Recommendation', 'Category', 'Submission_Date']
                            safety_pointers_sheet.append_row(headers)
                        
                        # Append the submission data - ensure correct order matching headers
                        row_data = [
                            submission_data['submitter'],          # Submitter
                            submission_data['observation_date'],   # Observation_Date  
                            submission_data['observation'],       # Observation
                            submission_data['reflection'],        # Reflection
                            submission_data['recommendation'],    # Recommendation
                            submission_data['category'],          # Category
                            submission_data['submission_date']    # Submission_Date
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
                
                # Ensure 'Days to Expiry' column is treated as string to avoid Arrow serialization errors
                display_df['Days to Expiry'] = display_df['Days to Expiry'].astype(str)
                
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
            
            # Ensure 'Days to Expiry' column is treated as string to avoid Arrow serialization errors
            table_df['Days to Expiry'] = table_df['Days to Expiry'].astype(str)
            
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

if __name__ == "__main__":
    main()
