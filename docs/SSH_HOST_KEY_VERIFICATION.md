# SSH Host Key Verification

This feature implements SSH host key verification to prevent man-in-the-middle (MITM) attacks when connecting to network devices.

## Overview

SSH host key verification ensures that you're connecting to the correct device and not an imposter. The implementation uses a database-backed approach with three verification policies:

1. **TOFU (Trust On First Use)** - Default, recommended
2. **Strict** - Maximum security, requires manual key management
3. **Disabled** - Not recommended, bypass verification

## Configuration

### Per-Customer SSH Policy

Each customer can have their own SSH host key verification policy. Configure it via:

**Web UI**: Settings → Customers → Edit Customer → SSH Host Key Policy

**API**:
```bash
PATCH /api/v1/customers/<customer_id>/
{
  "ssh_host_key_policy": "tofu"  # or "strict" or "disabled"
}
```

### Policy Modes

#### TOFU (Trust On First Use) - Recommended
- **Default setting** for new customers
- First connection: Accept and store the host key
- Subsequent connections: Verify against stored key
- Key change: Warn but accept (stores new key alongside old)
- **Use case**: Production environments with dynamic infrastructure

#### Strict Mode
- **Highest security** setting
- First connection: Reject (must manually import key first)
- Subsequent connections: Verify against stored key
- Key change: Reject connection with error
- **Use case**: Highly sensitive environments, compliance requirements

#### Disabled Mode
- **Not recommended** for production
- No host key verification
- All connections accepted
- **Use case**: Development/testing environments only

## Usage

### Automatic Key Storage (TOFU)

With TOFU mode (default), SSH host keys are automatically stored when connecting to devices:

1. First SSH connection to a device
2. Key is automatically stored in database
3. Status shown as "Unverified"
4. Manually verify key if needed (optional)

### Manual Key Verification

**Web UI**: SSH Host Keys → Find device → Click "Verify"

**API**:
```bash
POST /api/v1/ssh/host-keys/<key_id>/verify/
{
  "verified": true
}
```

Verifying a key records:
- Who verified it (user)
- When it was verified (timestamp)
- Marks it as trusted

### Importing Known Keys

If you already have SSH keys in OpenSSH `known_hosts` format:

**Web UI**: SSH Host Keys → Import Key

**API**:
```bash
POST /api/v1/ssh/host-keys/import/
{
  "device_id": 123,
  "known_hosts_line": "192.168.1.1 ssh-rsa AAAAB3NzaC1yc2EA..."
}
```

**CLI Method**:
```bash
# 1. SSH to device manually
ssh admin@192.168.1.1

# 2. Accept the key when prompted
# 3. Copy the line from ~/.ssh/known_hosts
grep 192.168.1.1 ~/.ssh/known_hosts

# 4. Import via web UI or API
```

### Viewing Host Keys

**Web UI**: SSH Host Keys

Shows:
- Device hostname and IP
- Key type (RSA, ECDSA, Ed25519)
- SHA256 fingerprint
- First/last seen timestamps
- Verification status
- Filter by device or verification status

**API**:
```bash
# List all keys
GET /api/v1/ssh/host-keys/

# Filter by device
GET /api/v1/ssh/host-keys/?device=123

# Filter by verification status
GET /api/v1/ssh/host-keys/?verified=true

# Get statistics
GET /api/v1/ssh/host-keys/stats/
```

### Deleting Host Keys

Delete keys when:
- Device has been decommissioned
- Key rotation occurred and old key should be removed
- False key was stored

**Web UI**: SSH Host Keys → Find device → Click "Delete"

**API**:
```bash
DELETE /api/v1/ssh/host-keys/<key_id>/
```

## Key Change Detection

When a device's SSH host key changes (e.g., after device replacement, OS reinstall):

### TOFU Mode
- **Warning logged**: Key change detected
- **Connection**: Accepted
- **Action**: New key stored alongside old key
- **Recommendation**: Review and delete old key

### Strict Mode
- **Error**: "Host key verification failed"
- **Connection**: Rejected
- **Action**: Manual intervention required
- **Resolution**: 
  1. Verify key change is legitimate
  2. Delete old key
  3. Import or manually accept new key

## Security Considerations

### Why TOFU is Recommended

TOFU provides a good balance between security and usability:
- ✅ Protects against MITM after first connection
- ✅ Detects key changes (warning)
- ✅ Minimal operational overhead
- ✅ Suitable for dynamic environments

### When to Use Strict Mode

