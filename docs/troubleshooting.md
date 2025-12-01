# Troubleshooting Guide

Common issues and solutions for the webnet application.

## Table of Contents
- [Database Issues](#database-issues)
- [Authentication Issues](#authentication-issues)
- [Tenant Scoping Issues](#tenant-scoping-issues)
- [Celery Issues](#celery-issues)
- [WebSocket Issues](#websocket-issues)
- [HTMX Issues](#htmx-issues)
- [Static Assets Issues](#static-assets-issues)
- [Deployment Issues](#deployment-issues)

## Database Issues

### Migration Errors
```bash
# Reset migrations (development only)
python manage.py migrate --fake-initial

# Check migration status
python manage.py showmigrations

# Rollback migration
python manage.py migrate app_name previous_migration
```

### Connection Errors
```bash
# Check database connection
python manage.py dbshell

# Verify DATABASE_URL
echo $DATABASE_URL

# Test connection
python -c "from django.db import connection; connection.ensure_connection()"
```

### Query Performance
```python
# Enable query logging
LOGGING = {
    'loggers': {
        'django.db.backends': {
            'level': 'DEBUG',
        },
    },
}

# Use django-debug-toolbar to inspect queries
```

## Authentication Issues

### JWT Token Expired
```python
# Refresh token
POST /api/v1/auth/refresh
{
    "refresh": "<refresh_token>"
}
```

### Invalid Credentials
```bash
# Check user exists
python manage.py shell
>>> from webnet.users.models import User
>>> User.objects.get(username="admin")

# Reset password
python manage.py changepassword <username>
```

### API Key Not Working
```python
# Verify API key
python manage.py shell
>>> from webnet.users.models import APIKey
>>> key = APIKey.objects.get(key_hash="...")
>>> print(key.is_active, key.expires_at)
```

## Tenant Scoping Issues

### Users See Wrong Data
```python
# Check customer assignments
python manage.py shell
>>> user = User.objects.get(username="operator")
>>> print(user.customers.all())
>>> print(user.role)

# Verify viewset uses CustomerScopedQuerysetMixin
# Check customer_field is set correctly
```

### Cross-Tenant Access
```python
# Test tenant isolation
def test_tenant_isolation():
    client = APIClient()
    client.force_authenticate(user=operator_user)
    response = client.get("/api/v1/devices/")
    # Should only see operator_user's customer devices
```

### Admin Sees No Data
```python
# Verify admin role
user = User.objects.get(username="admin")
assert user.role == "admin"

# Admin should see all customers
# If not, check CustomerScopedQuerysetMixin logic
```

## Celery Issues

### Tasks Not Executing
```bash
# Check worker is running
kubectl logs deployment/backend-worker

# Check Redis connection
redis-cli ping

# Verify CELERY_BROKER_URL
echo $CELERY_BROKER_URL

# Check task registration
celery -A webnet.core.celery:celery_app inspect registered
```

### Tasks Stuck in Queue
```bash
# Check queue length
celery -A webnet.core.celery:celery_app inspect active

# Purge queue (careful!)
celery -A webnet.core.celery:celery_app purge

# Restart workers
kubectl rollout restart deployment/backend-worker
```

### Task Failures
```python
# Check job logs
job = Job.objects.get(pk=job_id)
for log in job.logs.all():
    print(f"{log.level}: {log.message}")

# Check Celery logs
kubectl logs deployment/backend-worker | grep ERROR
```

## WebSocket Issues

### Connection Fails
```javascript
// Check WebSocket URL
const ws = new WebSocket('ws://localhost:8000/ws/jobs/1/');

// Check authentication
// WebSocket requires authenticated user

// Check ASGI server (Daphne)
// runserver doesn't support WebSockets
```

### Messages Not Received
```python
# Verify consumer is registered
# Check routing.py
from webnet.api.consumers import JobLogsConsumer

# Check channel layer
from channels.layers import get_channel_layer
channel_layer = get_channel_layer()
```

### Connection Drops
```python
# Check WebSocket timeout settings
# Increase timeout if needed
# Check network connectivity
```

## HTMX Issues

### Partials Not Loading
```html
<!-- Check hx-target exists -->
<div id="target"></div>
<div hx-get="/devices/" hx-target="#target"></div>

<!-- Check response format -->
<!-- HTMX expects HTML, not JSON -->
```

### Forms Not Submitting
```html
<!-- Check CSRF token -->
<form hx-post="/devices/create/">
  {% csrf_token %}
</form>

<!-- Or use headers -->
<div hx-post="/api/devices/"
     hx-headers='{"X-CSRFToken": "{{ csrf_token }}"}'>
</div>
```

### Swaps Not Working
```html
<!-- Check hx-swap attribute -->
<div hx-get="/devices/" hx-swap="innerHTML"></div>

<!-- Verify target element exists -->
<!-- Check browser console for errors -->
```

## Static Assets Issues

### CSS Not Loading
```bash
# Rebuild CSS
make backend-build-css

# Check collectstatic
python manage.py collectstatic --noinput

# Verify STATIC_URL in settings
```

### JavaScript Not Loading
```bash
# Rebuild JavaScript
make backend-build-js

# Check islands.tsx registration
# Verify component exported correctly
```

### Assets 404
```python
# Check STATIC_ROOT
STATIC_ROOT = "/app/staticfiles"

# Verify collectstatic ran
ls /app/staticfiles/

# Check STATIC_URL
STATIC_URL = "/static/"
```

## Deployment Issues

### Pod Not Starting
```bash
# Check pod status
kubectl get pods
kubectl describe pod <pod-name>

# Check logs
kubectl logs <pod-name>

# Check environment variables
kubectl exec <pod-name> -- env | grep SECRET_KEY
```

### Database Connection Fails
```bash
# Verify DATABASE_URL
kubectl exec deployment/backend -- env | grep DATABASE_URL

# Test connection
kubectl exec deployment/backend -- python manage.py dbshell

# Check PostgreSQL pod
kubectl logs deployment/postgres
```

### Image Build Fails
```bash
# Check Dockerfile syntax
docker build -f deploy/Dockerfile.backend .

# Check dependencies
pip install -e backend/

# Verify Node.js version
node --version
```

## Common Error Messages

### "ENCRYPTION_KEY is required"
```bash
# Set ENCRYPTION_KEY in environment
export ENCRYPTION_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

# Or in Kubernetes secrets
kubectl create secret generic webnet-secrets \
  --from-literal=ENCRYPTION_KEY="<key>"
```

### "No devices matched targets"
```python
# Check inventory building
from webnet.automation import build_inventory
inventory = build_inventory(targets, customer_id=customer_id)
print(len(inventory.hosts))  # Should be > 0

# Verify devices are enabled
Device.objects.filter(enabled=True).count()
```

### "Customer access required"
```python
# Check user has customer access
from webnet.api.permissions import user_has_customer_access
user_has_customer_access(user, customer_id)

# Verify customer assignment
user.customers.filter(id=customer_id).exists()
```

## Debugging Tips

### Enable Debug Mode
```python
# settings.py (development only!)
DEBUG = True

# Check error pages
# Django shows detailed error pages in debug mode
```

### Check Logs
```bash
# Application logs
kubectl logs -f deployment/backend

# Worker logs
kubectl logs -f deployment/backend-worker

# Database logs
kubectl logs -f deployment/postgres
```

### Django Shell
```bash
# Interactive shell
python manage.py shell

# Test queries
>>> from webnet.devices.models import Device
>>> Device.objects.count()
>>> Device.objects.filter(customer_id=1).count()
```

### Test API Endpoints
```bash
# With curl
curl -H "Authorization: Bearer <token>" http://localhost:8000/api/v1/devices/

# With httpie
http GET http://localhost:8000/api/v1/devices/ Authorization:"Bearer <token>"
```

## Getting Help

1. Check logs first
2. Verify environment variables
3. Test in development environment
4. Check documentation
5. Review recent changes
6. Ask team for help

## References

- [Getting Started](./getting-started.md)
- [Architecture](./architecture.md)
- [Multi-Tenancy Patterns](./multi-tenancy.md)
