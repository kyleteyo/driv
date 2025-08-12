# MSC DRIVr

## Overview
MSC DRIVr is a Streamlit-based web application for military personnel to track vehicle mileage and monitor currency status, ensuring compliance with operational requirements. It provides a secure, user-friendly interface for logging mileage data, managing user accounts, and offering an admin dashboard for team oversight. The project aims to streamline data management for military vehicle operations, enhance situational awareness regarding personnel currency, and provide tools for fitness tracking and safety reporting.

## User Preferences
Preferred communication style: Simple, everyday language.
UI preferences: Clean admin interface without emojis in headers, focus on essential functions like password resets and username lookup.

## System Architecture
The application features a modular architecture with a clear separation of concerns, built around a Streamlit frontend for rapid development and intuitive UI.

### UI/UX Decisions
- Clean, military-inspired interface with a focus on essential functions.
- Left sidebar navigation with simple text-style links.
- Visual status indicators and color-coded alerts for immediate recognition (e.g., currency status, safety pointer categories).
- Dashboard landing page with module navigation cards for intuitive flow.
- Mobile-responsive design.

### Technical Implementations & Feature Specifications
- **Frontend**: Streamlit for an intuitive web interface, providing dashboards, forms, and data visualization.
- **Authentication**: Simple file-based authentication with SHA256 hashed passwords and session management. Admin accounts have specialized interfaces for user management.
- **Data Storage**: Primarily Google Sheets integration via `gspread` for persistent data storage, leveraging its real-time collaboration capabilities. Includes dedicated User_Management worksheet for persistent user permissions.
- **Business Logic**: Utility functions handle core calculations like 30-day rolling mileage currency, qualification checks, and status formatting.
- **External Storage for Media**: Cloudflare R2 integration for storing safety infographics, including automatic image optimization (resizing, compression). Graceful fallback implemented if R2 not configured.
- **Security**: Hashed passwords, environment variables for sensitive API keys, and protected deletion safeguards for built-in accounts.
- **Performance Optimization**: Multi-layer caching system including Streamlit cache_data, session-level caching, and memory optimization. Balanced cache times (5-15 minutes) for speed vs data freshness. DataFrame optimization and lazy loading for improved responsiveness.
- **Module Features**:
    - **My Mileage**: Tracks 3-month rolling mileage currency with visual status indicators, qualification-based access to vehicles, and secure access with password change functionality.
    - **Safety Portal**: Comprehensive dashboard for submitting and viewing safety infographics and pointers, integrated with Cloudflare R2 for media storage. Displays uploader rank and full name from user qualifications data.
    - **Fitness Tracker**: A system for tracking strength and power fitness, including logging workouts, auto-populating fields based on past performance, and visualizing progress.
- **Admin Features**:
    - **Team Dashboard**: Provides admin users with a comprehensive overview of personnel status, including real-time currency statistics, platoon breakdowns, priority action lists, and search/filter capabilities.
    - **Account Management System**: Allows main admins to modify existing accounts (permissions, passwords, status), with an audit trail and protection for built-in accounts. Accounts are added via Google Sheets tracker data.
    - **Commander Access System**: Simple Google Sheets-based User_Management worksheet that tracks which accounts have commander privileges. Commanders get access to Team Overview to monitor their troops. No interface needed - just edit the sheet directly.

### System Design Choices
- **Modular Architecture**: Clear separation of concerns into `app.py` (main application), `auth.py` (authentication), `sheets_manager.py` (Google Sheets integration), and `utils.py` (business logic).
- **Data Flow**: User authentication -> Session management -> Data retrieval from Google Sheets -> Status calculations -> UI updates.
- **Read-Only Tracker Sheets**: The application only writes to the `Mileage_Logs` worksheet, preserving the integrity of core tracker sheets.
- **Dynamic Content**: Vehicle options and user qualifications are dynamically loaded based on data, ensuring relevance.

## External Dependencies

- **Google Sheets API**: Used for primary data storage, personnel qualifications, mileage logs, fitness tracking, and safety submissions. Configured via service account credentials (JSON keyfile or environment variable).
- **Cloudflare R2**: Integrated for cloud storage of safety infographics.
- **Authentication Files**:
    - `credentials.json`: Stores user credentials with pre-hashed passwords.
    - `service_account.json`: Google API service account credentials (can be replaced by environment variable `GOOGLE_SHEETS_CREDENTIALS`).
- **Environment Variables**: `GOOGLE_SHEETS_CREDENTIALS` (JSON string for service account), `GOOGLE_SHEET_ID` (target spreadsheet identifier).

## Password Management System

- **Password Preservation**: Enhanced authentication system prevents password resets during app updates by safely initializing missing users without overwriting existing passwords.
- **Backup Utility**: `password_backup.py` provides comprehensive backup, restore, and merge capabilities for `credentials.json`.
- **Safe User Initialization**: App automatically adds new users from Google Sheets while preserving all existing user passwords.
- **High-Load Performance**: Smart activation system automatically detects high concurrent usage (50+ users or 200+ requests) and enables protective rate limiting, then automatically disables when load decreases.