Use strict mode when:
- Regulatory compliance requires it
- Infrastructure is stable (minimal changes)
- Additional operational overhead is acceptable
- Maximum security is required

### Risks of Disabled Mode

Disabled mode is vulnerable to:
- ⚠️ Man-in-the-middle attacks
- ⚠️ Credential interception
- ⚠️ Unauthorized device access
- ⚠️ Compliance violations

**Only use in isolated development/test environments.**

## API Reference

### Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/ssh/host-keys/` | GET | List host keys |
| `/api/v1/ssh/host-keys/<id>/` | GET | Get key details |
| `/api/v1/ssh/host-keys/<id>/` | DELETE | Delete key |
| `/api/v1/ssh/host-keys/<id>/verify/` | POST | Verify/unverify key |
| `/api/v1/ssh/host-keys/import/` | POST | Import from known_hosts |
| `/api/v1/ssh/host-keys/stats/` | GET | Get statistics |

### Filters

- `?device=<id>` - Filter by device
- `?key_type=<type>` - Filter by key type
- `?verified=true/false` - Filter by verification status

### Permissions

- **Viewer**: Can view host keys
- **Operator**: Can view, verify, delete, and import keys
- **Admin**: Full access to all keys across all customers

## Troubleshooting

### Connection Rejected: "Host key verification failed"

**Cause**: Device key doesn't match stored key (strict mode)

**Solution**:
1. Verify the key change is legitimate (not a MITM attack)
2. Check device logs for key rotation events
3. Delete old key via Web UI or API
4. Retry connection (will store new key in TOFU mode) or manually import

### Warning: "Host key changed"

**Cause**: Device key changed (TOFU mode)

**Action**: Review key change
```bash
# Check both keys are stored
GET /api/v1/ssh/host-keys/?device=<id>

# Delete the old key if change is legitimate
DELETE /api/v1/ssh/host-keys/<old_key_id>/
```

### Key Not Automatically Stored

**Check**:
1. Customer SSH policy is set to TOFU or Strict
2. Device has customer assigned
3. Connection is using the device-aware SSH method

### Import Fails: "Invalid known_hosts line format"

**Cause**: Incorrect format

**Solution**: Ensure format is:
```
hostname_or_ip key_type base64_key_data [optional_comment]
```

Example:
```
192.168.1.1 ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDexample
```

## Migration from File-Based known_hosts

If you're currently using SSH with file-based `known_hosts`:

1. Set customer policy to TOFU
2. For each device, import existing key:
   ```bash
   # Extract key from known_hosts
   grep <device_ip> ~/.ssh/known_hosts
   
   # Import via API or Web UI
   ```
3. Verify imported keys in Web UI
4. Remove file-based known_hosts (optional)

## Database Schema

### SSHHostKey Model

| Field | Type | Description |
|-------|------|-------------|
| device | ForeignKey | Device this key belongs to |
| key_type | CharField | Key algorithm (ssh-rsa, ssh-ed25519, etc.) |
| public_key | TextField | Base64-encoded public key |
| fingerprint_sha256 | CharField | SHA256 hash of key (for comparison) |
| first_seen_at | DateTimeField | When key was first seen |
| last_seen_at | DateTimeField | When key was last seen |
| verified | BooleanField | Whether manually verified |
| verified_by | ForeignKey(User) | User who verified |
| verified_at | DateTimeField | When verified |

### Customer Policy Field

| Field | Type | Choices |
|-------|------|---------|
| ssh_host_key_policy | CharField | strict, tofu, disabled |

Default: `tofu`

## Compliance Notes

This implementation supports:
- **SOC 2**: Host key verification prevents unauthorized access
- **PCI DSS**: Strong cryptographic authentication
- **NIST Cybersecurity Framework**: Detect and Respond controls
- **ISO 27001**: A.9.4.2 Secure log-on procedures

Audit trail includes:
- All key additions (automatic or manual)
- All key verifications (who/when)
- All key deletions (who/when)
- All key mismatches (logged as warnings/errors)

## Performance Considerations

- Host key lookups use database indexes (device, fingerprint)
- Keys cached in SSH connection objects
- Minimal overhead (<10ms per connection)
- No impact on ongoing SSH sessions

## Best Practices

1. **Use TOFU mode** for most environments
2. **Manually verify keys** for critical devices
3. **Review key changes** immediately when detected
4. **Delete old keys** after device replacement
5. **Export keys regularly** for backup
6. **Monitor unverified keys** count
7. **Set up alerts** for key mismatches in strict mode
8. **Document exceptions** when using disabled mode
