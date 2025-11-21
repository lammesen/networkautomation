# Network Automation Platform

## Project Overview
This is a production-grade web application for network automation, designed to manage network devices, execute commands, back up configurations, and ensure compliance. It features a modern React frontend and a modular backend architecture with support for multiple execution environments.

## Architecture

### Components
- **Frontend:** React 18 application built with Vite, TypeScript, and Tailwind CSS. It uses TanStack Query for state management and communicates with the backend via REST and WebSockets.
- **Backend:** The project contains two backend implementations:
  - **Python (FastAPI):** Located in `backend/`. A comprehensive solution using FastAPI, SQLAlchemy (PostgreSQL), Celery, and Redis. This appears to be the feature-complete, original implementation.
  - **Bun (TypeScript):** Located in `backend-bun/`. A high-performance, lightweight alternative using the Bun runtime and SQLite. **Note:** The current `Makefile` builds this version by default for the `netauto-backend` image.
- **Microservice:** `network-microservice/` contains a Python-based service, likely for specific network interactions or offloading tasks.
- **Database:** PostgreSQL is the primary database for the Python backend. The Bun backend uses SQLite by default but may support others.
- **Infrastructure:** Kubernetes manifests (`k8s/`) and Docker Compose (`deploy/docker-compose.yml`) are provided for deployment.

### Key Technologies
- **Languages:** Python 3.11+, TypeScript
- **Web Frameworks:** FastAPI (Python), Native Bun HTTP (Bun)
- **Network Automation:** Nornir, NAPALM, Netmiko
- **Database:** PostgreSQL, SQLite, Redis
- **Containerization:** Docker, Kubernetes

## Directory Structure
- `backend/`: Python/FastAPI backend source code.
  - `app/`: Main application logic (API, automation, DB models).
  - `alembic/`: Database migration scripts.
- `backend-bun/`: Bun/TypeScript backend source code.
- `frontend/`: React frontend application.
- `network-microservice/`: Standalone Python microservice.
- `deploy/`: Deployment configuration (Dockerfiles, Docker Compose).
- `k8s/`: Kubernetes resource manifests.
- `docs/`: Detailed project documentation (Architecture, APIs).

## Building and Running

### Using Make
The project includes a `Makefile` to simplify building and deploying:

```bash
# Build all Docker images
make build

# Deploy to Kubernetes (requires kubectl context)
make deploy

# Clean up Kubernetes resources
make clean
```

### Local Development

#### Frontend
```bash
cd frontend
npm install
npm run dev
```
Access at `http://localhost:5173` (or configured port).

#### Backend (Python)
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload
```
Access API docs at `http://localhost:8000/docs`.

#### Backend (Bun)
```bash
cd backend-bun
bun install
bun run index.ts
```

### Docker Compose
To run the full stack locally (using the Python backend configuration):
```bash
cd deploy
docker-compose up -d
```

## Development Conventions
- **Python:** Follows PEP 8. Type hinting is used extensively. Testing is done with `pytest`.
- **TypeScript:** Uses ESLint and Prettier. React components are functional with Hooks.
- **Commits:** Semantic versioning and conventional commits are encouraged.
- **Migrations:** All database schema changes for the Python backend must be accompanied by an Alembic migration script.

## Critical Configuration
- **Environment Variables:** Check `deploy/.env.example` for required variables (e.g., `SECRET_KEY`, `DATABASE_URL`).
- **Security:** Default credentials (e.g., for `admin`) are often set in initialization scripts (`init_db.py` or `index.ts`). **Change these in production.**
