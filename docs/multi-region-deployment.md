# Multi-Region Deployment Guide

This guide explains how to configure and use multi-region deployment support for distributed network automation.

## Overview

Multi-region deployment allows you to:
- Deploy Celery workers in different geographic locations
- Route automation jobs to workers closest to target devices
- Reduce latency to network devices
- Improve reliability with automatic failover
- Scale horizontally across regions

## Architecture

### Components

1. **Region Model**: Defines geographic or logical regions with:
   - Name and unique identifier
   - Optional API endpoint URL
   - Worker pool configuration
   - Health status and monitoring
   - Priority for failover

2. **Regional Workers**: Celery workers listening to region-specific queues

3. **Job Routing**: Automatic routing based on device region assignment

4. **Health Monitoring**: Track region health and enable automatic failover

## Configuration

### 1. Create Regions

Use the API or Django admin to create regions:

```bash
curl -X POST http://localhost:8000/api/v1/regions/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "customer": 1,
    "name": "US East",
    "identifier": "us-east-1",
    "priority": 100,
    "enabled": true,
    "description": "US East Coast datacenter"
  }'
```

**Region Fields:**
- `name`: Human-readable name (e.g., "US East", "Europe West")
- `identifier`: Slug identifier for queue naming (e.g., "us-east-1", "eu-west-1")
- `priority`: Higher values are preferred for routing (default: 100)
- `enabled`: Whether region is active for job routing
- `health_status`: Current health (healthy, degraded, offline)
- `api_endpoint`: Optional URL for distributed API (future use)
- `worker_pool_config`: JSON configuration for worker settings

### 2. Assign Devices to Regions

Update devices to assign them to regions:

```bash
curl -X PATCH http://localhost:8000/api/v1/devices/123/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "region": 1
  }'
```

**Best Practices:**
- Assign devices based on physical location or network proximity
- Group devices in the same datacenter/region together
- Consider network latency and connectivity

### 3. Deploy Regional Workers

Start Celery workers with region-specific queues:

#### Central Worker (Fallback)
```bash
celery -A webnet.core.celery:celery_app worker \
  -Q celery \
  -n central-worker@%h \
  -l info
```

#### US East Worker
```bash
celery -A webnet.core.celery:celery_app worker \
  -Q region_us-east-1,celery \
  -n us-east-worker@%h \
  -l info
```

#### US West Worker
```bash
celery -A webnet.core.celery:celery_app worker \
  -Q region_us-west-1,celery \
  -n us-west-worker@%h \
  -l info
```

#### Europe West Worker
```bash
celery -A webnet.core.celery:celery_app worker \
  -Q region_eu-west-1,celery \
  -n eu-west-worker@%h \
  -l info
```

**Note:** 
- Queue names follow the pattern `region_{identifier}`
- Always include the `celery` queue for fallback jobs
- Use `-n` to give workers unique names

### 4. Docker/Kubernetes Deployment

For containerized deployments, create separate worker deployments per region:

**Example k8s deployment:**

```yaml
# backend-worker-us-east.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend-worker-us-east
spec:
  replicas: 2
  template:
    spec:
      containers:
      - name: worker
        image: networkautomation/backend:latest
        command:
          - celery
          - -A
          - webnet.core.celery:celery_app
          - worker
          - -Q
          - region_us-east-1,celery
          - -n
          - us-east-worker@%h
          - -l
          - info
        env:
          - name: DATABASE_URL
            valueFrom:
              secretKeyRef:
                name: backend-secrets
                key: database-url
          - name: CELERY_BROKER_URL
            value: "redis://redis:6379/0"
```

## Job Routing

Jobs are automatically routed to the appropriate region based on target devices:

### Routing Logic

1. **Target Device Analysis**: When a job is created, the system analyzes target devices
2. **Region Selection**: 
   - If devices have assigned regions, select the highest priority available region
   - If multiple regions match, choose the highest priority one
   - If selected region is offline, fall back to default queue
