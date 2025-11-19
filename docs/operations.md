# Operations Guide

## Local development

1. Install backend dependencies with `pip install -e backend/` and frontend deps with `npm install` in `frontend/`.
2. Run database migrations via `alembic upgrade head` inside `backend/`.
3. Start services for iterative work:
   ```bash
   uvicorn app.main:app --reload --app-dir backend/app
   celery -A celery_app.celery worker --loglevel=info
   cd frontend && npm run dev
   ```
4. Bootstrap an admin user with `POST /api/auth/bootstrap` then sign in via the React UI.
5. For a production-like stack run `docker compose -f deploy/docker-compose.yml up --build`.

## Device onboarding

* `POST /api/devices` with hostname, management IP, vendor, and optional credential reference.
* Devices can be filtered by site/role/tag via query params.

## Running command jobs

* UI: Navigate to **Run Commands**, enter optional device IDs, and paste CLI commands. The page dispatches `POST /api/automation/commands` and redirects to the job console.
* API: call `/api/automation/commands` with
  ```json
  {
    "targets": {"sites": ["nyc"], "roles": ["edge"]},
    "commands": ["show version", "show ip interface brief"],
    "timeout_sec": 60
  }
  ```
  Monitor `/api/jobs/{id}` or `/ws/jobs/{id}` for live logs.

## Backups and diffs

* UI: **Config Backup** lets operators choose device IDs + source label and dispatch `/api/automation/backup`.
* API: `POST /api/automation/backup` with `{ "targets": {...}, "source": "scheduled" }`.
* Snapshots can be listed via `GET /api/config/devices/{device_id}/snapshots` and diffed via `GET /api/config/devices/{device_id}/diff?from_snapshot=A&to_snapshot=B`.
* Each backup job only stores new snapshots when the running-config hash changes to conserve storage.

## Deploying snippets

1. Run a preview either from the UI (**Config Deploy → Preview changes**) or via `POST /api/automation/deploy/preview` (payload `{targets, snippet, mode: "merge"}`) and inspect diffs from `/api/jobs/{preview_job_id}/results`.
2. When satisfied, send `POST /api/automation/deploy/commit` with `{ "previous_job_id": <preview_job_id>, "confirm": true }`. This reuses the stored snippet/targets and executes Napalm `load_merge_candidate` + `commit_config`.
3. The UI renders per-device diffs and exposes a **Commit changes** button once preview results exist.

## Compliance

* Create/update policies via `POST /api/compliance/policies` with YAML content that matches `napalm_validate` format (see `docs/compliance_policies_example.yaml`).
* Trigger a run from the UI (**Compliance → Run now**) or call `POST /api/automation/compliance` with `{ "policy_id": 1, "targets": {"roles": ["edge"]} }`.
* Results are persisted in `compliance_results` and exposed through `GET /api/compliance/results` and the frontend compliance dashboard.
