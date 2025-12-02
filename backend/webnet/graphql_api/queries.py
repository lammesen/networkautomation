"""GraphQL queries with customer scoping."""

from __future__ import annotations

from typing import List, Optional

import strawberry
from django.db.models import Q
from strawberry.types import Info

from webnet.compliance.models import CompliancePolicy, ComplianceResult
from webnet.config_mgmt.models import ConfigSnapshot, ConfigTemplate
from webnet.customers.models import Customer
from webnet.devices.models import Credential, Device, Tag, TopologyLink
from webnet.jobs.models import Job
from webnet.users.models import User

from .auth import IsAuthenticated
from .types import (
    CompliancePolicyType,
    ComplianceResultType,
    ConfigSnapshotType,
    ConfigTemplateType,
    CredentialType,
    CustomerType,
    DeviceType,
    JobType,
    TagType,
    TopologyLinkType,
    UserType,
)

# Maximum number of items that can be returned in a single query
MAX_LIMIT = 1000


def get_user_from_info(info: Info) -> Optional[User]:
    """Extract user from info context."""
    request = (
        info.context.get("request") if isinstance(info.context, dict) else info.context.request
    )
    return request.user if request and hasattr(request, "user") else None


def get_customer_ids_for_user(user: User) -> List[int]:
    """Get list of customer IDs the user has access to."""
    if not user or not user.is_authenticated:
        return []
    if getattr(user, "role", "viewer") == "admin":
        # Admin can access all customers
        return list(Customer.objects.values_list("id", flat=True))
    return list(user.customers.values_list("id", flat=True))


