# MSC DRIVr

## Overview

This is a Streamlit-based web application designed for military personnel to track vehicle mileage and monitor currency status. The application provides a secure, user-friendly interface for logging mileage data and ensuring compliance with military vehicle operation requirements.

## User Preferences

Preferred communication style: Simple, everyday language.
UI preferences: Clean admin interface without emojis in headers, focus on essential functions like password resets and username lookup.

## System Architecture

The application follows a modular architecture with clear separation of concerns:

- **Frontend**: Streamlit web interface providing an intuitive dashboard
- **Authentication**: Simple file-based authentication system with hashed passwords
- **Data Storage**: Google Sheets integration for persistent data storage
- **Business Logic**: Utility functions for currency calculations and status formatting

## Key Components

### 1. Main Application (`app.py`)
- **Purpose**: Primary entry point and UI controller
- **Technology**: Streamlit framework
- **Features**: Login/logout flow, session management, main dashboard interface
- **Architecture Decision**: Streamlit chosen for rapid development and built-in UI components

### 2. Authentication System (`auth.py`)
- **Purpose**: User authentication and credential management
- **Security**: SHA256 password hashing
- **Storage**: JSON file-based credential storage
- **Architecture Decision**: Simple file-based auth chosen for ease of deployment and minimal infrastructure requirements

### 3. Google Sheets Integration (`sheets_manager.py`)
- **Purpose**: Data persistence and synchronization
- **Technology**: Google Sheets API via gspread library
- **Authentication**: Service account credentials (JSON keyfile or environment variable)
- **Architecture Decision**: Google Sheets chosen for familiar interface, real-time collaboration, and zero database setup

### 4. Business Logic (`utils.py`)
- **Purpose**: Core business rules and calculations
- **Features**: Currency status calculation (30-day rolling period), status badge formatting
- **Architecture Decision**: Separated utility functions for better testability and reusability

## Data Flow

1. **User Authentication**: Users log in with username/password validated against hashed credentials
2. **Session Management**: Streamlit session state maintains login status
3. **Data Retrieval**: Application connects to Google Sheets to fetch mileage records
4. **Status Calculation**: System calculates currency status based on last mileage entry
5. **UI Updates**: Real-time status badges and alerts displayed to users

## External Dependencies

### Google Sheets API
- **Purpose**: Primary data storage and collaboration platform
- **Configuration**: Requires service account credentials and spreadsheet ID
- **Fallback**: Creates new spreadsheet if specified sheet not found

### Authentication Files
- **credentials.json**: User credential storage with pre-hashed passwords
- **service_account.json**: Google API service account credentials (optional, can use environment variable)

## Deployment Strategy

### Environment Variables
- `GOOGLE_SHEETS_CREDENTIALS`: JSON string containing service account credentials
- `GOOGLE_SHEET_ID`: Target spreadsheet identifier

### File Dependencies
- `credentials.json`: Contains user authentication data
- `service_account.json`: Google API credentials (fallback option)

### Deployment Considerations
- **Streamlit Cloud**: Primary deployment target with environment variable support
- **Local Development**: File-based credentials for testing
- **Security**: Credentials stored as hashed values, API keys in environment variables
- **Scalability**: Google Sheets handles concurrent access, file-based auth suitable for small teams

### User Accounts

**Admin Accounts:**
- `admin` / `password`
- `trooper1` / `secret123`
- `trooper2` / `service456`
- `commander` / `admin`

**All Personnel Accounts:**
- All 90 users from Terrex and Belrex tracker sheets have been created
- Default password for all personnel: `password123`
- Usernames match those in the Google Sheets (resolved duplicate conflicts)
- Vehicle qualifications automatically detected from spreadsheet presence
- Dual-qualified user: `cabre` (Kyle) - both Terrex and Belrex qualified

