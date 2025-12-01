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
from django.utils import timezone
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
from webnet.devices.models import Device, Credential, TopologyLink
from webnet.jobs.models import Job, JobLog
from webnet.jobs.services import JobService
from webnet.config_mgmt.models import ConfigSnapshot, GitRepository, GitSyncLog
from webnet.compliance.models import CompliancePolicy, ComplianceResult

from .serializers import (
    UserSerializer,
    UserCreateSerializer,
    APIKeySerializer,
    CustomerSerializer,
    CustomerIPRangeSerializer,
    CredentialSerializer,
    DeviceSerializer,
    JobSerializer,
    JobLogSerializer,
    ConfigSnapshotSerializer,
    CompliancePolicySerializer,
    ComplianceResultSerializer,
    TopologyLinkSerializer,
    GitRepositorySerializer,
    GitSyncLogSerializer,
)
from .permissions import (
    RolePermission,
    CustomerScopedQuerysetMixin,
    ObjectCustomerPermission,
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
                    "detail": f"File too large. Maximum size is {self.MAX_UPLOAD_SIZE // (1024*1024)}MB"
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
        customer = resolve_customer_for_request(request)
        if not customer:
            return Response(
                {"detail": "customer_id required or no access"}, status=status.HTTP_400_BAD_REQUEST
            )
        targets = request.data.get("targets") or {}
        js = JobService()
        job = js.create_job(
            job_type="topology_discovery",
            user=request.user,
            customer=customer,
            target_summary={"filters": targets},
            payload={},
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
        nodes = {}
        edges = []
        for link in links:
            local_id = str(link.local_device_id)
            remote_id = str(link.remote_device_id or f"unknown-{link.remote_hostname}")
            nodes[local_id] = {
                "id": local_id,
                "label": link.local_device.hostname,
                "data": {
                    "hostname": link.local_device.hostname,
                    "mgmt_ip": link.local_device.mgmt_ip,
                    "vendor": link.local_device.vendor,
                    "platform": link.local_device.platform,
                    "site": link.local_device.site,
                },
                "type": "device",
            }
            nodes[remote_id] = {
                "id": remote_id,
                "label": link.remote_hostname,
                "data": {
                    "hostname": link.remote_hostname,
                    "mgmt_ip": link.remote_ip,
                    "vendor": link.remote_platform,
                    "platform": link.remote_platform,
                },
                "type": "device" if link.remote_device_id else "unknown",
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
                        "discovered_at": link.discovered_at.isoformat(),
                    },
                }
            )
        return Response({"nodes": list(nodes.values()), "edges": edges})


class GitRepositoryViewSet(CustomerScopedQuerysetMixin, viewsets.ModelViewSet):
    """ViewSet for Git repository configuration.

    Provides CRUD operations and additional actions for:
    - Testing repository connection
    - Triggering manual sync
    - Viewing sync history
    """

    queryset = GitRepository.objects.select_related("customer")
    serializer_class = GitRepositorySerializer
    permission_classes = [IsAuthenticated, RolePermission, ObjectCustomerPermission]

    @action(detail=True, methods=["post"], url_path="test-connection")
    def test_connection(self, request, pk=None):
        """Test the Git repository connection."""
        repository = self.get_object()

        from webnet.config_mgmt.git_service import GitService

        service = GitService(repository)
        result = service.test_connection()

        return Response(
            {
                "success": result.success,
                "message": result.message,
                "error": result.error,
            },
            status=status.HTTP_200_OK if result.success else status.HTTP_400_BAD_REQUEST,
        )

    @action(detail=True, methods=["post"])
    def sync(self, request, pk=None):
        """Trigger a manual sync of unsynced config snapshots."""
        repository = self.get_object()

        if not repository.enabled:
            return Response(
                {"detail": "Git sync is disabled for this repository"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from webnet.jobs.tasks import git_sync_job

        # Queue async sync task
        git_sync_job.delay(repository.customer_id)

        return Response(
            {"detail": "Git sync queued", "customer_id": repository.customer_id},
            status=status.HTTP_202_ACCEPTED,
        )

    @action(detail=True, methods=["get"])
    def logs(self, request, pk=None):
        """Get sync logs for this repository."""
        repository = self.get_object()
        limit = int(request.query_params.get("limit", 20))
        logs = GitSyncLog.objects.filter(repository=repository).order_by("-started_at")[:limit]
        return Response(GitSyncLogSerializer(logs, many=True).data)

    @action(detail=True, methods=["get"])
    def commits(self, request, pk=None):
        """Get recent commits from the Git repository."""
        repository = self.get_object()
        limit = int(request.query_params.get("limit", 10))

        from webnet.config_mgmt.git_service import GitService

        service = GitService(repository)
        commits = service.get_recent_commits(limit=limit)

        return Response(commits)


class GitSyncLogViewSet(CustomerScopedQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    """ViewSet for Git sync logs (read-only)."""

    queryset = GitSyncLog.objects.select_related("repository", "repository__customer", "job")
    serializer_class = GitSyncLogSerializer
    permission_classes = [IsAuthenticated, RolePermission]
    customer_field = "repository__customer_id"
