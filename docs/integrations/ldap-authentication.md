# LDAP/Active Directory Authentication

webnet supports LDAP and Active Directory authentication, allowing users to log in with their enterprise credentials instead of local accounts. This integration enables centralized identity management, reduces password fatigue, and simplifies user provisioning.

## Features

- **LDAP/AD Authentication**: Authenticate users against LDAP or Active Directory servers
- **Automatic Role Mapping**: Map LDAP/AD groups to webnet roles (viewer, operator, admin)
- **User Attribute Syncing**: Automatically sync user details (first name, last name, email) from directory
- **Customer Assignment**: Assign users to customers/tenants based on LDAP attributes
- **Local Fallback**: Local authentication continues to work when LDAP is unavailable
- **TLS/SSL Support**: Secure connections with TLS/StartTLS
- **Nested Groups**: Support for nested group membership (Active Directory)
- **Automatic User Creation**: Create user accounts on first login

## Configuration

LDAP authentication is configured via environment variables. All settings should be added to your `.env` file.

### Basic Configuration

To enable LDAP authentication:

```bash
# Enable LDAP authentication
LDAP_ENABLED=true

# LDAP server URI (required)
LDAP_SERVER_URI=ldap://ldap.example.com:389
# For LDAPS use: ldaps://ldap.example.com:636

# Bind credentials (leave empty for anonymous bind)
LDAP_BIND_DN=cn=readonly,dc=example,dc=com
LDAP_BIND_PASSWORD=readonly_password

# User search configuration (required)
LDAP_USER_SEARCH_BASE=ou=users,dc=example,dc=com
LDAP_USER_SEARCH_FILTER=(sAMAccountName=%(user)s)
LDAP_USER_SEARCH_SCOPE=SUBTREE
```

### Active Directory Example

```bash
LDAP_ENABLED=true
LDAP_SERVER_URI=ldap://ad.company.com:389
LDAP_BIND_DN=CN=Service Account,OU=Service Accounts,DC=company,DC=com
LDAP_BIND_PASSWORD=service_password

# User search
LDAP_USER_SEARCH_BASE=OU=Users,DC=company,DC=com
LDAP_USER_SEARCH_FILTER=(sAMAccountName=%(user)s)
LDAP_USER_SEARCH_SCOPE=SUBTREE

# Group search
LDAP_GROUP_SEARCH_BASE=OU=Groups,DC=company,DC=com
LDAP_GROUP_SEARCH_FILTER=(objectClass=group)
LDAP_GROUP_TYPE=ActiveDirectory

# Role mapping
LDAP_GROUP_VIEWER=CN=NetOps Viewers,OU=Groups,DC=company,DC=com
LDAP_GROUP_OPERATOR=CN=NetOps Engineers,OU=Groups,DC=company,DC=com
LDAP_GROUP_ADMIN=CN=NetOps Admins,OU=Groups,DC=company,DC=com
```

### OpenLDAP Example

```bash
LDAP_ENABLED=true
LDAP_SERVER_URI=ldap://ldap.example.com:389
LDAP_BIND_DN=cn=readonly,dc=example,dc=com
LDAP_BIND_PASSWORD=readonly_password

# User search
LDAP_USER_SEARCH_BASE=ou=people,dc=example,dc=com
LDAP_USER_SEARCH_FILTER=(uid=%(user)s)
LDAP_USER_SEARCH_SCOPE=SUBTREE

# Group search
LDAP_GROUP_SEARCH_BASE=ou=groups,dc=example,dc=com
LDAP_GROUP_SEARCH_FILTER=(objectClass=groupOfNames)
LDAP_GROUP_TYPE=GroupOfNames

# Role mapping
LDAP_GROUP_VIEWER=cn=netops-viewers,ou=groups,dc=example,dc=com
LDAP_GROUP_OPERATOR=cn=netops-operators,ou=groups,dc=example,dc=com
LDAP_GROUP_ADMIN=cn=netops-admins,ou=groups,dc=example,dc=com
```

## Configuration Reference

### Required Settings

| Variable | Description | Example |
|----------|-------------|---------|
| `LDAP_ENABLED` | Enable LDAP authentication | `true` |
| `LDAP_SERVER_URI` | LDAP server URL | `ldap://ldap.example.com:389` |
| `LDAP_USER_SEARCH_BASE` | Base DN for user searches | `ou=users,dc=example,dc=com` |

### Connection Settings

