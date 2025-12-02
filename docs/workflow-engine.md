# Workflow Engine (Developers)

Implementation notes for the visual workflow builder introduced in `feature/workflow-builder`. Covers data model, API surface, execution, and extension points.

## Data Model
- App: `webnet.workflows` (enabled in `INSTALLED_APPS`).
- Core tables:
  - `Workflow`: customer-scoped definition with `version`, `metadata`, `is_active`, `created_by/updated_by`.
  - `WorkflowNode`: graph nodes; `ref` (UUID) used for edges and serialization; `category` (`service`, `logic`, `data`, `notification`), `type`, `config`, `ui_state`, positional data.
  - `WorkflowEdge`: directed edges linking `source`/`target` nodes with optional `condition`, `label`, `is_default`.
  - `WorkflowRun`: execution record with `inputs`, `outputs`, `summary`, `status`, timestamps, `version`.
  - `WorkflowRunStep` / `WorkflowRunLog`: per-node status and log stream.
- Initial migration: `webnet/workflows/migrations/0001_initial.py`.

## API Surface (DRF)
- Routes: `/api/v1/workflows/` (CRUD) and `/api/v1/workflow-runs/` (read-only).
- Run action: `POST /api/v1/workflows/{id}/run` with `{"inputs": {...}, "async": false}`.
  - Async mode enqueues Celery task `workflows.execute`; sync runs inline.
  - Customer scoping via `CustomerScopedQuerysetMixin`; object checks via `ObjectCustomerPermission`.
- Serializers:
  - `WorkflowSerializer`: embeds `nodes` and `edges` (ref-based). Updating nodes/edges bumps `version` and rewrites edges.
  - `WorkflowRunSerializer`: includes steps and logs for UI consumption.

## Execution Path
- Entry points:
  - Inline: `WorkflowExecutor` (synchronous).
  - Celery: `workflows.execute` task → `WorkflowExecutor`.
- Traversal:
  - Builds `indegree` map; executes nodes with no incoming edges first; conditionally enqueues successors.
  - Edge traversal rules:
    - Edge `condition` is evaluated via restricted `eval` (`context`, `last` output available; safe builtins only).
    - If a node output contains `condition`, edges with label matching `true`/`false` are preferred; otherwise truthy → follow, falsey → skip.
  - Unvisited nodes are marked `skipped`; run status becomes `partial` if any skipped, `failed` on execution errors, else `success`.
- Node handlers:
  - `service`: resolves `job_type` and calls `JobService.create_job` unless `simulate` is true (default). `targets`/`filters` map to `target_summary_json`; `payload` is passed through.
  - `logic`: `condition`/`switch`/`loop` (loop currently returns metadata only).
  - `data`: `set_variable` (writes to context), `transform`, `input` passthrough.
  - `notification`: log-only marker (`channel` currently `log`).
- Context handling: `run.inputs` seeds `context`; `set_variable` and node outputs with `context` merge into `context` for downstream evaluation.

## UI / Island
- Template: `backend/templates/workflows/builder.html` hydrates `WorkflowBuilder` island.
- Island: `backend/static/src/components/islands/WorkflowBuilder.tsx`.
  - Uses `vis-network` to render nodes/edges, maintain selections, and POST/PUT to `/api/v1/workflows/`.
  - `runEndpoint` prop hits `/workflows/{id}/run`; supports inline execution and run status display.
  - Palette entries are provided from the view (`WorkflowBuilderView`) to keep server-authoritative node defaults.
  - Navigation entry in `AppSidebar` under Tools → Workflows.

## RBAC & Multi-Tenancy
- Views and APIs enforce:
  - `RolePermission` (`operator`/`admin` can write; `viewer` read-only where exposed).
  - `CustomerScopedQuerysetMixin` on viewsets; workflows/runs filtered by assigned customers.
  - UI view restricts access to `operator`/`admin` and filters workflows by customer set.

## Extending
- Add a new service type:
  1) Add `job_type` string handling in `WorkflowExecutor._execute_service_node` if special payload mapping is needed.
  2) Ensure downstream Celery task exists for the job type (Jobs app).
  3) Expose palette metadata in `WorkflowBuilderView` (server-side palette list).
- Add logic/data transformations: extend `_execute_logic_node` / `_execute_data_node` with guarded eval or explicit handlers.
- Adjust evaluation safety: `_safe_eval` restricts builtins; update carefully and prefer deterministic helpers.
- UI tweaks: update palette/server props in `WorkflowBuilderView`; island consumes server props without static registry.

## Testing
- New coverage: `backend/webnet/tests/test_workflows.py` validates branching behavior and tenant scoping for API + run.
- Run focused test: `cd backend && ../venv/bin/python -m pytest webnet/tests/test_workflows.py -v`.
- For end-to-end UI smoke, ensure migrations applied and build static assets before manual testing.

## Deployment Notes
- Migration required (`manage.py migrate`).
- Celery worker must include the new task module (default autodiscovery handles it).
- Static assets must be rebuilt so the WorkflowBuilder island is available (`make backend-build-static` or `npm run build` in `backend`).
