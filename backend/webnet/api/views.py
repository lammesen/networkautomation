"""DRF views for webnet APIs."""

from __future__ import annotations

import csv
import difflib
import hashlib
import io
import logging
import secrets
from datetime import datetime
from typing import Optional

from django.contrib.auth import authenticate
from django.db.models import Count
from django.utils import timezone
from django.utils.text import slugify
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

from webnet.users.models import User, APIKey
from webnet.customers.models import Customer, CustomerIPRange
from webnet.core.models import CustomFieldDefinition, Region
from webnet.devices.models import (
    Device,
    Credential,
    TopologyLink,
    DiscoveredDevice,
    Tag,
    DeviceGroup,
    NetBoxConfig,
    NetBoxSyncLog,
    SSHHostKey,
    ServiceNowConfig,
    ServiceNowSyncLog,
    ServiceNowIncident,
    ServiceNowChangeRequest,
)
from webnet.jobs.models import Job, JobLog, Schedule
from webnet.jobs.services import JobService
from webnet.config_mgmt.models import ConfigSnapshot, ConfigTemplate, ConfigDrift, DriftAlert
from webnet.compliance.models import (
    CompliancePolicy,
    ComplianceResult,
    RemediationRule,
    RemediationAction,
)
from webnet.ansible_mgmt.models import Playbook, AnsibleConfig
from webnet.webhooks.models import Webhook, WebhookDelivery

from .serializers import (
    UserSerializer,
    UserCreateSerializer,
    APIKeySerializer,
    CustomerSerializer,
    CustomerIPRangeSerializer,
    CustomFieldDefinitionSerializer,
    CredentialSerializer,
    DeviceSerializer,
    JobSerializer,
    JobLogSerializer,
    ScheduleSerializer,
    ConfigSnapshotSerializer,
    ConfigDriftSerializer,
    DriftAlertSerializer,
    CompliancePolicySerializer,
    ComplianceResultSerializer,
    RemediationRuleSerializer,
    RemediationActionSerializer,
    TopologyLinkSerializer,
    SSHHostKeySerializer,
    SSHHostKeyVerifySerializer,
    SSHHostKeyImportSerializer,
    DiscoveredDeviceSerializer,
    DiscoveredDeviceApproveSerializer,
    DiscoveredDeviceRejectSerializer,
    TopologyDiscoverRequestSerializer,
    # Issue #40 - Bulk Device Onboarding
    IPRangeScanRequestSerializer,
    CredentialTestRequestSerializer,
    # Issue #24 - Device Tags and Groups
    TagSerializer,
    DeviceGroupSerializer,
    DeviceTagAssignmentSerializer,
    # Issue #16 - Configuration Templates
    ConfigTemplateSerializer,
    ConfigTemplateRenderSerializer,
    ConfigTemplateDeploySerializer,
    # Issue #9 - NetBox Integration
    NetBoxConfigSerializer,
    NetBoxSyncLogSerializer,
    NetBoxSyncRequestSerializer,
    # Ansible Integration
    AnsibleConfigSerializer,
    PlaybookSerializer,
    PlaybookExecuteSerializer,
    # ServiceNow Integration
    ServiceNowConfigSerializer,
    ServiceNowSyncLogSerializer,
    ServiceNowSyncRequestSerializer,
    ServiceNowIncidentSerializer,
    ServiceNowIncidentUpdateSerializer,
    ServiceNowChangeRequestSerializer,
    ServiceNowChangeRequestCreateSerializer,
    ServiceNowChangeRequestUpdateSerializer,
    # Webhook Integration
    WebhookSerializer,
    WebhookDeliverySerializer,
    # Multi-region Deployment Support
    RegionSerializer,
    RegionHealthUpdateSerializer,
)
from .permissions import (
    RolePermission,
    CustomerScopedQuerysetMixin,
    ObjectCustomerPermission,
    _customer_ids_for_user,
    user_has_customer_access,
    resolve_customer_for_request,
)

logger = logging.getLogger(__name__)


class LoginRateThrottle(AnonRateThrottle):
    """Rate limit login attempts to prevent brute-force attacks."""

    rate = "5/minute"


class AuthViewSet(viewsets.ViewSet):
    permission_classes = []
    throttle_classes = [LoginRateThrottle]

    @action(
        detail=False, methods=["get"], permission_classes=[IsAuthenticated], throttle_classes=[]
    )
    def me(self, request) -> Response:
        return Response(UserSerializer(request.user).data)

    @action(detail=False, methods=["post"])
    def login(self, request):
        username = request.data.get("username")
        password = request.data.get("password")
        if not username or not password:
            return Response(
                {"detail": "username and password required"}, status=status.HTTP_400_BAD_REQUEST
            )
        user = authenticate(request, username=username, password=password)
        if not user or not user.is_active:
            return Response({"detail": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)
        return Response({"access": access_token, "refresh": refresh_token})

    @action(detail=False, methods=["post"])
    def refresh(self, request):
        token = request.data.get("refresh")
        if not token:
            return Response(
                {"detail": "refresh token required"}, status=status.HTTP_400_BAD_REQUEST
            )
        try:
            refresh = RefreshToken(token)
            data = {"access": str(refresh.access_token), "refresh": str(refresh)}
            return Response(data)
        except TokenError as exc:
            logger.warning("Invalid refresh token: %s", exc)
            return Response(
                {"detail": "invalid refresh token"}, status=status.HTTP_401_UNAUTHORIZED
            )

    @action(detail=False, methods=["post"], permission_classes=[IsAuthenticated])
    def logout(self, request):
        # Stateless JWT: nothing to revoke unless blacklist is enabled.
        return Response(status=status.HTTP_200_OK)


class UserViewSet(CustomerScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = User.objects.all()
    permission_classes = [IsAuthenticated, RolePermission]
    customer_field = "customers__id"

    def get_serializer_class(self):
        if self.action == "create":
            return UserCreateSerializer
        return UserSerializer

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):  # pragma: no cover
        user = self.get_object()
        user.is_active = True
        user.save()
        return Response(UserSerializer(user).data)

    @action(detail=True, methods=["post"])
    def deactivate(self, request, pk=None):  # pragma: no cover
        user = self.get_object()
        user.is_active = False
        user.save()
        return Response(UserSerializer(user).data)

    @action(detail=True, methods=["get", "post"], url_path="api-keys")
    def api_keys(self, request, pk=None):
        if request.method == "GET":
            keys = APIKey.objects.filter(user_id=pk)
            return Response(APIKeySerializer(keys, many=True).data)
        name = request.data.get("name") or f"key-{timezone.now().isoformat()}"
        scopes = request.data.get("scopes")
        expires_at_raw = request.data.get("expires_at")
        expires_at: Optional[datetime] = None
        if expires_at_raw:
            try:
                expires_at = datetime.fromisoformat(expires_at_raw)
            except ValueError:
                return Response(
                    {"detail": "expires_at must be ISO format"}, status=status.HTTP_400_BAD_REQUEST
                )
        raw_token = secrets.token_urlsafe(32)
        prefix = raw_token[:8]
        key_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        api_key = APIKey.objects.create(
            user_id=pk,
            name=name,
            key_prefix=prefix,
            key_hash=key_hash,
            scopes=scopes,
            expires_at=expires_at,
        )
        data = APIKeySerializer(api_key).data
        data["token"] = raw_token
        return Response(data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["delete"], url_path="api-keys/(?P<key_id>[^/.]+)")
    def delete_api_key(self, request, pk=None, key_id=None):
        deleted, _ = APIKey.objects.filter(user_id=pk, pk=key_id).delete()
        if not deleted:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)