| Variable | Description | Default |
|----------|-------------|---------|
| `LDAP_START_TLS` | Use StartTLS for encryption | `false` |
| `LDAP_IGNORE_CERT_ERRORS` | Ignore SSL certificate errors (not recommended for production) | `false` |
| `LDAP_BIND_DN` | Bind DN for authentication | (anonymous bind) |
| `LDAP_BIND_PASSWORD` | Password for bind DN | (anonymous bind) |

### User Search Settings

| Variable | Description | Default |
|----------|-------------|---------|
| `LDAP_USER_SEARCH_FILTER` | Filter for user searches | `(sAMAccountName=%(user)s)` |
| `LDAP_USER_SEARCH_SCOPE` | Search scope: BASE, ONELEVEL, or SUBTREE | `SUBTREE` |
| `LDAP_USER_DN_TEMPLATE` | Alternative to user search (e.g., `uid=%(user)s,ou=users,dc=example,dc=com`) | Not set |

### User Attribute Mapping

| Variable | Description | Default |
|----------|-------------|---------|
| `LDAP_ATTR_FIRST_NAME` | LDAP attribute for first name | `givenName` |
| `LDAP_ATTR_LAST_NAME` | LDAP attribute for last name | `sn` |
| `LDAP_ATTR_EMAIL` | LDAP attribute for email | `mail` |
| `LDAP_ATTR_CUSTOMER` | LDAP attribute for customer assignment | Not set |

### Group Settings

| Variable | Description | Default |
|----------|-------------|---------|
| `LDAP_GROUP_SEARCH_BASE` | Base DN for group searches | Not set |
| `LDAP_GROUP_SEARCH_FILTER` | Filter for group searches | `(objectClass=group)` |
| `LDAP_GROUP_TYPE` | Group type: ActiveDirectory or GroupOfNames | `ActiveDirectory` |
| `LDAP_FIND_GROUP_PERMS` | Enable nested group support | `true` |

### Role Mapping

| Variable | Description | Example |
|----------|-------------|---------|
| `LDAP_GROUP_VIEWER` | LDAP groups for viewer role (semicolon-separated) | `cn=viewers,ou=groups,dc=example,dc=com` |
| `LDAP_GROUP_OPERATOR` | LDAP groups for operator role (semicolon-separated) | `cn=operators,ou=groups,dc=example,dc=com` |
| `LDAP_GROUP_ADMIN` | LDAP groups for admin role (semicolon-separated) | `cn=admins,ou=groups,dc=example,dc=com` |

### Other Settings

| Variable | Description | Default |
|----------|-------------|---------|
| `LDAP_ALWAYS_UPDATE_USER` | Update user attributes on every login | `true` |
| `LDAP_USER_CREATE` | Create users automatically on first login | `true` |
| `LDAP_CACHE_TIMEOUT` | Cache timeout for group queries (seconds) | `3600` |
| `LDAP_DEBUG_LEVEL` | LDAP debug level (0-255) | `0` |

## Role Mapping

Users are automatically assigned roles based on their LDAP group membership. The role priority is:

1. **Admin** (highest priority)
2. **Operator**
3. **Viewer** (default)

If a user is a member of multiple groups, they receive the highest priority role.

### Example

```bash
# User in only the viewers group → viewer role
LDAP_GROUP_VIEWER=cn=netops-viewers,ou=groups,dc=example,dc=com

# User in both viewers and operators → operator role
LDAP_GROUP_VIEWER=cn=netops-viewers,ou=groups,dc=example,dc=com
LDAP_GROUP_OPERATOR=cn=netops-operators,ou=groups,dc=example,dc=com

# User in all three groups → admin role
LDAP_GROUP_VIEWER=cn=netops-viewers,ou=groups,dc=example,dc=com
LDAP_GROUP_OPERATOR=cn=netops-operators,ou=groups,dc=example,dc=com
LDAP_GROUP_ADMIN=cn=netops-admins,ou=groups,dc=example,dc=com
```

## Customer Assignment

Users can be automatically assigned to customers/tenants based on an LDAP attribute. This is useful for multi-tenant deployments.

```bash
# Use the 'department' attribute to assign users to customers
LDAP_ATTR_CUSTOMER=department
```

The customer attribute value should match either:
- The customer ID (numeric)
- The customer name (exact match)

For example, if a user has `department: Engineering` in their LDAP attributes, they will be assigned to the "Engineering" customer (if it exists).

## Security Considerations

### TLS/SSL

Always use TLS/SSL in production to protect credentials:

