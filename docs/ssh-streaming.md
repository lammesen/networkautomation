# SSH Streaming Architecture & Testing

## Overview

The live device terminal is backed by a dedicated async SSH service that uses `asyncssh`
and enforces:

- Connection/command timeouts, keepalive pings, and a global max-session limit (see
  `app/services/ssh/manager.py` and the `SSHSessionConfig` sourced from
  `app/core/config.py`).
- A structured websocket protocol exposed at
  `GET /api/v1/ws/devices/{device_id}/ssh` (`app/api/websocket.py`). Events emitted:
  - `connected`: includes device metadata and session id.
  - `command_ack`: server accepted the command.
  - `output`: stdout/stderr plus exit status for each command.
  - `error`: recoverable failures (auth, device disabled, etc).
  - `closed`: session termination reason.
  - `keepalive`: heartbeat so the UI can detect dropped tunnels.

The React terminal (`frontend/src/features/devices/components/DeviceTerminalDialog.tsx`)
consumes these events and renders system/user/device/error transcripts.

## Automated testing

```bash
# Install backend deps (creates backend/venv) and frontend deps
make bootstrap

# Run the focused SSH tests (service unit tests + websocket integration tests)
make ssh-test
```

`make ssh-test` executes `backend/app/tests/services/test_ssh_manager.py` and
`backend/app/tests/test_websocket.py`, which stub the async SSH layer and verify the
websocket contract.

## End-to-end manual test

1. Build the images and apply the Kubernetes manifests (Docker Desktop's Kubernetes
   shares the host image cache, so no registry push is required):

   ```bash
   make dev-up
   ```

2. In separate shells, port-forward the backend and frontend services:

   ```bash
   make k8s-port-forward-backend   # exposes FastAPI on http://localhost:8000
   make k8s-port-forward-frontend  # exposes React on http://localhost:3000
   ```

3. Watch backend logs to confirm `uvicorn` is ready (optional):

   ```bash
   kubectl logs -f deployment/backend -n default
   ```

4. Use the seeded `linux-lab-01` device (created by `init_db.py`) which targets the
   bundled `linux-device` container with the correct credentials (`testuser` /
   `testpassword`). If you deleted it, recreate a device whose `mgmt_ip` is
   `linux-device` and whose credentials match that container.

5. Open `http://localhost:3000`, log in as `admin`/`admin123`, navigate to Devices, and
   click **Terminal**. You should see the `connected` banner followed by streamed
   results for commands such as `hostname` or `uname -a`.

6. When finished, tear everything down:

   ```bash
   make dev-down
   ```

## Deployment helpers

- `make docker-build` – create backend, frontend, worker, linux-device, and helper
  images locally.
- `make deploy` – convenience target that builds the images and then runs
  `k8s-redeploy` (delete + apply all manifests under `k8s/`).

Refer to `docs/operations.md` for cluster-specific steps or customisations.

