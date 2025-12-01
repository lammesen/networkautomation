# Django Model Reference

Complete reference for all Django models in the webnet application, including fields, relationships, and usage patterns.

## Table of Contents
- [Customer Models](#customer-models)
- [User Models](#user-models)
- [Device Models](#device-models)
- [Job Models](#job-models)
- [Config Management Models](#config-management-models)
- [Compliance Models](#compliance-models)
- [Model Relationships](#model-relationships)
- [Common Query Patterns](#common-query-patterns)

## Customer Models

### Customer
Tenant model for multi-tenancy. All data is scoped by customer.

**Location**: `webnet.customers.models.Customer`

**Fields**:
- `id` (AutoField): Primary key
- `name` (CharField, max_length=100, unique=True): Customer name
- `description` (TextField, blank=True, null=True): Optional description
- `created_at` (DateTimeField, auto_now_add=True): Creation timestamp

**Meta**:
- `ordering = ["name"]`

**Relationships**:
- `devices` (reverse ForeignKey from Device)
- `credentials` (reverse ForeignKey from Credential)
- `jobs` (reverse ForeignKey from Job)
- `compliance_policies` (reverse ForeignKey from CompliancePolicy)
- `users` (ManyToMany through User.customers)
- `ip_ranges` (reverse ForeignKey from CustomerIPRange)

**Example**:
```python
from webnet.customers.models import Customer

customer = Customer.objects.create(name="Acme Corp", description="Enterprise customer")
```

### CustomerIPRange
IP address ranges associated with a customer for network discovery and validation.

**Location**: `webnet.customers.models.CustomerIPRange`

**Fields**:
- `id` (AutoField): Primary key
- `customer` (ForeignKey to Customer): Owner customer
- `cidr` (CharField, max_length=45): CIDR notation (e.g., "192.168.1.0/24")
- `description` (TextField, blank=True, null=True): Optional description
- `created_at` (DateTimeField, auto_now_add=True): Creation timestamp

**Meta**:
- `indexes = [models.Index(fields=["customer"])]`

**Example**:
```python
from webnet.customers.models import CustomerIPRange

ip_range = CustomerIPRange.objects.create(
    customer=customer,
    cidr="192.168.1.0/24",
    description="Main office network"
)
```

## User Models

### User
Extended Django user model with role-based access control and customer assignments.

**Location**: `webnet.users.models.User`

**Base**: `django.contrib.auth.models.AbstractUser`

**Fields**:
- All standard Django User fields (username, email, password, etc.)
- `role` (CharField, choices=ROLE_CHOICES, default="viewer"): User role
  - Choices: `"viewer"`, `"operator"`, `"admin"`
- `customers` (ManyToManyField to Customer): Assigned customers

**Relationships**:
- `jobs` (reverse ForeignKey from Job)
- `api_keys` (reverse ForeignKey from APIKey)
- `created_policies` (reverse ForeignKey from CompliancePolicy)

**Example**:
```python
from webnet.users.models import User

user = User.objects.create_user(
    username="operator1",
    password="secure123",
    role="operator"
)
user.customers.add(customer1)
```

### APIKey
API authentication keys for programmatic access.

**Location**: `webnet.users.models.APIKey`

**Fields**:
- `id` (AutoField): Primary key
- `user` (ForeignKey to User): Owner user
- `name` (CharField, max_length=100): Key name/description
- `key_prefix` (CharField, max_length=8): First 8 chars of key (for display)
- `key_hash` (CharField, max_length=64, unique=True): SHA256 hash of full key
- `scopes` (JSONField, blank=True, null=True): Optional permission scopes
- `expires_at` (DateTimeField, blank=True, null=True): Optional expiration
- `last_used_at` (DateTimeField, blank=True, null=True): Last usage timestamp
- `is_active` (BooleanField, default=True): Active status
- `created_at` (DateTimeField, auto_now_add=True): Creation timestamp

**Meta**:
- `indexes = [models.Index(fields=["user"]), models.Index(fields=["key_hash"])]`

**Example**:
```python
from webnet.users.models import APIKey
import secrets
import hashlib

raw_token = secrets.token_urlsafe(32)
prefix = raw_token[:8]
key_hash = hashlib.sha256(raw_token.encode()).hexdigest()

api_key = APIKey.objects.create(
    user=user,
    name="CI/CD Key",
    key_prefix=prefix,
    key_hash=key_hash,
    scopes=["read", "write"]
)
```

## Device Models

### Credential
Encrypted device authentication credentials.

**Location**: `webnet.devices.models.Credential`

**Fields**:
- `id` (AutoField): Primary key
- `customer` (ForeignKey to Customer): Owner customer
- `name` (CharField, max_length=100): Credential name
- `username` (CharField, max_length=100): Username
- `_password` (TextField, db_column="password"): Encrypted password (stored)
- `_enable_password` (TextField, db_column="enable_password", blank=True, null=True): Encrypted enable password
- `created_at` (DateTimeField, auto_now_add=True): Creation timestamp

**Properties**:
- `password` (property): Decrypted password (read/write)
- `enable_password` (property): Decrypted enable password (read/write)

**Meta**:
- `unique_together = ("customer", "name")`
- `ordering = ["name"]`

**Relationships**:
- `devices` (reverse ForeignKey from Device)

**Example**:
```python
from webnet.devices.models import Credential

credential = Credential.objects.create(
    customer=customer,
    name="cisco-lab",
    username="admin",
    password="Cisco123!"  # Automatically encrypted
)

# Access decrypted password
print(credential.password)  # "Cisco123!"
```

### Device
Network device inventory entry.

**Location**: `webnet.devices.models.Device`

**Fields**:
- `id` (AutoField): Primary key
- `customer` (ForeignKey to Customer): Owner customer
- `hostname` (CharField, max_length=255): Device hostname
- `mgmt_ip` (CharField, max_length=45): Management IP address
- `vendor` (CharField, max_length=50): Vendor name (e.g., "cisco", "juniper")
- `platform` (CharField, max_length=50): Platform/OS (e.g., "ios", "junos")
- `role` (CharField, max_length=50, blank=True, null=True): Device role (e.g., "core", "edge")
- `site` (CharField, max_length=100, blank=True, null=True): Site/location
- `tags` (JSONField, blank=True, null=True): Flexible tags/metadata
- `credential` (ForeignKey to Credential, on_delete=PROTECT): Authentication credential
- `enabled` (BooleanField, default=True): Whether device is enabled
- `reachability_status` (CharField, max_length=20, blank=True, null=True): Last reachability check result
- `last_reachability_check` (DateTimeField, blank=True, null=True): Last check timestamp
- `created_at` (DateTimeField, auto_now_add=True): Creation timestamp
- `updated_at` (DateTimeField, auto_now=True): Last update timestamp

**Meta**:
- `unique_together = ("customer", "hostname")`
- `indexes = [models.Index(fields=["role"]), models.Index(fields=["site"]), models.Index(fields=["vendor"])]`
- `ordering = ["hostname"]`

**Relationships**:
- `config_snapshots` (reverse ForeignKey from ConfigSnapshot)
- `compliance_results` (reverse ForeignKey from ComplianceResult)
- `outgoing_links` (reverse ForeignKey from TopologyLink as local_device)
- `incoming_links` (reverse ForeignKey from TopologyLink as remote_device)

**Example**:
```python
from webnet.devices.models import Device

device = Device.objects.create(
    customer=customer,
    hostname="router1",
    mgmt_ip="192.168.1.1",
    vendor="cisco",
    platform="ios",
    role="core",
    site="datacenter1",
    tags={"environment": "production", "region": "us-east"},
    credential=credential,
    enabled=True
)
```

### TopologyLink
Network topology link between devices (discovered via LLDP/CDP).

**Location**: `webnet.devices.models.TopologyLink`

**Fields**:
- `id` (AutoField): Primary key
- `customer` (ForeignKey to Customer): Owner customer
- `local_device` (ForeignKey to Device): Source device
- `local_interface` (CharField, max_length=100): Local interface name
- `remote_device` (ForeignKey to Device, null=True, blank=True): Target device (if known)
- `remote_hostname` (CharField, max_length=255): Remote device hostname
- `remote_interface` (CharField, max_length=100): Remote interface name
- `remote_ip` (CharField, max_length=45, blank=True, null=True): Remote IP address
- `remote_platform` (CharField, max_length=100, blank=True, null=True): Remote platform
- `protocol` (CharField, max_length=10, default="lldp"): Discovery protocol
- `discovered_at` (DateTimeField, auto_now_add=True): Discovery timestamp
- `job_id` (IntegerField, blank=True, null=True): Job that discovered this link

**Meta**:
- `unique_together = ("customer", "local_device", "local_interface", "remote_hostname", "remote_interface")`
- `indexes = [models.Index(fields=["local_device"]), models.Index(fields=["remote_device"]), models.Index(fields=["customer"])]`

**Example**:
```python
from webnet.devices.models import TopologyLink

link = TopologyLink.objects.create(
    customer=customer,
    local_device=device1,
    local_interface="GigabitEthernet0/0",
    remote_device=device2,
    remote_hostname="router2",
    remote_interface="GigabitEthernet0/1",
    protocol="lldp",
    job_id=job.id
)
```

## Job Models

### Job
Asynchronous automation job tracking.

**Location**: `webnet.jobs.models.Job`

**Fields**:
- `id` (AutoField): Primary key
- `customer` (ForeignKey to Customer): Owner customer
- `type` (CharField, choices=TYPE_CHOICES): Job type
  - Choices: `"run_commands"`, `"config_backup"`, `"config_deploy_preview"`, `"config_deploy_commit"`, `"compliance_check"`, `"topology_discovery"`
- `status` (CharField, choices=STATUS_CHOICES, default="queued"): Job status
  - Choices: `"queued"`, `"scheduled"`, `"running"`, `"success"`, `"partial"`, `"failed"`, `"cancelled"`
- `user` (ForeignKey to User): User who created the job
- `requested_at` (DateTimeField, auto_now_add=True): Request timestamp
- `scheduled_for` (DateTimeField, blank=True, null=True): Scheduled execution time
- `started_at` (DateTimeField, blank=True, null=True): Execution start time
- `finished_at` (DateTimeField, blank=True, null=True): Execution end time
- `target_summary_json` (JSONField, blank=True, null=True): Target device filters/summary
- `result_summary_json` (JSONField, blank=True, null=True): Execution results summary
- `payload_json` (JSONField, blank=True, null=True): Job-specific payload data

**Meta**:
- `indexes = [models.Index(fields=["status"]), models.Index(fields=["type"]), models.Index(fields=["user"]), models.Index(fields=["customer"])]`

**Relationships**:
- `logs` (reverse ForeignKey from JobLog)
- `config_snapshots` (reverse ForeignKey from ConfigSnapshot)
- `compliance_results` (reverse ForeignKey from ComplianceResult)

**Example**:
```python
from webnet.jobs.models import Job
from webnet.jobs.services import JobService

js = JobService()
job = js.create_job(
    job_type="run_commands",
    user=user,
    customer=customer,
    target_summary={"filters": {"site": "datacenter1"}},
    payload={"commands": ["show version", "show interfaces"]}
)
```

### JobLog
Individual log entry for a job execution.

**Location**: `webnet.jobs.models.JobLog`

**Fields**:
- `id` (AutoField): Primary key
- `job` (ForeignKey to Job): Parent job
- `ts` (DateTimeField, auto_now_add=True): Log timestamp
- `level` (CharField, choices=LEVEL_CHOICES): Log level
  - Choices: `"DEBUG"`, `"INFO"`, `"WARN"`, `"ERROR"`
- `host` (CharField, max_length=255, blank=True, null=True): Device hostname (if applicable)
- `message` (TextField): Log message
- `extra_json` (JSONField, blank=True, null=True): Additional structured data

**Meta**:
- `indexes = [models.Index(fields=["job"]), models.Index(fields=["job", "ts"])]`
- `ordering = ["ts"]`

**Example**:
```python
from webnet.jobs.models import JobLog
from webnet.jobs.services import JobService

js = JobService()
js.append_log(job, level="INFO", host="router1", message="Command executed successfully")
js.append_log(job, level="ERROR", host="router2", message="Connection timeout")
```

## Config Management Models

### ConfigSnapshot
Device configuration snapshot with change detection.

**Location**: `webnet.config_mgmt.models.ConfigSnapshot`

**Fields**:
- `id` (AutoField): Primary key
- `device` (ForeignKey to Device): Target device
- `job` (ForeignKey to Job, null=True, blank=True): Job that created snapshot
- `created_at` (DateTimeField, auto_now_add=True): Snapshot timestamp
- `source` (CharField, max_length=50, default="manual"): Source label
- `config_text` (TextField): Full configuration text
- `hash` (CharField, max_length=64, editable=False): SHA256 hash of config (auto-generated)

**Meta**:
- `indexes = [models.Index(fields=["device"]), models.Index(fields=["created_at"])]`
- `ordering = ["-created_at"]`

**Special Methods**:
- `save()`: Automatically computes hash if config_text is provided

**Example**:
```python
from webnet.config_mgmt.models import ConfigSnapshot

snapshot = ConfigSnapshot.objects.create(
    device=device,
    job=job,
    source="scheduled",
    config_text="hostname router1\ninterface GigabitEthernet0/0\n..."
)
# Hash is automatically computed
print(snapshot.hash)  # SHA256 hash string
```

## Compliance Models

### CompliancePolicy
YAML-based compliance policy definition.

**Location**: `webnet.compliance.models.CompliancePolicy`

**Fields**:
- `id` (AutoField): Primary key
- `customer` (ForeignKey to Customer): Owner customer
- `name` (CharField, max_length=255): Policy name
- `description` (TextField, blank=True, null=True): Policy description
- `scope_json` (JSONField): Device filter criteria
- `definition_yaml` (TextField): NAPALM validation YAML
- `created_by` (ForeignKey to User): Creator user
- `created_at` (DateTimeField, auto_now_add=True): Creation timestamp
- `updated_at` (DateTimeField, auto_now=True): Last update timestamp

**Meta**:
- `unique_together = ("customer", "name")`
- `ordering = ["name"]`

**Relationships**:
- `results` (reverse ForeignKey from ComplianceResult)

**Example**:
```python
from webnet.compliance.models import CompliancePolicy

policy = CompliancePolicy.objects.create(
    customer=customer,
    name="Interface Compliance",
    description="Ensure all interfaces are enabled",
    scope_json={"role": "edge"},
    definition_yaml="""
- get_interfaces:
    - GigabitEthernet0/0:
        is_enabled: true
"""
)
```

### ComplianceResult
Result of a compliance check for a specific device.

**Location**: `webnet.compliance.models.ComplianceResult`

**Fields**:
- `id` (AutoField): Primary key
- `policy` (ForeignKey to CompliancePolicy): Applied policy
- `device` (ForeignKey to Device): Checked device
- `job` (ForeignKey to Job): Job that ran the check
- `ts` (DateTimeField, auto_now_add=True): Check timestamp
- `status` (CharField, max_length=20): Result status (e.g., "passed", "failed")
- `details_json` (JSONField): Detailed compliance results

**Meta**:
- `indexes = [models.Index(fields=["policy"]), models.Index(fields=["device"]), models.Index(fields=["ts"])]`
- `ordering = ["-ts"]`

**Example**:
```python
from webnet.compliance.models import ComplianceResult

result = ComplianceResult.objects.create(
    policy=policy,
    device=device,
    job=job,
    status="passed",
    details_json={"interfaces": {"GigabitEthernet0/0": {"is_enabled": True}}}
)
```

## Model Relationships

### Entity Relationship Diagram

```
Customer
├── Device (customer_id)
│   ├── ConfigSnapshot (device_id)
│   ├── ComplianceResult (device_id)
│   └── TopologyLink (local_device_id, remote_device_id)
├── Credential (customer_id)
│   └── Device (credential_id)
├── Job (customer_id)
│   ├── JobLog (job_id)
│   ├── ConfigSnapshot (job_id)
│   └── ComplianceResult (job_id)
├── CompliancePolicy (customer_id)
│   └── ComplianceResult (policy_id)
└── User (customers M2M)
    ├── Job (user_id)
    ├── APIKey (user_id)
    └── CompliancePolicy (created_by_id)
```

### Foreign Key Relationships

| Model | Field | Related Model | on_delete |
|-------|-------|---------------|-----------|
| Device | customer | Customer | CASCADE |
| Device | credential | Credential | PROTECT |
| Credential | customer | Customer | CASCADE |
| Job | customer | Customer | CASCADE |
| Job | user | User | CASCADE |
| JobLog | job | Job | CASCADE |
| ConfigSnapshot | device | Device | CASCADE |
| ConfigSnapshot | job | Job | SET_NULL |
| CompliancePolicy | customer | Customer | CASCADE |
| CompliancePolicy | created_by | User | CASCADE |
| ComplianceResult | policy | CompliancePolicy | CASCADE |
| ComplianceResult | device | Device | CASCADE |
| ComplianceResult | job | Job | CASCADE |
| TopologyLink | customer | Customer | CASCADE |
| TopologyLink | local_device | Device | CASCADE |
| TopologyLink | remote_device | Device | SET_NULL |
| CustomerIPRange | customer | Customer | CASCADE |
| APIKey | user | User | CASCADE |

## Common Query Patterns

### Get Devices for Customer
```python
devices = Device.objects.filter(customer_id=customer_id, enabled=True)
```

### Get Jobs with Related Data
```python
jobs = Job.objects.select_related("customer", "user").prefetch_related("logs").filter(
    customer_id=customer_id
)
```

### Get Latest Config Snapshot per Device
```python
from django.db.models import Max

latest_snapshots = ConfigSnapshot.objects.filter(
    device__customer_id=customer_id
).values("device").annotate(
    latest_created=Max("created_at")
).values("device", "latest_created")
```

### Get Compliance Results by Policy
```python
results = ComplianceResult.objects.select_related(
    "policy", "device"
).filter(
    policy_id=policy_id,
    status="failed"
).order_by("-ts")
```

### Count Devices by Vendor
```python
from django.db.models import Count

vendor_counts = Device.objects.filter(
    customer_id=customer_id
).values("vendor").annotate(
    count=Count("id")
).order_by("-count")
```

## References

- [Django Model Documentation](https://docs.djangoproject.com/en/stable/topics/db/models/)
- [Multi-Tenancy Patterns](./multi-tenancy.md)
- [Data Querying Patterns](./snippets.md#django-orm-queries)
