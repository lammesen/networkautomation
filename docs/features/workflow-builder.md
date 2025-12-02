# Visual Workflow Builder (Operators)

Design and run multi-step automation with a drag-and-drop canvas. Combine service jobs, branching logic, data transforms, and notifications into repeatable workflows.

## Access & Roles
- URL: `/workflows/builder/`
- Roles: `operator` or `admin` (view/edit/run). Viewers are blocked.
- Tenant scoping: Workflows are scoped to the current customer's data; only your assigned customers are visible.

## Quick Start
1. Open the builder and pick an existing workflow from the selector or start with a blank canvas.
2. Drag node types from the **Nodes** list:
   - **Service**: `run_commands`, `config_backup`, `compliance_check` (queues jobs; default is simulated).
   - **Logic**: `condition` (if/else), `switch`.
   - **Data**: `set_variable`, `input`, `transform`.
   - **Notification**: `notify` (log-only).
3. Click a node, choose **Start link**, then click the target node to connect. Dashed edges mean they have conditions.
4. Select a node to edit its name, type, and `config` JSON (targets, payloads, conditions).
5. Save. Saved workflows get a version bump; nodes/edges are persisted per customer.
6. Run:
   - Inline: click **Run** (sync) to execute immediately and view step statuses.
   - API: POST `/api/v1/workflows/{id}/run` with `{"inputs": {...}}` (set `{"async": true}` to enqueue).

## Node Config Cheatsheet
- **Service** (`category: service`)
  - `job_type`: one of `run_commands`, `config_backup`, `compliance_check`, etc.
  - `targets`/`filters`: device filters (e.g., `{"site": "lab"}`); stored in `target_summary_json`.
  - `payload`: job payload (e.g., commands list).
  - `simulate`: `true` to skip queueing and only log (default).
- **Logic**
  - `condition`: Python-like expression using `context`/`last` (e.g., `context.get("mode") == "blue"`).
  - `expression` (switch): value computed from context (e.g., `context.get("site")`).
- **Data**
  - `set_variable`: `key` + `value` to write into workflow context.
  - `transform`: `expression` returning a derived value.
  - `input`: passes initial run inputs into context.
- **Notification**
  - `message`, `channel` (`log` only for now).

## Execution & Logs
- Each run records steps and logs under `/api/v1/workflow-runs/`.
- Edge traversal:
  - If a node output contains `condition`, edges with labels matching `true`/`false` are followed; others are skipped.
  - If an edge has `condition`, it must evaluate to truthy to traverse.
- Outcomes: `success`, `partial` (some skipped), `failed`.
- Service nodes with `simulate=false` queue Jobs; job logs still stream separately at `/api/v1/jobs/{id}/logs`.

## Patterns to Try
- **Compliance then backup on pass**: `compliance_check` → `condition (status==passed)` → `config_backup`.
- **Reachability gate**: `run_commands` (ping) → `condition` → `run_commands` (show tech) else `notify`.
- **Target templating**: Preload `context` with `{"site": "lab"}` via `input` or `set_variable`, then reuse in service node `targets`.

## Notes & Limits
- Default is simulated runs—set `simulate=false` on service nodes to enqueue real jobs.
- No parallel lane UI yet; edges are processed in graph order with conditional skips.
- Templates/library: seed your own by cloning a workflow and adjusting configs.