```bash
# Option 1: LDAPS (LDAP over SSL)
LDAP_SERVER_URI=ldaps://ldap.example.com:636

# Option 2: StartTLS (upgrade connection to TLS)
LDAP_SERVER_URI=ldap://ldap.example.com:389
LDAP_START_TLS=true
```

### Certificate Validation

In production, never disable certificate validation:

```bash
# Development only - never use in production!
LDAP_IGNORE_CERT_ERRORS=false
```

If you have custom certificates, ensure they are trusted by the system running webnet.

### Bind Credentials

Use a read-only service account with minimal permissions:

- Only grant read access to user and group attributes
- Use a dedicated service account, not an admin account
- Rotate credentials regularly
- Store credentials securely (e.g., using secrets management)

## Testing LDAP Configuration

### Test with ldapsearch

Before configuring webnet, test your LDAP connection with `ldapsearch`:

```bash
# Test connection and user search
ldapsearch -x -H ldap://ldap.example.com:389 \
  -D "cn=readonly,dc=example,dc=com" \
  -w "readonly_password" \
  -b "ou=users,dc=example,dc=com" \
  "(sAMAccountName=testuser)"

# Test group search
ldapsearch -x -H ldap://ldap.example.com:389 \
  -D "cn=readonly,dc=example,dc=com" \
  -w "readonly_password" \
  -b "ou=groups,dc=example,dc=com" \
  "(objectClass=group)"
```

### Test Authentication

1. Enable LDAP in your `.env` file
2. Restart the webnet backend: `make dev-backend`
3. Try logging in with LDAP credentials
4. Check logs for authentication details:

```bash
# View Django logs
tail -f /path/to/logs/django.log

# Or check console output for errors
```

### Debug Mode

For troubleshooting, enable LDAP debug logging:

```bash
LDAP_DEBUG_LEVEL=1
```

This will output detailed LDAP connection and query information to the logs.

## Troubleshooting

### Issue: "Invalid username or password"

**Possible causes:**
- Incorrect bind credentials
- Wrong user search base or filter
- User not found in LDAP

**Solutions:**
- Verify bind credentials with `ldapsearch`
- Check that `LDAP_USER_SEARCH_BASE` and `LDAP_USER_SEARCH_FILTER` are correct
- Ensure the user exists in the specified search base

### Issue: "Unable to connect to LDAP server"

**Possible causes:**
- Incorrect server URI
- Network/firewall issues
- SSL/TLS certificate errors

**Solutions:**
- Verify server URI and port
- Check firewall rules
- For SSL errors, ensure certificates are trusted or temporarily set `LDAP_IGNORE_CERT_ERRORS=true` (development only)

### Issue: User logs in but has wrong role

**Possible causes:**
- Group mapping misconfigured
- User not in expected groups
- Group search not working

**Solutions:**
- Verify `LDAP_GROUP_*` settings match actual group DNs
- Check user's group membership with `ldapsearch`
- Ensure `LDAP_GROUP_SEARCH_BASE` is correct

### Issue: Local authentication stopped working

**Cause:**
Local authentication should always work as a fallback. If it doesn't, there may be a configuration issue.

**Solution:**
Check that `AUTHENTICATION_BACKENDS` includes both LDAP and local backends:
```python
AUTHENTICATION_BACKENDS = [
    "webnet.core.ldap_backend.WebnetLDAPBackend",
    "django.contrib.auth.backends.ModelBackend",  # Local fallback
]
```

## Best Practices

1. **Use TLS/SSL**: Always encrypt connections in production
2. **Read-only account**: Use a service account with minimal permissions
3. **Test first**: Verify LDAP configuration with `ldapsearch` before configuring webnet
4. **Monitor**: Watch logs during initial setup to catch configuration issues
5. **Document groups**: Maintain documentation of LDAP groups and their corresponding roles
6. **Regular reviews**: Periodically review group memberships and role assignments
7. **Backup local admin**: Keep at least one local admin account for emergencies

## Migration from Local Accounts

If migrating from local accounts to LDAP:

1. **Keep local accounts**: Local authentication continues to work alongside LDAP
2. **Test with a single user**: Configure LDAP and test with one user first
3. **Communicate**: Inform users about the change to LDAP authentication
4. **Emergency access**: Maintain a local admin account for emergencies
5. **Clean up**: After successful migration, consider disabling unused local accounts

## References

- [django-auth-ldap Documentation](https://django-auth-ldap.readthedocs.io/)
- [Active Directory LDAP Syntax](https://docs.microsoft.com/en-us/windows/win32/adsi/search-filter-syntax)
- [OpenLDAP Documentation](https://www.openldap.org/doc/)
