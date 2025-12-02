# Security Best Practices

Security guidelines and best practices for the webnet application.

## Table of Contents
- [Authentication](#authentication)
- [Authorization](#authorization)
- [Credential Storage](#credential-storage)
- [API Security](#api-security)
- [Tenant Isolation](#tenant-isolation)
- [Input Validation](#input-validation)
- [Secrets Management](#secrets-management)
- [Network Security](#network-security)
- [Security Checklist](#security-checklist)

## Authentication

### Local Authentication

#### JWT Tokens
- Access tokens: 30-minute expiration
- Refresh tokens: 7-day expiration
- Tokens stored client-side (localStorage)
- Stateless authentication (no server-side session)

#### Password Security
```python
# Passwords hashed with Django's PBKDF2
# Minimum password requirements enforced by Django
```

### LDAP/Active Directory Authentication

webnet supports enterprise authentication via LDAP and Active Directory:

- Authenticate users against centralized directory services
- Automatic role mapping based on LDAP groups
- User attribute syncing (first name, last name, email)
- Customer/tenant assignment via LDAP attributes
- Local authentication fallback when LDAP is unavailable

See [LDAP Authentication Documentation](integrations/ldap-authentication.md) for configuration details.

### API Keys
- API keys hashed with SHA256
- Only key prefix stored for display
- Expiration dates supported
- Scope-based permissions

### Rate Limiting
```python
# Login endpoint rate limited
class LoginRateThrottle(AnonRateThrottle):
    rate = "5/minute"
```

## Authorization

### Role-Based Access Control (RBAC)
- **viewer**: Read-only access
- **operator**: Read + create jobs/actions
- **admin**: Full access

### Permission Enforcement
```python
# All viewsets use RolePermission
permission_classes = [IsAuthenticated, RolePermission]

# Object-level customer checks
permission_classes = [
    IsAuthenticated,
    RolePermission,
    ObjectCustomerPermission
]
```

### Customer Scoping
All queries automatically filtered by customer:
```python
class DeviceViewSet(CustomerScopedQuerysetMixin, viewsets.ModelViewSet):
    customer_field = "customer_id"
    # Non-admins only see their customers' devices
```

## Credential Storage

### Encryption at Rest
```python
# Credentials encrypted with Fernet (symmetric encryption)
# ENCRYPTION_KEY required in environment
# Passwords never stored in plaintext
```

### Encryption Implementation
```python
from webnet.core.crypto import encrypt_text, decrypt_text

# Automatic encryption on save
credential.password = "plaintext"  # Automatically encrypted
credential.password  # Returns decrypted value
```

### Key Management
- `ENCRYPTION_KEY` must be set in environment
- Key rotation requires re-encryption of all credentials
- Store key securely (secrets manager, not in code)

## API Security

### CSRF Protection
```python
# HTMX forms include CSRF token
{% csrf_token %}

# AJAX requests include CSRF header
hx-headers='{"X-CSRFToken": "{{ csrf_token }}"}'
```

### CORS Configuration
```python
# Production: restrict origins
CORS_ALLOWED_ORIGINS = [
    "https://example.com",
    "https://www.example.com"
]

# Development: allow localhost
CORS_ALLOWED_ORIGINS = [
    "http://localhost:8000",
    "http://127.0.0.1:8000"
]
```

### Input Validation
```python
# All inputs validated via DRF serializers
serializer = DeviceSerializer(data=request.data)
serializer.is_valid(raise_exception=True)

# Custom validation in serializers
def validate_hostname(self, value):
    # Validation logic
    return value
```

## Tenant Isolation

### Query Scoping
```python
# All viewsets use CustomerScopedQuerysetMixin
class DeviceViewSet(CustomerScopedQuerysetMixin, viewsets.ModelViewSet):
    customer_field = "customer_id"
    # Automatically filters by user's customers
```

### Object-Level Checks
```python
# ObjectCustomerPermission validates customer access
permission_classes = [
    IsAuthenticated,
    RolePermission,
    ObjectCustomerPermission
]
```

### Testing Isolation
```python
# Test tenant isolation
def test_cannot_access_other_customer_device(operator_user, device2):
    client = APIClient()
    client.force_authenticate(user=operator_user)
    response = client.get(f"/api/v1/devices/{device2.id}/")
    assert response.status_code in [403, 404]
```

## Input Validation

### Serializer Validation
```python
class DeviceSerializer(serializers.ModelSerializer):
    def validate_hostname(self, value):
        # Validate format
        if not re.match(r'^[a-zA-Z0-9-]+$', value):
            raise serializers.ValidationError("Invalid hostname format")
        return value
    
    def validate(self, data):
        # Cross-field validation
        if data.get("vendor") == "cisco" and not data.get("platform"):
            raise serializers.ValidationError("Platform required")
        return data
```

### SQL Injection Prevention
- Use Django ORM (parameterized queries)
- Never use raw SQL with user input
- Use `extra()` and `raw()` cautiously

### XSS Prevention
- Django templates auto-escape by default
- Use `|safe` filter only when necessary
- Validate and sanitize user input

## Secrets Management

### Environment Variables
```bash
# Never commit secrets to git
# Use environment variables or secrets manager
SECRET_KEY=<random-string>
ENCRYPTION_KEY=<fernet-key>
DATABASE_URL=<connection-string>
```

### Kubernetes Secrets
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: webnet-secrets
type: Opaque
stringData:
  SECRET_KEY: "<secret>"
  ENCRYPTION_KEY: "<key>"
```

### Production Recommendations
- Use HashiCorp Vault or AWS Secrets Manager
- Rotate keys regularly
- Never log secrets
- Use separate secrets per environment

## Network Security

### HTTPS/TLS
- Always use HTTPS in production
- Configure TLS termination at reverse proxy
- Use strong cipher suites
- Enable HSTS headers

### Firewall Rules
- Restrict access to management network
- Limit database access to application servers
- Use network segmentation

### Device Credentials
- Credentials never exposed to frontend
- API returns credential references only
- Use least-privilege credentials on devices

## Security Checklist

### Development
- [ ] All viewsets use tenant scoping
- [ ] All endpoints require authentication
- [ ] Input validation on all user inputs
- [ ] CSRF protection enabled
- [ ] CORS configured correctly
- [ ] Secrets not committed to git
- [ ] Dependencies kept up to date

### Production
- [ ] DEBUG=false
- [ ] Strong SECRET_KEY generated
- [ ] ENCRYPTION_KEY set and secure
- [ ] HTTPS/TLS configured
- [ ] CORS origins restricted
- [ ] Rate limiting enabled
- [ ] Database credentials secure
- [ ] Regular security updates
- [ ] Log monitoring enabled
- [ ] Backup encryption enabled

### Operational
- [ ] Regular security audits
- [ ] Penetration testing
- [ ] Incident response plan
- [ ] Security training for team
- [ ] Access logs reviewed
- [ ] Failed login attempts monitored

## Common Vulnerabilities

### ❌ Don't Do This
```python
# Expose credentials
class CredentialSerializer(serializers.ModelSerializer):
    password = serializers.CharField()  # Should be write_only=True

# Skip tenant scoping
class DeviceViewSet(viewsets.ModelViewSet):
    # Missing CustomerScopedQuerysetMixin

# Raw SQL with user input
Device.objects.extra(where=["hostname = '%s'" % user_input])

# Disable CSRF
@csrf_exempt
def my_view(request):
    pass
```

### ✅ Do This Instead
```python
# Write-only password field
password = serializers.CharField(write_only=True)

# Always scope by customer
class DeviceViewSet(CustomerScopedQuerysetMixin, viewsets.ModelViewSet):
    customer_field = "customer_id"

# Use ORM
Device.objects.filter(hostname=user_input)

# CSRF enabled by default
# Include token in forms
```

## References

- [Multi-Tenancy Patterns](./multi-tenancy.md)
- [API Development Guide](./api-development.md)
- [Django Security](https://docs.djangoproject.com/en/stable/topics/security/)
