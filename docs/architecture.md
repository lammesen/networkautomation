# Network Automation Application Architecture

## Overview

This document describes the architecture of the Network Automation web application, a production-grade system for managing network devices, executing commands, backing up configurations, and running compliance checks.

## System Architecture

### High-Level Components

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│                 │     │                  │     │                 │
│  React Frontend │────▶│  FastAPI Backend │────▶│   PostgreSQL    │
│   (TypeScript)  │     │     (Python)     │     │    Database     │
│                 │     │                  │     │                 │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                              │
                              │
                        ┌─────▼─────┐
                        │           │
                        │   Redis   │
                        │           │
                        └─────┬─────┘
                              │
                        ┌─────▼─────────┐
                        │               │
                        │ Celery Worker │────┐
                        │               │    │
                        └───────────────┘    │
                                             │
                        ┌────────────────────▼─────────┐
                        │                              │
                        │  Network Devices             │
                        │  (via Nornir/NAPALM/Netmiko) │
                        │                              │
                        └──────────────────────────────┘
```

## Backend Architecture

### Module Structure

The backend follows a modular architecture with clear separation of concerns:

#### Core (`app/core/`)
- **config.py**: Application configuration using Pydantic settings
- **auth.py**: JWT authentication and RBAC implementation
- **logging.py**: Centralized logging configuration

#### Database (`app/db/`)
- **models.py**: SQLAlchemy ORM models for all entities
- **session.py**: Database session management
- Migration management via Alembic

#### API (`app/api/`)
- **auth.py**: Authentication endpoints (login, register, token refresh)
- **devices.py**: Device and credential CRUD endpoints
- **jobs.py**: Job management and monitoring endpoints
- **commands.py**: Command execution endpoints
- **config.py**: Configuration backup and deployment endpoints
- **compliance.py**: Compliance policy and checking endpoints

#### Automation (`app/automation/`)
- **nornir_init.py**: Nornir initialization with database-backed inventory
- **tasks_cli.py**: CLI command execution tasks (Netmiko)
- **tasks_config.py**: Configuration management tasks (NAPALM)
- **tasks_validate.py**: Compliance validation tasks (NAPALM)
- **inventory.py**: Custom Nornir inventory plugin

#### Jobs (`app/jobs/`)
- **tasks.py**: Celery task definitions
- **manager.py**: Job creation and lifecycle management
- **logs.py**: Job logging and streaming utilities

### Data Models

#### User
- Stores user credentials and role (viewer/operator/admin)
- Used for authentication and authorization

#### Credential
- Stores device authentication credentials
- Encrypted at rest (should use HashiCorp Vault in production)
- Referenced by devices

#### Device
- Core inventory model
- Fields: hostname, mgmt_ip, vendor, platform, role, site, tags
- Linked to credentials
- Can be filtered by multiple criteria

#### Job
- Represents an asynchronous operation
- Types: run_commands, config_backup, config_deploy, compliance
- Statuses: queued, running, success, partial, failed
- Stores execution metadata and results

#### JobLog
- Individual log entries for a job
- Includes timestamp, level, host, message
- Used for live streaming and historical review

#### ConfigSnapshot
- Stores device configuration at a point in time
- Includes hash for change detection
- Linked to job that created it

#### CompliancePolicy
- YAML-based policy definition
- Scope filters determine target devices
- Uses NAPALM validation format

#### ComplianceResult
- Results of compliance check for a device
- Pass/fail status with detailed results
- Historical tracking

### Authentication & Authorization

#### JWT-Based Authentication
1. User provides username/password to `/auth/login`
2. Backend validates credentials and returns access + refresh tokens
3. Access token valid for 30 minutes, refresh token for 7 days
4. Client includes token in `Authorization: Bearer <token>` header

#### Role-Based Access Control (RBAC)
- **Viewer**: Read-only access to devices, jobs, configs
- **Operator**: Can run commands, backup configs, deploy changes
- **Admin**: Full access including user management and policy creation

Implemented via dependencies:
- `require_viewer`: Any authenticated user
- `require_operator`: Operator or Admin
- `require_admin`: Admin only

### Job System

#### Job Lifecycle

1. **Creation**: API endpoint creates Job record with status="queued"
2. **Queueing**: Celery task enqueued with job_id
3. **Execution**:
   - Worker picks up task
   - Updates status to "running"
   - Initializes Nornir with device inventory
   - Executes tasks across devices in parallel
   - Writes logs to database and Redis
4. **Completion**:
   - Aggregates results
   - Updates job with final status
   - Stores result summary

#### Log Streaming

- Logs written to both PostgreSQL (JobLog table) and Redis pub/sub
- WebSocket endpoint subscribes to Redis channel
- Real-time log delivery to connected clients
- Historical logs available via REST API

#### 2025 Refactor Enhancements

- `app/services/job_service.py` centralizes job creation, status transitions, and log persistence for both HTTP requests and Celery workers.
- `app/automation/context.py` wraps device filtering, Nornir initialization, and structured logging so each worker task shares the same orchestration primitives.
- FastAPI dependencies in `app/dependencies.py` expose typed services (`get_job_service`, `get_device_service`, etc.) ensuring tenancy checks happen before work is queued.

### Automation Layer

#### Nornir Integration

Nornir provides the orchestration framework:
- Custom inventory plugin reads devices from PostgreSQL
- Maps vendor/platform to correct NAPALM driver or Netmiko device_type
- Handles parallel execution with configurable workers
- Provides result aggregation

#### Task Types

**CLI Commands** (`tasks_cli.py`)
- Uses Netmiko for raw command execution
- Captures output for each device
- Handles connection errors gracefully

**Configuration** (`tasks_config.py`)
- Uses NAPALM for vendor-agnostic config operations
- Operations: get_config, load_merge_candidate, compare_config, commit, rollback
- Transaction-based with explicit commit

**Validation** (`tasks_validate.py`)
- Uses NAPALM's compliance validation
- Compares actual state against YAML-defined expected state
- Returns structured pass/fail results

#### Vendor Support

Current support via NAPALM/Netmiko:
- Cisco IOS/IOS-XE/IOS-XR
- Arista EOS
- Juniper Junos
- Cisco NX-OS
- And more via NAPALM drivers

## Frontend Architecture

### Technology Stack
- React 18 with TypeScript
- Vite for build tooling
- React Router for navigation
- TanStack Query for server state
- Zustand for client state
- Axios for HTTP requests

### Module Structure

#### Store (`src/store/`)
- **authStore.ts**: Authentication state (token, user, logout)
- Persisted to localStorage

#### API Client (`src/api/`)
- **client.ts**: Centralized API client with axios
- Automatic token injection
- Automatic 401 handling (redirect to login)

#### Pages (`src/pages/`)
- **LoginPage.tsx**: Authentication page
- **DevicesPage.tsx**: Device inventory
- **DeviceDetailPage.tsx**: Single device view
- **JobsPage.tsx**: Job list and monitoring
- **JobDetailPage.tsx**: Job details with live logs
- **CommandsPage.tsx**: Run commands interface
- **ConfigBackupPage.tsx**: Config backup management
- **ConfigDeployPage.tsx**: Config deployment workflow
- **CompliancePage.tsx**: Compliance overview

#### Components (`src/components/`)
- **Layout/DashboardLayout.tsx**: Main app layout with nav
- **DeviceTable.tsx**: Device list table
- **JobConsole.tsx**: Live log viewer with WebSocket
- **ConfigDiff.tsx**: Side-by-side diff viewer
- **TargetSelector.tsx**: Device filter widget

#### Features (`src/features/`)
- Modular feature bundles combining components, hooks, and logic

### State Management

#### Server State (TanStack Query)
- Caching API responses
- Automatic refetching
- Optimistic updates
- Background refetching

#### Client State (Zustand)
- Auth state (token, user)
- UI state (modals, filters)
- Minimal, focused stores

### Routing & Navigation

Protected routes require authentication:
```
/ (authenticated)
  ├── /devices
  │   └── /devices/:id
  ├── /commands
  ├── /config/backup
  ├── /config/deploy
  ├── /compliance
  └── /jobs
      └── /jobs/:id
