# NetBox Integration

Connect a NetBox instance to sync device inventory into the platform for one or more customers. Configure the API endpoint and token, test connectivity, and run syncs on demand or automatically.

## Capabilities
- Per‑customer NetBox configuration with name, API URL, API token [1]
- Sync frequency (manual to periodic) and default credential assignment for newly synced devices [1]
- Optional filters: site, tenant, role, status (comma‑separated slugs) [1]
- Test Connection action with NetBox version display on success [2]
- Sync Now action with optional “Full sync” to update all devices [2]
- Status cards and recent sync logs (created/updated/skipped/failed) [3]

## UI
- Settings → NetBox Integration → List: shows all configurations and their last sync status [4]
- Configure NetBox: add a new configuration or edit an existing one [1]
- Detail page: actions (Test Connection, Sync Now), last sync summary, and recent logs [2][3]
- Sync Logs: tabular history with status and counters [3]

## Operational Notes
- Keep the API token secure; UI obfuscates existing tokens on edit [1]
- Use filters to limit scope to intended sites/tenants/roles
- Assign a default credential so newly synced devices can be managed immediately
- Automatic syncs depend on the configured frequency and deployment scheduler

## Sources
1. NetBox form template: settings/_netbox_form.html (fields, defaults, filters) in PR #60
2. NetBox actions: settings/_netbox_test_result.html and settings/_netbox_sync_result.html in PR #60
3. Sync logs UI: settings/_netbox_sync_logs_table.html and settings/netbox_sync_logs.html in PR #60
4. List/detail pages: settings/netbox_list.html and settings/netbox_detail.html in PR #60
   https://github.com/lammesen/networkautomation/pull/60
