# Deployment & DevOps Guide

Guide for deploying and operating the webnet application in production environments.

## Table of Contents
- [Environment Setup](#environment-setup)
- [Docker Build](#docker-build)
- [Kubernetes Deployment](#kubernetes-deployment)
- [Environment Variables](#environment-variables)
- [Database Migrations](#database-migrations)
- [Static Assets](#static-assets)
- [Monitoring](#monitoring)
- [Scaling](#scaling)
- [Backup & Recovery](#backup--recovery)

## Environment Setup

### Prerequisites
- Docker Desktop with Kubernetes (or Kubernetes cluster)
- `kubectl` 1.28+
- GNU Make
- Node.js + npm
- PostgreSQL 16+ (or use provided k8s manifest)
- Redis 7+ (or use provided k8s manifest)

### Quick Start
```bash
# Install dependencies
make bootstrap

# Build images and deploy
make dev-up

# Check status
make k8s-status

# Port-forward backend
make k8s-port-forward-backend
```

## Docker Build

### Backend Image
```dockerfile
# deploy/Dockerfile.backend
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=webnet.settings

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    libpq-dev \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY backend/pyproject.toml /app/
COPY backend/ /app/
RUN pip install --no-cache-dir -e .

# Build static assets
RUN cd /app && npm install && npm run build:css || true
RUN python manage.py collectstatic --noinput || true

EXPOSE 8000

CMD ["python", "-m", "daphne", "-b", "0.0.0.0", "-p", "8000", "webnet.asgi:application"]
```

### Build Commands
```bash
# Build backend image
docker build -f deploy/Dockerfile.backend -t netauto-backend:latest .

# Build all images
make docker-build
```

## Kubernetes Deployment

### Backend Deployment
```yaml
# k8s/backend.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
spec:
  replicas: 1
  selector:
    matchLabels:
      app: backend
  template:
    metadata:
      labels:
        app: backend
    spec:
      containers:
      - name: backend
        image: netauto-backend:latest
        ports:
        - containerPort: 8000
        envFrom:
        - secretRef:
            name: webnet-secrets
        env:
        - name: DATABASE_URL
          value: "postgresql://netauto:netauto@postgres:5432/netauto"
        - name: REDIS_URL
          value: "redis://redis:6379/0"
        - name: CELERY_BROKER_URL
          value: "redis://redis:6379/0"
        - name: CELERY_RESULT_BACKEND
          value: "redis://redis:6379/1"
        resources:
          requests:
            cpu: 200m
            memory: 256Mi
          limits:
            cpu: 500m
            memory: 512Mi
```

### Worker Deployment
```yaml
# k8s/worker.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend-worker
spec:
  replicas: 2
  selector:
    matchLabels:
      app: backend-worker
  template:
    metadata:
      labels:
        app: backend-worker
    spec:
      containers:
      - name: worker
        image: netauto-backend:latest
        command: ["celery", "-A", "webnet.core.celery:celery_app", "worker", "-l", "info"]
        envFrom:
        - secretRef:
            name: webnet-secrets
        env:
        - name: DATABASE_URL
          value: "postgresql://netauto:netauto@postgres:5432/netauto"
        - name: CELERY_BROKER_URL
          value: "redis://redis:6379/0"
```

### Deploy Commands
```bash
# Apply all manifests
make k8s-apply

# Delete all manifests
make k8s-delete

# Redeploy
make k8s-redeploy

# Check status
make k8s-status
```

## Environment Variables

### Required Variables
```bash
# Security
SECRET_KEY=<random-32-char-string>
ENCRYPTION_KEY=<fernet-key-base64>

# Database
DATABASE_URL=postgresql://user:pass@host:5432/dbname

# Redis
REDIS_URL=redis://host:6379/0
CELERY_BROKER_URL=redis://host:6379/0
CELERY_RESULT_BACKEND=redis://host:6379/1

# Django
DJANGO_SETTINGS_MODULE=webnet.settings
DEBUG=false
ALLOWED_HOSTS=example.com,www.example.com
```

### Optional Variables
```bash
# CORS
CORS_ALLOWED_ORIGINS=https://example.com
CSRF_TRUSTED_ORIGINS=https://example.com

# Admin
ADMIN_DEFAULT_PASSWORD=<password>

# Logging
LOG_LEVEL=INFO
```

### Generating Encryption Key
```python
from cryptography.fernet import Fernet
key = Fernet.generate_key()
print(key.decode())  # Use this as ENCRYPTION_KEY
```

### Kubernetes Secrets
```yaml
# k8s/secrets.yaml
apiVersion: v1
kind: Secret
metadata:
  name: webnet-secrets
type: Opaque
stringData:
  SECRET_KEY: "change-me-in-production"
  ENCRYPTION_KEY: "<generated-fernet-key>"
  ADMIN_DEFAULT_PASSWORD: "change-me"
```

## Database Migrations

### Running Migrations
```bash
# Local development
make migrate
# or
cd backend && python manage.py migrate

# In Kubernetes
kubectl exec deployment/backend -- python manage.py migrate

# Via Makefile
make migrate
```

### Migration Best Practices
1. Always backup database before migrations
2. Test migrations in staging first
3. Run migrations during maintenance window for production
4. Monitor migration progress

## Static Assets

### Building Static Assets
```bash
# Install npm dependencies
make backend-npm-install

# Build CSS
make backend-build-css

# Build JavaScript
make backend-build-js

# Build all static assets
make backend-build-static
```

### Static Files in Docker
Static files are built during Docker image build:
```dockerfile
RUN cd /app && npm install && npm run build:css
RUN python manage.py collectstatic --noinput
```

### Serving Static Files
In production, use a reverse proxy (nginx/traefik) or CDN to serve static files.

## Monitoring

### Health Checks
```bash
# Check backend health
curl http://localhost:8000/health/

# Check Kubernetes pods
kubectl get pods
kubectl logs deployment/backend
kubectl logs deployment/backend-worker
```

### Logging
```bash
# View backend logs
kubectl logs -f deployment/backend

# View worker logs
kubectl logs -f deployment/backend-worker

# View logs for specific pod
kubectl logs <pod-name>
```

### Metrics
- Job success/failure rates
- Device reachability status
- Celery task queue length
- Database connection pool usage

## Scaling

### Horizontal Scaling
```yaml
# Increase backend replicas
spec:
  replicas: 3

# Increase worker replicas
spec:
  replicas: 5
```

### Resource Limits
```yaml
resources:
  requests:
    cpu: 200m
    memory: 256Mi
  limits:
    cpu: 1000m
    memory: 1Gi
```

### Database Connection Pooling
Configure PostgreSQL connection pooling (pgBouncer) for high-traffic deployments.

## Backup & Recovery

### Database Backup
```bash
# PostgreSQL backup
pg_dump -h postgres -U netauto netauto > backup.sql

# Restore
psql -h postgres -U netauto netauto < backup.sql
```

### Config Snapshots
Config snapshots are stored in the database. Regular database backups include all snapshots.

### Disaster Recovery
1. Regular database backups (daily)
2. Backup encryption keys securely
3. Document recovery procedures
4. Test recovery process regularly

## Production Checklist

- [ ] Change all default passwords
- [ ] Generate strong SECRET_KEY
- [ ] Generate ENCRYPTION_KEY
- [ ] Set DEBUG=false
- [ ] Configure ALLOWED_HOSTS
- [ ] Set up HTTPS/TLS
- [ ] Configure CORS origins
- [ ] Set up database backups
- [ ] Configure monitoring
- [ ] Set resource limits
- [ ] Enable log aggregation
- [ ] Set up alerting
- [ ] Document runbooks
- [ ] Test disaster recovery

## References

- [Getting Started](./getting-started.md)
- [Architecture](./architecture.md)
- [Security Best Practices](./security.md)
