# Operations Guide

This guide covers common operational tasks for the Network Automation application.

## Table of Contents
- [Initial Setup](#initial-setup)
- [Managing Devices](#managing-devices)
- [Running Commands](#running-commands)
- [Configuration Management](#configuration-management)
- [Compliance Checking](#compliance-checking)
- [Troubleshooting](#troubleshooting)

## Initial Setup

### Starting the Application

1. **Start all services**:
```bash
cd deploy
docker-compose up -d
```

2. **Check service health**:
```bash
docker-compose ps
docker-compose logs -f backend  # View backend logs
docker-compose logs -f celery-worker  # View worker logs
```

3. **Initialize database**:
```bash
# Run migrations
docker-compose exec backend alembic upgrade head

# Verify tables created
docker-compose exec postgres psql -U netauto -d netauto -c "\dt"
```

4. **Create admin user**:
```bash
docker-compose exec backend python << EOF
from app.db import SessionLocal, User
from app.core.auth import get_password_hash

db = SessionLocal()
admin = User(
    username='admin',
    hashed_password=get_password_hash('SecurePassword123!'),
    role='admin',
    is_active=True
)
db.add(admin)
db.commit()
db.close()
print("Admin user created successfully")
EOF
```

### Stopping the Application

```bash
cd deploy
docker-compose down  # Stop and remove containers
docker-compose down -v  # Also remove volumes (WARNING: deletes data!)
```

## Managing Devices

### Adding Credentials

Credentials must be created before adding devices.

**Via API**:
```bash
curl -X POST http://localhost:8000/api/v1/credentials \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "cisco_lab",
    "username": "netadmin",
    "password": "C1sc0Passw0rd!",
    "enable_password": "En@bleP@ss"
  }'
```

**Via Python Script**:
```bash
docker-compose exec backend python << EOF
from app.db import SessionLocal, Credential

db = SessionLocal()
cred = Credential(
    name="cisco_lab",
    username="netadmin",
    password="C1sc0Passw0rd!",  # Should be encrypted
    enable_password="En@bleP@ss"
)
db.add(cred)
db.commit()
print(f"Credential created with ID: {cred.id}")
db.close()
EOF
```

### Adding Devices

**Single Device via API**:
```bash
curl -X POST http://localhost:8000/api/v1/devices \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "hostname": "sw-core-01",
    "mgmt_ip": "192.168.1.10",
    "vendor": "cisco",
    "platform": "ios",
    "role": "core",
    "site": "HQ",
    "tags": {"environment": "production"},
    "credentials_ref": 1,
    "enabled": true
  }'
```

**Bulk Import via Python Script**:
```python
# bulk_import.py
from app.db import SessionLocal, Device, Credential

devices_data = [
    {"hostname": "sw-core-01", "mgmt_ip": "192.168.1.10", "platform": "ios"},
    {"hostname": "sw-core-02", "mgmt_ip": "192.168.1.11", "platform": "ios"},
    {"hostname": "sw-edge-01", "mgmt_ip": "192.168.2.10", "platform": "ios"},
]

db = SessionLocal()
cred = db.query(Credential).filter(Credential.name == "cisco_lab").first()

for data in devices_data:
    device = Device(
        hostname=data["hostname"],
        mgmt_ip=data["mgmt_ip"],
        vendor="cisco",
        platform=data["platform"],
        credentials_ref=cred.id,
        enabled=True
    )
    db.add(device)

db.commit()
print(f"Imported {len(devices_data)} devices")
db.close()
```

Run the script:
```bash
docker-compose exec backend python bulk_import.py
```

### Viewing Devices

**List all devices**:
```bash
curl http://localhost:8000/api/v1/devices \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Filter devices by site**:
```bash
curl "http://localhost:8000/api/v1/devices?site=HQ" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Search devices**:
```bash
curl "http://localhost:8000/api/v1/devices?search=core" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Updating Devices

```bash
curl -X PUT http://localhost:8000/api/v1/devices/1 \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "role": "distribution",
    "tags": {"environment": "production", "updated": "2024-01"}
  }'
```

### Deleting Devices

Deletion is a soft delete (sets `enabled=false`):
```bash
curl -X DELETE http://localhost:8000/api/v1/devices/1 \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Running Commands

### Ad-Hoc Command Execution

**Single command**:
```bash
curl -X POST http://localhost:8000/api/v1/commands/run \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "targets": {"site": "HQ"},
    "commands": ["show version"]
  }'
```

Response:
```json
{
  "job_id": 123
}
```

**Multiple commands**:
```bash
curl -X POST http://localhost:8000/api/v1/commands/run \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "targets": {"role": "core"},
    "commands": [
      "show version",
      "show ip interface brief",
      "show running-config | include hostname"
    ]
  }'
```

**Targeting specific devices**:
```bash
curl -X POST http://localhost:8000/api/v1/commands/run \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "targets": {"device_ids": [1, 2, 3]},
    "commands": ["show interfaces status"]
  }'
```

### Monitoring Job Progress

**Get job status**:
```bash
curl http://localhost:8000/api/v1/jobs/123 \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Get job logs**:
```bash
curl http://localhost:8000/api/v1/jobs/123/logs \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Get command results**:
```bash
curl http://localhost:8000/api/v1/jobs/123/results \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Live Log Streaming

Connect via WebSocket for real-time updates:
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/jobs/123');

ws.onmessage = (event) => {
  const log = JSON.parse(event.data);
  console.log(`[${log.level}] ${log.host}: ${log.message}`);
};
```

## Configuration Management

### Backing Up Configurations

**Backup all devices**:
```bash
curl -X POST http://localhost:8000/api/v1/config/backup \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "targets": {},
    "source_label": "manual"
  }'
```

**Backup specific site**:
```bash
curl -X POST http://localhost:8000/api/v1/config/backup \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "targets": {"site": "HQ"},
    "source_label": "scheduled"
  }'
```

### Viewing Configuration History

**List snapshots for a device**:
```bash
curl http://localhost:8000/api/v1/devices/1/config/snapshots \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Get specific snapshot**:
```bash
curl http://localhost:8000/api/v1/config/snapshots/456 \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Compare two snapshots**:
```bash
curl "http://localhost:8000/api/v1/devices/1/config/diff?from=456&to=457" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Deploying Configuration Changes

**Step 1: Preview changes**:
```bash
curl -X POST http://localhost:8000/api/v1/config/deploy/preview \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "targets": {"device_ids": [1]},
    "mode": "merge",
    "snippet": "interface GigabitEthernet0/1\n description UPLINK\n"
  }'
```

This returns a job_id. Check the results to see the diff:
```bash
curl http://localhost:8000/api/v1/jobs/789/results \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Step 2: Commit changes** (only if diff looks good):
```bash
curl -X POST http://localhost:8000/api/v1/config/deploy/commit \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "previous_job_id": 789,
    "confirm": true
  }'
```

### Rollback

If a commit fails, NAPALM automatically rolls back. To manually rollback:
1. Get the previous config snapshot
2. Deploy it using replace mode (with extreme caution)

## Compliance Checking

### Creating Compliance Policies

**Example policy YAML**:
```yaml
# ntp_policy.yaml
- get_facts:
    os_version: "15.6"

- get_ntp_servers:
    _mode: strict
    10.1.1.1: {}
    10.1.1.2: {}
```

**Create policy via API**:
```bash
curl -X POST http://localhost:8000/api/v1/compliance/policies \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "NTP Configuration",
    "description": "Ensures NTP servers are configured",
    "scope_json": {"role": "core"},
    "definition_yaml": "<YAML_CONTENT_HERE>"
  }'
```

### Running Compliance Checks

```bash
curl -X POST http://localhost:8000/api/v1/compliance/run \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "policy_id": 1
  }'
```

### Viewing Compliance Results

**All results**:
```bash
curl http://localhost:8000/api/v1/compliance/results \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Filter by policy**:
```bash
curl "http://localhost:8000/api/v1/compliance/results?policy_id=1" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Filter by device**:
```bash
curl "http://localhost:8000/api/v1/compliance/results?device_id=1" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Filter by status**:
```bash
curl "http://localhost:8000/api/v1/compliance/results?status=fail" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Troubleshooting

### Common Issues

#### "Cannot connect to database"

Check PostgreSQL is running:
```bash
docker-compose ps postgres
docker-compose logs postgres
```

Verify connection:
```bash
docker-compose exec postgres psql -U netauto -d netauto -c "SELECT 1;"
```

#### "Celery worker not processing jobs"

Check worker status:
```bash
docker-compose ps celery-worker
docker-compose logs celery-worker
```

Check Redis:
```bash
docker-compose exec redis redis-cli ping
```

Restart worker:
```bash
docker-compose restart celery-worker
```

#### "Device connection timeout"

1. Verify device is reachable:
```bash
docker-compose exec backend ping <device_ip>
```

2. Check credentials are correct:
```bash
docker-compose exec backend python << EOF
from app.db import SessionLocal, Device, Credential

db = SessionLocal()
device = db.query(Device).filter(Device.hostname == "sw-core-01").first()
cred = device.credential
print(f"Username: {cred.username}")
# Test connection manually
db.close()
EOF
```

3. Check firewall rules allow SSH from container

#### "Frontend cannot connect to backend"

Check CORS settings in `backend/app/core/config.py`:
```python
cors_origins: list[str] = ["http://localhost:3000"]
```

Verify backend is accessible:
```bash
curl http://localhost:8000/health
```

### Debugging

#### Enable debug logging

**Backend**:
Edit `backend/app/core/config.py`:
```python
log_level: str = "DEBUG"
```

Restart:
```bash
docker-compose restart backend
```

**Celery**:
```bash
docker-compose stop celery-worker
docker-compose run --rm celery-worker celery -A celery_app.celery_app worker --loglevel=debug
```

#### View all logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend

# Last 100 lines
docker-compose logs --tail=100 backend
```

#### Database inspection

```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U netauto -d netauto

# List tables
\dt

# Check devices
SELECT id, hostname, mgmt_ip, enabled FROM devices;

# Check jobs
SELECT id, type, status, requested_at FROM jobs ORDER BY requested_at DESC LIMIT 10;

# Check recent logs
SELECT job_id, level, host, message FROM job_logs ORDER BY ts DESC LIMIT 20;
```

### Performance Tuning

#### Increase Celery workers

Edit `docker-compose.yml`:
```yaml
celery-worker:
  command: celery -A celery_app.celery_app worker --loglevel=info --concurrency=4
```

#### Database connection pooling

Edit `backend/app/core/config.py`:
```python
database_url: str = "postgresql://netauto:netauto@postgres:5432/netauto?pool_size=20&max_overflow=10"
```

#### Redis memory limit

Edit `docker-compose.yml`:
```yaml
redis:
  command: redis-server --maxmemory 256mb --maxmemory-policy allkeys-lru
```

### Backup and Recovery

#### Backup database

```bash
docker-compose exec postgres pg_dump -U netauto netauto > backup.sql
```

#### Restore database

```bash
docker-compose exec -T postgres psql -U netauto netauto < backup.sql
```

#### Export configuration snapshots

```bash
docker-compose exec backend python << EOF
from app.db import SessionLocal, ConfigSnapshot
import json

db = SessionLocal()
snapshots = db.query(ConfigSnapshot).all()

data = [{
    "device_id": s.device_id,
    "created_at": s.created_at.isoformat(),
    "config_text": s.config_text,
    "hash": s.hash
} for s in snapshots]

with open("/tmp/snapshots.json", "w") as f:
    json.dump(data, f)

print(f"Exported {len(snapshots)} snapshots")
db.close()
EOF

docker-compose cp backend:/tmp/snapshots.json ./snapshots.json
```

### Monitoring

#### Check service health

```bash
# Backend health
curl http://localhost:8000/health

# Database connections
docker-compose exec postgres psql -U netauto -d netauto -c "SELECT count(*) FROM pg_stat_activity;"

# Redis info
docker-compose exec redis redis-cli info
```

#### Monitor jobs

```bash
# Active jobs
docker-compose exec backend python << EOF
from app.db import SessionLocal, Job

db = SessionLocal()
active = db.query(Job).filter(Job.status.in_(["queued", "running"])).count()
print(f"Active jobs: {active}")
db.close()
EOF
```

#### Celery monitoring with Flower

Add to `docker-compose.yml`:
```yaml
flower:
  build:
    context: .
    dockerfile: deploy/Dockerfile.backend
  command: celery -A celery_app.celery_app flower --port=5555
  ports:
    - "5555:5555"
  environment:
    CELERY_BROKER_URL: redis://redis:6379/0
  depends_on:
    - redis
```

Access at http://localhost:5555

## Best Practices

1. **Always preview before committing configs**
2. **Use meaningful source labels for backups**
3. **Test compliance policies on a small subset first**
4. **Regular database backups**
5. **Monitor job completion rates**
6. **Use tags for flexible device grouping**
7. **Implement least-privilege access**
8. **Rotate credentials regularly**
9. **Review job logs for errors**
10. **Document custom compliance policies**