class CustomerViewSet(CustomerScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated, RolePermission]

    @action(detail=True, methods=["get", "post"], url_path="ranges")
    def ranges(self, request, pk=None):
        if request.method == "GET":
            ranges = CustomerIPRange.objects.filter(customer_id=pk)
            return Response(CustomerIPRangeSerializer(ranges, many=True).data)
        serializer = CustomerIPRangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(customer_id=pk)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["delete"], url_path="ranges/(?P<range_id>[^/.]+)")
    def delete_range(self, request, pk=None, range_id=None):
        deleted, _ = CustomerIPRange.objects.filter(customer_id=pk, pk=range_id).delete()
        if not deleted:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"], url_path="users/(?P<user_id>[^/.]+)")
    def add_user(self, request, pk=None, user_id=None):
        try:
            user = User.objects.get(pk=user_id)
            customer = Customer.objects.get(pk=pk)
        except (User.DoesNotExist, Customer.DoesNotExist):
            return Response(status=status.HTTP_404_NOT_FOUND)
        customer.users.add(user)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["delete"], url_path="users/(?P<user_id>[^/.]+)")
    def remove_user(self, request, pk=None, user_id=None):
        try:
            user = User.objects.get(pk=user_id)
            customer = Customer.objects.get(pk=pk)
        except (User.DoesNotExist, Customer.DoesNotExist):
            return Response(status=status.HTTP_404_NOT_FOUND)
        customer.users.remove(user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class CustomFieldDefinitionViewSet(CustomerScopedQuerysetMixin, viewsets.ModelViewSet):
    """API viewset for managing custom field definitions."""

    queryset = CustomFieldDefinition.objects.all()
    serializer_class = CustomFieldDefinitionSerializer
    permission_classes = [IsAuthenticated, RolePermission]
    customer_field = "customer_id"
    filterset_fields = ["model_type", "field_type", "is_active"]


class CredentialViewSet(CustomerScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Credential.objects.select_related("customer")
    serializer_class = CredentialSerializer
    permission_classes = [IsAuthenticated, RolePermission, ObjectCustomerPermission]


class DeviceViewSet(CustomerScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Device.objects.select_related("credential", "customer")
    serializer_class = DeviceSerializer
    permission_classes = [IsAuthenticated, RolePermission, ObjectCustomerPermission]

    @action(detail=True, methods=["post"])
    def enable(self, request, pk=None):  # pragma: no cover
        device = self.get_object()
        device.enabled = True
        device.save()
        return Response(DeviceSerializer(device).data)

    @action(detail=True, methods=["post"])
    def disable(self, request, pk=None):  # pragma: no cover
        device = self.get_object()
        device.enabled = False
        device.save()
        return Response(DeviceSerializer(device).data)

    @action(detail=True, methods=["get"])
    def jobs(self, request, pk=None):  # pragma: no cover
        device = self.get_object()
        jobs = (
            Job.objects.filter(customer=device.customer, target_summary_json__device_id=device.id)
            .select_related("customer", "user")
            .order_by("-requested_at")
        )
        return Response(JobSerializer(jobs, many=True).data)

    @action(detail=True, methods=["get"])
    def snapshots(self, request, pk=None):  # pragma: no cover
        device = self.get_object()
        snaps = (
            ConfigSnapshot.objects.filter(device=device)
            .select_related("device", "job")
            .order_by("-created_at")
        )
        return Response(ConfigSnapshotSerializer(snaps, many=True).data)

    @action(detail=True, methods=["get"])
    def topology(self, request, pk=None):  # pragma: no cover
        device = self.get_object()
        links = (
            TopologyLink.objects.filter(local_device=device)
            .select_related("local_device", "remote_device")
            .order_by("local_interface", "remote_hostname")
        )
        return Response(TopologyLinkSerializer(links, many=True).data)

    @action(detail=False, methods=["post"], url_path="bulk-backup")
    def bulk_backup(self, request):
        """Queue config backup jobs for multiple devices."""
        device_ids = request.data.get("device_ids") or []
        if not device_ids:
            return Response({"detail": "device_ids required"}, status=status.HTTP_400_BAD_REQUEST)
        # Validate devices exist and user has access
        devices = self.get_queryset().filter(pk__in=device_ids)
        if not devices.exists():
            return Response({"detail": "No valid devices found"}, status=status.HTTP_404_NOT_FOUND)
        # Create backup jobs per customer (grouped)
        js = JobService()
        jobs = []
        # Get unique customer IDs
        customer_ids = set(devices.values_list("customer_id", flat=True))
        for customer_id in customer_ids:
            customer_devices = devices.filter(customer_id=customer_id)
            customer = customer_devices.first().customer
            device_ids_for_customer = list(customer_devices.values_list("id", flat=True))
            job = js.create_job(
                job_type="config_backup",
                user=request.user,
                customer=customer,
                target_summary={"filters": {"device_ids": device_ids_for_customer}},
                payload={"source_label": "bulk"},
            )
            jobs.append({"job_id": job.id, "device_count": len(device_ids_for_customer)})
        return Response(
            {"jobs": jobs, "total_devices": devices.count()}, status=status.HTTP_202_ACCEPTED
        )

    @action(detail=False, methods=["post"], url_path="bulk-compliance")
    def bulk_compliance(self, request):
        """Queue compliance check jobs for multiple devices."""
        device_ids = request.data.get("device_ids") or []
        if not device_ids:
            return Response({"detail": "device_ids required"}, status=status.HTTP_400_BAD_REQUEST)
        # Validate devices exist and user has access
        devices = self.get_queryset().filter(pk__in=device_ids)
        if not devices.exists():
            return Response({"detail": "No valid devices found"}, status=status.HTTP_404_NOT_FOUND)
        # Create compliance jobs per customer (grouped)
        js = JobService()
        jobs = []
        # Get unique customer IDs
        customer_ids = set(devices.values_list("customer_id", flat=True))
        for customer_id in customer_ids:
            customer_devices = devices.filter(customer_id=customer_id)
            customer = customer_devices.first().customer
            device_ids_for_customer = list(customer_devices.values_list("id", flat=True))
            job = js.create_job(
                job_type="compliance_check",
                user=request.user,
                customer=customer,
                target_summary={"filters": {"device_ids": device_ids_for_customer}},
                payload={},
            )
            jobs.append({"job_id": job.id, "device_count": len(device_ids_for_customer)})
        return Response(
            {"jobs": jobs, "total_devices": devices.count()}, status=status.HTTP_202_ACCEPTED
        )


class DeviceImportView(APIView):
    permission_classes = [IsAuthenticated, RolePermission]

    MAX_UPLOAD_SIZE = 5 * 1024 * 1024  # 5MB

    def post(self, request) -> Response:
        upload = request.FILES.get("file")
        if not upload:
            return Response({"detail": "file required"}, status=status.HTTP_400_BAD_REQUEST)

        # Validate file size
        if upload.size > self.MAX_UPLOAD_SIZE:
            return Response(
                {
                    "detail": f"File too large. Maximum size is {self.MAX_UPLOAD_SIZE // (1024 * 1024)}MB"
                },
                status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            )

        # Validate file extension
        if not upload.name.lower().endswith(".csv"):
            return Response(
                {"detail": "Only CSV files are allowed"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        customer_id = request.data.get("customer_id")
        user = request.user
        if customer_id:
            try:
                customer = Customer.objects.get(pk=customer_id)
            except Customer.DoesNotExist:
                return Response({"detail": "customer not found"}, status=status.HTTP_404_NOT_FOUND)
            if not user_has_customer_access(user, customer.id):
                return Response(
                    {"detail": "no access to customer"}, status=status.HTTP_403_FORBIDDEN
                )
        else:
            if getattr(user, "role", "viewer") != "admin" and user.customers.count() == 1:
                customer = user.customers.first()
            else:
                return Response(
                    {"detail": "customer_id required"}, status=status.HTTP_400_BAD_REQUEST
                )

        created = updated = skipped = 0
        errors = []
        try:
            decoded = upload.read().decode()
        except Exception:
            return Response({"detail": "invalid file encoding"}, status=status.HTTP_400_BAD_REQUEST)
        reader = csv.DictReader(io.StringIO(decoded))
        for row in reader:
            hostname = (row.get("hostname") or "").strip()
            mgmt_ip = (row.get("mgmt_ip") or "").strip()
            vendor = (row.get("vendor") or "").strip()
            platform = (row.get("platform") or "").strip()
            credential_name = (row.get("credential") or row.get("credential_name") or "").strip()
            if not hostname or not mgmt_ip or not credential_name:
                skipped += 1
                errors.append(f"missing required fields for row {row}")
                continue
            credential = Credential.objects.filter(customer=customer, name=credential_name).first()
            if not credential:
                skipped += 1
                errors.append(f"credential '{credential_name}' not found for customer")
                continue
            defaults = {
                "vendor": vendor,
                "platform": platform,
                "role": (row.get("role") or "").strip() or None,
                "site": (row.get("site") or "").strip() or None,
                "tags": row.get("tags") or None,
                "credential": credential,
            }
            obj, created_flag = Device.objects.update_or_create(
                customer=customer,
                hostname=hostname,
                defaults={"mgmt_ip": mgmt_ip, **defaults},
            )
            if created_flag:
                created += 1
            else:
                updated += 1
        summary = {
            "created": created,
            "updated": updated,
            "skipped": skipped,
            "errors": errors,
        }
        return Response(summary)


class JobViewSet(CustomerScopedQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = Job.objects.select_related("customer", "user")
    serializer_class = JobSerializer
    permission_classes = [IsAuthenticated, RolePermission, ObjectCustomerPermission]

    @action(detail=True, methods=["get"])
    def logs(self, request, pk=None):
        job = self.get_object()
        limit = int(request.query_params.get("limit", 500))
        logs = JobLog.objects.filter(job=job).order_by("-ts")[:limit]
        return Response(JobLogSerializer(logs, many=True).data)

    @action(detail=True, methods=["post"])
    def retry(self, request, pk=None):
        job = self.get_object()
        js = JobService()
        clone = js.create_job(
            job_type=job.type,
            user=request.user,
            customer=job.customer,
            target_summary=job.target_summary_json,
            payload=job.payload_json,
        )
        return Response(
            {"job_id": clone.id, "status": clone.status}, status=status.HTTP_202_ACCEPTED
        )

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        job = self.get_object()
        if job.status not in {"queued", "scheduled"}:
            return Response(
                {"detail": "Cannot cancel running or finished jobs"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        job.status = "cancelled"
        job.finished_at = timezone.now()
        job.save(update_fields=["status", "finished_at"])
        return Response({"status": "cancelled"})


class JobAdminViewSet(CustomerScopedQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = Job.objects.select_related("customer", "user")
    serializer_class = JobSerializer
    permission_classes = [IsAuthenticated, RolePermission]
    customer_field = "customer_id"


class ScheduleViewSet(CustomerScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Schedule.objects.select_related("customer", "created_by")
    serializer_class = ScheduleSerializer
    permission_classes = [IsAuthenticated, RolePermission, ObjectCustomerPermission]
    customer_field = "customer"

    def perform_create(self, serializer):
        """Set created_by to current user."""
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=["post"])
    def toggle(self, request, pk=None):
        """Toggle schedule enabled/disabled."""
        schedule = self.get_object()
        schedule.enabled = not schedule.enabled
        schedule.save(update_fields=["enabled"])
        return Response(ScheduleSerializer(schedule).data)


class JobLogsView(APIView):
    permission_classes = [IsAuthenticated, RolePermission]

    def get(self, request, pk):
        job = Job.objects.select_related("customer", "user").filter(pk=pk).first()
        if not job:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if not user_has_customer_access(request.user, job.customer_id):
            return Response(status=status.HTTP_404_NOT_FOUND)
        limit = int(request.query_params.get("limit", 500))
        logs = JobLog.objects.select_related("job").filter(job_id=pk).order_by("-ts")[:limit]
        return Response(JobLogSerializer(logs, many=True).data)


class CommandViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated, RolePermission]

    @action(detail=False, methods=["post"])
    def run(self, request) -> Response:
        customer = resolve_customer_for_request(request)
        if not customer:
            return Response(
                {"detail": "customer_id required or no access"}, status=status.HTTP_400_BAD_REQUEST
            )
        commands = request.data.get("commands") or []
        targets = request.data.get("targets") or {}
        timeout = request.data.get("timeout") or 30
        js = JobService()
        job = js.create_job(
            job_type="run_commands",
            user=request.user,
            customer=customer,
            target_summary={"filters": targets},
            payload={"commands": commands, "timeout": timeout},
        )
        return Response({"job_id": job.id, "status": job.status}, status=status.HTTP_202_ACCEPTED)

    @action(detail=False, methods=["post"])
    def reachability(self, request) -> Response:
        customer = resolve_customer_for_request(request)
        if not customer:
            return Response(
                {"detail": "customer_id required or no access"}, status=status.HTTP_400_BAD_REQUEST
            )
        targets = request.data.get("targets") or {}
        js = JobService()
        job = js.create_job(
            job_type="check_reachability",
            user=request.user,
            customer=customer,
            target_summary={"filters": targets},
            payload={"targets": targets},
        )
        return Response({"job_id": job.id, "status": job.status}, status=status.HTTP_202_ACCEPTED)

    @action(detail=False, methods=["post"])
    def discover(self, request) -> Response:
        """Run topology discovery using CDP and/or LLDP protocols.

        Request body:
        - targets: Device filter targets (optional, default: all devices)
        - protocol: 'cdp', 'lldp', or 'both' (default: 'both')
        - auto_create_devices: Queue discovered unknown devices for review (default: false)
        """
        customer = resolve_customer_for_request(request)
        if not customer:
            return Response(
                {"detail": "customer_id required or no access"}, status=status.HTTP_400_BAD_REQUEST
            )

        serializer = TopologyDiscoverRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        targets = serializer.validated_data.get("targets") or {}
        protocol = serializer.validated_data.get("protocol", "both")
        auto_create_devices = serializer.validated_data.get("auto_create_devices", False)

        js = JobService()
        job = js.create_job(
            job_type="topology_discovery",
            user=request.user,
            customer=customer,
            target_summary={"filters": targets, "protocol": protocol},
            payload={
                "protocol": protocol,
                "auto_create_devices": auto_create_devices,
            },
        )
        return Response({"job_id": job.id, "status": job.status}, status=status.HTTP_202_ACCEPTED)


class ConfigViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated, RolePermission]

    def backup(self, request) -> Response:
        customer = resolve_customer_for_request(request)
        if not customer:
            return Response(
                {"detail": "customer_id required or no access"}, status=status.HTTP_400_BAD_REQUEST
            )
        targets = request.data.get("targets") or {}
        source_label = request.data.get("source_label", "manual")
        js = JobService()
        job = js.create_job(
            job_type="config_backup",
            user=request.user,
            customer=customer,
            target_summary={"filters": targets},
            payload={"source_label": source_label},
        )
        return Response({"job_id": job.id, "status": job.status}, status=status.HTTP_202_ACCEPTED)

    def deploy_preview(self, request) -> Response:
        customer = resolve_customer_for_request(request)
        if not customer:
            return Response(
                {"detail": "customer_id required or no access"}, status=status.HTTP_400_BAD_REQUEST
            )
        mode = request.data.get("mode", "merge")
        snippet = request.data.get("snippet", "")
        targets = request.data.get("targets") or {}
        js = JobService()
        job = js.create_job(
            job_type="config_deploy_preview",
            user=request.user,
            customer=customer,
            target_summary={"filters": targets},
            payload={"mode": mode, "snippet": snippet},
        )
        return Response({"job_id": job.id, "status": job.status}, status=status.HTTP_202_ACCEPTED)

    def deploy_commit(self, request) -> Response:
        customer = resolve_customer_for_request(request)
        if not customer:
            return Response(
                {"detail": "customer_id required or no access"}, status=status.HTTP_400_BAD_REQUEST
            )
        mode = request.data.get("mode", "merge")
        snippet = request.data.get("snippet", "")
        targets = request.data.get("targets") or {}
        js = JobService()
        job = js.create_job(
            job_type="config_deploy_commit",
            user=request.user,
            customer=customer,
            target_summary={"filters": targets},
            payload={"mode": mode, "snippet": snippet},
        )
        return Response({"job_id": job.id, "status": job.status}, status=status.HTTP_202_ACCEPTED)

    def rollback_preview(self, request) -> Response:
        customer = resolve_customer_for_request(request)
        if not customer:
            return Response(
                {"detail": "customer_id required or no access"}, status=status.HTTP_400_BAD_REQUEST
            )
        device_id = request.data.get("device_id")
        target_config = request.data.get("target_config", "")
        js = JobService()
        job = js.create_job(
            job_type="config_deploy_preview",
            user=request.user,
            customer=customer,
            target_summary={"filters": {"device_ids": [device_id]}},
            payload={"mode": "replace", "snippet": target_config},
        )
        return Response({"job_id": job.id, "status": job.status}, status=status.HTTP_202_ACCEPTED)

    def rollback_commit(self, request) -> Response:
        customer = resolve_customer_for_request(request)
        if not customer:
            return Response(
                {"detail": "customer_id required or no access"}, status=status.HTTP_400_BAD_REQUEST
            )
        device_id = request.data.get("device_id")
        target_config = request.data.get("target_config", "")
        js = JobService()
        job = js.create_job(
            job_type="config_deploy_commit",
            user=request.user,
            customer=customer,
            target_summary={"filters": {"device_ids": [device_id]}},
            payload={"mode": "replace", "snippet": target_config},
        )
        return Response({"job_id": job.id, "status": job.status}, status=status.HTTP_202_ACCEPTED)

    def snapshot(self, request, pk=None):
        snap = ConfigSnapshot.objects.select_related("device").filter(pk=pk).first()
        if not snap or not user_has_customer_access(request.user, snap.device.customer_id):
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(ConfigSnapshotSerializer(snap).data)

    def device_snapshots(self, request, device_id=None):
        device = Device.objects.select_related("customer").filter(pk=device_id).first()
        if not device or not user_has_customer_access(request.user, device.customer_id):
            return Response(status=status.HTTP_404_NOT_FOUND)
        snaps = ConfigSnapshot.objects.filter(device=device).select_related("device", "job")
        return Response(ConfigSnapshotSerializer(snaps, many=True).data)

    def diff(self, request, device_id=None):
        from_id = request.query_params.get("from")
        to_id = request.query_params.get("to")
        if not from_id or not to_id:
            return Response(
                {"detail": "from and to query params required"}, status=status.HTTP_400_BAD_REQUEST
            )
        device = Device.objects.select_related("customer").filter(pk=device_id).first()
        if not device or not user_has_customer_access(request.user, device.customer_id):
            return Response(status=status.HTTP_404_NOT_FOUND)
        try:
            snap_from = ConfigSnapshot.objects.select_related("device").get(
                pk=from_id, device=device
            )
            snap_to = ConfigSnapshot.objects.select_related("device").get(pk=to_id, device=device)
        except ConfigSnapshot.DoesNotExist:
            return Response(
                {"detail": "snapshot not found for device"}, status=status.HTTP_404_NOT_FOUND
            )
        diff_lines = difflib.unified_diff(
            snap_from.config_text.splitlines(),
            snap_to.config_text.splitlines(),
            fromfile=f"snapshot-{snap_from.id}",
            tofile=f"snapshot-{snap_to.id}",
            lineterm="",
        )
        diff_text = "\n".join(diff_lines)
        return Response({"from": snap_from.id, "to": snap_to.id, "diff": diff_text})


class DriftViewSet(viewsets.ViewSet):
    """API endpoints for configuration drift analysis."""

    permission_classes = [IsAuthenticated, RolePermission]

    @action(detail=False, methods=["post"], url_path="detect")
    def detect_drift(self, request):
        """Detect drift between two snapshots."""
        from webnet.config_mgmt.drift_service import DriftService

        from_id = request.data.get("snapshot_from_id")
        to_id = request.data.get("snapshot_to_id")

        if not from_id or not to_id:
            return Response(
                {"detail": "snapshot_from_id and snapshot_to_id required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            snap_from = ConfigSnapshot.objects.select_related("device__customer").get(pk=from_id)
            snap_to = ConfigSnapshot.objects.select_related("device__customer").get(pk=to_id)
        except ConfigSnapshot.DoesNotExist:
            return Response({"detail": "snapshot not found"}, status=status.HTTP_404_NOT_FOUND)

        # Check access
        if not user_has_customer_access(request.user, snap_from.device.customer_id):
            return Response(status=status.HTTP_404_NOT_FOUND)
        if not user_has_customer_access(request.user, snap_to.device.customer_id):
            return Response(status=status.HTTP_404_NOT_FOUND)

        # Detect drift
        ds = DriftService()
        drift = ds.detect_drift(snap_from, snap_to, request.user)

        return Response(ConfigDriftSerializer(drift).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"], url_path="analyze-device")
    def analyze_device(self, request):
        """Analyze all consecutive snapshots for a device."""
        from webnet.config_mgmt.drift_service import DriftService

        device_id = request.data.get("device_id")
        if not device_id:
            return Response({"detail": "device_id required"}, status=status.HTTP_400_BAD_REQUEST)

        device = Device.objects.select_related("customer").filter(pk=device_id).first()
        if not device or not user_has_customer_access(request.user, device.customer_id):
            return Response(status=status.HTTP_404_NOT_FOUND)

        # Analyze drift
        ds = DriftService()
        drifts = ds.detect_consecutive_drifts(device_id, request.user)

        return Response(
            {
                "device_id": device_id,
                "drifts_analyzed": len(drifts),
                "drifts": ConfigDriftSerializer(drifts, many=True).data,
            }
        )

    @action(detail=False, methods=["get"], url_path="device/(?P<device_id>[^/.]+)")
    def device_drifts(self, request, device_id=None):
        """Get drift timeline for a device."""
        device = Device.objects.select_related("customer").filter(pk=device_id).first()
        if not device or not user_has_customer_access(request.user, device.customer_id):
            return Response(status=status.HTTP_404_NOT_FOUND)

        days = int(request.query_params.get("days", 30))
        from webnet.config_mgmt.drift_service import DriftService

        ds = DriftService()
        drifts = ds.get_drift_timeline(device_id, days)

        return Response(ConfigDriftSerializer(drifts, many=True).data)

    @action(detail=False, methods=["get"], url_path="device/(?P<device_id>[^/.]+)/frequency")
    def change_frequency(self, request, device_id=None):
        """Get change frequency statistics for a device."""
        device = Device.objects.select_related("customer").filter(pk=device_id).first()
        if not device or not user_has_customer_access(request.user, device.customer_id):
            return Response(status=status.HTTP_404_NOT_FOUND)

        days = int(request.query_params.get("days", 30))
        from webnet.config_mgmt.drift_service import DriftService

        ds = DriftService()
        stats = ds.get_change_frequency(device_id, days)

        return Response(stats)

    @action(detail=True, methods=["get"])
    def detail(self, request, pk=None):
        """Get drift details."""
        drift = (
            ConfigDrift.objects.select_related(
                "device__customer", "snapshot_from", "snapshot_to", "triggered_by"
            )
            .filter(pk=pk)
            .first()
        )

        if not drift or not user_has_customer_access(request.user, drift.device.customer_id):
            return Response(status=status.HTTP_404_NOT_FOUND)

        return Response(ConfigDriftSerializer(drift).data)


class DriftAlertViewSet(CustomerScopedQuerysetMixin, viewsets.ModelViewSet):
    """API endpoints for drift alerts."""

    queryset = DriftAlert.objects.select_related("drift__device__customer", "acknowledged_by")
    serializer_class = DriftAlertSerializer
    permission_classes = [IsAuthenticated, RolePermission, ObjectCustomerPermission]
    customer_field = "drift__device__customer_id"

    @action(detail=True, methods=["post"])
    def acknowledge(self, request, pk=None):
        """Acknowledge an alert."""
        alert = self.get_object()
        alert.status = "acknowledged"
        alert.acknowledged_by = request.user
        alert.acknowledged_at = timezone.now()
        alert.save()
        return Response(DriftAlertSerializer(alert).data)

    @action(detail=True, methods=["post"])
    def resolve(self, request, pk=None):
        """Resolve an alert."""
        alert = self.get_object()
        alert.status = "resolved"
        alert.resolution_notes = request.data.get("resolution_notes", "")
        alert.save()
        return Response(DriftAlertSerializer(alert).data)


class CompliancePolicyViewSet(CustomerScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = CompliancePolicy.objects.select_related("customer")
    serializer_class = CompliancePolicySerializer
    permission_classes = [IsAuthenticated, RolePermission, ObjectCustomerPermission]

    @action(detail=True, methods=["post"])
    def run(self, request, pk=None):
        policy = self.get_object()
        js = JobService()
        job = js.create_job(
            job_type="compliance_check",
            user=request.user,
            customer=policy.customer,
            target_summary=policy.scope_json,
            payload={"policy_id": policy.id},
        )
        return Response({"job_id": job.id, "status": job.status}, status=status.HTTP_202_ACCEPTED)


class ComplianceResultViewSet(CustomerScopedQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = ComplianceResult.objects.select_related("policy", "device", "job")
    serializer_class = ComplianceResultSerializer
    permission_classes = [IsAuthenticated, RolePermission, ObjectCustomerPermission]
    customer_field = ("policy__customer_id", "device__customer_id", "job__customer_id")


class RemediationRuleViewSet(CustomerScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = RemediationRule.objects.select_related("policy", "created_by")
    serializer_class = RemediationRuleSerializer
    permission_classes = [IsAuthenticated, RolePermission, ObjectCustomerPermission]
    customer_field = "policy__customer_id"

    @action(detail=True, methods=["post"])
    def enable(self, request, pk=None):
        """Enable a remediation rule."""
        rule = self.get_object()
        rule.enabled = True
        rule.save(update_fields=["enabled"])
        return Response({"status": "enabled"}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def disable(self, request, pk=None):
        """Disable a remediation rule."""
        rule = self.get_object()
        rule.enabled = False
        rule.save(update_fields=["enabled"])
        return Response({"status": "disabled"}, status=status.HTTP_200_OK)


class RemediationActionViewSet(CustomerScopedQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = RemediationAction.objects.select_related("rule", "device", "compliance_result")
    serializer_class = RemediationActionSerializer
    permission_classes = [IsAuthenticated, RolePermission, ObjectCustomerPermission]
    customer_field = (
        "rule__policy__customer_id",
        "device__customer_id",
        "compliance_result__policy__customer_id",
    )


class TopologyLinkViewSet(CustomerScopedQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = TopologyLink.objects.select_related("local_device", "remote_device").order_by(
        "local_device__hostname", "local_interface", "remote_hostname"
    )
    serializer_class = TopologyLinkSerializer
    permission_classes = [IsAuthenticated, RolePermission, ObjectCustomerPermission]

    @action(detail=False, methods=["delete"], url_path="clear")
    def clear(self, request):
        qs = self.get_queryset()
        if request.query_params.get("dry_run", "false").lower() == "true":
            return Response({"deleted": 0, "would_delete": qs.count()})
        deleted, _ = qs.delete()
        return Response({"deleted": deleted})

    @action(detail=False, methods=["get"], url_path="graph")
    def graph(self, request):
        links = self.get_queryset()
        nodes: dict[str, dict] = {}
        edges = []
        for link in links:
            local_id = str(link.local_device_id)
            remote_id = str(link.remote_device_id or f"unknown-{link.remote_hostname}")
            local_dev = link.local_device
            nodes[local_id] = {
                "id": local_id,
                "label": local_dev.hostname,
                "data": {
                    "hostname": local_dev.hostname,
                    "mgmt_ip": local_dev.mgmt_ip,
                    "vendor": local_dev.vendor,
                    "platform": local_dev.platform,
                    "site": local_dev.site,
                    "role": local_dev.role,
                    "enabled": local_dev.enabled,
                    "reachability_status": local_dev.reachability_status,
                    "detail_url": f"/devices/{local_dev.id}/",
                },
                "type": "device",
            }
            # Remote device node
            if link.remote_device_id and link.remote_device:
                remote_dev = link.remote_device
                nodes[remote_id] = {
                    "id": remote_id,
                    "label": remote_dev.hostname,
                    "data": {
                        "hostname": remote_dev.hostname,
                        "mgmt_ip": remote_dev.mgmt_ip,
                        "vendor": remote_dev.vendor,
                        "platform": remote_dev.platform,
                        "site": remote_dev.site,
                        "role": remote_dev.role,
                        "enabled": remote_dev.enabled,
                        "reachability_status": remote_dev.reachability_status,
                        "detail_url": f"/devices/{remote_dev.id}/",
                    },
                    "type": "device",
                }
            else:
                nodes[remote_id] = {
                    "id": remote_id,
                    "label": link.remote_hostname,
                    "data": {
                        "hostname": link.remote_hostname,
                        "mgmt_ip": link.remote_ip,
                        "vendor": link.remote_platform,
                        "platform": link.remote_platform,
                        "site": None,
                        "role": None,
                        "enabled": None,
                        "reachability_status": None,
                        "detail_url": None,
                    },
                    "type": "unknown",
                }
            edges.append(
                {
                    "id": f"{local_id}->{remote_id}:{link.local_interface}",
                    "source": local_id,
                    "target": remote_id,
                    "data": {
                        "local_interface": link.local_interface,
                        "remote_interface": link.remote_interface,
                        "protocol": link.protocol,
                        "discovered_at": link.discovered_at.isoformat()
                        if link.discovered_at
                        else None,
                    },
                }
            )
        return Response({"nodes": list(nodes.values()), "edges": edges})


class GeoMapDataView(APIView):
    """Return aggregated site/device data for geographic map visualization."""

    permission_classes = [IsAuthenticated, RolePermission]

    @staticmethod
    def _site_key(customer_id: int, site_name: str | None) -> str:
        slug = slugify(site_name or "site") or "site"
        return f"{customer_id}:{slug}"

    @staticmethod
    def _normalize_device_status(device: Device) -> str:
        if device.enabled is False:
            return "disabled"
        status = (device.reachability_status or "").lower()
        if status in {"reachable", "up", "online", "ok", "success"}:
            return "reachable"
        if status in {"unreachable", "down", "offline", "failed"}:
            return "unreachable"
        return "unknown"

    @staticmethod
    def _merge_link_status(current: str, new: str) -> str:
        """Pick the most severe status for a link."""
        severity = {"down": 3, "degraded": 2, "up": 1, "unknown": 0}
        return new if severity.get(new, 0) >= severity.get(current, 0) else current

    def _derive_site_status(self, summary: dict[str, int]) -> str:
        reachable = summary.get("reachable_devices", 0)
        unreachable = summary.get("unreachable_devices", 0)
        disabled = summary.get("disabled_devices", 0)
        if reachable and not unreachable:
            return "healthy"
        if unreachable and reachable:
            return "degraded"
        if unreachable and not reachable:
            return "down"
        if disabled:
            return "maintenance"
        return "unknown"

    def _derive_link_status(self, local: Device, remote: Device) -> str:
        statuses = {
            self._normalize_device_status(local),
            self._normalize_device_status(remote),
        }
        if "unreachable" in statuses:
            return "down"
        if "reachable" in statuses and ({"unknown", "disabled"} & statuses):
            return "degraded"
        if statuses == {"reachable"}:
            return "up"
        return "unknown"

    def _customer_ids(self, user) -> list[int]:
        if getattr(user, "role", "viewer") == "admin":
            return list(Customer.objects.values_list("id", flat=True))
        return _customer_ids_for_user(user)

    def _build_sites(self, devices):
        sites: dict[str, dict] = {}
        for device in devices:
            if device.site_latitude is None or device.site_longitude is None:
                continue
            key = self._site_key(device.customer_id, device.site)
            site = sites.get(key)
            if not site:
                site = {
                    "id": key,
                    "name": device.site or "Unassigned",
                    "customer_id": device.customer_id,
                    "latitude": float(device.site_latitude),
                    "longitude": float(device.site_longitude),
                    "address": device.site_address,
                    "device_count": 0,
                    "reachable_devices": 0,
                    "unreachable_devices": 0,
                    "disabled_devices": 0,
                    "unknown_devices": 0,
                    "devices": [],
                }
                sites[key] = site

            status = self._normalize_device_status(device)
            site["device_count"] += 1
            if status == "reachable":
                site["reachable_devices"] += 1
            elif status == "unreachable":
                site["unreachable_devices"] += 1
            elif status == "disabled":
                site["disabled_devices"] += 1
            else:
                site["unknown_devices"] += 1

            site["devices"].append(
                {
                    "id": device.id,
                    "hostname": device.hostname,
                    "mgmt_ip": device.mgmt_ip,
                    "vendor": device.vendor,
                    "platform": device.platform,
                    "role": device.role,
                    "status": status,
                    "reachability_status": device.reachability_status,
                    "detail_url": f"/devices/{device.id}/",
                }
            )

        for site in sites.values():
            site["status"] = self._derive_site_status(site)
        return sites

    def _build_links(self, customer_ids: list[int], sites: dict[str, dict]):
        links: dict[str, dict] = {}
        qs = (
            TopologyLink.objects.select_related("local_device", "remote_device")
            .filter(local_device__customer_id__in=customer_ids)
            .order_by("local_device__hostname")
        )

        for link in qs:
            local = link.local_device
            remote = link.remote_device
            if not local or not remote:
                continue
            local_key = self._site_key(local.customer_id, local.site)
            remote_key = self._site_key(remote.customer_id, remote.site)
            local_site = sites.get(local_key)
            remote_site = sites.get(remote_key)
            if not local_site or not remote_site:
                continue

            link_key = "->".join(sorted([local_key, remote_key]))
            edge = links.get(link_key)
            if not edge:
                edge = {
                    "id": link_key,
                    "source": local_key,
                    "target": remote_key,
                    "source_name": local_site["name"],
                    "target_name": remote_site["name"],
                    "count": 0,
                    "status": "unknown",
                    "samples": [],
                }
                links[link_key] = edge

            edge["count"] += 1
            edge["status"] = self._merge_link_status(
                edge["status"], self._derive_link_status(local, remote)
            )
            edge["samples"].append(
                {
                    "local_interface": link.local_interface,
                    "remote_interface": link.remote_interface,
                    "protocol": link.protocol,
                    "discovered_at": (
                        link.discovered_at.isoformat() if link.discovered_at else None
                    ),
                }
            )

        return list(links.values())

    def get(self, request):
        customer_ids = self._customer_ids(request.user)
        if not customer_ids:
            return Response({"sites": [], "links": []})

        devices = (
            Device.objects.select_related("customer")
            .filter(customer_id__in=customer_ids)
            .exclude(site_latitude__isnull=True)
            .exclude(site_longitude__isnull=True)
        )
        sites = self._build_sites(devices)
        links = self._build_links(customer_ids, sites)
        return Response({"sites": list(sites.values()), "links": links})


class SSHHostKeyViewSet(CustomerScopedQuerysetMixin, viewsets.ModelViewSet):
    """ViewSet for managing SSH host keys.

    Provides endpoints for viewing, verifying, and managing SSH host keys
    stored in the database for MITM attack prevention.
    """

    queryset = SSHHostKey.objects.select_related("device", "device__customer", "verified_by").all()
    serializer_class = SSHHostKeySerializer
    permission_classes = [IsAuthenticated, RolePermission, ObjectCustomerPermission]
    customer_field = "device__customer_id"
    filterset_fields = ["device", "key_type", "verified"]
    search_fields = ["device__hostname", "fingerprint_sha256"]
    ordering_fields = ["first_seen_at", "last_seen_at", "verified"]
    ordering = ["-verified", "-first_seen_at"]

    @action(detail=True, methods=["post"], url_path="verify")
    def verify(self, request, pk=None):
        """Manually verify or unverify a host key.

        Request body:
            {
                "verified": true/false
            }
        """
        host_key = self.get_object()
        serializer = SSHHostKeyVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        from webnet.core.ssh_host_keys import SSHHostKeyService

        if serializer.validated_data["verified"]:
            SSHHostKeyService.verify_key_manual(host_key, request.user)
            return Response({"status": "verified", "message": "Host key verified successfully"})
        else:
            SSHHostKeyService.unverify_key(host_key)
            return Response({"status": "unverified", "message": "Host key unverified successfully"})

    @action(detail=False, methods=["post"], url_path="import")
    def import_key(self, request):
        """Import a host key from OpenSSH known_hosts format.

        Request body:
            {
                "device_id": 123,
                "known_hosts_line": "192.168.1.1 ssh-rsa AAAAB3NzaC1yc2EA..."
            }
        """
        serializer = SSHHostKeyImportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        device_id = serializer.validated_data["device_id"]
        known_hosts_line = serializer.validated_data["known_hosts_line"]

        # Get device and verify customer access
        try:
            device = Device.objects.select_related("customer").get(id=device_id)
        except Device.DoesNotExist:
            return Response({"error": "Device not found"}, status=status.HTTP_404_NOT_FOUND)

        # Verify user has access to the device's customer
        if not user_has_customer_access(request.user, device.customer):
            return Response(
                {"error": "Access denied to this device"},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Import the key
        from webnet.core.ssh_host_keys import SSHHostKeyService

        try:
            host_key = SSHHostKeyService.import_from_openssh_known_hosts(device, known_hosts_line)
            return Response(SSHHostKeySerializer(host_key).data, status=status.HTTP_201_CREATED)
        except ValueError as e:
            logger.warning("SSH host key import failed: %s", e)
            return Response(
                {"error": "Invalid known_hosts line"}, status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=["get"], url_path="stats")
    def stats(self, request):
        """Get statistics about SSH host keys for the current customer."""
        qs = self.get_queryset()

        # Use single aggregation query for efficiency
        # Count with filter requires Django 2.2+
        total = qs.count()
        verified = qs.filter(verified=True).count()
        unverified = total - verified
        by_type = dict(qs.values_list("key_type").annotate(Count("key_type")))

        return Response(
            {
                "total": total,
                "verified": verified,
                "unverified": unverified,
                "by_key_type": by_type,
            }
        )


class DiscoveredDeviceViewSet(CustomerScopedQuerysetMixin, viewsets.ModelViewSet):
    """ViewSet for managing discovered devices in the discovery queue.

    Discovered devices are neighbors found via CDP/LLDP that are not yet
    in the device inventory. Users can review, approve, reject, or ignore them.
    """

    queryset = DiscoveredDevice.objects.all()
    serializer_class = DiscoveredDeviceSerializer
    permission_classes = [IsAuthenticated, RolePermission, ObjectCustomerPermission]
    customer_field = "customer_id"
    filterset_fields = ["status", "discovered_via_protocol", "hostname"]

    def get_queryset(self):
        qs = super().get_queryset()
        # Filter by status if provided
        status_filter = self.request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs.select_related(
            "customer", "discovered_via_device", "reviewed_by", "created_device"
        )

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None) -> Response:
        """Approve a discovered device and create a Device from it.

        Request body:
        - credential_id: ID of credential to assign (required)
        - vendor: Device vendor (required if not auto-detected)
        - platform: Device platform (optional, uses discovered if not provided)
        - role: Device role (optional)
        - site: Device site (optional)
        """
        discovered = self.get_object()

        if discovered.status != DiscoveredDevice.STATUS_PENDING:
            return Response(
                {"detail": f"Device already {discovered.status}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = DiscoveredDeviceApproveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Verify credential belongs to same customer
        credential_id = serializer.validated_data["credential_id"]
        try:
            credential = Credential.objects.get(id=credential_id, customer=discovered.customer)
        except Credential.DoesNotExist:
            return Response(
                {"detail": "Credential not found or not accessible"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            device = discovered.approve_and_create_device(
                credential=credential,
                user=request.user,
                vendor=serializer.validated_data.get("vendor") or None,
                platform=serializer.validated_data.get("platform") or None,
                role=serializer.validated_data.get("role") or None,
                site=serializer.validated_data.get("site") or None,
            )
            return Response(
                {
                    "detail": "Device created",
                    "device_id": device.id,
                    "hostname": device.hostname,
                },
                status=status.HTTP_201_CREATED,
            )
        except ValueError as e:
            logger.warning("Device approval failed for %s: %s", discovered.id, e)
            return Response(
                {"detail": "Could not approve device. Check vendor is provided."},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None) -> Response:
        """Reject a discovered device."""
        discovered = self.get_object()

        if discovered.status != DiscoveredDevice.STATUS_PENDING:
            return Response(
                {"detail": f"Device already {discovered.status}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = DiscoveredDeviceRejectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        discovered.reject(
            user=request.user,
            notes=serializer.validated_data.get("notes"),
        )
        return Response({"detail": "Device rejected"})

    @action(detail=True, methods=["post"])
    def ignore(self, request, pk=None) -> Response:
        """Mark a discovered device as ignored (e.g., non-network device)."""
        discovered = self.get_object()

        if discovered.status != DiscoveredDevice.STATUS_PENDING:
            return Response(
                {"detail": f"Device already {discovered.status}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = DiscoveredDeviceRejectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        discovered.ignore(
            user=request.user,
            notes=serializer.validated_data.get("notes"),
        )
        return Response({"detail": "Device ignored"})

    @action(detail=False, methods=["post"], url_path="bulk-approve")
    def bulk_approve(self, request) -> Response:
        """Approve multiple discovered devices at once.

        Request body:
        - ids: List of discovered device IDs to approve
        - credential_id: ID of credential to assign to all
        - vendor: Default vendor for devices without auto-detected vendor

        Note: All devices must belong to the same customer.
        """
        ids = request.data.get("ids", [])
        credential_id = request.data.get("credential_id")
        default_vendor = request.data.get("vendor")

        if not ids:
            return Response(
                {"detail": "No device IDs provided"}, status=status.HTTP_400_BAD_REQUEST
            )
        if not credential_id:
            return Response(
                {"detail": "credential_id is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Get all pending devices
        devices = self.get_queryset().filter(id__in=ids, status=DiscoveredDevice.STATUS_PENDING)

        # Verify all devices belong to the same customer (security: prevent cross-tenant)
        customer_ids = set(devices.values_list("customer_id", flat=True))
        if not customer_ids:
            return Response(
                {"detail": "No valid devices found"}, status=status.HTTP_400_BAD_REQUEST
            )
        if len(customer_ids) > 1:
            return Response(
                {"detail": "All devices must belong to the same customer"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        customer_id = next(iter(customer_ids))

        # Verify credential belongs to the same customer
        try:
            credential = Credential.objects.get(id=credential_id, customer_id=customer_id)
        except Credential.DoesNotExist:
            return Response(
                {"detail": "Credential not found or not accessible"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        created = []
        errors = []
        for discovered in devices:
            try:
                device = discovered.approve_and_create_device(
                    credential=credential,
                    user=request.user,
                    vendor=default_vendor,
                )
                created.append({"id": discovered.id, "device_id": device.id})
            except ValueError as e:
                logger.warning("Bulk approval failed for device %s: %s", discovered.id, e)
                errors.append({"id": discovered.id, "error": "Failed to approve device"})

        return Response(
            {"created": created, "errors": errors},
            status=status.HTTP_201_CREATED if created else status.HTTP_400_BAD_REQUEST,
        )

    @action(detail=False, methods=["get"], url_path="stats")
    def stats(self, request) -> Response:
        """Get discovery queue statistics."""
        qs = self.get_queryset()
        return Response(
            {
                "pending": qs.filter(status=DiscoveredDevice.STATUS_PENDING).count(),
                "approved": qs.filter(status=DiscoveredDevice.STATUS_APPROVED).count(),
                "rejected": qs.filter(status=DiscoveredDevice.STATUS_REJECTED).count(),
                "ignored": qs.filter(status=DiscoveredDevice.STATUS_IGNORED).count(),
                "total": qs.count(),
            }
        )


# =============================================================================
# Issue #40 - Bulk Device Onboarding ViewSets
# =============================================================================


class BulkOnboardingViewSet(viewsets.ViewSet):
    """ViewSet for bulk device onboarding operations.

    Provides endpoints for:
    - IP range scanning
    - SNMP-based discovery
    - Credential testing
    """

    permission_classes = [IsAuthenticated, RolePermission]

    @action(detail=False, methods=["post"], url_path="scan")
    def scan_ip_range(self, request) -> Response:
        """Start an IP range scan job for device discovery.

        Request body:
        - ip_ranges: List of CIDR notation IP ranges (e.g., ["192.168.1.0/24"])
        - credential_ids: List of credential IDs to test
        - use_snmp: Use SNMP for discovery (default: true)
        - snmp_community: SNMP community string (default: "public")
        - snmp_version: SNMP version "2c" or "3" (default: "2c")
        - test_ssh: Test SSH connectivity (default: true)
        - ports: SSH ports to test (default: [22])
        """
        customer = resolve_customer_for_request(request)
        if not customer:
            return Response(
                {"detail": "customer_id required or no access"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = IPRangeScanRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Validate credentials belong to customer
        credential_ids = serializer.validated_data["credential_ids"]
        valid_creds = Credential.objects.filter(
            id__in=credential_ids, customer=customer
        ).values_list("id", flat=True)
        if not valid_creds:
            return Response(
                {"detail": "No valid credentials found for customer"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        js = JobService()
        job = js.create_job(
            job_type="ip_range_scan",
            user=request.user,
            customer=customer,
            target_summary={"ip_ranges": serializer.validated_data["ip_ranges"]},
            payload={
                "ip_ranges": serializer.validated_data["ip_ranges"],
                "credential_ids": list(valid_creds),
                "use_snmp": serializer.validated_data.get("use_snmp", True),
                "snmp_community": serializer.validated_data.get("snmp_community", "public"),
                "snmp_version": serializer.validated_data.get("snmp_version", "2c"),
                "test_ssh": serializer.validated_data.get("test_ssh", True),
                "ports": serializer.validated_data.get("ports", [22]),
            },
        )
        return Response(
            {"job_id": job.id, "status": job.status},
            status=status.HTTP_202_ACCEPTED,
        )

    @action(detail=False, methods=["post"], url_path="test-credential")
    def test_credential(self, request) -> Response:
        """Test a credential against a specific IP address.

        Request body:
        - ip_address: IP address to test
        - credential_id: Credential ID to test
        - port: SSH port (default: 22)
        - timeout: Connection timeout in seconds (default: 10)
        """
        customer = resolve_customer_for_request(request)
        if not customer:
            return Response(
                {"detail": "customer_id required or no access"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = CredentialTestRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Validate credential belongs to customer
        try:
            credential = Credential.objects.get(
                id=serializer.validated_data["credential_id"],
                customer=customer,
            )
        except Credential.DoesNotExist:
            return Response(
                {"detail": "Credential not found or not accessible"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Import the test function
        from webnet.jobs.tasks import _test_ssh_credential

        success, device_info, message = _test_ssh_credential(
            serializer.validated_data["ip_address"],
            credential.username,
            credential.password or "",
            serializer.validated_data.get("port", 22),
            serializer.validated_data.get("timeout", 10),
        )

        return Response(
            {
                "success": success,
                "credential_id": credential.id,
                "ip_address": serializer.validated_data["ip_address"],
                "message": message,
                "device_info": device_info,
            }
        )

    @action(detail=False, methods=["post"], url_path="test-credentials-bulk")
    def test_credentials_bulk(self, request) -> Response:
        """Queue a job to test credentials against multiple discovered devices.

        Request body:
        - discovered_device_ids: List of DiscoveredDevice IDs to test
        - credential_ids: List of Credential IDs to try
        """
        customer = resolve_customer_for_request(request)
        if not customer:
            return Response(
                {"detail": "customer_id required or no access"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        device_ids = request.data.get("discovered_device_ids", [])
        credential_ids = request.data.get("credential_ids", [])

        if not device_ids or not credential_ids:
            return Response(
                {"detail": "discovered_device_ids and credential_ids are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate devices and credentials belong to customer
        valid_devices = DiscoveredDevice.objects.filter(
            id__in=device_ids, customer=customer
        ).values_list("id", flat=True)
        valid_creds = Credential.objects.filter(
            id__in=credential_ids, customer=customer
        ).values_list("id", flat=True)

        if not valid_devices or not valid_creds:
            return Response(
                {"detail": "No valid devices or credentials found"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        js = JobService()
        job = js.create_job(
            job_type="credential_test",
            user=request.user,
            customer=customer,
            target_summary={"device_count": len(valid_devices)},
            payload={
                "discovered_device_ids": list(valid_devices),
                "credential_ids": list(valid_creds),
            },
        )
        return Response(
            {"job_id": job.id, "status": job.status},
            status=status.HTTP_202_ACCEPTED,
        )


# =============================================================================
# Issue #24 - Device Tags and Groups ViewSets
# =============================================================================


class TagViewSet(CustomerScopedQuerysetMixin, viewsets.ModelViewSet):
    """ViewSet for managing device tags.

    Tags allow flexible grouping of devices for automation targeting,
    compliance scoping, and organization.
    """

    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [IsAuthenticated, RolePermission, ObjectCustomerPermission]
    customer_field = "customer_id"

    def get_queryset(self):
        qs = super().get_queryset()
        # Annotate with device count

        return qs.annotate(device_count=Count("devices")).order_by("category", "name")

    @action(detail=False, methods=["post"], url_path="bulk-assign")
    def bulk_assign(self, request) -> Response:
        """Bulk assign or remove tags from devices.

        Request body:
        - device_ids: List of device IDs
        - tag_ids: List of tag IDs
        - action: "add", "remove", or "set" (replace all tags)
        """
        serializer = DeviceTagAssignmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        device_ids = serializer.validated_data["device_ids"]
        tag_ids = serializer.validated_data["tag_ids"]
        action_type = serializer.validated_data.get("action", "add")

        # Get devices and tags (customer-scoped)
        devices = Device.objects.filter(id__in=device_ids)
        devices = self._filter_by_customer(devices)
        tags = Tag.objects.filter(id__in=tag_ids)
        tags = self._filter_by_customer(tags)

        if not devices.exists():
            return Response(
                {"detail": "No valid devices found"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        updated_count = 0
        for device in devices:
            if action_type == "add":
                device.device_tags.add(*tags)
            elif action_type == "remove":
                device.device_tags.remove(*tags)
            elif action_type == "set":
                device.device_tags.set(tags)
            updated_count += 1

        return Response(
            {
                "updated_count": updated_count,
                "action": action_type,
            }
        )

    def _filter_by_customer(self, qs):
        """Filter queryset by customer access."""
        user = self.request.user
        if getattr(user, "role", "viewer") == "admin":
            return qs
        customer_ids = list(user.customers.values_list("id", flat=True))
        return qs.filter(customer_id__in=customer_ids)


class DeviceGroupViewSet(CustomerScopedQuerysetMixin, viewsets.ModelViewSet):
    """ViewSet for managing device groups.

    Device groups support both static (explicit device list) and
    dynamic (filter-based) membership.
    """

    queryset = DeviceGroup.objects.all()
    serializer_class = DeviceGroupSerializer
    permission_classes = [IsAuthenticated, RolePermission, ObjectCustomerPermission]
    customer_field = "customer_id"

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.select_related("customer", "parent").order_by("name")

    @action(detail=True, methods=["get"])
    def devices(self, request, pk=None) -> Response:
        """Get all devices in this group (evaluates dynamic rules)."""
        group = self.get_object()
        devices = group.get_devices()
        return Response(DeviceSerializer(devices, many=True).data)

    @action(detail=True, methods=["post"], url_path="add-devices")
    def add_devices(self, request, pk=None) -> Response:
        """Add devices to a static group.

        Request body:
        - device_ids: List of device IDs to add
        """
        group = self.get_object()
        if group.group_type != DeviceGroup.TYPE_STATIC:
            return Response(
                {"detail": "Cannot manually add devices to dynamic groups"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        device_ids = request.data.get("device_ids", [])
        devices = Device.objects.filter(id__in=device_ids, customer=group.customer)
        group.devices.add(*devices)

        return Response({"added_count": devices.count()})

    @action(detail=True, methods=["post"], url_path="remove-devices")
    def remove_devices(self, request, pk=None) -> Response:
        """Remove devices from a static group.

        Request body:
        - device_ids: List of device IDs to remove
        """
        group = self.get_object()
        if group.group_type != DeviceGroup.TYPE_STATIC:
            return Response(
                {"detail": "Cannot manually remove devices from dynamic groups"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        device_ids = request.data.get("device_ids", [])
        devices = Device.objects.filter(id__in=device_ids)
        group.devices.remove(*devices)

        return Response({"removed_count": len(device_ids)})

    @action(detail=True, methods=["post"], url_path="run-job")
    def run_job(self, request, pk=None) -> Response:
        """Run an automation job targeting this group's devices.

        Request body:
        - job_type: Type of job (e.g., "config_backup", "run_commands")
        - payload: Job-specific payload
        """
        group = self.get_object()
        job_type = request.data.get("job_type")
        payload = request.data.get("payload", {})

        if not job_type:
            return Response(
                {"detail": "job_type is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get device IDs from group
        device_ids = list(group.get_devices().values_list("id", flat=True))
        if not device_ids:
            return Response(
                {"detail": "Group has no devices"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        js = JobService()
        job = js.create_job(
            job_type=job_type,
            user=request.user,
            customer=group.customer,
            target_summary={"group_id": group.id, "group_name": group.name},
            payload={**payload, "device_ids": device_ids},
        )

        return Response(
            {"job_id": job.id, "status": job.status, "device_count": len(device_ids)},
            status=status.HTTP_202_ACCEPTED,
        )

    @action(detail=False, methods=["post"], url_path="from-filter")
    def create_from_filter(self, request) -> Response:
        """Create a dynamic group from current filter criteria.

        Request body:
        - name: Group name
        - description: Optional description
        - filter_rules: Filter rules dict (vendor, platform, site, role, tags, etc.)
        """
        customer = resolve_customer_for_request(request)
        if not customer:
            return Response(
                {"detail": "customer_id required or no access"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        name = request.data.get("name")
        if not name:
            return Response(
                {"detail": "name is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        filter_rules = request.data.get("filter_rules", {})

        group = DeviceGroup.objects.create(
            customer=customer,
            name=name,
            description=request.data.get("description", ""),
            group_type=DeviceGroup.TYPE_DYNAMIC,
            filter_rules=filter_rules,
        )

        return Response(
            DeviceGroupSerializer(group).data,
            status=status.HTTP_201_CREATED,
        )


# ==============================================================================
# Configuration Template ViewSet (Issue #16)
# ==============================================================================


class ConfigTemplateViewSet(CustomerScopedQuerysetMixin, viewsets.ModelViewSet):
    """ViewSet for managing configuration templates.

    Provides CRUD operations for Jinja2 configuration templates,
    plus rendering and deployment capabilities.
    """

    queryset = ConfigTemplate.objects.select_related("customer", "created_by")
    serializer_class = ConfigTemplateSerializer
    permission_classes = [IsAuthenticated, RolePermission, ObjectCustomerPermission]
    customer_field = "customer_id"
    filterset_fields = ["category", "is_active"]

    def get_queryset(self):
        qs = super().get_queryset()
        # Filter by category if provided
        category = self.request.query_params.get("category")
        if category:
            qs = qs.filter(category=category)
        # Filter by platform tag if provided
        platform = self.request.query_params.get("platform")
        if platform:
            qs = qs.filter(platform_tags__contains=[platform])
        return qs.order_by("category", "name")

    @action(detail=True, methods=["post"])
    def render(self, request, pk=None) -> Response:
        """Render a template with provided variables.

        Request body:
        - variables: Dictionary of variable values
        - device_id: Optional device ID for context

        Returns:
        - rendered_config: The rendered configuration text
        - errors: Any validation or rendering errors
        """
        template = self.get_object()
        serializer = ConfigTemplateRenderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        variables = serializer.validated_data.get("variables", {})
        device_id = serializer.validated_data.get("device_id")

        # Add device context if provided
        if device_id:
            try:
                device = Device.objects.get(pk=device_id, customer=template.customer)
                variables.setdefault("hostname", device.hostname)
                variables.setdefault("mgmt_ip", device.mgmt_ip)
                variables.setdefault("vendor", device.vendor)
                variables.setdefault("platform", device.platform)
                variables.setdefault("site", device.site or "")
                variables.setdefault("role", device.role or "")
            except Device.DoesNotExist:
                return Response(
                    {"detail": "Device not found or not accessible"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        try:
            rendered = template.render(variables)
            return Response(
                {
                    "rendered_config": rendered,
                    "template_id": template.id,
                    "template_name": template.name,
                    "variables_used": variables,
                }
            )
        except ValueError as e:
            # ValueError from template validation contains user-facing messages
            logger.warning("Template validation error for template %s: %s", template.id, e)
            return Response(
                {
                    "detail": "Template rendering failed due to invalid input.",
                    "errors": ["Invalid template or variable values."],
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception:
            logger.exception("Template rendering failed for template %s", template.id)
            return Response(
                {"detail": "Template rendering failed due to an internal error."},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=True, methods=["post"])
    def deploy(self, request, pk=None) -> Response:
        """Deploy a rendered template to devices.

        Request body:
        - variables: Dictionary of variable values
        - device_ids: List of device IDs to deploy to
        - mode: 'merge' or 'replace' (default: merge)
        - dry_run: If true, preview only (default: true)

        Returns:
        - job_id: ID of the created deployment job
        """
        template = self.get_object()
        serializer = ConfigTemplateDeploySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        variables = serializer.validated_data.get("variables", {})
        device_ids = serializer.validated_data["device_ids"]
        mode = serializer.validated_data.get("mode", "merge")
        dry_run = serializer.validated_data.get("dry_run", True)

        # Validate devices exist and belong to the same customer
        devices = Device.objects.filter(pk__in=device_ids, customer=template.customer)
        if devices.count() != len(device_ids):
            return Response(
                {"detail": "Some devices not found or not accessible"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Render the template
        try:
            rendered = template.render(variables)
        except ValueError as e:
            logger.warning("Template rendering value error: %s", e)
            return Response(
                {"detail": "Invalid input for template rendering."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception:
            logger.exception("Template rendering failed for template %s", template.id)
            return Response(
                {"detail": "Template rendering failed due to an internal error."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Create the deployment job
        job_type = "config_deploy_preview" if dry_run else "config_deploy_commit"
        js = JobService()
        job = js.create_job(
            job_type=job_type,
            user=request.user,
            customer=template.customer,
            target_summary={"filters": {"device_ids": device_ids}},
            payload={
                "mode": mode,
                "snippet": rendered,
                "template_id": template.id,
                "template_name": template.name,
            },
        )

        return Response(
            {"job_id": job.id, "status": job.status, "dry_run": dry_run},
            status=status.HTTP_202_ACCEPTED,
        )

    @action(detail=True, methods=["get"])
    def validate(self, request, pk=None) -> Response:
        """Validate template syntax without rendering.

        Returns:
        - valid: Whether the template is syntactically valid
        - errors: List of syntax errors if any
        """
        template = self.get_object()

        from jinja2 import Environment, BaseLoader, TemplateSyntaxError

        env = Environment(loader=BaseLoader())
        try:
            env.parse(template.template_content)
            return Response({"valid": True, "errors": []})
        except TemplateSyntaxError as e:
            return Response(
                {
                    "valid": False,
                    "errors": [{"line": e.lineno, "message": str(e.message)}],
                }
            )

    @action(detail=False, methods=["get"])
    def categories(self, request) -> Response:
        """Get available template categories with counts."""

        qs = self.get_queryset()
        categories = qs.values("category").annotate(count=Count("id")).order_by("category")
        return Response(
            {
                "categories": list(categories),
                "choices": ConfigTemplate.CATEGORY_CHOICES,
            }
        )


# ==============================================================================
# NetBox Integration ViewSet (Issue #9)
# ==============================================================================


class NetBoxConfigViewSet(CustomerScopedQuerysetMixin, viewsets.ModelViewSet):
    """ViewSet for managing NetBox configurations.

    Each customer can have one NetBox configuration for syncing devices.
    """

    queryset = NetBoxConfig.objects.select_related("customer", "default_credential")
    serializer_class = NetBoxConfigSerializer
    permission_classes = [IsAuthenticated, RolePermission, ObjectCustomerPermission]
    customer_field = "customer_id"

    @action(detail=True, methods=["post"])
    def sync(self, request, pk=None) -> Response:
        """Trigger a manual sync from NetBox.

        Request body:
        - full_sync: If true, sync all devices (default: false for delta sync)

        Returns:
        - job_id: ID of the created sync job (if async)
        - or direct sync results (if sync is quick)
        """
        config = self.get_object()

        if not config.enabled:
            return Response(
                {"detail": "NetBox sync is disabled for this configuration"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not config.has_api_token():
            return Response(
                {"detail": "NetBox API token is not configured"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = NetBoxSyncRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        full_sync = serializer.validated_data.get("full_sync", False)

        # Queue the sync task
        from webnet.jobs.tasks import netbox_sync_job

        netbox_sync_job.delay(config.id, full_sync=full_sync)

        return Response(
            {
                "detail": "NetBox sync queued",
                "config_id": config.id,
                "full_sync": full_sync,
            },
            status=status.HTTP_202_ACCEPTED,
        )

    @action(detail=True, methods=["post"], url_path="test-connection")
    def test_connection(self, request, pk=None) -> Response:
        """Test the NetBox API connection.

        Returns:
        - success: Whether the connection was successful
        - message: Success or error message
        - netbox_version: NetBox version if successful
        """
        config = self.get_object()

        if not config.has_api_token():
            return Response(
                {
                    "success": False,
                    "message": "API token is not configured",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        from webnet.devices.netbox_service import NetBoxService

        service = NetBoxService(config)
        result = service.test_connection()

        return Response(
            {
                "success": result.success,
                "message": result.message,
                "netbox_version": getattr(result, "netbox_version", None),
            },
            status=status.HTTP_200_OK if result.success else status.HTTP_400_BAD_REQUEST,
        )

    @action(detail=True, methods=["get"])
    def logs(self, request, pk=None) -> Response:
        """Get sync logs for this configuration."""
        config = self.get_object()
        logs = NetBoxSyncLog.objects.filter(config=config).order_by("-started_at")[:50]
        return Response(NetBoxSyncLogSerializer(logs, many=True).data)

    @action(detail=True, methods=["get"])
    def preview(self, request, pk=None) -> Response:
        """Preview what devices would be synced without actually syncing.

        Returns:
        - devices: List of devices that would be created/updated
        - total: Total count of devices
        """
        config = self.get_object()

        if not config.has_api_token():
            return Response(
                {"detail": "API token is not configured"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from webnet.devices.netbox_service import NetBoxService

        service = NetBoxService(config)
        try:
            preview = service.preview_sync()
            return Response(
                {
                    "devices": preview.devices[:100],  # Limit preview
                    "total": preview.total,
                    "would_create": preview.would_create,
                    "would_update": preview.would_update,
                }
            )
        except Exception:
            logger.exception("NetBox preview failed for config %s", config.id)
            return Response(
                {"detail": "Preview failed due to an internal error."},
                status=status.HTTP_400_BAD_REQUEST,
            )


class AnsibleConfigViewSet(CustomerScopedQuerysetMixin, viewsets.ModelViewSet):
    """ViewSet for Ansible configuration management."""

    queryset = AnsibleConfig.objects.all()
    serializer_class = AnsibleConfigSerializer
    permission_classes = [IsAuthenticated, RolePermission, ObjectCustomerPermission]
    customer_field = "customer_id"


class PlaybookViewSet(CustomerScopedQuerysetMixin, viewsets.ModelViewSet):
    """ViewSet for Ansible playbook management."""

    queryset = Playbook.objects.all()
    serializer_class = PlaybookSerializer
    permission_classes = [IsAuthenticated, RolePermission, ObjectCustomerPermission]
    customer_field = "customer_id"

    def get_queryset(self):
        """Filter playbooks by customer."""
        qs = super().get_queryset()
        # Optionally filter by tags
        tags = self.request.query_params.get("tags")
        if tags:
            tag_list = [t.strip() for t in tags.split(",")]
            for tag in tag_list:
                qs = qs.filter(tags__contains=[tag])
        return qs

    @action(detail=True, methods=["post"])
    def execute(self, request, pk=None) -> Response:
        """Execute a playbook against managed devices.

        Request body:
        - targets: Device filter targets (site, role, vendor, device_ids)
        - extra_vars: Extra variables to pass to playbook
        - limit: Limit execution to specific hosts
        - tags: Ansible tags to run
        """
        playbook = self.get_object()
        serializer = PlaybookExecuteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        targets = serializer.validated_data.get("targets", {})
        extra_vars = serializer.validated_data.get("extra_vars", {})
        limit = serializer.validated_data.get("limit")
        tags = serializer.validated_data.get("tags")

        # Use playbook's customer
        customer = playbook.customer

        # Create job
        js = JobService()
        job = js.create_job(
            job_type="ansible_playbook",
            user=request.user,
            customer=customer,
            target_summary={"filters": targets},
            payload={
                "playbook_id": playbook.id,
                "extra_vars": extra_vars,
                "limit": limit,
                "tags": tags or [],
            },
        )

        return Response(
            {
                "job_id": job.id,
                "status": job.status,
                "message": f"Playbook '{playbook.name}' execution started",
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["get"])
    def validate(self, request, pk=None) -> Response:
        """Validate playbook YAML syntax.

        Returns validation result with any syntax errors.
        """
        playbook = self.get_object()

        if playbook.source_type != "inline":
            return Response(
                {"detail": "Validation only supported for inline playbooks"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            import yaml

            yaml.safe_load(playbook.content)
            return Response(
                {
                    "valid": True,
                    "message": "Playbook syntax is valid",
                }
            )
        except yaml.YAMLError as e:
            return Response(
                {
                    "valid": False,
                    "message": "Playbook syntax error",
                    "error": str(e),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception:
            logger.exception("Error validating playbook %s", playbook.id)
            return Response(
                {
                    "valid": False,
                    "message": "Validation failed due to an internal error",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# ==============================================================================
# ServiceNow Integration ViewSets
# ==============================================================================


class ServiceNowConfigViewSet(CustomerScopedQuerysetMixin, viewsets.ModelViewSet):
    """ViewSet for managing ServiceNow configurations.

    Each customer can have one ServiceNow configuration for CMDB sync,
    incident management, and change requests.
    """

    queryset = ServiceNowConfig.objects.select_related("customer", "default_credential")
    serializer_class = ServiceNowConfigSerializer
    permission_classes = [IsAuthenticated, RolePermission, ObjectCustomerPermission]
    customer_field = "customer_id"

    @action(detail=True, methods=["post"])
    def sync(self, request, pk=None) -> Response:
        """Trigger a manual sync with ServiceNow CMDB.

        Request body:
        - direction: "import" (from ServiceNow), "export" (to ServiceNow), or "both"
        - device_ids: Optional list of device IDs to sync (only for export)

        Returns:
        - detail: Status message
        - config_id: ID of the ServiceNow configuration
        """
        config = self.get_object()

        if not config.has_password():
            return Response(
                {"detail": "ServiceNow password is not configured"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = ServiceNowSyncRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        direction = serializer.validated_data.get("direction", "both")
        device_ids = serializer.validated_data.get("device_ids")

        # Queue the sync task
        from webnet.jobs.tasks import servicenow_sync_job

        servicenow_sync_job.delay(config.id, direction=direction, device_ids=device_ids)

        return Response(
            {
                "detail": "ServiceNow sync queued",
                "config_id": config.id,
                "direction": direction,
            },
            status=status.HTTP_202_ACCEPTED,
        )

    @action(detail=True, methods=["post"], url_path="test-connection")
    def test_connection(self, request, pk=None) -> Response:
        """Test the ServiceNow API connection.

        Returns:
        - success: Whether the connection was successful
        - message: Success or error message
        - servicenow_version: ServiceNow version if available
        """
        config = self.get_object()

        if not config.has_password():
            return Response(
                {
                    "success": False,
                    "message": "Password is not configured",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        from webnet.devices.servicenow_service import ServiceNowService

        service = ServiceNowService(config)
        result = service.test_connection()

        return Response(
            {
                "success": result.success,
                "message": result.message,
                "servicenow_version": getattr(result, "servicenow_version", None),
            },
            status=status.HTTP_200_OK if result.success else status.HTTP_400_BAD_REQUEST,
        )

    @action(detail=True, methods=["get"])
    def logs(self, request, pk=None) -> Response:
        """Get sync logs for this configuration."""
        config = self.get_object()
        logs = ServiceNowSyncLog.objects.filter(config=config).order_by("-started_at")[:50]
        return Response(ServiceNowSyncLogSerializer(logs, many=True).data)


class ServiceNowIncidentViewSet(CustomerScopedQuerysetMixin, viewsets.ModelViewSet):
    """ViewSet for managing ServiceNow incidents."""

    queryset = ServiceNowIncident.objects.select_related("config", "job")
    serializer_class = ServiceNowIncidentSerializer
    permission_classes = [IsAuthenticated, RolePermission, ObjectCustomerPermission]
    customer_field = "config__customer_id"

    @action(detail=True, methods=["patch"])
    def update_state(self, request, pk=None) -> Response:
        """Update an incident's state in ServiceNow.

        Request body:
        - state: New state (1=New, 2=In Progress, 3=On Hold, 6=Resolved, 7=Closed)
        - work_notes: Optional work notes
        - resolution_notes: Optional resolution notes
        """
        incident = self.get_object()
        serializer = ServiceNowIncidentUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        from webnet.devices.servicenow_service import ServiceNowService

        service = ServiceNowService(incident.config)
        result = service.update_incident(
            incident.incident_sys_id,
            state=serializer.validated_data.get("state"),
            work_notes=serializer.validated_data.get("work_notes"),
            resolution_notes=serializer.validated_data.get("resolution_notes"),
        )

        if result.success:
            # Update local record
            if serializer.validated_data.get("state"):
                incident.state = serializer.validated_data["state"]
            if incident.state in [6, 7] and not incident.resolved_at:
                incident.resolved_at = timezone.now()
            incident.save()

            return Response(
                {
                    "success": True,
                    "message": result.message,
                    "incident_number": result.incident_number,
                },
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {
                    "success": False,
                    "message": result.message or "Failed to update incident",
                    "error": result.error,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )


class ServiceNowChangeRequestViewSet(CustomerScopedQuerysetMixin, viewsets.ModelViewSet):
    """ViewSet for managing ServiceNow change requests."""

    queryset = ServiceNowChangeRequest.objects.select_related("config", "job")
    serializer_class = ServiceNowChangeRequestSerializer
    permission_classes = [IsAuthenticated, RolePermission, ObjectCustomerPermission]
    customer_field = "config__customer_id"

    def create(self, request, *args, **kwargs) -> Response:
        """Create a new change request in ServiceNow.

        Request body must include:
        - config_id: ServiceNow configuration ID
        - job_id: Job ID to link to the change
        - short_description: Brief summary
        - description: Detailed description
        - justification: Business justification
        - risk: Risk level (1-3)
        - impact: Impact level (1-3)
        - device_ids: Optional list of device IDs affected
        """
        serializer = ServiceNowChangeRequestCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Get config and validate access
        config_id = request.data.get("config_id")
        job_id = request.data.get("job_id")

        if not config_id:
            return Response(
                {"detail": "config_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not job_id:
            return Response(
                {"detail": "job_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            config = ServiceNowConfig.objects.get(id=config_id)
            if not user_has_customer_access(request.user, config.customer_id):
                return Response(
                    {"detail": "You do not have access to this configuration"},
                    status=status.HTTP_403_FORBIDDEN,
                )
        except ServiceNowConfig.DoesNotExist:
            return Response(
                {"detail": "ServiceNow configuration not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            job = Job.objects.get(id=job_id, customer_id=config.customer_id)
        except Job.DoesNotExist:
            return Response(
                {"detail": "Job not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Get device sys_ids if device_ids provided
        ci_sys_ids = []
        device_ids = serializer.validated_data.get("device_ids")
        if device_ids:
            devices = Device.objects.filter(id__in=device_ids, customer_id=config.customer_id)
            for device in devices:
                tags = device.tags or {}
                if sys_id := tags.get("servicenow_sys_id"):
                    ci_sys_ids.append(sys_id)

        # Create change request in ServiceNow
        from webnet.devices.servicenow_service import ServiceNowService

        service = ServiceNowService(config)
        result = service.create_change_request(
            short_description=serializer.validated_data["short_description"],
            description=serializer.validated_data["description"],
            justification=serializer.validated_data["justification"],
            risk=serializer.validated_data.get("risk", 3),
            impact=serializer.validated_data.get("impact", 3),
            assignment_group=config.change_assignment_group,
            configuration_items=ci_sys_ids if ci_sys_ids else None,
        )

        if result.success:
            # Create local record
            change = ServiceNowChangeRequest.objects.create(
                config=config,
                job=job,
                change_number=result.change_number,
                change_sys_id=result.change_sys_id,
                short_description=serializer.validated_data["short_description"],
                description=serializer.validated_data["description"],
                justification=serializer.validated_data["justification"],
            )

            return Response(
                ServiceNowChangeRequestSerializer(change).data,
                status=status.HTTP_201_CREATED,
            )
        else:
            return Response(
                {
                    "success": False,
                    "message": result.message or "Failed to create change request",
                    "error": result.error,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=True, methods=["patch"])
    def update_state(self, request, pk=None) -> Response:
        """Update a change request's state in ServiceNow.

        Request body:
        - state: New state (-5=New, 0=Assess, 1=Authorize, 2=Scheduled, 3=Implement, 4=Review, 6=Closed)
        - work_notes: Optional work notes
        - close_notes: Optional closing notes
        """
        change = self.get_object()
        serializer = ServiceNowChangeRequestUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        from webnet.devices.servicenow_service import ServiceNowService

        service = ServiceNowService(change.config)
        result = service.update_change_request(
            change.change_sys_id,
            state=serializer.validated_data.get("state"),
            work_notes=serializer.validated_data.get("work_notes"),
            close_notes=serializer.validated_data.get("close_notes"),
        )

        if result.success:
            # Update local record
            if serializer.validated_data.get("state"):
                change.state = serializer.validated_data["state"]
            if change.state == 6 and not change.closed_at:
                change.closed_at = timezone.now()
            change.save()

            return Response(
                {
                    "success": True,
                    "message": result.message,
                    "change_number": result.change_number,
                },
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {
                    "success": False,
                    "message": result.message or "Failed to update change request",
                    "error": result.error,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )


# ==============================================================================
# Webhook ViewSets
# ==============================================================================


class WebhookViewSet(CustomerScopedQuerysetMixin, viewsets.ModelViewSet):
    """ViewSet for managing webhooks."""

    queryset = Webhook.objects.all()
    serializer_class = WebhookSerializer
    permission_classes = [IsAuthenticated, RolePermission]
    customer_field = "customer_id"
    filterset_fields = ["enabled", "customer"]
    search_fields = ["name", "url"]
    ordering_fields = ["name", "created_at"]

    def perform_create(self, serializer):
        """Set created_by when creating webhook."""
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=["post"])
    def test(self, request, pk=None):
        """Test webhook delivery with a sample payload."""
        webhook = self.get_object()

        # Create a test delivery
        test_payload = {
            "event_timestamp": timezone.now().isoformat(),
            "event_type": "webhook.test",
            "message": "This is a test webhook delivery",
            "webhook": {
                "id": webhook.id,
                "name": webhook.name,
            },
        }

        delivery = WebhookDelivery.objects.create(
            webhook=webhook,
            event_type="webhook.test",
            event_id=webhook.id,
            payload=test_payload,
            status=WebhookDelivery.STATUS_PENDING,
        )

        # Trigger delivery asynchronously
        from webnet.webhooks.tasks import deliver_webhook

        deliver_webhook.delay(delivery.id)

        return Response(
            {
                "message": "Test webhook delivery initiated",
                "delivery_id": delivery.id,
            },
            status=status.HTTP_202_ACCEPTED,
        )


class WebhookDeliveryViewSet(CustomerScopedQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing webhook delivery history."""

    queryset = WebhookDelivery.objects.select_related("webhook").all()
    serializer_class = WebhookDeliverySerializer
    permission_classes = [IsAuthenticated, RolePermission]
    customer_field = "webhook__customer_id"
    filterset_fields = ["webhook", "status", "event_type"]
    search_fields = ["event_type", "error_message"]
    ordering_fields = ["created_at", "status"]
    ordering = ["-created_at"]

    @action(detail=True, methods=["post"])
    def retry(self, request, pk=None):
        """Manually retry a failed webhook delivery."""
        delivery = self.get_object()

        if delivery.status not in [WebhookDelivery.STATUS_FAILED, WebhookDelivery.STATUS_RETRYING]:
            return Response(
                {"detail": "Only failed or retrying deliveries can be manually retried"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Reset delivery state for retry
        delivery.status = WebhookDelivery.STATUS_PENDING
        delivery.next_retry_at = None
        delivery.save()

        # Trigger delivery
        from webnet.webhooks.tasks import deliver_webhook

        deliver_webhook.delay(delivery.id)

        return Response(
            {"message": "Webhook delivery retry initiated"},
            status=status.HTTP_202_ACCEPTED,
        )


# ==============================================================================
# Multi-region Deployment ViewSets
# ==============================================================================


class RegionViewSet(viewsets.ModelViewSet):
    """ViewSet for managing regions in multi-region deployment."""

    serializer_class = RegionSerializer
    permission_classes = [IsAuthenticated, RolePermission, ObjectCustomerPermission]
    customer_field = "customer_id"

    def get_serializer_class(self):
        if self.action == "update_health":
            return RegionHealthUpdateSerializer
        return RegionSerializer

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return Region.objects.none()

        customer_ids = user.customers.values_list("id", flat=True)
        return Region.objects.filter(customer_id__in=customer_ids).order_by("-priority", "name")

    def perform_create(self, serializer):
        # Ensure customer is one of user's customers
        customer_id = serializer.validated_data.get("customer")
        if customer_id and customer_id.id not in self.request.user.customers.values_list(
            "id", flat=True
        ):
            from rest_framework.exceptions import ValidationError

            raise ValidationError({"customer": "Invalid customer"})
        serializer.save()

    @action(detail=True, methods=["post"])
    def update_health(self, request, pk=None):
        """Update health status of a region."""
        region = self.get_object()
        serializer = RegionHealthUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        health_status = serializer.validated_data["health_status"]
        message = serializer.validated_data.get("message")

        region.update_health_status(health_status, message)

        return Response(RegionSerializer(region).data)

    @action(detail=True, methods=["get"])
    def jobs(self, request, pk=None):
        """Get jobs associated with this region."""
        region = self.get_object()
        jobs = Job.objects.filter(region=region, customer=region.customer).order_by(
            "-requested_at"
        )[:100]

        serializer = JobSerializer(jobs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def devices(self, request, pk=None):
        """Get devices assigned to this region."""
        region = self.get_object()
        devices = Device.objects.filter(region=region, customer=region.customer).order_by(
            "hostname"
        )[:100]

        serializer = DeviceSerializer(devices, many=True)
        return Response(serializer.data)
