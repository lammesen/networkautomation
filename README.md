# Network Automation Web Application

A production-grade web application for network automation using NAPALM, Netmiko, and Nornir.

## Features

- **Device Inventory Management**: CRUD operations for network devices with filtering and search
- **Bulk Command Execution**: Run show commands across multiple devices in parallel
- **Configuration Backup**: Automated config backups with versioning and diff viewing
- **Configuration Deployment**: Safe config changes with preview and rollback
- **Compliance Checking**: YAML-based compliance policies using NAPALM validation
- **Job Tracking**: Real-time job monitoring with live log streaming
- **Role-Based Access Control**: Viewer, Operator, and Admin roles

## Technology Stack (Django/HTMX/DRF)

### Backend
- **Django + DRF + Channels**: Server-rendered HTML (HTMX) and APIs with websockets
- **Celery + Redis**: Background jobs for automation
- **PostgreSQL**: Primary database
- **Nornir / NAPALM / Netmiko**: Network automation drivers

### Frontend
- **Django templates + HTMX + Tailwind** (primary UI)
- **React Islands** for interactive widgets under `backend/static/src/components/islands` (no separate SPA)

## Quick Start

See [`docs/getting-started.md`](docs/getting-started.md) for setup. Run `make backend-build-static` to build CSS/JS and collectstatic before packaging. Set secrets in `k8s/secrets.yaml` (SECRET_KEY, ENCRYPTION_KEY, optional CORS/CSRF origins) before deploy.

### Prerequisites
- Docker Desktop with Kubernetes enabled (or another local Kubernetes cluster)
- `kubectl` 1.28+
- GNU Make
- Node.js + npm
- Git


### Installation (Django stack)

1. Clone the repository:
```bash
git clone https://github.com/lammesen/networkautomation.git
cd networkautomation
```

2. Install project dependencies (backend venv):
```bash
make bootstrap
```

3. Build images and deploy to Kubernetes (backend + worker + redis/postgres):
```bash
make dev-up
make k8s-status
kubectl wait --for=condition=available deployment/backend --timeout=120s
kubectl wait --for=condition=available deployment/backend-worker --timeout=120s
```

4. Port-forward backend (HTML, API, websockets):
```bash
make k8s-port-forward-backend   # exposes Django on http://localhost:8000
```

5. Run migrations and create superuser inside the backend:
```bash
make migrate
make seed-admin   # createsuperuser --no-input; set credentials via env
```

6. Access the application:
- UI: http://localhost:8000 (HTMX pages)
- APIs: http://localhost:8000/api/v1/
- WebSockets: ws://localhost:8000/ws/jobs/<id>/, ws://localhost:8000/ws/devices/<id>/ssh/

### Required Environment

- `ENCRYPTION_KEY` (Fernet base64) **required** for backend start; generate with  
  `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`
- `SECRET_KEY` must be set for JWT signing (use a random 32+ char string).
- `ADMIN_DEFAULT_PASSWORD` should be overridden for any non-dev environment.
- `DATABASE_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`, and `REDIS_URL` should be set per environment; defaults are for local dev only.

## Project Structure

```
networkautomation/
├── backend/                         # Django project `webnet`
│   ├── webnet/                      # Django apps (users, devices, jobs, compliance, etc.)
│   ├── templates/                   # Django templates (HTMX)
│   ├── static/src/components/       # React Islands + shadcn/ui components
│   ├── static/src/islands.tsx       # Island registry
│   ├── manage.py
│   └── pyproject.toml               # Python dependencies
├── deploy/                          # Container build assets
│   ├── Dockerfile.backend           # Django/Channels/Daphne
│   ├── Dockerfile.backend-bun       # Optional Bun toolchain image
│   └── Dockerfile.linux-device      # Test/simulated device image
├── k8s/                             # Kubernetes manifests
│   ├── backend.yaml                 # Django ASGI service
│   ├── worker.yaml                  # Celery worker
│   ├── postgres.yaml, redis.yaml, pvc.yaml, services.yaml, linux-device.yaml, ingress.yaml
└── docs/                            # Documentation (see docs/README.md)
```

Documentation index: [`docs/README.md`](docs/README.md)

## Usage

### Adding a Device

1. Create credentials first:
```bash
curl -X POST http://localhost:8000/api/v1/credentials \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "cisco_creds",
    "username": "admin",
    "password": "password123"
  }'
```

2. Add a device:
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
    "site": "datacenter1",
    "credentials_ref": 1,
    "enabled": true
  }'
```

### Running Commands

Use the web UI or API:
```bash
curl -X POST http://localhost:8000/api/v1/commands/run \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "targets": {"site": "datacenter1"},
    "commands": ["show version", "show interfaces"]
  }'
