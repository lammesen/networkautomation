 # User Guide
 
 This guide helps operators use the Network Automation platform via the web UI and (optionally) the REST API.
 
 ## Who is this for?
 - Network engineers and operators running day‑to‑day tasks
 - Read‑only viewers monitoring inventory, jobs, and compliance
 
 ## Access & Roles
 - Sign in at your deployment URL (default: http://localhost:8000)
 - Roles determine access:
   - Viewer: read‑only
   - Operator: can run jobs and manage devices/configs within their tenant
   - Admin: full access including user and policy management
 
 ## Navigation Overview
 - Dashboard: status cards and recent activity
 - Devices: inventory, add/import devices, device details
 - Jobs: job list and details with live logs
 - Config: configuration snapshots, diffs, and deployment
 - Compliance: policies, runs, and results
 - Topology: discovered links and tables
 - Commands: run ad‑hoc commands across devices
 
 ## Devices
 
 ### Add a device (UI)
 1. Go to Devices → Add
 2. Provide hostname, management IP, vendor/platform, site/role, and credentials reference
 3. Save to add to inventory
 
 ### Bulk import (UI)
 - Devices → Import: upload CSV with columns such as hostname, mgmt_ip, vendor, platform, site, role
 
 ### Device details
 - View recent jobs, configuration snapshots, and quick actions (backup, run commands, SSH)

### Bulk Device Onboarding
- Devices → Bulk Onboarding: scan IP ranges, run SNMP discovery, and test SSH credentials across ranges. Results go to the Discovery Queue for review and approval.
- See: Features → [Bulk Device Onboarding](./features/bulk-device-onboarding.md)

### Discovery Queue
- Review discovered items, approve with credential assignment, reject with notes, or ignore.
- Approved entries create Device records and link to the Device detail page.
 
 ## Running Commands
 1. Go to Commands → Run
 2. Select scope (e.g., by site, role, tags) or choose specific devices
 3. Enter one or more show commands
 4. Submit; a Job is created
 5. Open the Job from the toast or Jobs list to watch live log output
 
 Tips:
 - Use small test scopes first
 - Save commonly used command sets in your notes or scripts
 
 ## Job Monitoring
 - Jobs → List: filter by status, type, and date
 - Job → Detail: live logs via WebSocket, per‑device status and results
 
 ## Configuration Management
 
 ### Take backups
 1. Config → Backups → Run Backup
 2. Choose scope and source label (e.g., scheduled, manual)
 3. Submit and monitor the job
 
 ### View history and diffs
 - Config → Device snapshots: browse snapshots by device
 - Select a snapshot to view content
 - Use Diff to compare two snapshots
 
 ### Deploy changes (preview then commit)
 1. Config → Deploy → Preview: choose scope, mode (merge/replace), and snippet
 2. Review the generated diff in the job results
 3. If correct, run Deploy → Commit using the previous job id
 
 Best practice: always preview before committing.
 
 ## Compliance
 
 ### Create a policy
 1. Compliance → Policies → New Policy
 2. Provide name, description, scope, and definition (NAPALM validation YAML)
 
 Example YAML (simplified):
 ```yaml
 - get_facts:
     os_version: "15.6"
 ```
 
 ### Run compliance and view results
 1. Compliance → Run: select policy and (optional) scope
 2. Monitor the job
 3. Compliance → Results: filter by policy, device, or status
 
 ## SSH Terminal
 - From a device page, open SSH Terminal for interactive sessions
 - Output is streamed via WebSockets; sessions may be logged for auditing
 
 ## Topology
 - Topology → List: view discovered links and tables
 - Use filters to focus on a site or role
 
 ## API Access (optional)
 - Browseable API: http://localhost:8000/api/v1/
 - Authenticate with session or JWT (see API docs)
 
 Example: run commands via API
 ```bash
 curl -X POST http://localhost:8000/api/v1/commands/run \
   -H "Authorization: Bearer <TOKEN>" \
   -H "Content-Type: application/json" \
   -d '{
     "targets": {"site": "HQ"},
     "commands": ["show version", "show ip interface brief"]
   }'
 ```
 
 ## Troubleshooting
 - See [Troubleshooting](./troubleshooting.md)
 - For deployment/runtime issues, see [Operations](./operations.md)
 
 ## Safety Tips
 - Prefer small scopes before network‑wide operations
 - Always preview config changes
 - Review job logs for errors; retry failed devices only
 - Keep credentials updated and rotate regularly
 
 Happy automating! 🚀

## Tags & Groups
- Devices → Tags: create colored tags with optional category; device counts per tag are shown. Use tags for targeting commands, config, and compliance.
- Devices → Groups: create Static (manual) or Dynamic (rule‑based) groups. Dynamic groups compute membership from rules like vendor/platform/site/role.
- See: Features → [Device Tags and Groups](./features/device-groups-tags.md)

## NetBox Sync
- Settings → NetBox Integration: configure API URL/token per customer, test connection, run manual syncs, and view sync logs.
- Assign a default credential for newly synced devices and limit scope with filters (site/tenant/role/status).
- See: Integrations → [NetBox Integration](./integrations/netbox.md)

## Configuration Templates
- Templates: manage Jinja2 templates with variables schema and platform tags. Render previews by providing variable inputs.
- See: [Configuration Templates](./config-templates.md)
 