3. **Queue Assignment**: Job is dispatched to region-specific queue
4. **Worker Execution**: Regional worker picks up and executes the job

### Examples

```python
# Job targeting devices in US East will route to region_us-east-1 queue
job = service.create_job(
    job_type="run_commands",
    user=user,
    customer=customer,
    target_summary={"filters": {"site": "us-east-datacenter"}},
    payload={"commands": ["show version"]},
)
```

### Fallback Scenarios

Jobs fall back to the default queue when:
- Target devices have no region assignment
- Selected region is offline (health_status = "offline")
- Selected region is disabled (enabled = False)
- No region workers are available

## Health Monitoring

### Update Region Health

Use the API to update region health status:

```bash
curl -X POST http://localhost:8000/api/v1/regions/1/update_health/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "health_status": "degraded",
    "message": "High worker load detected"
  }'
```

**Health Statuses:**
- `healthy`: Region is operating normally
- `degraded`: Region is operational but experiencing issues
- `offline`: Region is unavailable, jobs will failover

### Automated Health Checks

Implement health checks in your deployment:

```python
from webnet.core.models import Region
from django.utils import timezone

def check_region_health(region):
    """Example health check function."""
    try:
        # Check worker availability, latency, etc.
        if worker_available and latency_ok:
            region.update_health_status(Region.STATUS_HEALTHY)
        elif worker_available:
            region.update_health_status(
                Region.STATUS_DEGRADED, 
                "High latency detected"
            )
        else:
            region.update_health_status(
                Region.STATUS_OFFLINE, 
                "Workers unavailable"
            )
    except Exception as e:
        region.update_health_status(Region.STATUS_OFFLINE, str(e))
```

Schedule health checks with Celery Beat:

```python
from celery import shared_task

@shared_task
def monitor_region_health():
    """Periodic task to monitor all regions."""
    from webnet.core.models import Region
    
    for region in Region.objects.filter(enabled=True):
        check_region_health(region)
```

## Monitoring and Observability

### View Region Statistics

Get region information via API:

```bash
# List all regions
curl http://localhost:8000/api/v1/regions/ \
  -H "Authorization: Bearer YOUR_TOKEN"

# Get specific region
curl http://localhost:8000/api/v1/regions/1/ \
  -H "Authorization: Bearer YOUR_TOKEN"

# Get jobs for a region
curl http://localhost:8000/api/v1/regions/1/jobs/ \
  -H "Authorization: Bearer YOUR_TOKEN"

# Get devices in a region
curl http://localhost:8000/api/v1/regions/1/devices/ \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Celery Monitoring

Monitor regional queues:

```bash
# Check queue lengths
celery -A webnet.core.celery:celery_app inspect active_queues

# View active tasks
celery -A webnet.core.celery:celery_app inspect active

