# Two-Factor Authentication (2FA) Implementation

This document describes the two-factor authentication implementation for the webnet network automation platform.

## Overview

The implementation provides TOTP-based (Time-based One-Time Password) two-factor authentication using the `django-otp` library, with support for:

- **TOTP Authentication**: Compatible with Google Authenticator, Authy, Microsoft Authenticator, and other standard TOTP apps
- **Backup Codes**: 10 single-use backup codes for account recovery
- **User Management**: Enable/disable 2FA per user
- **Admin Controls**: Admins can reset 2FA for users
- **Policy Enforcement**: Optional or required 2FA by user

## Features

### 1. TOTP Setup
- QR code enrollment for easy setup
- Manual key entry option for authenticator apps
- Token verification during setup
- Automatic backup code generation

### 2. Login Flow
- Standard username/password authentication
- 2FA verification step if enabled
- Backup code support for recovery
- Session management

### 3. Backup Codes
- 10 single-use codes generated during setup
- Hashed storage for security
- Can be regenerated at any time
- Download and print options

### 4. Management UI
- Enable/disable 2FA from user settings
- Regenerate backup codes
- View 2FA status
- Admin reset capability

## User Workflow

### Enabling 2FA

1. Navigate to **Two-Factor Auth** link in the user menu (bottom of sidebar)
2. Click **Enable Two-Factor Authentication**
3. Scan QR code with authenticator app or enter secret key manually
4. Enter verification code from app to confirm
5. Save backup codes in a secure location
6. 2FA is now enabled

### Logging In with 2FA

1. Enter username and password as normal
2. If 2FA is enabled, redirected to verification page
3. Enter 6-digit code from authenticator app
4. Or use a backup code if authenticator is unavailable
5. Successfully authenticated

### Disabling 2FA

1. Navigate to **Two-Factor Auth** settings
2. Click **Disable 2FA** (if not required)
3. Confirm the action
4. 2FA is disabled

### Using Backup Codes

1. At 2FA verification screen, click **Use backup code instead**
2. Enter one of your saved backup codes
3. Backup code is consumed and cannot be reused
4. Successfully authenticated
5. Consider regenerating backup codes after use

## Admin Features

### Admin Panel

Administrators can manage 2FA for users through the Django admin:

1. Navigate to **Admin** → **Users & Roles**
2. Select a user
3. View 2FA status in the user details
4. Click **Reset 2FA** button to disable 2FA for that user

### Policy Enforcement

Administrators can enforce 2FA requirements:

- **Optional**: Users can choose to enable 2FA (default)
- **Required**: Set `two_factor_required=True` on User model
  - Users must enable 2FA before accessing the system
  - Cannot disable 2FA once required

## Technical Details

### Database Schema

**User Model Extensions**:
```python
class User(AbstractUser):
    # ... existing fields ...
    two_factor_enabled = models.BooleanField(default=False)
    two_factor_required = models.BooleanField(default=False)
    backup_codes = models.JSONField(default=list, blank=True)
```

**TOTP Device** (from django-otp):
- Created and managed by `django_otp.plugins.otp_totp`
- Linked to User via ForeignKey
- Stores TOTP secret key

### Security Considerations

1. **Backup Code Storage**: Backup codes are hashed using Django's password hasher before storage
2. **Single-Use Codes**: Backup codes are removed after successful use
3. **Token Validation**: TOTP tokens have a 30-second window
4. **Session Management**: 2FA verification required per session
5. **Admin Reset**: Audit trail maintained for admin resets

### URLs

- `/login/` - Login with 2FA support
- `/2fa/verify/` - 2FA token verification
- `/2fa/setup/` - Enable and configure 2FA
- `/2fa/qrcode/` - Generate QR code image
- `/2fa/manage/` - Manage 2FA settings
- `/2fa/disable/` - Disable 2FA
- `/2fa/regenerate-codes/` - Regenerate backup codes
- `/2fa/admin/reset/<user_id>/` - Admin reset endpoint

### Dependencies

```toml
dependencies = [
    "django-otp>=1.5.0",
    "qrcode>=7.4.2",
]
```

## Configuration

### Settings

The following settings are configured in `webnet/settings.py`:

```python
INSTALLED_APPS = [
    # ... other apps ...
    "django_otp",
    "django_otp.plugins.otp_totp",
]

MIDDLEWARE = [
    # ... other middleware ...
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django_otp.middleware.OTPMiddleware",  # After auth middleware
]

LOGIN_EXEMPT_PREFIXES = (
    # ... other prefixes ...
    "/2fa/",
)
```

### Migration

Run migrations to create 2FA-related tables:

```bash
python manage.py migrate users
python manage.py migrate otp_totp
```

## Testing

Run 2FA tests:

```bash
pytest backend/webnet/tests/test_two_factor.py -v
```

Test coverage includes:
- Backup code generation and verification
- TOTP device management
- Login flow with 2FA
- Admin reset functionality
- User model extensions

## API Integration

For API authentication with 2FA:

1. **API Keys**: API keys bypass 2FA requirement
2. **JWT Tokens**: Initial JWT token acquisition requires 2FA verification
3. **Session Auth**: Session-based API calls respect 2FA verification status

## Troubleshooting

### User Lost Authenticator Access

1. Admin can reset 2FA from admin panel
2. User can use backup codes if available
3. User re-enables 2FA with new device after reset

### QR Code Not Displaying

1. Ensure `qrcode` library is installed
2. Check `/2fa/qrcode/` endpoint is accessible
3. Verify TOTP device was created in database

### Token Verification Failing

1. Check device time synchronization (TOTP is time-based)
2. Ensure token is being entered within 30-second window
3. Verify TOTP device is confirmed in database

### Backup Codes Not Working

1. Ensure codes are entered in uppercase
2. Check codes haven't been previously used
3. Verify backup codes exist in user's `backup_codes` field

## Future Enhancements

Potential future improvements:

- [ ] WebAuthn/FIDO2 hardware token support
- [ ] SMS/Email backup authentication methods
- [ ] Remember device functionality
- [ ] 2FA enrollment grace period
- [ ] Audit logging for 2FA events
- [ ] Push notification authentication (e.g., Duo)
- [ ] Recovery email verification

## References

- [django-otp Documentation](https://django-otp-official.readthedocs.io/)
- [RFC 6238 - TOTP Specification](https://tools.ietf.org/html/rfc6238)
- [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