```

### Backing Up Configurations

```bash
curl -X POST http://localhost:8000/api/v1/config/backup \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "targets": {"role": "edge"},
    "source_label": "manual"
  }'
```

## Development (Django)

1. Setup Python environment:
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -e ".[dev]"
```

2. Run migrations:
```bash
python manage.py migrate
```

3. Start the development server:
```bash
python manage.py runserver 0.0.0.0:8000
```

4. Start Celery worker (separate shell):
```bash
celery -A webnet.core.celery:celery_app worker -l info
```

5. Run tests:
```bash
pytest
```

(React frontend is deprecated; primary UI is Django templates + HTMX.)

## API Documentation

### Authentication

- `POST /api/v1/auth/login` - Login and get JWT token
- `POST /api/v1/auth/register` - Register new user
- `GET /api/v1/auth/me` - Get current user info

### Devices

- `GET /api/v1/devices` - List devices (with filters)
- `POST /api/v1/devices` - Create device
- `GET /api/v1/devices/{id}` - Get device details
- `PUT /api/v1/devices/{id}` - Update device
- `DELETE /api/v1/devices/{id}` - Delete device

### Credentials

- `GET /api/v1/credentials` - List credentials
- `POST /api/v1/credentials` - Create credential
- `GET /api/v1/credentials/{id}` - Get credential

### Jobs

- `GET /api/v1/jobs` - List jobs
- `GET /api/v1/jobs/{id}` - Get job details
- `GET /api/v1/jobs/{id}/logs` - Get job logs
- `GET /ws/jobs/{id}` - WebSocket for live logs

### Commands

- `POST /api/v1/commands/run` - Run commands on devices
- `GET /api/v1/jobs/{id}/results` - Get command results

### Configuration

- `POST /api/v1/config/backup` - Backup device configs
- `GET /api/v1/devices/{id}/config/snapshots` - List config snapshots
- `GET /api/v1/config/snapshots/{id}` - Get snapshot content
- `GET /api/v1/devices/{id}/config/diff` - Get config diff
- `POST /api/v1/config/deploy/preview` - Preview config changes
- `POST /api/v1/config/deploy/commit` - Commit config changes

### Compliance

- `GET /api/v1/compliance/policies` - List policies
- `POST /api/v1/compliance/policies` - Create policy
- `GET /api/v1/compliance/policies/{id}` - Get policy
- `POST /api/v1/compliance/run` - Run compliance check
- `GET /api/v1/compliance/results` - Get compliance results

## Security Considerations

1. **Change Default Credentials**: Update the SECRET_KEY and database passwords
2. **Use HTTPS**: Configure SSL/TLS in production
3. **Credential Storage**: Consider integrating HashiCorp Vault for credential management
4. **Network Security**: Restrict access to management network
5. **Regular Updates**: Keep dependencies updated
6. **Encrypt Device Secrets**: Set `ENCRYPTION_KEY` (Fernet) in all environments; the API refuses to start without it.
7. **Production Hardening**: When `ENVIRONMENT=production`, supply a non-default `DATABASE_URL` and explicit CORS origins (wildcards are rejected).

## Architecture

### Job System

Every operation (commands, backups, deploys, compliance) is a "job":
1. API endpoint creates Job record in database
2. Celery task is enqueued with job_id
3. Worker updates job status to "running"
4. Worker executes Nornir tasks across devices
5. Logs are written to JobLog table and published to Redis
6. WebSocket clients receive live log updates
7. Final status and results are saved to Job record

### Device Inventory

Devices are stored in PostgreSQL with support for:
- Filtering by site, role, vendor, platform
- Tags for flexible grouping
- Credential references (pluggable)
- Enable/disable state

The inventory is converted to Nornir format on-demand for task execution.

### Configuration Management

- Configs are pulled using NAPALM `get_config()`
- Only changed configs are stored (hash comparison)
- Snapshots include metadata (job_id, source, timestamp)
- Diffs use Python's difflib
- Deployment uses NAPALM's transaction model (load, compare, commit)

### Compliance Checking

- Policies defined as YAML (NAPALM validation format)
- Scope defines which devices to check
- Results stored per device/policy/run
- Historical tracking of compliance status

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

MIT License - see LICENSE file for details

## Support

For issues and questions:
- GitHub Issues: https://github.com/lammesen/networkautomation/issues
- Documentation: See docs/ directory

## Roadmap

- [ ] NetBox integration for inventory
- [ ] Scheduled backup jobs
- [ ] Configuration templates library
- [ ] Advanced compliance reports
- [ ] Multi-tenancy support
- [ ] Audit logging
- [ ] LDAP/AD authentication
- [ ] REST API webhooks
- [ ] Device discovery
- [ ] Topology visualization
