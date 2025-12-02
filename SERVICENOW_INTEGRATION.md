# ServiceNow CMDB Integration

This document describes the ServiceNow CMDB integration implementation for webnet.

## Overview

The ServiceNow integration provides bi-directional synchronization between webnet and ServiceNow CMDB, automatic incident creation on job failures, and change request management for configuration deployments.

## Features

### 1. CMDB Synchronization

**Export to ServiceNow:**
- Sync devices from webnet to ServiceNow Configuration Items (CIs)
- Create new CIs or update existing ones
- Customizable field mappings
- Track sync history with detailed logs

**Import from ServiceNow:**
- Import CIs from ServiceNow as webnet devices
- Auto-create devices with default credentials
- Update existing devices when bidirectional sync is enabled
- Filter CIs by class, location, company, or custom queries

### 2. Incident Management

**Automatic Incident Creation:**
- Automatically create ServiceNow incidents when jobs fail
- Includes job details, error messages, and logs
- Configurable assignment groups and categories
- Track incident status in webnet

**Manual Incident Management:**
- Update incident state (New, In Progress, Resolved, Closed)
- Add work notes and resolution notes
- Link incidents to specific jobs

### 3. Change Management

**Change Request Creation:**
- Create change requests for configuration deployments
- Link change requests to jobs
- Associate affected CIs (devices)
- Configurable risk and impact levels

**Change Request Updates:**
- Update change state through workflow
- Add work notes and closing notes
- Track change approval and implementation

### 4. Scheduled Sync

**Automatic Synchronization:**
- Schedule sync at configurable intervals (hourly, daily, weekly)
- Separate import and export jobs
- Retry on failure with exponential backoff
- Email notifications on sync errors

## Architecture

### Models

**ServiceNowConfig**
- Stores ServiceNow instance connection details
- Encrypted password storage
- Field mapping configuration
- Sync schedule and filters

**ServiceNowSyncLog**
- Audit trail for sync operations
- Detailed statistics (created, updated, skipped, failed)
- Error tracking and diagnostics

**ServiceNowIncident**
- Links ServiceNow incidents to webnet jobs
- Tracks incident state and resolution
- Stores incident number and sys_id

**ServiceNowChangeRequest**
- Links change requests to jobs
- Tracks change state and approval
- Stores change number and sys_id

### Service Layer

**ServiceNowService**
- Handles all ServiceNow API interactions
- Implements connection testing
- Manages authentication
- Provides sync operations

### API Endpoints

**Configuration Endpoints:**
```
GET    /api/integrations/servicenow/          # List configurations
POST   /api/integrations/servicenow/          # Create configuration
GET    /api/integrations/servicenow/{id}/     # Get configuration
PUT    /api/integrations/servicenow/{id}/     # Update configuration
DELETE /api/integrations/servicenow/{id}/     # Delete configuration
POST   /api/integrations/servicenow/{id}/test-connection/  # Test connection
POST   /api/integrations/servicenow/{id}/sync/             # Trigger manual sync
GET    /api/integrations/servicenow/{id}/logs/             # Get sync logs
```

**Incident Endpoints:**
```
GET    /api/integrations/servicenow-incidents/            # List incidents
GET    /api/integrations/servicenow-incidents/{id}/       # Get incident
PATCH  /api/integrations/servicenow-incidents/{id}/update_state/  # Update incident
```

**Change Request Endpoints:**
```
GET    /api/integrations/servicenow-changes/             # List changes
POST   /api/integrations/servicenow-changes/             # Create change
GET    /api/integrations/servicenow-changes/{id}/        # Get change
PATCH  /api/integrations/servicenow-changes/{id}/update_state/  # Update change
```

### Celery Tasks

**servicenow_sync_job**
- Manual sync trigger
- Supports import, export, or both directions
- Optional device filtering for export

**scheduled_servicenow_sync**
- Periodic task (runs every hour)
- Checks all configs for sync eligibility
- Respects sync frequency settings

**create_servicenow_incident**
- Automatically triggered on job failure
- Creates incident with job context
- Links incident to job in database

## Configuration

### ServiceNow Instance Setup

1. Create a user account in ServiceNow with appropriate permissions:
   - Read access to CMDB tables
   - Write access to CMDB tables (for export)
   - Write access to incident and change_request tables

2. Required ServiceNow Roles:
   - `itil` - Basic ITSM functionality
   - `cmdb_read` - Read CMDB
   - `cmdb_write` - Write CMDB
   - `incident_manager` - Manage incidents
   - `change_manager` - Manage changes

### Field Mappings

**Default Device to CMDB Mappings:**
```python
{
    "name": "hostname",           # webnet hostname -> ServiceNow CI name
    "ip_address": "mgmt_ip",      # webnet mgmt_ip -> ServiceNow ip_address
    "manufacturer": "vendor",     # webnet vendor -> ServiceNow manufacturer
    "os": "platform",             # webnet platform -> ServiceNow os
    "location": "site",           # webnet site -> ServiceNow location
    "u_role": "role",             # webnet role -> ServiceNow u_role (custom field)
}
```

**Default CMDB to Device Mappings:**
```python
{
    "hostname": "name",                          # ServiceNow name -> webnet hostname
    "mgmt_ip": "ip_address",                     # ServiceNow ip_address -> webnet mgmt_ip
    "vendor": "manufacturer.display_value",      # ServiceNow manufacturer -> webnet vendor
    "platform": "os",                            # ServiceNow os -> webnet platform
    "site": "location.display_value",            # ServiceNow location -> webnet site
    "role": "u_role",                            # ServiceNow u_role -> webnet role
}
```

