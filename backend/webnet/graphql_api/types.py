"""GraphQL types for webnet models."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional, List
from strawberry import auto
import strawberry_django
from strawberry_django import type as strawberry_django_type

from webnet.customers.models import Customer
from webnet.users.models import User
from webnet.devices.models import Device, Credential, Tag, DeviceGroup, TopologyLink
from webnet.jobs.models import Job, JobLog
from webnet.config_mgmt.models import ConfigSnapshot, ConfigTemplate
from webnet.compliance.models import CompliancePolicy, ComplianceResult

if TYPE_CHECKING:
    pass


@strawberry_django_type(Customer)
class CustomerType:
    """Customer type for multi-tenant organization."""

    id: auto
    name: auto
    description: auto
    ssh_host_key_policy: auto
    created_at: auto

    @strawberry_django.field
    def devices(self, info) -> List["DeviceType"]:
        """Devices belonging to this customer."""
        return self.devices.all()

    @strawberry_django.field
    def jobs(self, info) -> List["JobType"]:
        """Jobs for this customer."""
        return self.jobs.all()


@strawberry_django_type(User)
class UserType:
    """User type for authentication and authorization."""

    id: auto
    username: auto
    email: auto
    role: auto
    is_active: auto
    date_joined: auto

    @strawberry_django.field
    def customers(self, info) -> List[CustomerType]:
        """Customers this user has access to."""
        return self.customers.all()


@strawberry_django_type(Credential, exclude=["_password", "_enable_password"])
class CredentialType:
    """Device credential (passwords excluded from GraphQL)."""

    id: auto
    name: auto
    username: auto
    created_at: auto
    customer: CustomerType


@strawberry_django_type(Tag)
class TagType:
    """Tag for organizing devices."""

    id: auto
    name: auto
    color: auto
    description: auto
    category: auto
    created_at: auto
    customer: CustomerType


@strawberry_django_type(DeviceGroup)
class DeviceGroupType:
    """Device group for organizing and targeting devices."""

    id: auto
    name: auto
    description: auto
    group_type: auto
    filter_rules: auto
    created_at: auto
    customer: CustomerType


@strawberry_django_type(Device)
class DeviceType:
    """Network device."""

    id: auto
    hostname: auto
    mgmt_ip: auto
    vendor: auto
    platform: auto
    role: auto
    site: auto
    enabled: auto
    reachability_status: auto
    last_reachability_check: auto
    discovery_protocol: auto
    created_at: auto
    updated_at: auto
    customer: CustomerType
    credential: CredentialType

    @strawberry_django.field
    def tags(self, info) -> List[TagType]:
        """Tags assigned to this device."""
        return self.device_tags.all()

    @strawberry_django.field
    def jobs(self, info) -> List["JobType"]:
        """Jobs targeting this device."""
        from webnet.jobs.models import Job

        # Get jobs where this device is in the target summary
        return Job.objects.filter(
            customer=self.customer, target_summary_json__contains={"device_ids": [self.id]}
        ).order_by("-requested_at")[:50]

    @strawberry_django.field
    def config_snapshots(self, info) -> List["ConfigSnapshotType"]:
        """Configuration snapshots for this device."""
        return self.config_snapshots.order_by("-created_at")[:20]


@strawberry_django_type(Job)
class JobType:
    """Job for automation tasks."""

    id: auto
    type: auto
    status: auto
    requested_at: auto
    scheduled_for: auto
    started_at: auto
    finished_at: auto
    target_summary_json: auto
    result_summary_json: auto
    payload_json: auto
    customer: CustomerType
    user: UserType

    @strawberry_django.field
    def logs(self, info, limit: int = 100) -> List["JobLogType"]:
        """Logs for this job."""
        return self.logs.order_by("ts")[:limit]


@strawberry_django_type(JobLog)
class JobLogType:
    """Job log entry."""

    id: auto
    ts: auto
    level: auto
    host: auto
    message: auto
    extra_json: auto


@strawberry_django_type(
    ConfigSnapshot, fields=["id", "created_at", "source", "config_text", "hash"]
)
class ConfigSnapshotType:
    """Configuration snapshot."""

    id: auto
    created_at: auto
    source: auto
    config_text: auto
    hash: auto

    @strawberry_django.field
    def device(self, info) -> DeviceType:
        """Device this snapshot belongs to."""
        return self.device

    @strawberry_django.field
    def job(self, info) -> Optional[JobType]:
        """Job that created this snapshot."""
        return self.job


@strawberry_django_type(ConfigTemplate)
class ConfigTemplateType:
    """Configuration template."""

    id: auto
    name: auto
    description: auto
    category: auto
    template_content: auto
    variables_schema: auto
    platform_tags: auto
    is_active: auto
    created_at: auto
    customer: CustomerType


@strawberry_django_type(CompliancePolicy)
class CompliancePolicyType:
    """Compliance policy."""

    id: auto
    name: auto
    description: auto
    scope_json: auto
    definition_yaml: auto
    created_at: auto
    updated_at: auto
    customer: CustomerType
    created_by: UserType

    @strawberry_django.field
    def results(self, info, limit: int = 50) -> List["ComplianceResultType"]:
        """Recent compliance results for this policy."""
        return self.results.order_by("-ts")[:limit]


@strawberry_django_type(ComplianceResult)
class ComplianceResultType:
    """Compliance result."""

    id: auto
    ts: auto
    status: auto
    details_json: auto
    policy: CompliancePolicyType
    device: DeviceType
    job: JobType


@strawberry_django_type(TopologyLink)
class TopologyLinkType:
    """Topology link between devices."""

    id: auto
    local_device: DeviceType
    local_interface: auto
    remote_device: Optional[DeviceType]
    remote_interface: auto
    remote_hostname: auto
    remote_ip: auto
    remote_platform: auto
    protocol: auto
    discovered_at: auto
