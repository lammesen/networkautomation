# API Summary

## Authentication

* `POST /api/auth/login` — OAuth2 password grant. Returns `{access_token, refresh_token, token_type}`.
* `GET /api/auth/me` — Returns authenticated user profile.
* `POST /api/auth/bootstrap` — Creates the first admin account if none exist.
* `POST /api/auth/refresh` — Accepts `{refresh_token}` and issues a new access token.

## Devices

* `GET /api/devices` — List inventory with optional filters (`site`, `role`, `vendor`, `tag`, `search`, `enabled`).
* `POST /api/devices` — Create device (operator+).
* `GET /api/devices/{id}` — Retrieve device.
* `PUT /api/devices/{id}` — Update device (operator+).
* `DELETE /api/devices/{id}` — Delete device (admin).

## Jobs

* `GET /api/jobs` — List jobs with optional `status` and `job_type` filters.
* `GET /api/jobs/{job_id}` — Fetch job details including target and result summaries.
* `GET /api/jobs/{job_id}/logs` — Retrieve log stream snapshot with `limit`/`offset`.
* `GET /api/jobs/{job_id}/results` — Structured JSON stored by the worker for that job.
* `GET /ws/jobs/{job_id}` — WebSocket stream of live log events published by Celery tasks.

## Automation jobs

The Celery tasks defined in `app/jobs/tasks.py` expect a `Job` database row and execute:

* `run_commands_task(job_id, device_ids, commands, timeout)`
* `backup_configs(job_id, device_ids, source)`
* `preview_deploy(job_id, device_ids, snippet, mode)`
* `commit_deploy(job_id, device_ids, snippet, mode)`
* `compliance_task(job_id, device_ids, policy_id, definition)`

API wrappers enqueue these tasks using `POST /api/automation/...` endpoints:

* `POST /api/automation/commands` — payload `{targets, commands, timeout_sec}`.
* `POST /api/automation/backup` — payload `{targets, source}`.
* `POST /api/automation/deploy/preview` — payload `{targets, snippet, mode}` stores per-device diffs and returns `job_id`.
* `POST /api/automation/deploy/commit` — payload `{previous_job_id, confirm}` reuses preview targets/snippet.
* `POST /api/automation/compliance` — payload `{policy_id, targets}` executes `napalm_validate` style checks.

Target selectors accept device ID lists and filter arrays (`sites`, `roles`, `vendors`, `tags`, `include_disabled`).

## Configuration history

* `GET /api/config/devices/{device_id}/snapshots` — list snapshot metadata.
* `GET /api/config/snapshots/{snapshot_id}` — fetch config text.
* `GET /api/config/devices/{device_id}/diff?from_snapshot=<id>&to_snapshot=<id>` — unified diff.

## Compliance policies

* `GET /api/compliance/policies` — list YAML definitions and scopes.
* `POST /api/compliance/policies` — create policy (admin).
* `PUT /api/compliance/policies/{id}` / `DELETE /api/compliance/policies/{id}` — manage policies (admin).
* `GET /api/compliance/results` — filter stored device results (`policy_id`, `device_id`, `status`).
* `GET /api/compliance/devices/{device_id}` — summarize latest result per policy.
