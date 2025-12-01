.SHELL := /bin/bash

# -------------------------------------------------------------------
# Tooling
# -------------------------------------------------------------------
PYTHON      ?= python3
VENV_DIR    ?= backend/venv
PYTHON_BIN  := $(VENV_DIR)/bin/python
PIP_BIN     := $(VENV_DIR)/bin/pip
RUFF        := $(VENV_DIR)/bin/ruff
BLACK       := $(VENV_DIR)/bin/black
UVICORN     := $(VENV_DIR)/bin/uvicorn
DAPHNE      := $(VENV_DIR)/bin/daphne
CELERY      := $(VENV_DIR)/bin/celery

NPM         ?= npm
DOCKER      ?= docker
DOCKER_COMPOSE ?= docker compose
KUBECTL     ?= kubectl
K8S_NAMESPACE ?= default
K8S_MANIFESTS := \
	k8s/pvc.yaml \
	k8s/postgres.yaml \
	k8s/redis.yaml \
	k8s/services.yaml \
	k8s/secrets.yaml \
	k8s/backend.yaml \
	k8s/worker.yaml \
	k8s/linux-device.yaml \
	k8s/ingress.yaml
K8S_DELETE_MANIFESTS := \
	k8s/ingress.yaml \
	k8s/linux-device.yaml \
	k8s/worker.yaml \
	k8s/backend.yaml \
	k8s/secrets.yaml \
	k8s/services.yaml \
	k8s/redis.yaml \
	k8s/postgres.yaml \
	k8s/pvc.yaml

TEST_DATABASE_URL ?= sqlite:///db.sqlite3

# -------------------------------------------------------------------
# Convenience targets
# -------------------------------------------------------------------
.PHONY: help
help:
	@echo "Usage: make <target>"
	@echo
	@echo "Dev Environment:"
	@echo "  venv                 Create Python virtual environment"
	@echo "  backend-install      Install backend deps (dev)"
	@echo "  backend-npm-install  Install backend npm deps (React, shadcn, esbuild)"
	@echo "  backend-build-css    Build Tailwind CSS"
	@echo "  backend-build-js     Build React islands bundle"
	@echo "  backend-collectstatic     Collect Django static assets"
	@echo "  backend-build-static Build CSS + JS + collectstatic"
	@echo "  backend-watch        Watch mode for CSS + JS development"
	@echo "  bootstrap            Install backend and npm deps"

	@echo
	@echo "Quality & Tests:"
	@echo "  backend-lint         Run Ruff + Black check"
	@echo "  backend-typecheck    Run mypy against Django apps"
	@echo "  backend-format       Auto-format with Ruff+Black"
	@echo "  backend-test         Run backend pytest suite"
	@echo "  backend-js-check     Typecheck React islands (tsc --noEmit)"
	@echo "  backend-verify       Run lint + mypy + tests"
	@echo "  ssh-test             Run SSH service + websocket tests"
	@echo "  dev-backend          Start Daphne ASGI server (WebSocket support, requires .env)"
	@echo "  dev-backend-simple   Start Django runserver (no WebSocket, requires .env)"
	@echo "  dev-worker           Start Celery worker (requires .env)"
	@echo "  dev-beat             Start Celery beat (requires .env)"
	@echo "  dev-migrate          Run Django migrations locally"
	@echo "  dev-seed             Seed admin user locally"
	@echo "  dev-services         Start backend/worker/beat in tmux (Daphne + Celery)"
	@echo "  dev-login-ready      Install deps, build static, migrate, create superuser, run Daphne"
	@echo "  dev-login-ready-services Install deps, build static, migrate, seed, start Daphne/worker/beat"
	@echo "  dev-all              Migrate, seed, and start backend/worker/beat in tmux"

	@echo "  test                 Run backend tests"
	@echo "  k8s-apply            Apply backend/worker/infra manifests (no frontend)"
	@echo "  k8s-delete           Delete backend/worker/infra manifests"
	@echo
	@echo "Runtime:"
	@echo "  dev                  Backend tests"
	@echo "  docker-build         Build all Docker images"
	@echo "  dev-up               Build images then apply k8s manifests"
	@echo "  dev-down             Tear down k8s manifests"
	@echo "  deploy               Build images and redeploy k8s manifests"
	@echo "  compose-up           Start local stack (Django + Celery + Postgres + Redis)"
	@echo "  compose-down         Stop local stack and remove volumes"
	@echo "  compose-logs         Tail local stack logs"
	@echo "  migrate              Run Alembic migrations"
	@echo "  seed-admin           Seed admin user via init_db.py"
	@echo
	@echo "Kubernetes:"
	@echo "  k8s-apply            Apply manifests to $(K8S_NAMESPACE)"
	@echo "  k8s-delete           Delete manifests from $(K8S_NAMESPACE)"
	@echo "  k8s-status           Show pods + services"
	@echo "  k8s-port-forward-backend   Port-forward backend svc:8000"
	@echo "  k8s-port-forward-frontend  Port-forward frontend svc:3000"
	@echo "  k8s-redeploy         Delete then apply"
	@echo
	@echo "Everything:"
	@echo "  all                  bootstrap + test"

