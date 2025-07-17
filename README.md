# Military Vehicle Mileage Tracker

A Streamlit web application designed for military personnel to track vehicle mileage and monitor currency status across different vehicle platforms.

## Features

- **Currency Tracking**: 3-month rolling mileage currency with visual status indicators (2.0 KM minimum)
- **Qualification-Based Access**: Users can only access vehicles they're qualified for
- **Multi-User Support**: Role-based access with individual tracking
- **Real-Time Sync**: Google Sheets integration for instant data sharing
- **Admin Team Dashboard**: Comprehensive team oversight with platoon breakdowns
- **Account Management**: User administration for main admin accounts

## Deployment on Streamlit Community Cloud

1. **Requirements**: Rename `streamlit_requirements.txt` to `requirements.txt`
2. **Environment Variables**: Set `GOOGLE_SHEETS_CREDENTIALS` in Streamlit Cloud secrets
3. **Google Sheets**: Ensure your service account has access to the spreadsheet

## Configuration

The application requires:
- Google Sheets API credentials
- Access to Terrex and Belrex tracker spreadsheets
- User credentials file for authentication

## Usage

- **Regular Users**: Log mileage entries and view currency status
- **Admin Users**: Access team overview and account management
- **Main Admin**: Complete system administration capabilities

## Security

- SHA256 password hashing
- Role-based access control
- Protected built-in admin accounts
- Read-only tracker sheet access