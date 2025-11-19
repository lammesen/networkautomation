# Getting Started with Network Automation

This guide will help you get the Network Automation application up and running quickly.

## Prerequisites

- Docker and Docker Compose (v2.0+)
- Git
- 4GB+ RAM recommended
- Network devices accessible via SSH (optional for testing)

## Quick Start (5 minutes)

### 1. Clone and Navigate

```bash
git clone https://github.com/lammesen/networkautomation.git
cd networkautomation
```

### 2. Start Services

```bash
cd deploy
docker-compose up -d
```

Wait for services to start (~30 seconds):
```bash
docker-compose ps
```

### 3. Initialize Database

```bash
docker-compose exec backend alembic upgrade head
docker-compose exec backend python init_db.py
```

This creates:
- All database tables
- Default admin user (username: `admin`, password: `admin123`)

### 4. Verify Services

```bash
# Check API health
curl http://localhost:8000/health

# Check API docs
open http://localhost:8000/docs  # or visit in browser

# Check frontend
open http://localhost:3000  # or visit in browser
```

### 5. Login

1. Visit http://localhost:3000
2. Login with:
   - Username: `admin`
   - Password: `admin123`

3. **IMPORTANT**: Change the admin password immediately after first login!

## Next Steps

### Add Your First Device

1. **Create Credentials**

Via UI or API:
```bash
curl -X POST http://localhost:8000/api/v1/credentials \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "lab_creds",
    "username": "admin",
    "password": "your_device_password"
  }'
```

2. **Add a Device**

```bash
curl -X POST http://localhost:8000/api/v1/devices \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "hostname": "router1",
    "mgmt_ip": "192.168.1.1",
    "vendor": "cisco",
    "platform": "ios",
    "role": "edge",
    "site": "lab",
    "credentials_ref": 1,
    "enabled": true
  }'
```

### Run Your First Command

```bash
curl -X POST http://localhost:8000/api/v1/commands/run \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "targets": {"site": "lab"},
    "commands": ["show version"]
  }'
```

Response will include a `job_id`. Check job status:
```bash
curl http://localhost:8000/api/v1/jobs/1 \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Backup Configurations

```bash
curl -X POST http://localhost:8000/api/v1/config/backup \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "targets": {"site": "lab"},
    "source_label": "manual"
  }'
```

## Getting Your API Token

### Via cURL

```bash
TOKEN=$(curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' \
  | jq -r '.access_token')

echo $TOKEN
```

Use the token in subsequent requests:
```bash
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/devices
```

### Via Browser

1. Login to the frontend at http://localhost:3000
2. Open browser developer tools (F12)
3. Check Application → Local Storage → auth-storage
4. Copy the token value

## Supported Device Types

The application supports these platforms out of the box:

| Vendor   | Platform      | NAPALM Driver | Netmiko Type    |
|----------|---------------|---------------|-----------------|
| Cisco    | ios           | ios           | cisco_ios       |
| Cisco    | iosxe         | ios           | cisco_ios       |
| Cisco    | iosxr         | iosxr         | cisco_xr        |
| Cisco    | nxos          | nxos          | cisco_nxos      |
| Arista   | eos           | eos           | arista_eos      |
| Juniper  | junos         | junos         | juniper_junos   |

To add more platforms, edit `backend/app/automation/inventory.py`.

## Configuration

### Environment Variables

Create `deploy/.env`:
```bash
SECRET_KEY=your-secret-key-here
DATABASE_URL=postgresql://netauto:netauto@postgres:5432/netauto
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/1
CORS_ORIGINS=["http://localhost:3000"]
```

Generate a secure secret key:
```bash
openssl rand -hex 32
```

### Database Credentials

For production, change the PostgreSQL password in `docker-compose.yml`:
```yaml
postgres:
  environment:
    POSTGRES_PASSWORD: secure_password_here
```

And update `DATABASE_URL` accordingly.

## Testing Without Real Devices

For testing without physical network devices, you can:

1. **Use a Network Simulator**
   - GNS3
   - EVE-NG
   - Cisco CML (VIRL)
   - Containerlab

2. **Mock Device for Testing**
   - The application will gracefully handle connection failures
   - Jobs will show status and error messages
   - Useful for testing the UI and workflow

3. **Use Docker Network Containers**
   ```bash
   docker run -d --name cisco-sim -p 2222:22 \
     networkprofile/cisco-sim
   ```
   Then add device with `mgmt_ip: host.docker.internal:2222`

## Common Issues

### "Cannot connect to database"

```bash
# Check PostgreSQL is running
docker-compose ps postgres

# Check logs
docker-compose logs postgres

# Restart if needed
docker-compose restart postgres
```

### "Celery worker not processing jobs"

```bash
# Check worker status
docker-compose logs celery-worker

# Restart worker
docker-compose restart celery-worker
```

### "Frontend won't connect to API"

Check CORS settings in `backend/app/core/config.py`:
```python
cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]
```

### Port Already in Use

If port 8000, 3000, 5432, or 6379 is already in use, edit `docker-compose.yml` to use different ports:
```yaml
backend:
  ports:
    - "8001:8000"  # External:Internal