# -------------------------------------------------------------------
# Backend env / deps
# -------------------------------------------------------------------
$(VENV_DIR):
	$(PYTHON) -m venv $(VENV_DIR)

.PHONY: venv
venv: $(VENV_DIR)

.PHONY: backend-install
backend-install: venv
	$(PIP_BIN) install --upgrade pip
	$(PIP_BIN) install -e "backend/.[dev]"

.PHONY: backend-npm-install
backend-npm-install:
	cd backend && $(NPM) install

.PHONY: bootstrap
bootstrap: backend-install backend-npm-install

# -------------------------------------------------------------------
# Backend quality gates
# -------------------------------------------------------------------
.PHONY: backend-lint
backend-lint: venv
	$(RUFF) check backend/webnet
	$(BLACK) --check backend/webnet

.PHONY: backend-typecheck
backend-typecheck: venv
	cd backend && DJANGO_SETTINGS_MODULE=webnet.settings ../$(PYTHON_BIN) -m mypy webnet

.PHONY: backend-format
backend-format: venv
	$(RUFF) check backend/webnet --fix
	$(BLACK) backend/webnet

.PHONY: backend-test
backend-test: venv
	cd backend && DATABASE_URL=$(TEST_DATABASE_URL) DEBUG=true ../$(PYTHON_BIN) -m pytest

.PHONY: backend-js-check
backend-js-check:
	cd backend && npm run lint

.PHONY: backend-verify
backend-verify: backend-lint backend-typecheck backend-test

.PHONY: ssh-test
ssh-test: venv
	cd backend && ../$(PYTHON_BIN) -m pytest \
		webnet/tests/test_ssh_manager.py \
		webnet/tests/test_websocket.py

.PHONY: migrate
migrate: venv
	cd backend && ../$(PYTHON_BIN) manage.py migrate

.PHONY: seed-admin
seed-admin: venv
	cd backend && ../$(PYTHON_BIN) manage.py createsuperuser --no-input || true

# -------------------------------------------------------------------
# Frontend tasks (HTMX + React Islands + shadcn/ui)
# -------------------------------------------------------------------
.PHONY: backend-build-css
backend-build-css:
	cd backend && $(NPM) run build:css

.PHONY: backend-build-js
backend-build-js:
	cd backend && $(NPM) run build:js

.PHONY: backend-watch
backend-watch:
	cd backend && $(NPM) run watch

.PHONY: backend-collectstatic
backend-collectstatic: venv
	cd backend && ../$(PYTHON_BIN) manage.py collectstatic --noinput

.PHONY: backend-build-static
backend-build-static: backend-build-css backend-build-js backend-collectstatic

# -------------------------------------------------------------------
# Local dev runtime
# -------------------------------------------------------------------
.PHONY: dev-backend
dev-backend: venv
	cd backend && ../$(DAPHNE) -b 0.0.0.0 -p 8000 webnet.asgi:application

.PHONY: dev-backend-simple
dev-backend-simple: venv
	cd backend && ../$(PYTHON_BIN) manage.py runserver 0.0.0.0:8000

.PHONY: dev-worker
dev-worker: venv
	cd backend && ../$(CELERY) -A webnet.core.celery:celery_app worker -l info

.PHONY: dev-beat
dev-beat: venv
	cd backend && rm -f celerybeat-schedule* && ../$(CELERY) -A webnet.core.celery:celery_app beat -l info

.PHONY: dev-services
dev-services: venv
	# Start backend (Daphne), worker, and beat in background tmux session "netauto"
	# Daphne is used for WebSocket support (SSH terminal, job updates, etc.)
	# If tmux is not installed, fall back to spawning background processes.
	if command -v tmux >/dev/null 2>&1; then \
		tmux kill-session -t netauto >/dev/null 2>&1 || true; \
		tmux new-session -d -s netauto "cd backend && ../$(DAPHNE) -b 0.0.0.0 -p 8000 webnet.asgi:application"; \
		tmux split-window -h -t netauto:0 "cd backend && ../$(CELERY) -A webnet.core.celery:celery_app worker -l info"; \
		tmux select-pane -t netauto:0.0; \
		tmux split-window -v -t netauto:0 "cd backend && rm -f celerybeat-schedule* && ../$(CELERY) -A webnet.core.celery:celery_app beat -l info"; \
		tmux select-layout -t netauto even-vertical; \
		tmux set-option -t netauto mouse on; \
		tmux attach -t netauto; \
	else \
		( cd backend && ../$(DAPHNE) -b 0.0.0.0 -p 8000 webnet.asgi:application & echo $$! > /tmp/netauto-api.pid ); \
		( cd backend && ../$(CELERY) -A webnet.core.celery:celery_app worker -l info & echo $$! > /tmp/netauto-worker.pid ); \
		( cd backend && rm -f celerybeat-schedule* && ../$(CELERY) -A webnet.core.celery:celery_app beat -l info & echo $$! > /tmp/netauto-beat.pid ); \
		echo "Started Daphne/worker/beat without tmux. PIDs stored in /tmp/netauto-*.pid"; \
	fi