Custom mappings can be defined per configuration in JSON format.

### Filters

**CI Class Filter:**
- Filter by ServiceNow CI class (e.g., `cmdb_ci_netgear`, `cmdb_ci_network_equipment`)

**Query Filters:**
- Use ServiceNow encoded query syntax
- Example: `operational_status=1^location=datacenter-1`

**Company:**
- Associate CIs with a specific ServiceNow company (sys_id)

## Usage Examples

### Create a ServiceNow Configuration

```python
from webnet.devices.models import ServiceNowConfig, Credential

config = ServiceNowConfig(
    customer=customer,
    name="Production ServiceNow",
    instance_url="https://mycompany.service-now.com",
    username="integration_user",
    cmdb_table="cmdb_ci_netgear",
    ci_class="cmdb_ci_netgear",
    sync_frequency="daily",
    auto_sync_enabled=True,
    bidirectional_sync=True,
    default_credential=credential,
    create_incidents_on_failure=True,
    incident_category="Network",
)
config.password = "secure_password"
config.save()
```

### Test Connection

```python
from webnet.devices.servicenow_service import ServiceNowService

service = ServiceNowService(config)
result = service.test_connection()

if result.success:
    print(f"Connected to ServiceNow {result.servicenow_version}")
else:
    print(f"Connection failed: {result.message}")
```

### Manual Sync

```python
from webnet.jobs.tasks import servicenow_sync_job

# Sync both directions
result = servicenow_sync_job.delay(config.id, direction="both")

# Export specific devices
result = servicenow_sync_job.delay(
    config.id, 
    direction="export",
    device_ids=[1, 2, 3]
)
```

### Create Change Request

```python
from webnet.devices.servicenow_service import ServiceNowService

service = ServiceNowService(config)
result = service.create_change_request(
    short_description="Update router configs",
    description="Deploying security hardening configs to production routers",
    justification="Required for security compliance",
    risk=2,  # Medium risk
    impact=2,  # Medium impact
    configuration_items=["abc123", "def456"],  # CI sys_ids
)

if result.success:
    print(f"Created change {result.change_number}")
```

## Security Considerations

1. **Credential Storage:**
   - Passwords are encrypted using Fernet symmetric encryption
   - Encryption key stored in environment variable `ENCRYPTION_KEY`
   - Never store plaintext passwords

2. **API Authentication:**
   - All endpoints require authentication
   - Role-based access control (RBAC) enforced
   - Customer scoping prevents data leakage

3. **Network Security:**
   - All ServiceNow API calls use HTTPS
   - Certificate validation enabled by default
   - Timeouts prevent hanging connections

4. **Data Privacy:**
   - Device data filtered by customer
   - Sync logs contain no sensitive data
   - API tokens not exposed in logs or responses

## Troubleshooting

### Connection Test Fails

**Issue:** "Authentication failed - check username and password"
- **Solution:** Verify ServiceNow credentials are correct
- Check if account is active and not locked
- Ensure user has required roles

**Issue:** "Failed to connect - check instance URL"
- **Solution:** Verify instance URL is correct
- Ensure URL includes protocol (https://)
- Check network connectivity and firewall rules

### Sync Errors

**Issue:** "No default credential configured"
- **Solution:** Configure a default credential for importing devices

**Issue:** "Conflict: Device already exists"
- **Solution:** Enable bidirectional sync to update existing devices
- Or manually resolve conflicts before syncing

### Incident Creation Fails

**Issue:** "No incident creation config"
- **Solution:** Ensure `create_incidents_on_failure` is enabled
- Verify ServiceNow config exists for the customer

**Issue:** "Incident already exists for job"
- **Solution:** Each job can only have one incident
- Update existing incident instead of creating new one

## Testing

Comprehensive test suite included with 22 tests covering:
- Model encryption and validation
- Service layer functionality
- API endpoint permissions
- Celery task execution
- Error handling and edge cases

Run tests:
```bash
cd backend
./venv/bin/python -m pytest webnet/tests/test_servicenow_integration.py -v
```

## Future Enhancements

1. **Enhanced CMDB Sync:**
   - Support for relationships between CIs
   - Sync CI hierarchy and dependencies
   - Custom CI attributes mapping

2. **Incident Automation:**
   - Auto-resolve incidents when jobs succeed
   - Escalation rules for long-running incidents
   - Custom incident templates

3. **Change Management:**
   - Approval workflow integration
   - Risk assessment automation
   - Post-implementation review

4. **Performance:**
   - Batch operations for large syncs
   - Delta sync to reduce API calls
   - Caching for frequently accessed data

5. **Monitoring:**
   - Grafana dashboards for sync metrics
   - Alerting on sync failures
   - Performance analytics

## References

- [ServiceNow REST API Documentation](https://docs.servicenow.com/bundle/tokyo-application-development/page/integrate/inbound-rest/concept/c_RESTAPI.html)
- [ServiceNow CMDB Documentation](https://docs.servicenow.com/bundle/tokyo-servicenow-platform/page/product/configuration-management/concept/c_ITILConfigurationManagement.html)
- [ServiceNow Incident Management](https://docs.servicenow.com/bundle/tokyo-it-service-management/page/product/incident-management/concept/c_IncidentManagement.html)
- [ServiceNow Change Management](https://docs.servicenow.com/bundle/tokyo-it-service-management/page/product/change-management/concept/c_ITILChangeManagement.html)