```

## Stopping the Application

```bash
cd deploy
docker-compose down
```

To also remove data:
```bash
docker-compose down -v
```

## Updating the Application

```bash
git pull
cd deploy
docker-compose down
docker-compose build --no-cache
docker-compose up -d
docker-compose exec backend alembic upgrade head
```

## Development Mode

### Backend Development

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -e ".[dev]"

# Run migrations
alembic upgrade head

# Start FastAPI with auto-reload
uvicorn app.main:app --reload
```

### Frontend Development

```bash
cd frontend
npm install
npm run dev
```

The frontend will be available at http://localhost:5173 with hot reload.

## Production Deployment

### Security Checklist

- [ ] Change all default passwords
- [ ] Generate strong SECRET_KEY
- [ ] Use HTTPS (configure reverse proxy)
- [ ] Restrict CORS origins
- [ ] Use environment-specific credentials
- [ ] Enable PostgreSQL SSL
- [ ] Implement rate limiting
- [ ] Setup firewall rules
- [ ] Regular backups
- [ ] Monitor logs

### Recommended Architecture

```
Internet
    │
    ▼
[NGINX/Traefik]  ← SSL termination
    │
    ├─▶ [Frontend]  (static files)
    │
    └─▶ [Backend API]
          │
          ├─▶ [PostgreSQL]  (primary DB)
          ├─▶ [Redis]       (cache/queue)
          └─▶ [Celery Workers] × N
```

## Getting Help

- **Documentation**: See `docs/` directory
- **API Reference**: http://localhost:8000/docs
- **Issues**: https://github.com/lammesen/networkautomation/issues
- **Operations Guide**: `docs/operations.md`
- **Architecture**: `docs/architecture.md`

## What's Next?

1. **Add Devices**: Start adding your network devices
2. **Run Commands**: Test command execution
3. **Setup Backup Schedule**: Use Celery Beat for scheduled backups
4. **Create Compliance Policies**: Define compliance checks
5. **Customize**: Extend with custom tasks and integrations

## Example Workflow

Here's a typical workflow:

1. **Morning**: Run compliance checks
   ```bash
   curl -X POST .../compliance/run -d '{"policy_id": 1}'
   ```

2. **Backup configs** before changes
   ```bash
   curl -X POST .../config/backup -d '{"targets": {}}'
   ```

3. **Deploy change** with preview
   ```bash
   # Preview
   curl -X POST .../config/deploy/preview -d '{...}'
   
   # Review diff
   curl .../jobs/{job_id}/results
   
   # Commit if OK
   curl -X POST .../config/deploy/commit -d '{...}'
   ```

4. **Verify** with commands
   ```bash
   curl -X POST .../commands/run -d '{...}'
   ```

5. **Evening**: Review job history and compliance results

Enjoy automating your network! 🚀