@strawberry.type
class Query:
    """GraphQL query root with customer-scoped queries."""

    @strawberry.field(permission_classes=[IsAuthenticated])
    def me(self, info: Info) -> Optional[UserType]:
        """Get current authenticated user."""
        user = get_user_from_info(info)
        if user and user.is_authenticated:
            return user
        return None

    @strawberry.field(permission_classes=[IsAuthenticated])
    def customers(self, info: Info) -> List[CustomerType]:
        """List customers the user has access to."""
        user = get_user_from_info(info)
        customer_ids = get_customer_ids_for_user(user)
        return list(Customer.objects.filter(id__in=customer_ids))

    @strawberry.field(permission_classes=[IsAuthenticated])
    def customer(self, info: Info, id: int) -> Optional[CustomerType]:
        """Get a specific customer by ID."""
        user = get_user_from_info(info)
        customer_ids = get_customer_ids_for_user(user)
        try:
            return Customer.objects.get(id=id, id__in=customer_ids)
        except Customer.DoesNotExist:
            return None

    @strawberry.field(permission_classes=[IsAuthenticated])
    def devices(
        self,
        info: Info,
        customer_id: Optional[int] = None,
        hostname: Optional[str] = None,
        vendor: Optional[str] = None,
        platform: Optional[str] = None,
        role: Optional[str] = None,
        site: Optional[str] = None,
        enabled: Optional[bool] = None,
        limit: int = 100,
    ) -> List[DeviceType]:
        """List devices with filtering."""
        user = get_user_from_info(info)
        customer_ids = get_customer_ids_for_user(user)

        # Enforce maximum limit
        limit = min(limit, MAX_LIMIT)

        queryset = Device.objects.filter(customer_id__in=customer_ids)

        if customer_id is not None:
            if customer_id in customer_ids:
                queryset = queryset.filter(customer_id=customer_id)
            else:
                return []

        if hostname:
            queryset = queryset.filter(hostname__icontains=hostname)
        if vendor:
            queryset = queryset.filter(vendor__icontains=vendor)
        if platform:
            queryset = queryset.filter(platform__icontains=platform)
        if role:
            queryset = queryset.filter(role__icontains=role)
        if site:
            queryset = queryset.filter(site__icontains=site)
        if enabled is not None:
            queryset = queryset.filter(enabled=enabled)

        return list(queryset.select_related("customer", "credential")[:limit])

    @strawberry.field(permission_classes=[IsAuthenticated])
    def device(self, info: Info, id: int) -> Optional[DeviceType]:
        """Get a specific device by ID."""
        user = get_user_from_info(info)
        customer_ids = get_customer_ids_for_user(user)
        try:
            return Device.objects.select_related("customer", "credential").get(
                id=id, customer_id__in=customer_ids
            )
        except Device.DoesNotExist:
            return None

    @strawberry.field(permission_classes=[IsAuthenticated])
    def credentials(
        self, info: Info, customer_id: Optional[int] = None, limit: int = 100
    ) -> List[CredentialType]:
        """List credentials."""
        user = get_user_from_info(info)
        customer_ids = get_customer_ids_for_user(user)

        # Enforce maximum limit
        limit = min(limit, MAX_LIMIT)

        queryset = Credential.objects.filter(customer_id__in=customer_ids)
        if customer_id is not None:
            if customer_id in customer_ids:
                queryset = queryset.filter(customer_id=customer_id)
            else:
                return []

        return list(queryset.select_related("customer")[:limit])

    @strawberry.field(permission_classes=[IsAuthenticated])
    def tags(
        self, info: Info, customer_id: Optional[int] = None, limit: int = 100
    ) -> List[TagType]:
        """List tags."""
        user = get_user_from_info(info)
        customer_ids = get_customer_ids_for_user(user)

        # Enforce maximum limit
        limit = min(limit, MAX_LIMIT)

        queryset = Tag.objects.filter(customer_id__in=customer_ids)
        if customer_id is not None:
            if customer_id in customer_ids:
                queryset = queryset.filter(customer_id=customer_id)
            else:
                return []

        return list(queryset.select_related("customer")[:limit])

    @strawberry.field(permission_classes=[IsAuthenticated])
    def jobs(
        self,
        info: Info,
        customer_id: Optional[int] = None,
        status: Optional[str] = None,
        type: Optional[str] = None,
        limit: int = 100,
    ) -> List[JobType]:
        """List jobs with filtering."""
        user = get_user_from_info(info)
        customer_ids = get_customer_ids_for_user(user)

        # Enforce maximum limit
        limit = min(limit, MAX_LIMIT)

        queryset = Job.objects.filter(customer_id__in=customer_ids)

        if customer_id is not None:
            if customer_id in customer_ids:
                queryset = queryset.filter(customer_id=customer_id)
            else:
                return []

        if status:
            queryset = queryset.filter(status=status)
        if type:
            queryset = queryset.filter(type=type)

        return list(queryset.select_related("customer", "user").order_by("-requested_at")[:limit])

    @strawberry.field(permission_classes=[IsAuthenticated])
    def job(self, info: Info, id: int) -> Optional[JobType]:
        """Get a specific job by ID."""
        user = get_user_from_info(info)
        customer_ids = get_customer_ids_for_user(user)
        try:
            return Job.objects.select_related("customer", "user").get(
                id=id, customer_id__in=customer_ids
            )
        except Job.DoesNotExist:
            return None

    @strawberry.field(permission_classes=[IsAuthenticated])
    def config_snapshots(
        self,
        info: Info,
        device_id: Optional[int] = None,
        customer_id: Optional[int] = None,
        limit: int = 50,
    ) -> List[ConfigSnapshotType]:
        """List configuration snapshots."""
        user = get_user_from_info(info)
        customer_ids = get_customer_ids_for_user(user)

        # Enforce maximum limit
        limit = min(limit, MAX_LIMIT)

        queryset = ConfigSnapshot.objects.filter(device__customer_id__in=customer_ids)

        if customer_id is not None:
            if customer_id in customer_ids:
                queryset = queryset.filter(device__customer_id=customer_id)
            else:
                return []

        if device_id is not None:
            queryset = queryset.filter(device_id=device_id)

        return list(queryset.select_related("device", "job").order_by("-created_at")[:limit])

    @strawberry.field(permission_classes=[IsAuthenticated])
    def config_templates(
        self, info: Info, customer_id: Optional[int] = None, limit: int = 100
    ) -> List[ConfigTemplateType]:
        """List configuration templates."""
        user = get_user_from_info(info)
        customer_ids = get_customer_ids_for_user(user)

        # Enforce maximum limit
        limit = min(limit, MAX_LIMIT)

        queryset = ConfigTemplate.objects.filter(customer_id__in=customer_ids)
        if customer_id is not None:
            if customer_id in customer_ids:
                queryset = queryset.filter(customer_id=customer_id)
            else:
                return []

        return list(queryset.select_related("customer").filter(is_active=True)[:limit])

    @strawberry.field(permission_classes=[IsAuthenticated])
    def compliance_policies(
        self, info: Info, customer_id: Optional[int] = None, limit: int = 100
    ) -> List[CompliancePolicyType]:
        """List compliance policies."""
        user = get_user_from_info(info)
        customer_ids = get_customer_ids_for_user(user)

        # Enforce maximum limit
        limit = min(limit, MAX_LIMIT)

        queryset = CompliancePolicy.objects.filter(customer_id__in=customer_ids)
        if customer_id is not None:
            if customer_id in customer_ids:
                queryset = queryset.filter(customer_id=customer_id)
            else:
                return []

        return list(queryset.select_related("customer", "created_by")[:limit])

    @strawberry.field(permission_classes=[IsAuthenticated])
    def compliance_results(
        self,
        info: Info,
        policy_id: Optional[int] = None,
        device_id: Optional[int] = None,
        limit: int = 100,
    ) -> List[ComplianceResultType]:
        """List compliance results."""
        user = get_user_from_info(info)
        customer_ids = get_customer_ids_for_user(user)

        # Enforce maximum limit
        limit = min(limit, MAX_LIMIT)

        queryset = ComplianceResult.objects.filter(policy__customer_id__in=customer_ids)

        if policy_id is not None:
            queryset = queryset.filter(policy_id=policy_id)
        if device_id is not None:
            queryset = queryset.filter(device_id=device_id)

        return list(queryset.select_related("policy", "device", "job").order_by("-ts")[:limit])

    @strawberry.field(permission_classes=[IsAuthenticated])
    def topology_links(
        self,
        info: Info,
        device_id: Optional[int] = None,
        customer_id: Optional[int] = None,
        limit: int = 500,
    ) -> List[TopologyLinkType]:
        """List topology links."""
        user = get_user_from_info(info)
        customer_ids = get_customer_ids_for_user(user)

        # Enforce maximum limit
        limit = min(limit, MAX_LIMIT)

        queryset = TopologyLink.objects.filter(local_device__customer_id__in=customer_ids)

        if customer_id is not None:
            if customer_id in customer_ids:
                queryset = queryset.filter(local_device__customer_id=customer_id)
            else:
                return []

        if device_id is not None:
            queryset = queryset.filter(Q(local_device_id=device_id) | Q(remote_device_id=device_id))

        return list(queryset.select_related("local_device", "remote_device")[:limit])