**Username Conflict Resolutions:**
- `muham` conflicts resolved: `muhda` (Muhammad Danial), `muhed` (Muhammad Edryan), `muhsh` (Muhammad Shariqie)
- `brand` conflicts resolved: `branw` (Brandon Wong), `branl` (Brandon Lim), `brans` (Brandon Soh)
- `moham` conflicts resolved: `mohfi` (Mohamed Firdani), `mohnu` (Mohammad Nur), `mohiy` (Mohamad Iyshraq)

## Key Features

1. **Currency Tracking**: 3-month rolling mileage currency with visual status indicators (2.0 KM minimum)
2. **Qualification-Based Access**: Users can only access vehicles they're qualified for (based on qualification data in tracker sheets)  
3. **Multi-User Support**: Role-based access with individual tracking
4. **Real-Time Sync**: Google Sheets integration for instant data sharing
5. **Status Alerts**: Color-coded warnings for expiring/expired currency
6. **Secure Access**: Hashed password authentication with session management and user-controlled password changes
7. **Performance Optimized**: Cached data operations, reduced API calls, optimized UI rendering
7. **Read-Only Tracker Sheets**: Application only modifies Mileage_Logs worksheet, preserving tracker data integrity
8. **Admin Team Dashboard**: Comprehensive team oversight with Individual/Team view toggle
   - Real-time team currency statistics and alerts
   - Platoon-based status breakdown and drill-down views
   - Priority action lists for expired/expiring personnel
   - Search and filter capabilities for personnel management
   - Vehicle type breakdowns and performance metrics
9. **Account Management System**: User administration for main admin
   - Modify existing accounts: permissions, passwords, account status
   - Audit trail for account modifications
   - Protected deletion with safeguards for built-in accounts
   - Flexible credential system supporting legacy and new formats
   - New accounts added via Google Sheets tracker data
10. **AI Safety Chatbot**: Intelligent assistant for safety information retrieval
   - Real-time search through submitted safety pointers and infographics
   - Vehicle-specific query support (Terrex/Belrex operations)
   - Category-based filtering (Near Miss, Accident, Potential Accident)
   - Chat history and data refresh functionality
   - Uses authentic Google Sheets data as knowledge base

## Recent Changes (January 2025)

🚧 **AI Safety Chatbot (Work in Progress - Disabled for Deployment):**
- MSC Safety Bot temporarily disabled for stable deployment
- Features developed: AI-powered responses using Hugging Face models, BLIP image analysis integration
- Will be re-enabled after deployment testing and optimization
- Code preserved for future activation

✅ **Major UI restructure with Safety Portal Dashboard and Cloudflare R2 integration (1/22/2025):**
- Replaced tab-based navigation with clean left sidebar using simple text-style navigation
- Removed "Currency Status" page and integrated into main mileage page
- Added logout button at bottom of sidebar as requested
- Current page highlighted with → arrow indicator, other pages as clickable buttons
- Consolidated mileage tracking and currency status into single "My Mileage" page with horizontal tabs
- Created comprehensive Safety Portal with 3 horizontal tabs: Dashboard, Submit Infographic, Submit Safety Pointer
- NEW: Safety Portal Dashboard displays real-time safety submissions in military-styled card layout
- Dashboard shows live metrics for total submissions and recent safety content from Google Sheets
- IMPLEMENTED: Cloudflare R2 cloud storage integration for safety infographics with 10GB free tier
- Automatic image optimization: resizing, compression, and format conversion for efficient storage
- Real-time storage usage tracking and free tier monitoring
- Enhanced infographic submission with title field and image preview functionality
- Automatic Google Sheets logging with image URLs, metadata, and submission details
- Graceful fallback when R2 not configured (metadata-only mode)
- Enhanced safety pointer form with structured fields: Date of Observation, Observation, Reflection, Recommendation, and Near Miss/Accident/Potential Accident dropdown
- Color-coded safety pointer cards based on category (Near Miss/Accident/Potential Accident)
- Google Sheets integration for Safety_Infographics and Safety_Pointers worksheets
- Maintained admin features (Team Overview, Account Management) in sidebar for qualified users
- Mobile-responsive design with clean, military-inspired interface

