# Two-Factor Authentication (2FA) Implementation

This document describes the two-factor authentication implementation for the webnet network automation platform.

## Overview

The implementation provides comprehensive two-factor authentication using:
- **TOTP (Time-based One-Time Password)**: Compatible with Google Authenticator, Authy, Microsoft Authenticator, and other standard TOTP apps
- **WebAuthn/FIDO2**: Hardware security keys (YubiKey, Windows Hello, Touch ID, etc.)
- **Backup Codes**: Single-use recovery codes

## Features

### 1. TOTP Setup
- QR code enrollment for easy setup
- Manual key entry option for authenticator apps
- Token verification during setup
- Automatic backup code generation

### 2. WebAuthn/FIDO2 Hardware Keys
- Register security keys (YubiKey, Windows Hello, etc.)
- Support for multiple keys per user
- Cross-platform authenticator support
- User-friendly key naming and management
- Key deletion and replacement

### 3. Login Flow
- Standard username/password authentication
- 2FA verification step if enabled
- Choose between TOTP, security key, or backup code
- Session management

### 4. Backup Codes
- 10 single-use codes generated during setup
- Hashed storage for security
- Can be regenerated at any time
- Download and print options

### 5. Management UI
- Enable/disable 2FA from user settings
- Register and manage security keys
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

### Registering a Security Key

1. Navigate to **Two-Factor Auth** settings
2. Scroll to **Security Keys** section
3. Click **Add Security Key**
4. Follow browser prompts to activate your security key (insert YubiKey, use fingerprint, etc.)
5. Enter a name for your key (e.g., "YubiKey 5", "Windows Hello")
6. Key is registered and ready to use

### Using a Security Key

1. At 2FA verification screen, click **Use security key instead**
2. Follow browser prompts to activate your security key
3. Insert and touch YubiKey, use fingerprint, or other method
4. Successfully authenticated

### Managing Security Keys

1. Navigate to **Two-Factor Auth** settings
2. View all registered keys in **Security Keys** section
3. See when each key was added and last used
4. Click **Remove** to delete a key
5. Register multiple keys for redundancy

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

**WebAuthn Credential**:
```python
class WebAuthnCredential(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    credential_id = models.BinaryField(unique=True)
    public_key = models.BinaryField()
    sign_count = models.PositiveIntegerField(default=0)
    aaguid = models.BinaryField()
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
```

### Security Considerations

1. **Backup Code Storage**: Backup codes are hashed using Django's password hasher before storage
2. **Single-Use Codes**: Backup codes are removed after successful use
3. **Token Validation**: TOTP tokens have a 30-second window
4. **WebAuthn Security**: 
   - Public key cryptography (private key never leaves device)
   - Phishing-resistant (origin validation)
   - Replay attack protection (signature counter)
5. **Session Management**: 2FA verification required per session
6. **Admin Reset**: Audit trail maintained for admin resets

### URLs

- `/login/` - Login with 2FA support
- `/2fa/verify/` - 2FA token verification
- `/2fa/setup/` - Enable and configure 2FA
- `/2fa/qrcode/` - Generate QR code image
- `/2fa/manage/` - Manage 2FA settings
- `/2fa/disable/` - Disable 2FA
- `/2fa/regenerate-codes/` - Regenerate backup codes
- `/2fa/admin/reset/<user_id>/` - Admin reset endpoint
- `/webauthn/register/start/` - Start WebAuthn registration
- `/webauthn/register/complete/` - Complete WebAuthn registration
- `/webauthn/auth/start/` - Start WebAuthn authentication
- `/webauthn/auth/complete/` - Complete WebAuthn authentication
- `/webauthn/credential/<id>/delete/` - Delete WebAuthn credential

### Dependencies

```toml
dependencies = [
    "django-otp>=1.5.0",
    "qrcode>=7.4.2",
    "webauthn>=2.1.0",
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
    "/webauthn/",
)

# WebAuthn settings
WEBAUTHN_RP_ID = env("WEBAUTHN_RP_ID", "localhost")
WEBAUTHN_RP_NAME = env("WEBAUTHN_RP_NAME", "webnet Network Automation")
WEBAUTHN_ORIGIN = env("WEBAUTHN_ORIGIN", "http://localhost:8000")
```

### WebAuthn Configuration

For production deployment, configure the following environment variables:

- `WEBAUTHN_RP_ID`: The Relying Party ID (usually your domain, e.g., "example.com")
- `WEBAUTHN_RP_NAME`: Display name for your application
- `WEBAUTHN_ORIGIN`: The full origin URL (e.g., "https://example.com")

**Important**: The RP_ID must match your domain, and ORIGIN must include the full URL with protocol.

### Migration

Run migrations to create 2FA-related tables:

```bash
python manage.py migrate users
python manage.py migrate otp_totp
```

## Browser Compatibility

WebAuthn is supported in:
- Chrome/Edge 67+
- Firefox 60+
- Safari 13+
- Opera 54+

Mobile support:
- iOS Safari 14.5+
- Chrome Android 70+
- Samsung Internet 11.2+

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
- WebAuthn registration and authentication

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

### Security Key Not Working

1. Ensure browser supports WebAuthn (Chrome 67+, Firefox 60+, Safari 13+)
2. Check HTTPS is enabled (WebAuthn requires secure context)
3. Verify WebAuthn settings (RP_ID, ORIGIN) match your domain
4. Try a different security key or browser
5. Check browser console for JavaScript errors

### Security Key Registration Fails

1. Verify RP_ID matches your domain (no protocol, just domain)
2. Ensure ORIGIN includes full URL with protocol
3. Check that security key is not already registered
4. Try removing and reinserting the key

## Future Enhancements

Potential future improvements:

- [x] WebAuthn/FIDO2 hardware token support (COMPLETED)
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
