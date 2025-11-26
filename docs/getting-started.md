# Getting Started with Network Automation

This guide will help you get the Network Automation application up and running quickly.

## Prerequisites

- Docker Desktop with Kubernetes enabled (or another local Kubernetes cluster)
- `kubectl` 1.28+
- GNU Make
- Bun (for the React frontend)
- Git
- 4GB+ RAM recommended
- Network devices accessible via SSH (optional for testing)

## Quick Start (5 minutes)

### 1. Clone and Navigate

```bash
git clone https://github.com/lammesen/networkautomation.git
cd networkautomation
```

### 2. Install Project Dependencies

```bash
make bootstrap
```

This creates the Python virtualenv, installs backend dev requirements, and installs frontend packages via Bun.

### 3. Build Images & Deploy to Kubernetes

```bash
make dev-up
```

The target builds all local container images (Docker Desktop shares its image cache with the Kubernetes cluster) and applies every manifest in `k8s/` to the `default` namespace. Check progress with:

```bash
make k8s-status
kubectl wait --for=condition=available deployment/backend --timeout=120s
kubectl wait --for=condition=available deployment/frontend --timeout=120s
```

### 4. Port-forward Services (two terminals)

In terminal #1:
```bash
make k8s-port-forward-backend
```

In terminal #2:
```bash
make k8s-port-forward-frontend
```

### 5. Initialize Database & Seed Admin

```bash
make migrate
make seed-admin
```

`seed-admin` runs `python init_db.py` inside the backend pod to create the default admin user. The password comes from the `ADMIN_DEFAULT_PASSWORD` environment variable (default `Admin123!`) and the command also seeds the sample linux device.

### 6. Verify Services

```bash
# Check API health
curl http://localhost:8000/health

# Check API docs
open http://localhost:8000/docs  # or visit in browser

# Check frontend
open http://localhost:3000  # or visit in browser
```

### 7. Login

1. Visit http://localhost:3000
2. Login with:
   - Username: `admin`
   - Password: value of `ADMIN_DEFAULT_PASSWORD` (default `Admin123!`)

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

### Try the Live SSH Terminal

- The seed data includes a `linux-lab-01` device that points to the bundled
  `linux-device` container (credentials `testuser` / `testpassword`). Click its
  **Terminal** action to open an interactive shell.
- For architecture details and troubleshooting steps see
  [`docs/ssh-streaming.md`](./ssh-streaming.md).

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
  -d "{\"username\":\"admin\",\"password\":\"${ADMIN_DEFAULT_PASSWORD:-Admin123!}\"}" \
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

The Kubernetes manifests define runtime configuration directly inside `k8s/backend.yaml`. Edit the `env` block to customize items such as the FastAPI secret key, database connection, or CORS policy:

```yaml
      containers:
      - name: backend
        env:
        - name: SECRET_KEY
          value: "change-me"
        - name: DB_PATH
          value: "/app/data/netauto.sqlite"
        # Optional: switch to Postgres instead of SQLite
        # - name: DATABASE_URL
        #   value: "postgresql://netauto:netauto@postgres:5432/netauto"
        - name: CORS_ORIGINS
          value: '["http://localhost:3000"]'
```

Apply changes with `make k8s-apply` (or `kubectl apply -f k8s/backend.yaml`). For one-off tweaks you can also run:

```bash
kubectl set env deployment/backend SECRET_KEY=$(openssl rand -hex 32) -n default
```

### Database Credentials

`k8s/postgres.yaml` contains the PostgreSQL deployment and environment variables. Update the `POSTGRES_PASSWORD` (and matching `DATABASE_URL` in `k8s/backend.yaml` if you switch away from SQLite), then redeploy:

```bash
kubectl apply -f k8s/postgres.yaml
kubectl rollout restart deployment/postgres
```

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
# Ensure the pod is running
make k8s-status

# Inspect logs
kubectl logs deployment/postgres -n default

# Restart the deployment if needed
kubectl rollout restart deployment/postgres -n default
```

### "Celery worker not processing jobs"

```bash
# Check worker logs
kubectl logs deployment/worker -n default

# Restart worker deployment
kubectl rollout restart deployment/worker -n default
```

### "Frontend won't connect to API"

Check CORS settings in `backend/app/core/config.py`:
```python
cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]
```

### Port Already in Use

When port-forwarding, change the local bind port:

```bash
# Backend API on localhost:9000 instead of 8000
kubectl port-forward svc/backend 9000:8000 -n default

# Frontend on localhost:3333 instead of 3000
kubectl port-forward svc/frontend 3333:3000 -n default
```

## Stopping the Application

```bash
make dev-down
```

To also remove persistent volumes (SQLite + Postgres data):
```bash
kubectl delete pvc sqlite-pvc postgres-pvc --ignore-not-found=true -n default
```

## Updating the Application

```bash
git pull
make dev-down
make docker-build
make k8s-redeploy
make migrate
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
