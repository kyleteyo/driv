# MSC DRIVr Deployment Guide

## Password Preservation During Updates

### CRITICAL: Before Any Code Upload

1. **Backup your passwords**:
   ```bash
   python password_backup.py
   # Select option 1 to create backup
   ```

2. **Download from production**: 
   - Save your production `credentials.json` file locally
   - This contains all user passwords and custom changes

### After Code Upload

1. **Restore passwords**:
   ```bash
   python password_backup.py
   # Select option 2 to restore from backup
   ```

2. **Or manually replace**:
   - Upload your saved `credentials.json` to overwrite the reset version

### Why Passwords Reset

The app was automatically creating users from Google Sheets data, which overwrote existing passwords. This has been **DISABLED** to prevent future resets.

### Current Status

- User initialization is disabled
- Passwords will no longer reset automatically
- New users must be added manually via admin interface
- Existing passwords are preserved during updates

### Recovery Options

1. **File History**: Check Replit file history for `credentials.json`
2. **Checkpoints**: Use Replit rollback to restore previous state
3. **Git History**: Restore from previous git commits

### Manual User Management

To add new users without affecting existing passwords:
1. Use the admin interface in the app
2. Or manually edit `credentials.json` carefully
3. Never overwrite the entire file during updates