# API Quick Reference

## Authentication

### Login
```bash
POST /api/v1/auth/login
{
  "username": "string",
  "password": "string"
}
```

### Get Current User
```bash
GET /api/v1/auth/me
Authorization: Bearer {token}
```

## Devices

### List Devices
```bash
GET /api/v1/devices?site={site}&role={role}&vendor={vendor}&search={query}
```

### Get Device
```bash
GET /api/v1/devices/{id}
```

### Create Device
```bash
POST /api/v1/devices
{
  "hostname": "string",
  "mgmt_ip": "string",
  "vendor": "string",
  "platform": "string",
  "role": "string",
  "site": "string",
  "credentials_ref": 0,
  "enabled": true
}
```

### Update Device
```bash
PUT /api/v1/devices/{id}
{...updates...}
```

### Delete Device
```bash
DELETE /api/v1/devices/{id}
```

## Credentials

### List Credentials
```bash
GET /api/v1/credentials
```

### Create Credential
```bash
POST /api/v1/credentials
{
  "name": "string",
  "username": "string",
  "password": "string",
  "enable_password": "string"
}
```

## Jobs

### List Jobs
```bash
GET /api/v1/jobs?type={type}&status={status}
```

### Get Job
```bash
GET /api/v1/jobs/{id}
```

### Get Job Logs
```bash
GET /api/v1/jobs/{id}/logs
```

### Get Job Results
```bash
GET /api/v1/jobs/{id}/results
```

## Commands

### Run Commands
```bash
POST /api/v1/commands/run
{
  "targets": {
    "site": "string",
    "role": "string",
    "vendor": "string",
    "device_ids": [1, 2, 3]
  },
  "commands": ["show version", "show ip interface brief"],
  "timeout_sec": 30
}
```

## Configuration

### Backup Configs
```bash
POST /api/v1/config/backup
{
  "targets": {...},
  "source_label": "manual"
}
```

### Get Snapshot
```bash
GET /api/v1/config/snapshots/{id}
```

### List Device Snapshots
```bash
GET /api/v1/config/devices/{id}/snapshots
```

### Get Config Diff
```bash
GET /api/v1/config/devices/{id}/diff?from={snapshot_id}&to={snapshot_id}
```

### Preview Config Deployment
```bash
POST /api/v1/config/deploy/preview
{
  "targets": {...},
  "mode": "merge",
  "snippet": "interface GigabitEthernet0/1\n description UPLINK\n"
}
```

### Commit Config Deployment
```bash
POST /api/v1/config/deploy/commit
{
  "previous_job_id": 0,
  "confirm": true
}
```

## Compliance

### List Policies
```bash
GET /api/v1/compliance/policies
```

### Get Policy
```bash
GET /api/v1/compliance/policies/{id}
```

### Create Policy
```bash
POST /api/v1/compliance/policies
{
  "name": "string",
  "description": "string",
  "scope_json": {"role": "edge"},
  "definition_yaml": "..."
}
```

### Run Compliance Check
```bash
POST /api/v1/compliance/run
{
  "policy_id": 0
}
```

### List Results
```bash
GET /api/v1/compliance/results?policy_id={id}&device_id={id}&status={pass|fail|error}
```

### Get Device Compliance
```bash
GET /api/v1/compliance/devices/{id}
```

## Target Filters

All targeting APIs accept these filter parameters:

```json
{
  "site": "datacenter1",
  "role": "edge",
  "vendor": "cisco",
  "device_ids": [1, 2, 3]
}
```

Filters are combined with AND logic. Empty filters `{}` targets all enabled devices.

## Job Statuses

- `queued` - Job created, waiting for worker
- `running` - Job is being executed
- `success` - Job completed successfully on all devices
- `partial` - Job completed with some failures
- `failed` - Job failed completely

## Platform Support

| vendor  | platform | NAPALM driver | Netmiko type  |
|---------|----------|---------------|---------------|
| cisco   | ios      | ios           | cisco_ios     |
| cisco   | iosxe    | ios           | cisco_ios     |
| cisco   | iosxr    | iosxr         | cisco_xr      |
| cisco   | nxos     | nxos          | cisco_nxos    |
| arista  | eos      | eos           | arista_eos    |
| juniper | junos    | junos         | juniper_junos |

## Role-Based Access

- **viewer**: Read-only access to all resources
- **operator**: Can run commands, backup/deploy configs, run compliance
- **admin**: Full access including user and policy management

## Rate Limits

(To be implemented)

- Commands: 100 per hour
- Config changes: 20 per hour
- API requests: 1000 per hour

## Response Codes

- `200` - Success
- `201` - Created
- `202` - Accepted (async job started)
- `204` - No Content (delete success)
- `400` - Bad Request
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not Found
- `500` - Server Error

## Common cURL Examples

### Get Token
```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' \
  | jq -r '.access_token')
```

### List All Devices
```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/devices
```

### Run Show Version on All Devices
```bash
curl -X POST http://localhost:8000/api/v1/commands/run \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"targets":{},"commands":["show version"]}'
```

### Backup All Devices
```bash
curl -X POST http://localhost:8000/api/v1/config/backup \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"targets":{},"source_label":"daily"}'
```

### Check Job Status
```bash
JOB_ID=1
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/jobs/$JOB_ID
```

### Get Job Results
```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/jobs/$JOB_ID/results | jq
```
