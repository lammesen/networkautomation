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

## Technology Stack

### Backend
- **FastAPI**: Modern Python web framework
- **SQLAlchemy + Alembic**: ORM and database migrations
- **PostgreSQL**: Primary database
- **Celery + Redis**: Distributed task queue
- **Nornir**: Network automation orchestration
- **NAPALM**: Multi-vendor network device abstraction
- **Netmiko**: SSH/Telnet connection library

### Frontend
- **React + TypeScript**: UI framework
- **Vite**: Build tool
- **React Router**: Navigation
- **TanStack Query**: Data fetching
- **Axios**: HTTP client

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Git

### Installation

1. Clone the repository:
```bash
git clone https://github.com/lammesen/networkautomation.git
cd networkautomation
```

2. Create environment file:
```bash
cat > deploy/.env << EOF
SECRET_KEY=$(openssl rand -hex 32)
DATABASE_URL=postgresql://netauto:netauto@postgres:5432/netauto
REDIS_URL=redis://redis:6379/0
EOF
```

3. Start the services:
```bash
cd deploy
docker-compose up -d
```

4. Initialize the database:
```bash
docker-compose exec backend alembic upgrade head
```

5. Create an admin user:
```bash
docker-compose exec backend python -c "
from app.db import SessionLocal, User
from app.core.auth import get_password_hash

db = SessionLocal()
admin = User(
    username='admin',
    hashed_password=get_password_hash('admin123'),
    role='admin',
    is_active=True
)
db.add(admin)
db.commit()
print('Admin user created: username=admin, password=admin123')
"
```

6. Access the application:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

## Project Structure

```
networkautomation/
├── backend/                    # Backend application
│   ├── app/
│   │   ├── api/               # API endpoints
│   │   ├── automation/        # Nornir/NAPALM/Netmiko tasks
│   │   ├── compliance/        # Compliance checking
│   │   ├── config_backup/     # Config backup logic
│   │   ├── config_deploy/     # Config deployment
│   │   ├── core/              # Core configuration and auth
│   │   ├── db/                # Database models
│   │   ├── jobs/              # Job system and Celery tasks
│   │   ├── schemas/           # Pydantic schemas
│   │   └── main.py            # FastAPI application
│   ├── alembic/               # Database migrations
│   ├── celery_app.py          # Celery configuration
│   └── pyproject.toml         # Python dependencies
├── frontend/                   # React frontend
│   ├── src/
│   │   ├── api/               # API client
│   │   ├── components/        # React components
│   │   ├── pages/             # Page components
│   │   ├── features/          # Feature modules
│   │   └── App.tsx            # Main app component
│   └── package.json           # Node dependencies
├── deploy/                     # Deployment configuration
│   ├── docker-compose.yml
│   ├── Dockerfile.backend
│   └── Dockerfile.frontend
└── docs/                       # Documentation
```

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

## Development

### Backend Development

1. Setup Python environment:
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -e ".[dev]"
```

2. Run migrations:
```bash
alembic upgrade head
```

3. Start the development server:
```bash
uvicorn app.main:app --reload
```

4. Run tests:
```bash
pytest
```

### Frontend Development

1. Install dependencies:
```bash
cd frontend
npm install
```

2. Start development server:
```bash
npm run dev
```

3. Build for production:
```bash
npm run build
```

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