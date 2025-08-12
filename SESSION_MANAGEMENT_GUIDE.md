# Session Management Guide

## Current Implementation

The MSC DRIVr app now includes persistent session management to prevent frequent logouts.

### Features

**✅ 2-Hour Sessions**
- Users stay logged in for 2 hours of inactivity
- Sessions automatically refresh with user activity

**✅ Cross-Tab Persistence**
- Login persists across multiple browser tabs
- Closing and reopening browser maintains session (within 2 hours)

**✅ Automatic Restoration**
- App automatically detects valid sessions on page load
- Users don't need to re-login if session is still valid

**✅ Clean Logout**
- Logout button clears all session data from browser storage
- Prevents session conflicts between different users

### How It Works

1. **Login Process**:
   - User logs in with username/password
   - Session token generated and stored in browser localStorage
   - Login timestamp saved for expiration checking

2. **Session Validation**:
   - On each page load, JavaScript checks for valid session data
   - Validates session hasn't expired (2 hours)
   - Automatically logs user back in if session is valid

3. **Session Storage**:
   - `localStorage.msc_drivr_logged_in`: Login status flag
   - `localStorage.msc_drivr_username`: Username
   - `localStorage.msc_drivr_session_token`: Security token
   - `localStorage.msc_drivr_login_time`: Timestamp for expiration

4. **Security**:
   - Session tokens are hashed with user-specific salt
   - Automatic cleanup of expired sessions
   - Logout clears all browser storage

### Troubleshooting

**Sessions Not Persisting:**
- Check browser allows localStorage
- Ensure browser isn't clearing storage on close
- Verify session hasn't expired (2 hours)

**Frequent Logouts:**
- May indicate browser privacy settings clearing storage
- Check if "Clear cookies on exit" is enabled
- Private/Incognito mode may not persist sessions

**Multiple Users Same Computer:**
- Always use "Logout" button when switching users
- Browser storage is shared across tabs for same domain
- Clear browser data if sessions conflict

### For Developers

Session restoration happens in the `restore_session()` function:
- Checks localStorage for valid session data
- Validates session token and expiration
- Automatically re-authenticates user if valid
- Clears expired session data

The system is designed to be transparent to users while providing robust session persistence for military operational use.