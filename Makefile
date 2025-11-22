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

BUN         ?= bun
DOCKER      ?= docker
KUBECTL     ?= kubectl
K8S_NAMESPACE ?= default
K8S_MANIFESTS := \
	k8s/pvc.yaml \
	k8s/postgres.yaml \
	k8s/redis.yaml \
	k8s/services.yaml \
	k8s/backend.yaml \
	k8s/frontend.yaml \
	k8s/network-microservice.yaml \
	k8s/worker.yaml \
	k8s/linux-device.yaml
K8S_DELETE_MANIFESTS := \
	k8s/linux-device.yaml \
	k8s/worker.yaml \
	k8s/network-microservice.yaml \
	k8s/frontend.yaml \
	k8s/backend.yaml \
	k8s/services.yaml \
	k8s/redis.yaml \
	k8s/postgres.yaml \
	k8s/pvc.yaml

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
	@echo "  frontend-install     Install frontend deps via Bun"
	@echo "  bootstrap            Install both backend & frontend deps"
	@echo
	@echo "Quality & Tests:"
	@echo "  backend-lint         Run Ruff + Black check"
	@echo "  backend-test         Run backend pytest suite"
	@echo "  ssh-test             Run SSH service + websocket tests"
	@echo "  frontend-build       Build frontend (vite)"
	@echo "  test                 Run backend tests + frontend build"
	@echo
	@echo "Runtime:"
	@echo "  dev                  Backend tests + frontend build (quick confidence)"
	@echo "  docker-build         Build all Docker images"
	@echo "  dev-up               Build images then apply k8s manifests"
	@echo "  dev-down             Tear down k8s manifests"
	@echo "  deploy               Build images and redeploy k8s manifests"
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

.PHONY: frontend-install
frontend-install:
	cd frontend && $(BUN) install

.PHONY: bootstrap
bootstrap: backend-install frontend-install

# -------------------------------------------------------------------
# Backend quality gates
# -------------------------------------------------------------------
.PHONY: backend-lint
backend-lint: venv
	$(RUFF) check backend/app
	$(BLACK) --check backend/app

.PHONY: backend-test
backend-test: venv
	cd backend && ../$(PYTHON_BIN) -m pytest

.PHONY: ssh-test
ssh-test: venv
	cd backend && ../$(PYTHON_BIN) -m pytest \
		app/tests/services/test_ssh_manager.py \
		app/tests/test_websocket.py

.PHONY: migrate
migrate:
	$(KUBECTL) exec deploy/backend -n $(K8S_NAMESPACE) -- python -m alembic upgrade head

.PHONY: seed-admin
seed-admin:
	$(KUBECTL) exec deploy/backend -n $(K8S_NAMESPACE) -- python init_db.py

# -------------------------------------------------------------------
# Frontend tasks
# -------------------------------------------------------------------
.PHONY: frontend-build
frontend-build:
	cd frontend && $(BUN) run build

.PHONY: frontend-dev
frontend-dev:
	cd frontend && $(BUN) run dev

# -------------------------------------------------------------------
# Combined convenience
# -------------------------------------------------------------------
.PHONY: test
test: backend-test frontend-build

.PHONY: dev
dev: backend-test frontend-build

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
	@echo "Building Network microservice..."
	$(DOCKER) build -t netauto-microservice:latest network-microservice/
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