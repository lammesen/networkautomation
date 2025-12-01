# Performance Optimization Guide

Performance optimization strategies and best practices for the webnet application.

## Table of Contents
- [Database Optimization](#database-optimization)
- [Query Optimization](#query-optimization)
- [Caching Strategies](#caching-strategies)
- [Celery Optimization](#celery-optimization)
- [Frontend Optimization](#frontend-optimization)
- [API Optimization](#api-optimization)
- [Monitoring Performance](#monitoring-performance)

## Database Optimization

### Indexes
```python
# Add indexes for frequently queried fields
class Device(models.Model):
    class Meta:
        indexes = [
            models.Index(fields=["customer", "hostname"]),
            models.Index(fields=["vendor"]),
            models.Index(fields=["site"]),
            models.Index(fields=["status"]),
        ]
```

### Connection Pooling
```python
# Use pgBouncer or connection pooler
DATABASE_URL = "postgresql://user:pass@pgbouncer:6432/dbname"
```

### Query Optimization
```python
# Use select_related for ForeignKey
devices = Device.objects.select_related("customer", "credential")

# Use prefetch_related for ManyToMany/Reverse FK
jobs = Job.objects.prefetch_related("logs")

# Combine both
devices = Device.objects.select_related(
    "customer", "credential"
).prefetch_related(
    "config_snapshots"
)
```

## Query Optimization

### Avoid N+1 Queries
```python
# ❌ Bad - N+1 queries
devices = Device.objects.all()
for device in devices:
    print(device.customer.name)  # Queries customer for each device

# ✅ Good - Single query
devices = Device.objects.select_related("customer")
for device in devices:
    print(device.customer.name)  # Customer already loaded
```

### Use values()/values_list()
```python
# When you don't need full model instances
hostnames = Device.objects.values_list("hostname", flat=True)

# For aggregations
vendor_counts = Device.objects.values("vendor").annotate(
    count=Count("id")
)
```

### Limit Querysets
```python
# Use pagination
devices = Device.objects.all()[:50]

# Use iterator() for large querysets
for device in Device.objects.iterator(chunk_size=100):
    process(device)
```

### Exists() vs Count()
```python
# ✅ Good - stops at first match
if Device.objects.filter(hostname="router1").exists():
    pass

# ❌ Bad - counts all matches
if Device.objects.filter(hostname="router1").count() > 0:
    pass
```

## Caching Strategies

### Django Cache Framework
```python
# settings.py
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
    }
}

# Cache view results
from django.views.decorators.cache import cache_page

@cache_page(60 * 15)  # Cache for 15 minutes
def my_view(request):
    pass
```

### Cache API Responses
```python
from django.core.cache import cache

def get_devices(customer_id):
    cache_key = f"devices_{customer_id}"
    devices = cache.get(cache_key)
    if devices is None:
        devices = list(Device.objects.filter(customer_id=customer_id))
        cache.set(cache_key, devices, timeout=300)
    return devices
```

### Cache Invalidation
```python
# Invalidate cache on update
def update_device(device_id):
    device = Device.objects.get(pk=device_id)
    device.save()
    cache.delete(f"devices_{device.customer_id}")
```

## Celery Optimization

### Worker Scaling
```yaml
# Scale workers based on load
spec:
  replicas: 5  # Increase for high load
```

### Task Routing
```python
# Route tasks to specific queues
@shared_task(name="run_commands_job", queue="commands")
def run_commands_job(job_id: int):
    pass

@shared_task(name="config_backup_job", queue="config")
def config_backup_job(job_id: int):
    pass
```

### Result Backend Optimization
```python
# Use Redis for result backend
CELERY_RESULT_BACKEND = "redis://redis:6379/1"

# Set result expiration
CELERY_RESULT_EXPIRES = 3600  # 1 hour
```

### Task Timeouts
```python
# Set appropriate timeouts
@shared_task(name="long_task", time_limit=300, soft_time_limit=240)
def long_task():
    pass
```

## Frontend Optimization

### Static Asset Optimization
```bash
# Build optimized assets
make backend-build-static

# Minify CSS/JS in production
npm run build:prod
```

### HTMX Optimization
```html
<!-- Use hx-indicator for loading states -->
<div hx-get="/devices/" hx-indicator="#loading">
  <div id="loading" class="htmx-indicator">Loading...</div>
</div>

<!-- Debounce search inputs -->
<input hx-get="/devices/"
       hx-trigger="keyup changed delay:500ms">
```

### React Islands
- Only use islands for complex interactivity
- Lazy load island components
- Minimize island bundle size

## API Optimization

### Pagination
```python
# Always paginate large result sets
class DeviceViewSet(CustomerScopedQuerysetMixin, viewsets.ModelViewSet):
    pagination_class = PageNumberPagination
    page_size = 50
```

### Response Compression
```python
# Enable gzip compression
MIDDLEWARE = [
    'django.middleware.gzip.GZipMiddleware',
    # ...
]
```

### Selective Field Loading
```python
# Use only() to limit fields
devices = Device.objects.only("id", "hostname", "mgmt_ip")

# Use defer() to exclude heavy fields
devices = Device.objects.defer("tags", "description")
```

## Monitoring Performance

### Database Query Monitoring
```python
# Enable query logging in development
LOGGING = {
    'loggers': {
        'django.db.backends': {
            'level': 'DEBUG',
        },
    },
}

# Use django-debug-toolbar
```

### Celery Monitoring
```python
# Use Flower for Celery monitoring
# Access at http://localhost:5555
celery -A webnet.core.celery:celery_app flower
```

### Application Metrics
- Response times
- Database query counts
- Celery task execution times
- Error rates
- Queue lengths

## Performance Checklist

### Database
- [ ] Indexes on frequently queried fields
- [ ] Use select_related/prefetch_related
- [ ] Avoid N+1 queries
- [ ] Paginate large result sets
- [ ] Connection pooling configured

### Caching
- [ ] Cache frequently accessed data
- [ ] Cache invalidation strategy
- [ ] Redis configured for caching

### Celery
- [ ] Appropriate worker count
- [ ] Task timeouts set
- [ ] Result backend optimized
- [ ] Task routing configured

### Frontend
- [ ] Static assets optimized
- [ ] HTMX requests debounced
- [ ] Islands minimized
- [ ] Loading indicators shown

### API
- [ ] Pagination enabled
- [ ] Response compression enabled
- [ ] Selective field loading
- [ ] Rate limiting configured

## References

- [Django Performance](https://docs.djangoproject.com/en/stable/topics/performance/)
- [Celery Optimization](https://docs.celeryproject.org/en/stable/userguide/optimizing.html)