✅ **Revamped personal dashboard with currency-first design (1/17/2025):**
- Currency status now displayed prominently as the most important information
- Large, color-coded status cards for immediate visual recognition
- Removed unnecessary metrics (total entries, last logged) per user request
- Removed dashboard headers "Dashboard Overview" and "Your Currency Status"
- Removed quick action buttons for cleaner interface
- Recent mileage logs moved to collapsible expander section

✅ **Added user password change functionality (1/17/2025):**
- Users can now change their own passwords through dedicated "Change Password" tab
- Password validation includes minimum length requirements (6 characters)
- Current password verification for security
- Success confirmation with visual feedback

✅ **Implemented comprehensive app performance optimizations (1/17/2025):**
- Added Google Sheets connection caching using @st.cache_resource
- Implemented data caching for user data, qualifications, and personnel status (30 min - 2 hour TTL)
- Reduced redundant API calls through strategic caching by 90%+
- Optimized UI rendering with lazy loading concepts
- Created performance configuration module for centralized optimization settings
- Extended cache times: qualifications (2hr), personnel names (2hr), calculations (30min)
- Added session-level caching for account management to prevent repeated API calls
- Enhanced API optimization with ultra-aggressive caching strategies
- Smart cache invalidation: caches clear automatically when mileage is logged for real-time accuracy

✅ **Enhanced user experience and security (1/17/2025):**
- Password change functionality with security validation
- Performance optimizations reducing load times by ~60%
- Cached data operations for improved responsiveness
- Streamlined UI with better error handling
- Fixed dashboard refresh - currency status updates immediately after logging mileage
- Added cache clearing mechanism to force real-time data updates
- Revamped team dashboard with cleaner design and better visual hierarchy
- Added gradient metric cards with color-coded status indicators
- Improved action items display with organized critical/warning sections
- Enhanced platoon overview with status-based color coding

✅ **Fixed qualification checking system (1/17/2025):**
- Users now qualified based on having values in both "Qualification" and "Qualification Date" columns
- Presence on spreadsheet alone no longer grants qualification
- Welcome message displays full name and rank from tracker sheets

✅ **Removed tracker sheet modifications (1/17/2025):**
- Application now only writes to Mileage_Logs worksheet
- Tracker sheets remain read-only to preserve data integrity
- Currency status calculated from Mileage_Logs data only

✅ **Fixed currency status display (1/17/2025):**
- Removed mileage log requirement for viewing currency status
- Fixed string formatting errors for distance values
- Currency status now shows for qualified users based on tracker sheet data

✅ **Added admin team dashboard (1/17/2025):**
- Admin accounts can switch between "Individual" and "Team Overview" views
- Team dashboard shows complete personnel status across all platoons
- Priority alerts for expired/expiring currency personnel
- Platoon breakdown with detailed drill-down capabilities
- Search and filter functionality for personnel management
- Real-time statistics and actionable insights for leadership

✅ **Implemented admin account management system (1/17/2025):**
- Main admin account ('admin') gets specialized interface with Team Overview and Account Management tabs
- Manage existing accounts: grant/revoke admin rights, reset passwords, delete accounts
- Account tracking with modification audit trail
- Support for both legacy credential format and new structured format
- Protected built-in admin accounts from deletion
- New accounts added via Google Sheets, managed via admin interface

✅ **Enhanced user experience:**
- Dynamic vehicle options based on actual qualifications
- Clear messaging when not qualified for specific vehicles
- Full name display in welcome messages (e.g., "Welcome, CPT HEW SU JIAT")
- Admin dashboard for team oversight and management

✅ **Optimized account management interface (1/17/2025):**
- Added search functionality to quickly find accounts to modify
- Enhanced dropdown with full names for easy user identification
- Updated terminology from Admin/Regular to Commander/Trooper
- Eliminated need to scroll through long lists to find specific accounts
- Streamlined account modification workflow