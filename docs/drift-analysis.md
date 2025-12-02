# Configuration Drift Analysis

## Overview
The configuration drift analysis feature helps you track, visualize, and alert on configuration changes across your network devices over time. This is crucial for:

- **Security**: Detect unauthorized configuration changes
- **Troubleshooting**: Review configuration history to identify what changed
- **Compliance**: Ensure configuration changes follow policies
- **Change Management**: Validate that changes were intentional and properly documented

## Features

### 1. Drift Detection
- Automatically compare consecutive configuration snapshots
- Calculate additions, deletions, and modifications
- Generate human-readable change summaries
- Track who triggered each backup

### 2. Timeline View
- Visual timeline showing all configuration changes for a device
- Color-coded change magnitude (minor/moderate/major)
- Filter by time period (7/30/90/365 days)
- Quick links to view detailed diffs

### 3. Change Analytics
- Total changes count
- Lines added vs. deleted
- Average changes per drift
- Change frequency statistics

### 4. Alert System
- Automatic alerts for significant changes
- Configurable thresholds (default: 50 lines)
- Severity levels: info, warning, critical
- Alert lifecycle management (open → acknowledged → resolved)

## API Endpoints

### Detect Drift Between Snapshots
```bash
POST /api/v1/config/drift/detect
Content-Type: application/json

{
  "snapshot_from_id": 1,
  "snapshot_to_id": 2
}
```

**Response:**
```json
{
  "id": 1,
  "device": 1,
  "device_hostname": "router-1",
  "snapshot_from": 1,
  "snapshot_to": 2,
  "detected_at": "2025-12-01T22:30:00Z",
  "additions": 5,
  "deletions": 2,
  "changes": 7,
  "has_changes": true,
  "change_magnitude": "Minor changes",
  "diff_summary": "Interface configuration changed: ip address 10.0.0.2",
  "triggered_by": "admin"
}
```

### Analyze Device Drift
Analyze all consecutive snapshots for a device:

```bash
POST /api/v1/config/drift/analyze-device
Content-Type: application/json

{
  "device_id": 1
}
```

**Response:**
```json
{
  "device_id": 1,
  "drifts_analyzed": 5,
  "drifts": [...]
}
```

### Get Device Drift Timeline
```bash
GET /api/v1/config/drift/device/{device_id}?days=30
```

### Get Change Frequency Statistics
```bash
GET /api/v1/config/drift/device/{device_id}/frequency?days=30
```

**Response:**
```json
{
  "total_changes": 12,
  "total_additions": 45,
  "total_deletions": 23,
  "avg_changes_per_drift": 5.67,
  "days_analyzed": 30
}
```

### Drift Alerts API
```bash
# List alerts
GET /api/v1/config/drift/alerts/?status=open&severity=critical

# Acknowledge alert
POST /api/v1/config/drift/alerts/{id}/acknowledge

# Resolve alert
POST /api/v1/config/drift/alerts/{id}/resolve
{
  "resolution_notes": "Expected change from maintenance window"
}
```

## UI Views

### Drift Timeline
Navigate to: **Configurations → Drift Analysis**

Features:
- Select device and time period
- Visual timeline with color-coded change indicators
- Statistics cards (total changes, additions, deletions)
- Quick access to detailed diffs

### Drift Detail
Click on any drift from the timeline to see:
- Change magnitude and statistics
- Snapshot metadata (IDs, timestamps, triggered by)
- Full unified diff output with syntax highlighting
- Link to open in standard diff view

### Drift Alerts
Navigate to: **Configurations → Drift Analysis → View Alerts**

Features:
- Filter by status (open/acknowledged/resolved/ignored)
- Filter by severity (info/warning/critical)
- View alert details
- Quick links to associated drift analysis

## Usage Example

### 1. Create Configuration Snapshots
First, create some configuration snapshots using the backup feature:

```bash
POST /api/v1/config/backup
{
  "customer_id": 1,
  "device_ids": [1, 2, 3]
}
```

### 2. Analyze Drift
After collecting multiple snapshots, analyze drift:

```bash
POST /api/v1/config/drift/analyze-device
{
  "device_id": 1
}
```

### 3. View Timeline
Access the UI at `/config/drift/timeline?device_id=1` to see the visual timeline.

### 4. Review Alerts
Check `/config/drift/alerts` for any alerts triggered by significant changes.

## Configuration

### Alert Thresholds
The default threshold for creating alerts is 50 changed lines. You can customize this when calling the drift analysis:

```python
from webnet.config_mgmt.drift_service import DriftService

ds = DriftService()
drift = ds.detect_drift(snap1, snap2)
alert = ds.analyze_drift_for_alert(drift, threshold=100)  # Custom threshold
```

### Severity Levels
- **Critical**: Changes >= 2x threshold (default: 100+ lines)
- **Warning**: Changes >= threshold (default: 50-99 lines)
- **Info**: Changes < threshold (no alert created)

## Database Models

### ConfigDrift
Tracks drift between two snapshots:
- `device`: Device this drift belongs to
- `snapshot_from`: Earlier snapshot
- `snapshot_to`: Later snapshot
- `detected_at`: When drift was detected
- `additions`: Number of lines added
- `deletions`: Number of lines deleted
- `changes`: Total number of lines changed
- `has_changes`: Boolean flag for quick filtering
- `diff_summary`: Human-readable change summary
- `triggered_by`: User who triggered the backup

### DriftAlert
Alerts for unexpected changes:
- `drift`: Associated drift analysis
- `severity`: info/warning/critical
- `status`: open/acknowledged/resolved/ignored
- `message`: Alert message
- `detected_at`: When alert was created
- `acknowledged_by`: User who acknowledged
- `acknowledged_at`: Acknowledgment timestamp
- `resolution_notes`: Notes about resolution

## Testing

The feature includes comprehensive test coverage (17 tests):

```bash
# Run drift analysis tests
make backend-test -k test_drift_analysis

# Run all tests
make backend-test
```

Test categories:
- Drift detection (no changes, with changes, idempotency)
- Alert generation (minor/major changes, thresholds)
- Timeline and statistics
- API endpoints
- UI views

## Performance Considerations

1. **Drift Analysis**: Run drift analysis asynchronously for large devices
2. **Timeline Queries**: Limited to last 30 days by default
3. **Alert Generation**: Only creates alerts when threshold is exceeded
4. **Pagination**: UI views limit to 100 most recent records

## Integration with Existing Features

- **Config Snapshots**: Drift builds on existing snapshot functionality
- **Job System**: Tracks which job created each snapshot
- **Git Integration**: Drifts reference snapshots that may be synced to Git
- **RBAC**: All endpoints respect customer scoping and role permissions

## Future Enhancements

Potential improvements:
- Scheduled drift analysis jobs
- Email notifications for critical alerts
- Drift policies (whitelist expected changes)
- Cross-device drift comparison
- Machine learning for anomaly detection
- Integration with change management workflows