/login (public)
```

## Deployment Architecture

### Docker Compose Setup

Services:
1. **postgres**: PostgreSQL 16 database
2. **redis**: Redis 7 for caching and message broker
3. **backend**: FastAPI application server
4. **celery-worker**: Celery worker for async tasks
5. **frontend**: React dev server (production: static build served by nginx)

### Production Considerations

1. **Secrets Management**
   - Use environment variables
   - Consider HashiCorp Vault for device credentials
   - Rotate SECRET_KEY regularly

2. **Scaling**
   - Horizontal scaling of Celery workers
   - Database connection pooling
   - Redis Sentinel for HA

3. **Monitoring**
   - Prometheus metrics export
   - Grafana dashboards
   - Celery Flower for task monitoring
   - Application logs aggregation (ELK/Loki)

4. **Networking**
   - TLS termination at reverse proxy
   - Network segmentation for management network
   - Firewall rules for device access

5. **Backup**
   - Regular PostgreSQL backups
   - Config snapshot backups to S3/object storage
   - Disaster recovery procedures

## Security Architecture

### Authentication
- JWT tokens with short expiration
- Refresh token rotation
- Password hashing with bcrypt
- Rate limiting on login endpoint

### Authorization
- Role-based access control at API level
- Permission checks on all write operations
- Audit logging of sensitive actions

### Data Protection
- Encrypted credentials (at rest)
- TLS for all communications (in production)
- SQL injection protection via ORM
- Input validation via Pydantic

### Network Security
- Device credentials never exposed to frontend
- API rate limiting
- CORS configuration
- CSP headers

## Extensibility

### Adding New Device Types
1. Add vendor mapping in `automation/inventory.py`
2. Test with sample device
3. Add platform-specific handling if needed

### NetBox Integration
Replace database inventory with NetBox source:
1. Implement NetBox inventory plugin for Nornir
2. Update API endpoints to proxy to NetBox
3. Maintain Job/Log models locally

### Custom Compliance Checks
1. Define policy in YAML (NAPALM validation format)
2. Create CompliancePolicy via API
3. Run compliance job against devices
4. Review results in UI

### Scheduled Jobs
1. Add Celery Beat for periodic tasks
2. Configure backup schedules in database
3. Trigger via cron-like expressions

## Performance Considerations

### Database
- Indexes on frequently queried fields (site, role, vendor)
- Query optimization for device listing
- Pagination for large result sets
- Connection pooling

### API
- Async endpoints where possible
- Response caching for read-heavy endpoints
- Efficient pagination
- Query parameter filtering

### Celery
- Worker autoscaling based on queue length
- Task routing to specialized workers
- Result backend optimization
- Periodic cleanup of old job results

### Frontend
- Code splitting for faster initial load
- Lazy loading of components
- Optimistic UI updates
- Debounced search inputs

## Testing Strategy

### Backend
- Unit tests for business logic
- Integration tests for API endpoints
- Mock Nornir for automation tests
- Database fixtures for consistent test data

### Frontend
- Component tests with React Testing Library
- Integration tests for critical flows
- E2E tests with Playwright
- API mocking with MSW

## Future Enhancements

1. **Device Discovery**
   - CDP/LLDP neighbor discovery
   - Network scanning
   - Auto-add to inventory

2. **Topology Visualization**
   - Interactive network map
   - Layer 2/3 topology
   - Real-time status overlay

3. **Advanced Templating**
   - Template library
   - Variable validation
   - Template testing

4. **Multi-Tenancy**
   - Organization model
   - Per-tenant isolation
   - Delegated administration

5. **Webhooks**
   - Job completion notifications
   - Config change events
   - Compliance violation alerts

6. **Advanced Reporting**
   - Compliance trends
   - Config drift analysis
   - Device inventory reports
