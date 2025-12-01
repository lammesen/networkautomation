# Bulk Device Onboarding

Discover and onboard devices at scale using IP scanning, SNMP discovery, and credential testing. This feature lets you scan one or more customer IP ranges, identify reachable network devices, enqueue them for review, and approve or reject additions to inventory.

## What you can do
- Scan multiple CIDR ranges (e.g., 192.168.1.0/24) for candidate devices [1]
- Use SNMP (v2c or v3) to fingerprint vendor, platform, and software version [1]
- Test one or more stored credentials over SSH to find a working login [1]
- Review results in a Discovery Queue, then approve, reject, or ignore items [1]
- Assign a credential and optional vendor/platform overrides at approval time [1]

## UI: Bulk Onboarding
Path: Devices → Bulk Onboarding

1) Enter IP ranges in CIDR notation (comma‑separated)
2) Pick credentials to test (per‑customer)
3) Optional: enable SNMP discovery and set community/version
4) Optional: enable SSH credential testing and custom port list
5) Start Scan → A background Job is created; a toast links to the Job detail [1]

A summary shows Pending/Approved/Rejected counts and quick links to the Discovery Queue.

## UI: Discovery Queue
Path: Devices → Discovery Queue

- Columns: Hostname, IP, Vendor/Platform, Source, Credential (match/failed/untested), Status, Discovered at, Actions [1]
- Actions on Pending:
  - Approve → choose credential, optional vendor/platform overrides
  - Reject → with optional notes
  - Ignore → hide without decision
- Approved entries link to the created Device page when inventory records are created [1]

## API (overview)
The backend exposes serializers and endpoints to support scanning and approval flows:
- IP range scan request/response models for bulk discovery [2]
- Credential testing request/response models [2]
- Discovered device list, approve, and reject/ignore actions [2]

Refer to the Browseable API at /api/v1/ for the exact paths and to the OpenAPI document if your deployment includes schema generation.

## Tips & Limits
- Start with small ranges and a minimal credential set, then expand scope
- Use Customer IP Ranges to maintain authorized scan prefixes
- SNMP discovery can quickly fingerprint many devices; combine with SSH tests for high confidence
- Approve in batches after sorting by vendor/platform

## Related
- Device Tags and Groups — use tags/groups after onboarding for targeting [3]
- NetBox Sync — optionally seed devices from NetBox, then use Bulk Onboarding for gaps [4]

## Sources
1. PR #60 UI templates for Bulk Onboarding and Discovery Queue (bulk_onboarding.html, discovery_queue.html, _discovery_queue_table.html, _scan_result.html)
   https://github.com/lammesen/networkautomation/pull/60
2. Backend serializers added for IP scans, credential tests, and discovery actions in webnet/api/serializers.py (Issue #40 section)
3. Device tagging/grouping UI templates (groups.html, group_detail.html, _groups_table.html, _group_devices.html, tags.html, _tags_table.html) in PR #60
4. NetBox integration settings UI templates (netbox_list.html, netbox_detail.html, _netbox_form.html, _netbox_test_result.html, _netbox_sync_result.html, netbox_sync_logs.html) in PR #60