# View worker statistics
celery -A webnet.core.celery:celery_app inspect stats
```

## Best Practices

### 1. Region Design
- Create regions based on physical datacenter locations
- Consider network boundaries and latency zones
- Use descriptive identifiers (e.g., "us-east-1", "eu-west-1")

### 2. Priority Assignment
- Assign higher priority to primary/production regions
- Use lower priority for DR/backup regions
- Adjust priorities based on capacity and performance

### 3. Device Assignment
- Auto-assign devices based on site or location fields
- Review and verify region assignments periodically
- Document region boundaries and device mapping

### 4. Worker Scaling
- Start with 1-2 workers per region
- Scale based on job volume and device count
- Monitor queue lengths and worker utilization
- Consider concurrency settings per worker

### 5. Failover Strategy
- Always run a central fallback worker
- Set appropriate health check intervals (60-300s)
- Monitor health status and alerts
- Test failover scenarios regularly

### 6. Network Considerations
- Ensure workers can reach target devices
- Configure appropriate firewall rules
- Use VPN or private links for security
- Monitor network latency and connectivity

## Troubleshooting

### Jobs Not Routing to Region

**Check:**
1. Device has region assigned: `device.region`
2. Region is enabled: `region.enabled = True`
3. Region is not offline: `region.health_status != 'offline'`
4. Worker is listening to region queue
5. Job target filters match devices with region

### Worker Not Picking Up Jobs

**Check:**
1. Worker is running and connected to broker
2. Worker is listening to correct queue (`-Q` parameter)
3. Redis/broker is accessible from worker
4. No network connectivity issues
5. Celery logs for errors

### High Latency or Timeouts

**Solutions:**
1. Add more workers to region
2. Increase worker concurrency
3. Check network path to devices
4. Verify region assignment matches physical location
5. Consider splitting region into smaller zones

### Region Shows as Offline

**Check:**
1. Worker processes are running
2. Network connectivity to broker
3. Health check configuration
4. Recent health status updates
5. Worker logs for errors

## API Reference

### Region Endpoints

- `GET /api/v1/regions/` - List regions
- `POST /api/v1/regions/` - Create region
- `GET /api/v1/regions/{id}/` - Get region details
- `PATCH /api/v1/regions/{id}/` - Update region
- `DELETE /api/v1/regions/{id}/` - Delete region
- `POST /api/v1/regions/{id}/update_health/` - Update health status
- `GET /api/v1/regions/{id}/jobs/` - Get region jobs
- `GET /api/v1/regions/{id}/devices/` - Get region devices

### Device Updates

- `PATCH /api/v1/devices/{id}/` - Assign device region

### Job Information

- `GET /api/v1/jobs/{id}/` - View job details including region

## Migration Guide

### Existing Deployments

For existing deployments without multi-region support:

1. **Run migrations:**
   ```bash
   python manage.py migrate
   ```

2. **Create default region (optional):**
   ```python
   from webnet.core.models import Region
   from webnet.customers.models import Customer
   
   customer = Customer.objects.first()
   Region.objects.create(
       customer=customer,
       name="Default",
       identifier="default",
       priority=100,
       enabled=True
   )
   ```

3. **Assign devices to regions:**
   - Use API or Django admin to assign devices
   - Can be done gradually without downtime

4. **Deploy regional workers:**
   - Start with central worker only
   - Add regional workers as needed
   - No changes required to existing worker

5. **Monitor and adjust:**
   - Verify job routing works correctly
   - Adjust priorities and health checks
   - Scale workers as needed

## Security Considerations

1. **Network Segmentation**: Ensure regional workers have appropriate network access
2. **Authentication**: Use secure credentials for broker connections
3. **TLS/SSL**: Enable encryption for Redis/broker connections
4. **Access Control**: Limit region management to admin users
5. **Audit Logging**: Monitor region configuration changes

## Performance Tuning

### Worker Configuration

```bash
# Adjust concurrency (number of parallel tasks)
celery worker -Q region_us-east-1 --concurrency=4

# Use prefork pool (default, good for I/O bound)
celery worker -Q region_us-east-1 --pool=prefork

# Use gevent pool (for high concurrency)
celery worker -Q region_us-east-1 --pool=gevent --concurrency=100

# Adjust prefetch multiplier (tasks fetched per worker)
celery worker -Q region_us-east-1 --prefetch-multiplier=1
```

### Region Settings

```python
# In Region.worker_pool_config:
{
    "concurrency": 4,
    "pool": "prefork",
    "prefetch_multiplier": 1,
    "max_tasks_per_child": 1000  # Restart worker after N tasks
}
```

## Future Enhancements

Planned features for multi-region support:

- [ ] Distributed API endpoints per region
- [ ] Cross-region job coordination
- [ ] Automatic region discovery
- [ ] Enhanced latency monitoring
- [ ] Geographic load balancing
- [ ] Region-specific configuration templates
- [ ] Multi-region dashboard and metrics