.PHONY: dev-frontend
dev-frontend:
	cd frontend && $(NPM) run dev -- --port 5173

.PHONY: dev-migrate
dev-migrate: venv
	cd backend && ../$(PYTHON_BIN) manage.py migrate

.PHONY: dev-seed
dev-seed: venv
	cd backend && ../$(PYTHON_BIN) manage.py createsuperuser --no-input || true

.PHONY: dev-login-ready
dev-login-ready: backend-install backend-npm-install backend-build-static dev-migrate dev-seed dev-services
	@echo "Daphne + worker + beat running (tmux 'netauto' or background); superuser seeded from .env"

.PHONY: dev-login-ready-services
dev-login-ready-services: backend-install backend-npm-install backend-build-static dev-migrate dev-seed dev-services
	@echo "Daphne + worker + beat running (tmux 'netauto' or background); superuser seeded from .env"

.PHONY: dev-all
dev-all: venv dev-migrate dev-seed dev-services
	@# Runs migrations, seeds admin, then starts all services in tmux

# -------------------------------------------------------------------
# Combined convenience
# -------------------------------------------------------------------
.PHONY: test
test: backend-test

.PHONY: dev
dev: backend-test

.PHONY: all
all: bootstrap test

# -------------------------------------------------------------------
# Container images
# -------------------------------------------------------------------
.PHONY: docker-build
docker-build:
	@echo "Building Backend image..."
	$(DOCKER) build -t netauto-backend:latest -f deploy/Dockerfile.backend .
	@echo "Building Frontend image..."
	$(DOCKER) build -t netauto-frontend:latest -f deploy/Dockerfile.frontend .
	@echo "Building Linux device..."
	$(DOCKER) build -t netauto-linux-device:latest -f deploy/Dockerfile.linux-device .

.PHONY: dev-up
dev-up: docker-build k8s-apply

.PHONY: dev-down
dev-down:
	$(MAKE) k8s-delete

.PHONY: deploy
deploy: docker-build k8s-redeploy

# -------------------------------------------------------------------
# Docker Compose (local stack)
# -------------------------------------------------------------------
.PHONY: compose-up
compose-up:
	$(DOCKER_COMPOSE) up -d --build

.PHONY: compose-down
compose-down:
	$(DOCKER_COMPOSE) down -v

.PHONY: compose-logs
compose-logs:
	$(DOCKER_COMPOSE) logs -f backend worker beat

# -------------------------------------------------------------------
# Kubernetes workflow
# -------------------------------------------------------------------
.PHONY: k8s-namespace
k8s-namespace:
	@if ! $(KUBECTL) get namespace $(K8S_NAMESPACE) >/dev/null 2>&1; then \
		$(KUBECTL) create namespace $(K8S_NAMESPACE); \
	fi

.PHONY: k8s-apply
k8s-apply: k8s-namespace
	@for manifest in $(K8S_MANIFESTS); do \
		echo "Applying $$manifest"; \
		$(KUBECTL) apply -n $(K8S_NAMESPACE) -f $$manifest; \
	done

.PHONY: k8s-delete
k8s-delete:
	@for manifest in $(K8S_DELETE_MANIFESTS); do \
		echo "Deleting $$manifest"; \
		$(KUBECTL) delete -n $(K8S_NAMESPACE) -f $$manifest --ignore-not-found=true; \
	done

.PHONY: k8s-redeploy
k8s-redeploy: k8s-delete k8s-apply

.PHONY: k8s-status
k8s-status:
	$(KUBECTL) get pods -n $(K8S_NAMESPACE)
	$(KUBECTL) get svc -n $(K8S_NAMESPACE)

.PHONY: k8s-port-forward-backend
k8s-port-forward-backend:
	$(KUBECTL) port-forward svc/backend 8000:8000 -n $(K8S_NAMESPACE)

.PHONY: k8s-port-forward-frontend
k8s-port-forward-frontend:
	$(KUBECTL) port-forward svc/frontend 3000:3000 -n $(K8S_NAMESPACE)
