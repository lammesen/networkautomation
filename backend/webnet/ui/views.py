from __future__ import annotations

from difflib import unified_diff
import json
import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Count
from django.http import HttpResponseForbidden, HttpResponseBadRequest, HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.views import View

from django import forms
from django.contrib.auth import logout
from django.urls import reverse

from webnet.api.permissions import user_has_customer_access
from webnet.compliance.models import (
    CompliancePolicy,
    ComplianceResult,
    RemediationRule,
    RemediationAction,
)
from webnet.config_mgmt.models import (
    ConfigSnapshot,
    GitRepository,
    GitSyncLog,
    ConfigTemplate,
    ConfigDrift,
    DriftAlert,
)
from webnet.customers.models import Customer
from webnet.devices.models import (
    Device,
    TopologyLink,
    Credential,
    DiscoveredDevice,
    Tag,
    DeviceGroup,
    NetBoxConfig,
    NetBoxSyncLog,
    SSHHostKey,
)
from webnet.jobs.models import Job, JobLog, Schedule
from webnet.jobs.services import JobService

logger = logging.getLogger(__name__)


class DeviceForm(forms.ModelForm):
    class Meta:
        model = Device
        fields = [
            "customer",
            "hostname",
            "mgmt_ip",
            "vendor",
            "platform",
            "role",
            "site",
            "credential",
        ]

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        if user and getattr(user, "role", "viewer") != "admin":
            self.fields["customer"].queryset = user.customers.all()
            self.fields["credential"].queryset = Credential.objects.filter(
                customer__in=user.customers.all()
            )
        else:
            self.fields["customer"].queryset = Customer.objects.all()
            self.fields["credential"].queryset = Credential.objects.all()
        self.fields["role"].required = False
        self.fields["site"].required = False


def logout_view(request):
    logout(request)
    return render(request, "auth/logout.html", status=200)


class TenantScopedView(LoginRequiredMixin, View):
    customer_field: str | tuple[str, ...] = "customer_id"
    allowed_write_roles = {"operator", "admin"}

    def filter_by_customer(self, qs):
        user = self.request.user
        if getattr(user, "role", "viewer") == "admin":
            return qs
        customer_ids = list(user.customers.values_list("id", flat=True))
        if not customer_ids:
            return qs.none()
        fields = self.customer_field
        if isinstance(fields, str):
            fields = (fields,)
        q = Q()
        for field in fields:
            q |= Q(**{f"{field}__in": customer_ids})
        return qs.filter(q)

    def get_accessible_customer_ids(self):
        """Get list of customer IDs the current user has access to."""
        user = self.request.user
        if getattr(user, "role", "viewer") == "admin":
            # Admin has access to all customers
            return list(Customer.objects.values_list("id", flat=True))
        customer_ids = list(user.customers.values_list("id", flat=True))
        return customer_ids if customer_ids else []

    def ensure_can_write(self):
        if self.request.method == "GET":
            return None
        if getattr(self.request.user, "role", "viewer") not in self.allowed_write_roles:
            return HttpResponseForbidden("Insufficient role")
        return None

    def ensure_customer_access(self, customer_id: int | None):
        if customer_id is None:
            return HttpResponseForbidden("Customer access required")
        if not user_has_customer_access(self.request.user, customer_id):
            return HttpResponseForbidden("Customer access required")
        return None


class AdminRequiredMixin(LoginRequiredMixin):
    """Restrict access to admin users."""

    def dispatch(self, request, *args, **kwargs):
        if getattr(request.user, "role", "") != "admin":
            return HttpResponseForbidden("Admin access required")
        return super().dispatch(request, *args, **kwargs)


class DashboardView(TenantScopedView):
    template_name = "dashboard.html"

    def get(self, request):
        now = timezone.now()
        last_24h = now - timezone.timedelta(hours=24)

        devices = self.filter_by_customer(Device.objects.all())
        devices_total = devices.count()
        devices_reachable = devices.filter(enabled=True).count()
        devices_unreachable = devices_total - devices_reachable

        jobs = self.filter_by_customer(Job.objects.all())
        jobs_24h = jobs.filter(requested_at__gte=last_24h).count()
        recent_jobs = jobs.order_by("-requested_at")[:5]

        compliance_results = self.filter_by_customer(ComplianceResult.objects.all())
        compliance_total = compliance_results.count()
        compliance_pass = (
            compliance_results.filter(status="passed").count() if compliance_total else 0
        )
        compliance_score = (
            int((compliance_pass / compliance_total) * 100) if compliance_total else None
        )

        unreachable_sites = (
            devices.filter(enabled=False)
            .exclude(site__isnull=True)
            .values("site")
            .annotate(count=Count("id"))
            .order_by("-count")[:5]
        )

        context = {
            "devices_total": devices_total,
            "devices_reachable": devices_reachable,
            "devices_unreachable": devices_unreachable,
            "jobs_24h": jobs_24h,
            "compliance_score": compliance_score,
            "recent_jobs": recent_jobs,
            "unreachable_sites": unreachable_sites,
        }
        return render(request, self.template_name, context)


class DeviceListView(TenantScopedView):
    template_name = "devices/list.html"
    partial_name = "devices/_table.html"

    def _get_form(self, request):
        form = DeviceForm(user=request.user)
        if not form.fields["customer"].queryset.exists():
            if getattr(request.user, "role", "viewer") == "admin":
                default_customer, _ = Customer.objects.get_or_create(name="Default")
                request.user.customers.add(default_customer)
                form = DeviceForm(user=request.user)
        return form

    def _get_stats(self, request):
        """Calculate device statistics for dashboard cards."""
        devices = self.filter_by_customer(Device.objects.all())
        total = devices.count()
        enabled = devices.filter(enabled=True).count()
        disabled = total - enabled

        # Calculate percentages
        enabled_pct = int((enabled / total * 100)) if total > 0 else 0

        # Get top vendor
        top_vendor = (
            devices.exclude(vendor__isnull=True)
            .exclude(vendor="")
            .values("vendor")
            .annotate(count=Count("id"))
            .order_by("-count")
            .first()
        )

        # Count devices added this week
        week_ago = timezone.now() - timezone.timedelta(days=7)
        added_this_week = (
            devices.filter(created_at__gte=week_ago).count() if hasattr(Device, "created_at") else 0
        )

        return {
            "total": total,
            "enabled": enabled,
            "disabled": disabled,
            "enabled_pct": enabled_pct,
            "top_vendor": top_vendor or {"vendor": None, "count": 0},
            "added_this_week": added_this_week,
        }

    def get(self, request):
        search = request.GET.get("search", "").strip()
        vendor = request.GET.get("vendor", "").strip()
        platform = request.GET.get("platform", "").strip()
        site = request.GET.get("site", "").strip()
        role = request.GET.get("role", "").strip()

        qs = Device.objects.select_related("customer", "credential").order_by("hostname")
        if search:
            qs = qs.filter(
                Q(hostname__icontains=search)
                | Q(mgmt_ip__icontains=search)
                | Q(vendor__icontains=search)
                | Q(site__icontains=search)
            )
        if vendor:
            qs = qs.filter(vendor__iexact=vendor)
        if platform:
            qs = qs.filter(platform__iexact=platform)
        if site:
            qs = qs.filter(site__iexact=site)
        if role:
            qs = qs.filter(role__iexact=role)

        qs = self.filter_by_customer(qs)

        devices_payload = [
            {
                "id": device.id,
                "hostname": device.hostname,
                "mgmtIp": str(device.mgmt_ip),
                "vendor": device.vendor or "",
                "platform": device.platform or "",
                "site": device.site or "",
                "enabled": bool(device.enabled),
                "detailUrl": reverse("devices-detail", args=[device.id]),
                "apiUrl": reverse("device-detail", args=[device.id]),
            }
            for device in qs
        ]

        data_table_props = {
            "rows": devices_payload,
            "emptyState": {
                "title": "No devices found",
                "description": "Try adjusting your search or add a new device.",
            },
        }

        # Distinct filter options
        filters = self.filter_by_customer(Device.objects.all())
        vendor_choices = (
            filters.exclude(vendor__isnull=True)
            .exclude(vendor="")
            .values_list("vendor", flat=True)
            .distinct()
            .order_by("vendor")
        )
        platform_choices = (
            filters.exclude(platform__isnull=True)
            .exclude(platform="")
            .values_list("platform", flat=True)
            .distinct()
            .order_by("platform")
        )
        site_choices = (
            filters.exclude(site__isnull=True)
            .exclude(site="")
            .values_list("site", flat=True)
            .distinct()
            .order_by("site")
        )
        role_choices = (
            filters.exclude(role__isnull=True)
            .exclude(role="")
            .values_list("role", flat=True)
            .distinct()
            .order_by("role")
        )

        def _select_props(name: str, current: str, choices):
            return {
                "name": name,
                "value": current,
                "placeholder": name.title(),
                "submitOnChange": True,
                "options": [{"value": choice, "label": choice} for choice in choices],
            }

        context = {
            "devices": qs,
            "devices_table_props": json.dumps(data_table_props),
            "search": search,
            "vendor": vendor,
            "platform": platform,
            "site": site,
            "role": role,
            "vendor_choices": vendor_choices,
            "platform_choices": platform_choices,
            "site_choices": site_choices,
            "role_choices": role_choices,
            "vendor_select": json.dumps(_select_props("vendor", vendor, vendor_choices)),
            "platform_select": json.dumps(_select_props("platform", platform, platform_choices)),
            "site_select": json.dumps(_select_props("site", site, site_choices)),
            "role_select": json.dumps(_select_props("role", role, role_choices)),
            "form": self._get_form(request),
            "stats": self._get_stats(request),
        }
        if request.headers.get("HX-Request"):
            return render(request, self.partial_name, context)
        return render(request, self.template_name, context)


class DeviceDetailView(TenantScopedView):
    template_name = "devices/detail.html"

    def get(self, request, pk: int):
        device = get_object_or_404(Device.objects.select_related("customer", "credential"), pk=pk)
        forbidden = self.ensure_customer_access(device.customer_id)
        if forbidden:
            return forbidden
        context = {"device": device}
        return render(request, self.template_name, context)


class DeviceCreateView(TenantScopedView):
    template_name = "devices/create.html"
    modal_name = "devices/_add_modal.html"
    partial_name = "devices/_table.html"
    allowed_write_roles = {"operator", "admin"}

    def _form(self, request, data=None):
        return DeviceForm(data, user=request.user)

    def get(self, request):
        form = self._form(request)
        if not form.fields["customer"].queryset.exists():
            # seed a default customer for admins to get started
            if getattr(request.user, "role", "viewer") == "admin":
                default_customer, _ = Customer.objects.get_or_create(name="Default")
                request.user.customers.add(default_customer)
                form = self._form(request)
            else:
                return HttpResponseBadRequest("No customer access configured")
        # For HTMX requests, return just the modal content
        if request.headers.get("HX-Request"):
            return render(request, self.modal_name, {"form": form})
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        forbidden = self.ensure_can_write()
        if forbidden:
            return forbidden
        form = self._form(request, request.POST)
        if form.is_valid():
            device = form.save()
            # For HTMX requests, return the updated table
            if request.headers.get("HX-Request"):
                qs = Device.objects.select_related("customer", "credential").order_by("hostname")
                if getattr(request.user, "role", "viewer") != "admin":
                    customer_ids = list(request.user.customers.values_list("id", flat=True))
                    qs = qs.filter(customer_id__in=customer_ids)
                return render(request, self.partial_name, {"devices": qs})
            return redirect("devices-detail", pk=device.id)
        # For HTMX requests with errors, return the modal with errors
        if request.headers.get("HX-Request"):
            response = render(request, self.modal_name, {"form": form}, status=422)
            response["HX-Retarget"] = "#add-device-modal .modal-box"
            response["HX-Reswap"] = "innerHTML"
            return response
        return render(request, self.template_name, {"form": form}, status=400)


class DeviceSnapshotsPartialView(TenantScopedView):
    partial_name = "devices/_snapshots.html"
    customer_field = "device__customer_id"

    def get(self, request, pk: int):
        qs = (
            ConfigSnapshot.objects.select_related("job", "device")
            .filter(device_id=pk)
            .order_by("-created_at")
        )
        qs = self.filter_by_customer(qs)[:100]
        return render(request, self.partial_name, {"snapshots": qs})


class DeviceJobsPartialView(TenantScopedView):
    partial_name = "devices/_jobs.html"

    def get(self, request, pk: int):
        device = get_object_or_404(Device, pk=pk)
        forbidden = self.ensure_customer_access(device.customer_id)
        if forbidden:
            return forbidden
        qs = Job.objects.filter(customer=device.customer).order_by("-requested_at")[:50]
        return render(request, self.partial_name, {"jobs": qs, "device": device})


class DeviceTopologyPartialView(TenantScopedView):
    partial_name = "devices/_topology.html"
    customer_field = "customer_id"

    def get(self, request, pk: int):
        qs = TopologyLink.objects.select_related("local_device", "remote_device").filter(
            local_device_id=pk
        )
        qs = self.filter_by_customer(qs)
        return render(request, self.partial_name, {"links": qs})


class DeviceImportView(TenantScopedView):
    template_name = "devices/import.html"
    partial_name = "devices/_import_results.html"
    allowed_write_roles = {"operator", "admin"}

    def get(self, request):
        customers = (
            request.user.customers.all()
            if getattr(request.user, "role", "viewer") != "admin"
            else None
        )
        if getattr(request.user, "role", "viewer") == "admin":
            customers = Customer.objects.all()
        creds = Credential.objects.filter(customer__in=customers)
        return render(request, self.template_name, {"customers": customers, "credentials": creds})

    def post(self, request):
        import csv

        forbidden = self.ensure_can_write()
        if forbidden:
            return forbidden

        is_htmx = request.headers.get("HX-Request")
        customer_id = request.POST.get("customer")

        try:
            customer = Customer.objects.get(pk=customer_id)
        except Customer.DoesNotExist:
            if is_htmx:
                return render(request, self.partial_name, {"error": "Invalid customer"})
            return HttpResponseBadRequest("Invalid customer")

        if not user_has_customer_access(request.user, customer.id):
            if is_htmx:
                return render(request, self.partial_name, {"error": "No access to this customer"})
            return HttpResponseBadRequest("No access")

        upload = request.FILES.get("file")
        if not upload:
            if is_htmx:
                return render(request, self.partial_name, {"error": "CSV file is required"})
            return HttpResponseBadRequest("File required")

        created = updated = skipped = 0
        errors = []
        try:
            decoded = upload.read().decode()
        except Exception:
            if is_htmx:
                return render(request, self.partial_name, {"error": "Invalid file encoding"})
            return HttpResponseBadRequest("Invalid file")

        reader = csv.DictReader(decoded.splitlines())
        for row in reader:
            hostname = (row.get("hostname") or "").strip()
            mgmt_ip = (row.get("mgmt_ip") or "").strip()
            vendor = (row.get("vendor") or "").strip()
            platform = (row.get("platform") or "").strip()
            credential_name = (row.get("credential") or row.get("credential_name") or "").strip()
            if not hostname or not mgmt_ip or not credential_name:
                skipped += 1
                errors.append(f"Missing required fields for row {row}")
                continue
            cred = Credential.objects.filter(customer=customer, name=credential_name).first()
            if not cred:
                skipped += 1
                errors.append(f"Credential '{credential_name}' not found for customer")
                continue
            defaults = {
                "mgmt_ip": mgmt_ip,
                "vendor": vendor,
                "platform": platform,
                "role": (row.get("role") or "").strip() or None,
                "site": (row.get("site") or "").strip() or None,
                "tags": row.get("tags") or None,
                "credential": cred,
            }
            obj, created_flag = Device.objects.update_or_create(
                customer=customer,
                hostname=hostname,
                defaults=defaults,
            )
            if created_flag:
                created += 1
            else:
                updated += 1

        summary = {"created": created, "updated": updated, "skipped": skipped, "errors": errors}

        if is_htmx:
            return render(request, self.partial_name, {"summary": summary})

        return render(
            request,
            self.template_name,
            {
                "customers": [customer],
                "credentials": Credential.objects.filter(customer=customer),
                "summary": summary,
            },
        )


class JobListView(TenantScopedView):
    template_name = "jobs/list.html"
    partial_name = "jobs/_table.html"

    def get(self, request):
        qs = Job.objects.select_related("customer", "user")
        qs = self.filter_by_customer(qs).order_by("-requested_at")[:200]

        jobs_payload = [
            {
                "id": job.id,
                "type": job.type,
                "status": job.status,
                "user": getattr(job.user, "username", ""),
                "customer": getattr(job.customer, "name", ""),
                "requestedAt": timezone.localtime(job.requested_at).strftime("%Y-%m-%d %H:%M:%S"),
                "detailUrl": reverse("jobs-detail", args=[job.id]),
            }
            for job in qs
        ]
        jobs_table_props = {
            "rows": jobs_payload,
            "emptyState": {
                "title": "No jobs found",
                "description": "Jobs will appear when automation tasks run.",
            },
        }

        context = {"jobs": qs, "jobs_table_props": json.dumps(jobs_table_props)}
        if request.headers.get("HX-Request"):
            return render(request, self.partial_name, context)
        return render(request, self.template_name, context)


class JobDetailLogsView(TenantScopedView):
    partial_name = "jobs/_logs.html"

    def get(self, request, pk: int):
        job = get_object_or_404(Job, pk=pk)
        forbidden = self.ensure_customer_access(job.customer_id)
        if forbidden:
            return forbidden
        logs = JobLog.objects.filter(job=job).order_by("-ts")[:200][::-1]
        logs_payload = [
            {
                "ts": timezone.localtime(log.ts).strftime("%H:%M:%S"),
                "level": log.level,
                "host": log.host or "",
                "message": log.message,
            }
            for log in logs
        ]
        context = {
            "job": job,
            "logs": logs,
            "logs_props": json.dumps({"jobId": job.id, "status": job.status, "logs": logs_payload}),
        }
        return render(request, self.partial_name, context)


class JobDetailView(TenantScopedView):
    template_name = "jobs/detail.html"

    def get(self, request, pk: int):
        job = get_object_or_404(Job, pk=pk)
        forbidden = self.ensure_customer_access(job.customer_id)
        if forbidden:
            return forbidden
        context = {"job": job}
        return render(request, self.template_name, context)


class ConfigSnapshotListView(TenantScopedView):
    template_name = "config/list.html"
    partial_name = "config/_table.html"
    customer_field = "device__customer_id"

    def get(self, request):
        device_id = request.GET.get("device_id")
        qs = ConfigSnapshot.objects.select_related("device", "job").order_by("-created_at")[:200]
        if device_id:
            qs = qs.filter(device_id=device_id)
        qs = self.filter_by_customer(qs)

        snapshots_payload = [
            {
                "id": snap.id,
                "deviceId": snap.device_id,
                "deviceName": snap.device.hostname if snap.device else "",
                "source": snap.source,
                "createdAt": timezone.localtime(snap.created_at).strftime("%Y-%m-%d %H:%M:%S"),
                "hash": (snap.hash or "")[:16],
            }
            for snap in qs
        ]
        snapshots_table_props = {
            "rows": snapshots_payload,
            "emptyState": {
                "title": "No snapshots found",
                "description": "Configuration snapshots will appear here after collection.",
            },
        }

        context = {
            "snapshots": qs,
            "snapshots_table_props": json.dumps(snapshots_table_props),
            "device_id": device_id,
        }
        if request.headers.get("HX-Request"):
            return render(request, self.partial_name, context)
        return render(request, self.template_name, context)


class ConfigDiffView(TenantScopedView):
    template_name = "config/diff.html"
    partial_name = "config/_diff_output.html"

    def get(self, request):
        from_id = request.GET.get("from")
        to_id = request.GET.get("to")
        diff_text = None
        snap_from = snap_to = None
        error = None

        if from_id and to_id:
            try:
                snap_from = ConfigSnapshot.objects.get(pk=from_id)
            except ConfigSnapshot.DoesNotExist:
                error = f"Snapshot {from_id} not found"
            try:
                snap_to = ConfigSnapshot.objects.get(pk=to_id)
            except ConfigSnapshot.DoesNotExist:
                error = f"Snapshot {to_id} not found"

            if snap_from and snap_to and not error:
                forbidden = self.ensure_customer_access(
                    getattr(snap_from.device, "customer_id", None)
                )
                forbidden = forbidden or self.ensure_customer_access(
                    getattr(snap_to.device, "customer_id", None)
                )
                if forbidden:
                    error = "Access denied to one or both snapshots"
                else:
                    diff_lines = unified_diff(
                        (snap_from.config_text or "").splitlines(),
                        (snap_to.config_text or "").splitlines(),
                        fromfile=f"snapshot-{snap_from.id}",
                        tofile=f"snapshot-{snap_to.id}",
                        lineterm="",
                    )
                    diff_text = "\n".join(diff_lines)
                    if not diff_text:
                        diff_text = "No differences found between snapshots."

        context = {"snap_from": snap_from, "snap_to": snap_to, "diff": diff_text, "error": error}

        if request.headers.get("HX-Request"):
            return render(request, self.partial_name, context)
        return render(request, self.template_name, context)


class DriftTimelineView(TenantScopedView):
    """View for configuration drift timeline."""

    template_name = "config/drift_timeline.html"
    partial_name = "config/_drift_timeline.html"
    customer_field = "device__customer_id"

    def get(self, request):
        device_id = request.GET.get("device_id")
        days = int(request.GET.get("days", 30))

        if not device_id:
            context = {
                "error": "device_id parameter required",
                "drifts": [],
                "device": None,
                "days": days,
            }
            if request.headers.get("HX-Request"):
                return render(request, self.partial_name, context)
            return render(request, self.template_name, context)

        from webnet.devices.models import Device
        from webnet.config_mgmt.drift_service import DriftService

        try:
            device = Device.objects.select_related("customer").get(pk=device_id)
        except Device.DoesNotExist:
            context = {
                "error": "Device not found",
                "drifts": [],
                "device": None,
                "days": days,
            }
            if request.headers.get("HX-Request"):
                return render(request, self.partial_name, context)
            return render(request, self.template_name, context)

        # Check access
        forbidden = self.ensure_customer_access(device.customer_id)
        if forbidden:
            return forbidden

        # Get drift timeline
        ds = DriftService()
        drifts = ds.get_drift_timeline(device_id, days)
        frequency_stats = ds.get_change_frequency(device_id, days)

        drifts_payload = [
            {
                "id": drift.id,
                "detected_at": timezone.localtime(drift.detected_at).strftime("%Y-%m-%d %H:%M:%S"),
                "additions": drift.additions,
                "deletions": drift.deletions,
                "changes": drift.changes,
                "has_changes": drift.has_changes,
                "change_magnitude": drift.get_change_magnitude(),
                "snapshot_from_id": drift.snapshot_from_id,
                "snapshot_to_id": drift.snapshot_to_id,
                "triggered_by": drift.triggered_by.username if drift.triggered_by else "System",
            }
            for drift in drifts
        ]

        context = {
            "device": device,
            "drifts": drifts,
            "drifts_payload": json.dumps(drifts_payload),
            "frequency_stats": frequency_stats,
            "days": days,
            "error": None,
        }

        if request.headers.get("HX-Request"):
            return render(request, self.partial_name, context)
        return render(request, self.template_name, context)


class DriftDetailView(TenantScopedView):
    """View for drift detail with enhanced diff visualization."""

    template_name = "config/drift_detail.html"

    def get(self, request, drift_id):
        try:
            drift = ConfigDrift.objects.select_related(
                "device__customer",
                "snapshot_from",
                "snapshot_to",
                "triggered_by",
            ).get(pk=drift_id)
        except ConfigDrift.DoesNotExist:
            return render(
                request,
                self.template_name,
                {"error": "Drift not found", "drift": None},
            )

        # Check access
        forbidden = self.ensure_customer_access(drift.device.customer_id)
        if forbidden:
            return forbidden

        # Generate diff with highlighting
        diff_lines = unified_diff(
            drift.snapshot_from.config_text.splitlines(),
            drift.snapshot_to.config_text.splitlines(),
            fromfile=f"snapshot-{drift.snapshot_from_id}",
            tofile=f"snapshot-{drift.snapshot_to_id}",
            lineterm="",
        )
        diff_text = "\n".join(diff_lines)

        context = {
            "drift": drift,
            "diff_text": diff_text,
            "error": None,
        }

        return render(request, self.template_name, context)


class DriftAlertsView(TenantScopedView):
    """View for drift alerts."""

    template_name = "config/drift_alerts.html"
    partial_name = "config/_alerts_table.html"
    customer_field = "drift__device__customer_id"

    def get(self, request):
        status_filter = request.GET.get("status", "open")
        severity_filter = request.GET.get("severity")

        qs = DriftAlert.objects.select_related(
            "drift__device__customer",
            "drift__device",
            "acknowledged_by",
        ).order_by("-detected_at")

        # Apply filters before slicing
        if status_filter:
            qs = qs.filter(status=status_filter)
        if severity_filter:
            qs = qs.filter(severity=severity_filter)

        qs = self.filter_by_customer(qs)

        # Slice after filtering
        qs = qs[:100]

        alerts_payload = [
            {
                "id": alert.id,
                "drift_id": alert.drift_id,
                "device_hostname": alert.drift.device.hostname,
                "severity": alert.severity,
                "status": alert.status,
                "message": alert.message,
                "detected_at": timezone.localtime(alert.detected_at).strftime("%Y-%m-%d %H:%M:%S"),
                "acknowledged_by": (
                    alert.acknowledged_by.username if alert.acknowledged_by else None
                ),
            }
            for alert in qs
        ]

        context = {
            "alerts": qs,
            "alerts_payload": json.dumps(alerts_payload),
            "status_filter": status_filter,
            "severity_filter": severity_filter,
        }

        if request.headers.get("HX-Request"):
            return render(request, self.partial_name, context)
        return render(request, self.template_name, context)


class CompliancePolicyListView(TenantScopedView):
    template_name = "compliance/policies.html"
    partial_name = "compliance/_policies_table.html"

    def get(self, request):
        qs = CompliancePolicy.objects.select_related("customer").order_by("name")
        qs = self.filter_by_customer(qs)

        policies_payload = [
            {
                "id": p.id,
                "name": p.name,
                "customer": p.customer.name if p.customer else "",
                "updatedAt": timezone.localtime(p.updated_at).strftime("%Y-%m-%d %H:%M:%S"),
                "runUrl": reverse("compliance-run"),
            }
            for p in qs
        ]
        policies_table_props = {
            "rows": policies_payload,
            "emptyState": {
                "title": "No policies found",
                "description": "Create compliance policies to validate your network configurations.",
            },
        }

        context = {"policies": qs, "policies_table_props": json.dumps(policies_table_props)}
        if request.headers.get("HX-Request"):
            return render(request, self.partial_name, context)
        return render(request, self.template_name, context)


class ComplianceResultListView(TenantScopedView):
    template_name = "compliance/results.html"
    partial_name = "compliance/_results_table.html"
    customer_field = ("policy__customer_id", "device__customer_id")

    def get(self, request):
        qs = ComplianceResult.objects.select_related("policy", "device").order_by("-ts")[:200]
        qs = self.filter_by_customer(qs)

        results_payload = [
            {
                "id": r.id,
                "policy": r.policy.name if r.policy else "",
                "deviceId": r.device_id,
                "deviceName": r.device.hostname if r.device else "",
                "status": r.status,
                "timestamp": timezone.localtime(r.ts).strftime("%Y-%m-%d %H:%M:%S"),
            }
            for r in qs
        ]
        results_table_props = {
            "rows": results_payload,
            "emptyState": {
                "title": "No results found",
                "description": "Compliance results will appear here after running checks.",
            },
        }

        context = {"results": qs, "results_table_props": json.dumps(results_table_props)}
        if request.headers.get("HX-Request"):
            return render(request, self.partial_name, context)
        return render(request, self.template_name, context)


class ComplianceOverviewView(TenantScopedView):
    template_name = "compliance/overview.html"
    partial_name = "compliance/_overview_table.html"

    def get(self, request):
        from django.db.models import OuterRef, Subquery

        # Use subquery to get latest status in a single query (fixes N+1)
        latest_status_subquery = (
            ComplianceResult.objects.filter(policy=OuterRef("pk"))
            .order_by("-ts")
            .values("status")[:1]
        )

        policies = self.filter_by_customer(
            CompliancePolicy.objects.select_related("customer")
        ).annotate(latest_status=Subquery(latest_status_subquery))[:200]

        summary = [
            {
                "policy": policy,
                "status": policy.latest_status or "unknown",
            }
            for policy in policies
        ]

        context = {"summary": summary}
        if request.headers.get("HX-Request"):
            return render(request, self.partial_name, context)
        return render(request, self.template_name, context)


class TopologyListView(TenantScopedView):
    template_name = "topology/list.html"
    partial_name = "topology/_table.html"
    map_partial_name = "topology/_map.html"
    customer_field = ("local_device__customer_id",)

    def get(self, request):
        view = request.GET.get("view", "table")
        qs = TopologyLink.objects.select_related("local_device", "remote_device").order_by(
            "local_device__hostname"
        )
        qs = self.filter_by_customer(qs)

        # Table view data
        links_payload = [
            {
                "id": link.id,
                "localDeviceId": link.local_device_id,
                "localDevice": link.local_device.hostname if link.local_device else "",
                "localInterface": link.local_interface,
                "remoteHost": link.remote_hostname,
                "remoteInterface": link.remote_interface,
                "protocol": link.protocol,
            }
            for link in qs
        ]
        topology_table_props = {
            "rows": links_payload,
            "emptyState": {
                "title": "No topology links discovered",
                "description": "Links will appear here after topology discovery runs.",
            },
        }

        context = {
            "links": qs,
            "topology_table_props": json.dumps(topology_table_props),
            "view": view,
        }

        # If map view, also generate graph data
        if view == "map":
            nodes: dict[str, dict] = {}
            edges = []
            for link in qs:
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
                            "discovered_at": (
                                link.discovered_at.isoformat() if link.discovered_at else None
                            ),
                        },
                    }
                )
            # Use wss:// for secure connections, ws:// otherwise
            ws_scheme = "wss" if request.is_secure() else "ws"
            topology_map_props = {
                "nodes": list(nodes.values()),
                "edges": edges,
                "wsUrl": f"{ws_scheme}://{request.get_host()}/ws/updates/",
            }
            context["topology_map_props"] = json.dumps(topology_map_props)

        if request.headers.get("HX-Request"):
            if view == "map":
                return render(request, self.map_partial_name, context)
            return render(request, self.partial_name, context)
        return render(request, self.template_name, context)


class CommandsView(TenantScopedView):
    template_name = "commands/run.html"
    partial_name = "commands/_result.html"

    def post(self, request):
        forbidden = self.ensure_can_write()
        if forbidden:
            return forbidden
        command = (request.POST.get("command") or "").strip()
        customer = request.user.customers.first()
        if not command or not customer:
            context = {"error": "Command and customer are required", "job": None}
            return render(request, self.partial_name, context, status=400)
        forbidden = self.ensure_customer_access(getattr(customer, "id", None))
        if forbidden:
            return forbidden
        targets_raw = request.POST.get("targets", "").strip()
        targets = {}
        if targets_raw:
            for pair in targets_raw.split(","):
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    targets[k.strip()] = v.strip()
        js = JobService(dispatcher=lambda *args, **kwargs: None)
        job = js.create_job(
            job_type="run_commands",
            user=request.user,
            customer=customer,
            target_summary={"filters": targets},
            payload={"commands": [command]},
        )
        context = {"job": job, "error": None}
        return render(request, self.partial_name, context)

    def get(self, request):
        return render(request, self.template_name)


class ReachabilityView(TenantScopedView):
    template_name = "commands/reachability.html"
    partial_name = "commands/_result.html"

    def post(self, request):
        forbidden = self.ensure_can_write()
        if forbidden:
            return forbidden
        customer = request.user.customers.first()
        targets_raw = request.POST.get("targets", "").strip()
        targets = {}
        if targets_raw:
            for pair in targets_raw.split(","):
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    targets[k.strip()] = v.strip()
        if not customer:
            return render(
                request, self.partial_name, {"error": "Customer required", "job": None}, status=400
            )
        forbidden = self.ensure_customer_access(getattr(customer, "id", None))
        if forbidden:
            return forbidden
        js = JobService(dispatcher=lambda *args, **kwargs: None)
        job = js.create_job(
            job_type="check_reachability",
            user=request.user,
            customer=customer,
            target_summary={"filters": targets},
            payload={"targets": targets},
        )
        return render(request, self.partial_name, {"job": job, "error": None})

    def get(self, request):
        return render(request, self.template_name)


class ComplianceRunView(TenantScopedView):
    template_name = "compliance/run.html"
    partial_name = "compliance/_run_result.html"

    def post(self, request):
        forbidden = self.ensure_can_write()
        if forbidden:
            return forbidden
        policy_id = request.POST.get("policy_id")
        if not policy_id:
            return render(
                request, self.partial_name, {"error": "policy_id required", "job": None}, status=400
            )
        try:
            policy = CompliancePolicy.objects.get(pk=policy_id)
        except CompliancePolicy.DoesNotExist:
            return render(
                request, self.partial_name, {"error": "policy not found", "job": None}, status=404
            )
        forbidden = self.ensure_customer_access(getattr(policy, "customer_id", None))
        if forbidden:
            return forbidden
        js = JobService(dispatcher=lambda *args, **kwargs: None)
        job = js.create_job(
            job_type="compliance_check",
            user=request.user,
            customer=policy.customer,
            target_summary=policy.scope_json,
            payload={"policy_id": policy.id},
        )
        return render(request, self.partial_name, {"job": job, "error": None})

    def get(self, request):
        policies = self.filter_by_customer(CompliancePolicy.objects.all())[:200]
        return render(request, self.template_name, {"policies": policies})


class WizardStep1View(TenantScopedView):
    """Wizard Step 1: Task Type Selection"""

    template_name = "commands/wizard/_step1_task_type.html"

    def get(self, request):
        return render(request, self.template_name)


class WizardStep2View(TenantScopedView):
    """Wizard Step 2: Scope Selection"""

    template_name = "commands/wizard/_step2_scope.html"

    def get(self, request):
        return render(request, self.template_name)


class WizardStep3View(TenantScopedView):
    """Wizard Step 3: Parameters"""

    template_name = "commands/wizard/_step3_parameters.html"

    def get(self, request):
        return render(request, self.template_name)


class WizardStep4View(TenantScopedView):
    """Wizard Step 4: Confirmation"""

    template_name = "commands/wizard/_step4_confirm.html"

    def get(self, request):
        return render(request, self.template_name)


class GitRepositoryForm(forms.ModelForm):
    """Form for Git repository configuration."""

    auth_token = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={"placeholder": "Enter access token"}),
        help_text="Access token for HTTPS authentication (GitHub, GitLab, Bitbucket)",
    )
    ssh_private_key = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={"rows": 5, "placeholder": "-----BEGIN OPENSSH PRIVATE KEY-----"}
        ),
        help_text="SSH private key for SSH authentication",
    )

    class Meta:
        model = GitRepository
        fields = [
            "customer",
            "name",
            "remote_url",
            "branch",
            "auth_type",
            "auth_token",
            "ssh_private_key",
            "path_structure",
            "enabled",
        ]

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        if user and getattr(user, "role", "viewer") != "admin":
            self.fields["customer"].queryset = user.customers.all()
        else:
            self.fields["customer"].queryset = Customer.objects.all()

    def save(self, commit=True):
        instance = super().save(commit=False)
        auth_token = self.cleaned_data.get("auth_token")
        ssh_private_key = self.cleaned_data.get("ssh_private_key")
        if auth_token:
            instance.auth_token = auth_token
        if ssh_private_key:
            instance.ssh_private_key = ssh_private_key
        if commit:
            instance.save()
        return instance


class GitSettingsListView(TenantScopedView):
    """List Git repository settings for the user's customers."""

    template_name = "settings/git_list.html"

    def get(self, request):
        repos = self.filter_by_customer(GitRepository.objects.select_related("customer").all())
        return render(request, self.template_name, {"repositories": repos})


class GitSettingsDetailView(TenantScopedView):
    """View/edit a Git repository configuration."""

    template_name = "settings/git_detail.html"
    partial_name = "settings/_git_form.html"

    def get(self, request, pk):
        repo = get_object_or_404(GitRepository.objects.select_related("customer"), pk=pk)
        check = self.ensure_customer_access(repo.customer_id)
        if check:
            return check

        # Get recent sync logs
        sync_logs = GitSyncLog.objects.filter(repository=repo).order_by("-started_at")[:10]

        form = GitRepositoryForm(instance=repo, user=request.user)
        return render(
            request,
            self.template_name,
            {
                "repository": repo,
                "form": form,
                "sync_logs": sync_logs,
            },
        )

    def post(self, request, pk):
        check = self.ensure_can_write()
        if check:
            return check

        repo = get_object_or_404(GitRepository.objects.select_related("customer"), pk=pk)
        check = self.ensure_customer_access(repo.customer_id)
        if check:
            return check

        form = GitRepositoryForm(request.POST, instance=repo, user=request.user)
        if form.is_valid():
            form.save()
            if request.headers.get("HX-Request"):
                return render(
                    request,
                    self.partial_name,
                    {"repository": repo, "form": form, "success": True},
                )
            return redirect("git-settings-detail", pk=pk)

        return render(
            request,
            self.template_name,
            {"repository": repo, "form": form},
        )


class GitSettingsCreateView(TenantScopedView):
    """Create a new Git repository configuration."""

    template_name = "settings/git_create.html"

    def get(self, request):
        form = GitRepositoryForm(user=request.user)
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        check = self.ensure_can_write()
        if check:
            return check

        form = GitRepositoryForm(request.POST, user=request.user)
        if form.is_valid():
            repo = form.save()
            return redirect("git-settings-detail", pk=repo.pk)

        return render(request, self.template_name, {"form": form})


class GitSettingsDeleteView(TenantScopedView):
    """Delete a Git repository configuration."""

    def post(self, request, pk):
        check = self.ensure_can_write()
        if check:
            return check

        repo = get_object_or_404(GitRepository.objects.select_related("customer"), pk=pk)
        check = self.ensure_customer_access(repo.customer_id)
        if check:
            return check

        repo.delete()
        return redirect("git-settings")


class GitSyncView(TenantScopedView):
    """Trigger a manual Git sync."""

    partial_name = "settings/_git_sync_result.html"

    def post(self, request, pk):
        check = self.ensure_can_write()
        if check:
            return check

        repo = get_object_or_404(GitRepository.objects.select_related("customer"), pk=pk)
        check = self.ensure_customer_access(repo.customer_id)
        if check:
            return check

        if not repo.enabled:
            return render(
                request,
                self.partial_name,
                {"repository": repo, "error": "Git sync is disabled for this repository"},
            )

        from webnet.jobs.tasks import git_sync_job

        git_sync_job.delay(repo.customer_id)

        return render(
            request,
            self.partial_name,
            {"repository": repo, "success": True, "message": "Git sync queued"},
        )


class GitTestConnectionView(TenantScopedView):
    """Test Git repository connection."""

    partial_name = "settings/_git_test_result.html"

    def post(self, request, pk):
        repo = get_object_or_404(GitRepository.objects.select_related("customer"), pk=pk)
        check = self.ensure_customer_access(repo.customer_id)
        if check:
            return check

        from webnet.config_mgmt.git_service import GitService

        service = GitService(repo)
        result = service.test_connection()

        return render(
            request,
            self.partial_name,
            {
                "repository": repo,
                "success": result.success,
                "message": result.message,
                "error": result.error,
            },
        )


class GitSyncLogsView(TenantScopedView):
    """View Git sync logs for a repository."""

    template_name = "settings/git_sync_logs.html"
    partial_name = "settings/_git_sync_logs_table.html"

    def get(self, request, pk):
        repo = get_object_or_404(GitRepository.objects.select_related("customer"), pk=pk)
        check = self.ensure_customer_access(repo.customer_id)
        if check:
            return check

        logs = GitSyncLog.objects.filter(repository=repo).order_by("-started_at")[:50]

        if request.headers.get("HX-Request"):
            return render(request, self.partial_name, {"repository": repo, "sync_logs": logs})

        return render(request, self.template_name, {"repository": repo, "sync_logs": logs})


# =============================================================================
# Issue #40 - Bulk Device Onboarding Views
# =============================================================================


class BulkOnboardingView(TenantScopedView):
    """Main view for bulk device onboarding."""

    template_name = "devices/bulk_onboarding.html"

    def get(self, request):
        # Get customer's credentials
        customers = (
            request.user.customers.all()
            if getattr(request.user, "role", "viewer") != "admin"
            else Customer.objects.all()
        )
        credentials = Credential.objects.filter(customer__in=customers)

        # Get discovered devices stats
        discovered_qs = self.filter_by_customer(DiscoveredDevice.objects.all())
        stats = {
            "pending": discovered_qs.filter(status=DiscoveredDevice.STATUS_PENDING).count(),
            "approved": discovered_qs.filter(status=DiscoveredDevice.STATUS_APPROVED).count(),
            "rejected": discovered_qs.filter(status=DiscoveredDevice.STATUS_REJECTED).count(),
            "total": discovered_qs.count(),
        }

        return render(
            request,
            self.template_name,
            {
                "customers": customers,
                "credentials": credentials,
                "stats": stats,
            },
        )


class DiscoveryQueueView(TenantScopedView):
    """View for the discovery staging area / queue."""

    template_name = "devices/discovery_queue.html"
    partial_name = "devices/_discovery_queue_table.html"
    customer_field = "customer_id"

    def get(self, request):
        status_filter = request.GET.get("status", "pending")

        qs = DiscoveredDevice.objects.select_related(
            "customer", "discovered_via_device", "credential_tested"
        ).order_by("-discovered_at")

        qs = self.filter_by_customer(qs)

        if status_filter and status_filter != "all":
            qs = qs.filter(status=status_filter)

        # Get credentials for approval
        customers = (
            request.user.customers.all()
            if getattr(request.user, "role", "viewer") != "admin"
            else Customer.objects.all()
        )
        credentials = Credential.objects.filter(customer__in=customers)

        # Get stats
        all_qs = self.filter_by_customer(DiscoveredDevice.objects.all())
        stats = {
            "pending": all_qs.filter(status=DiscoveredDevice.STATUS_PENDING).count(),
            "approved": all_qs.filter(status=DiscoveredDevice.STATUS_APPROVED).count(),
            "rejected": all_qs.filter(status=DiscoveredDevice.STATUS_REJECTED).count(),
            "ignored": all_qs.filter(status=DiscoveredDevice.STATUS_IGNORED).count(),
            "total": all_qs.count(),
        }

        context = {
            "discovered_devices": qs[:200],
            "credentials": credentials,
            "stats": stats,
            "status_filter": status_filter,
        }

        if request.headers.get("HX-Request"):
            return render(request, self.partial_name, context)
        return render(request, self.template_name, context)


class DiscoveryQueueActionView(TenantScopedView):
    """Handle actions on discovered devices (approve/reject/ignore)."""

    partial_name = "devices/_discovery_queue_table.html"
    allowed_write_roles = {"operator", "admin"}

    def post(self, request, pk, action):
        check = self.ensure_can_write()
        if check:
            return check

        device = get_object_or_404(DiscoveredDevice, pk=pk)
        check = self.ensure_customer_access(device.customer_id)
        if check:
            return check

        if action == "approve":
            credential_id = request.POST.get("credential_id")
            if not credential_id:
                return HttpResponseBadRequest("Credential ID required")
            try:
                credential = Credential.objects.get(id=credential_id, customer=device.customer)
            except Credential.DoesNotExist:
                return HttpResponseBadRequest("Invalid credential")

            vendor = request.POST.get("vendor") or device.vendor
            platform = request.POST.get("platform") or device.platform

            try:
                device.approve_and_create_device(
                    credential=credential,
                    user=request.user,
                    vendor=vendor,
                    platform=platform,
                )
            except ValueError as e:
                logger.error("Device approval failed: %s", e, exc_info=True)
                return HttpResponseBadRequest("Invalid device approval request.")

        elif action == "reject":
            notes = request.POST.get("notes", "")
            device.reject(request.user, notes)

        elif action == "ignore":
            notes = request.POST.get("notes", "")
            device.ignore(request.user, notes)

        # Return updated table
        qs = self.filter_by_customer(
            DiscoveredDevice.objects.filter(status=DiscoveredDevice.STATUS_PENDING)
        ).order_by("-discovered_at")[:200]

        return render(request, self.partial_name, {"discovered_devices": qs})


class ScanIPRangeView(TenantScopedView):
    """Start an IP range scan job."""

    partial_name = "devices/_scan_result.html"
    allowed_write_roles = {"operator", "admin"}

    def post(self, request):
        check = self.ensure_can_write()
        if check:
            return check

        ip_ranges = request.POST.get("ip_ranges", "").strip()
        credential_ids = request.POST.getlist("credential_ids")
        use_snmp = request.POST.get("use_snmp") == "on"
        snmp_community = request.POST.get("snmp_community", "public")
        test_ssh = request.POST.get("test_ssh") == "on"

        if not ip_ranges:
            return render(request, self.partial_name, {"error": "IP ranges required"})

        if not credential_ids:
            return render(request, self.partial_name, {"error": "At least one credential required"})

        customer = request.user.customers.first()
        if not customer:
            return render(request, self.partial_name, {"error": "No customer access"})

        # Parse IP ranges (comma-separated)
        ranges = [r.strip() for r in ip_ranges.split(",") if r.strip()]

        # Validate credentials belong to customer
        valid_cred_ids = list(
            Credential.objects.filter(id__in=credential_ids, customer=customer).values_list(
                "id", flat=True
            )
        )

        if not valid_cred_ids:
            return render(request, self.partial_name, {"error": "No valid credentials found"})

        js = JobService()
        job = js.create_job(
            job_type="ip_range_scan",
            user=request.user,
            customer=customer,
            target_summary={"ip_ranges": ranges},
            payload={
                "ip_ranges": ranges,
                "credential_ids": valid_cred_ids,
                "use_snmp": use_snmp,
                "snmp_community": snmp_community,
                "test_ssh": test_ssh,
                "ports": [22],
            },
        )

        return render(
            request,
            self.partial_name,
            {"job": job, "message": f"Scan job started for {len(ranges)} IP range(s)"},
        )


# =============================================================================
# Issue #24 - Device Tags and Groups Views
# =============================================================================


class TagListView(TenantScopedView):
    """List and manage device tags."""

    template_name = "devices/tags.html"
    partial_name = "devices/_tags_table.html"
    customer_field = "customer_id"

    def get(self, request):
        from django.db.models import Count

        qs = Tag.objects.annotate(device_count=Count("devices")).order_by("category", "name")
        qs = self.filter_by_customer(qs)

        # Get customers for new tag form
        customers = (
            request.user.customers.all()
            if getattr(request.user, "role", "viewer") != "admin"
            else Customer.objects.all()
        )

        context = {
            "tags": qs,
            "customers": customers,
        }

        if request.headers.get("HX-Request"):
            return render(request, self.partial_name, context)
        return render(request, self.template_name, context)


class TagCreateView(TenantScopedView):
    """Create a new tag."""

    partial_name = "devices/_tags_table.html"
    allowed_write_roles = {"operator", "admin"}

    def post(self, request):
        check = self.ensure_can_write()
        if check:
            return check

        name = request.POST.get("name", "").strip()
        color = request.POST.get("color", "#3B82F6")
        description = request.POST.get("description", "").strip()
        category = request.POST.get("category", "").strip() or None
        customer_id = request.POST.get("customer")

        if not name or not customer_id:
            return HttpResponseBadRequest("Name and customer required")

        try:
            customer = Customer.objects.get(pk=customer_id)
        except Customer.DoesNotExist:
            return HttpResponseBadRequest("Invalid customer")

        check = self.ensure_customer_access(customer.id)
        if check:
            return check

        Tag.objects.create(
            customer=customer,
            name=name,
            color=color,
            description=description,
            category=category,
        )

        # Return updated table
        from django.db.models import Count

        qs = Tag.objects.annotate(device_count=Count("devices")).order_by("category", "name")
        qs = self.filter_by_customer(qs)

        return render(request, self.partial_name, {"tags": qs})


class TagDeleteView(TenantScopedView):
    """Delete a tag."""

    partial_name = "devices/_tags_table.html"
    allowed_write_roles = {"operator", "admin"}

    def post(self, request, pk):
        check = self.ensure_can_write()
        if check:
            return check

        tag = get_object_or_404(Tag, pk=pk)
        check = self.ensure_customer_access(tag.customer_id)
        if check:
            return check

        tag.delete()

        # Return updated table
        from django.db.models import Count

        qs = Tag.objects.annotate(device_count=Count("devices")).order_by("category", "name")
        qs = self.filter_by_customer(qs)

        return render(request, self.partial_name, {"tags": qs})


class DeviceGroupListView(TenantScopedView):
    """List and manage device groups."""

    template_name = "devices/groups.html"
    partial_name = "devices/_groups_table.html"
    customer_field = "customer_id"

    def get(self, request):
        qs = DeviceGroup.objects.select_related("customer", "parent").order_by("name")
        qs = self.filter_by_customer(qs)

        # Add device counts
        groups_with_counts = []
        for group in qs:
            groups_with_counts.append(
                {
                    "group": group,
                    "device_count": group.device_count,
                }
            )

        # Get customers for new group form
        customers = (
            request.user.customers.all()
            if getattr(request.user, "role", "viewer") != "admin"
            else Customer.objects.all()
        )

        context = {
            "groups": groups_with_counts,
            "customers": customers,
        }

        if request.headers.get("HX-Request"):
            return render(request, self.partial_name, context)
        return render(request, self.template_name, context)


class DeviceGroupCreateView(TenantScopedView):
    """Create a new device group."""

    partial_name = "devices/_groups_table.html"
    allowed_write_roles = {"operator", "admin"}

    def post(self, request):
        check = self.ensure_can_write()
        if check:
            return check

        name = request.POST.get("name", "").strip()
        description = request.POST.get("description", "").strip()
        group_type = request.POST.get("group_type", DeviceGroup.TYPE_STATIC)
        customer_id = request.POST.get("customer")
        filter_rules = {}

        if not name or not customer_id:
            return HttpResponseBadRequest("Name and customer required")

        try:
            customer = Customer.objects.get(pk=customer_id)
        except Customer.DoesNotExist:
            return HttpResponseBadRequest("Invalid customer")

        check = self.ensure_customer_access(customer.id)
        if check:
            return check

        # Parse filter rules for dynamic groups
        if group_type == DeviceGroup.TYPE_DYNAMIC:
            if request.POST.get("filter_vendor"):
                filter_rules["vendor"] = request.POST.get("filter_vendor")
            if request.POST.get("filter_platform"):
                filter_rules["platform"] = request.POST.get("filter_platform")
            if request.POST.get("filter_site"):
                filter_rules["site"] = request.POST.get("filter_site")
            if request.POST.get("filter_role"):
                filter_rules["role"] = request.POST.get("filter_role")

        DeviceGroup.objects.create(
            customer=customer,
            name=name,
            description=description,
            group_type=group_type,
            filter_rules=filter_rules or None,
        )

        # Return updated table
        qs = DeviceGroup.objects.select_related("customer", "parent").order_by("name")
        qs = self.filter_by_customer(qs)
        groups_with_counts = [{"group": g, "device_count": g.device_count} for g in qs]

        return render(request, self.partial_name, {"groups": groups_with_counts})


class DeviceGroupDetailView(TenantScopedView):
    """View device group details and members."""

    template_name = "devices/group_detail.html"
    partial_name = "devices/_group_devices.html"

    def get(self, request, pk):
        group = get_object_or_404(DeviceGroup.objects.select_related("customer"), pk=pk)
        check = self.ensure_customer_access(group.customer_id)
        if check:
            return check

        devices = group.get_devices()

        context = {
            "group": group,
            "devices": devices,
            "device_count": devices.count(),
        }

        if request.headers.get("HX-Request"):
            return render(request, self.partial_name, context)
        return render(request, self.template_name, context)


class DeviceGroupDeleteView(TenantScopedView):
    """Delete a device group."""

    partial_name = "devices/_groups_table.html"
    allowed_write_roles = {"operator", "admin"}

    def post(self, request, pk):
        check = self.ensure_can_write()
        if check:
            return check

        group = get_object_or_404(DeviceGroup, pk=pk)
        check = self.ensure_customer_access(group.customer_id)
        if check:
            return check

        group.delete()

        # Return updated table
        qs = DeviceGroup.objects.select_related("customer", "parent").order_by("name")
        qs = self.filter_by_customer(qs)
        groups_with_counts = [{"group": g, "device_count": g.device_count} for g in qs]

        return render(request, self.partial_name, {"groups": groups_with_counts})


class ConfigTemplateForm(forms.ModelForm):
    """Form for configuration templates."""

    class Meta:
        model = ConfigTemplate
        fields = [
            "customer",
            "name",
            "description",
            "category",
            "template_content",
            "variables_schema",
            "platform_tags",
            "is_active",
        ]
        widgets = {
            "template_content": forms.Textarea(attrs={"rows": 15, "class": "font-mono"}),
            "description": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        if user and getattr(user, "role", "viewer") != "admin":
            self.fields["customer"].queryset = user.customers.all()
        else:
            self.fields["customer"].queryset = Customer.objects.all()


class ConfigTemplateListView(TenantScopedView):
    """List configuration templates."""

    template_name = "templates/list.html"
    partial_name = "templates/_table.html"

    def get(self, request):
        category = request.GET.get("category", "")
        search = request.GET.get("search", "").strip()

        qs = ConfigTemplate.objects.select_related("customer", "created_by").order_by(
            "category", "name"
        )

        if category:
            qs = qs.filter(category=category)
        if search:
            qs = qs.filter(name__icontains=search)

        qs = self.filter_by_customer(qs)

        context = {
            "templates": qs,
            "category": category,
            "search": search,
            "categories": ConfigTemplate.CATEGORY_CHOICES,
        }

        if request.headers.get("HX-Request"):
            return render(request, self.partial_name, context)
        return render(request, self.template_name, context)


class ConfigTemplateDetailView(TenantScopedView):
    """View/edit a configuration template."""

    template_name = "templates/detail.html"
    partial_name = "templates/_form.html"

    def get(self, request, pk):
        template = get_object_or_404(
            ConfigTemplate.objects.select_related("customer", "created_by"), pk=pk
        )
        check = self.ensure_customer_access(template.customer_id)
        if check:
            return check

        form = ConfigTemplateForm(instance=template, user=request.user)
        return render(
            request,
            self.template_name,
            {"template": template, "form": form},
        )

    def post(self, request, pk):
        check = self.ensure_can_write()
        if check:
            return check

        template = get_object_or_404(
            ConfigTemplate.objects.select_related("customer", "created_by"), pk=pk
        )
        check = self.ensure_customer_access(template.customer_id)
        if check:
            return check

        form = ConfigTemplateForm(request.POST, instance=template, user=request.user)
        if form.is_valid():
            form.save()
            if request.headers.get("HX-Request"):
                return render(
                    request,
                    self.partial_name,
                    {"template": template, "form": form, "success": True},
                )
            return redirect("templates-detail", pk=pk)

        return render(
            request,
            self.template_name,
            {"template": template, "form": form},
        )


class ConfigTemplateCreateView(TenantScopedView):
    """Create a new configuration template."""

    template_name = "templates/create.html"

    def get(self, request):
        form = ConfigTemplateForm(user=request.user)
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        check = self.ensure_can_write()
        if check:
            return check

        form = ConfigTemplateForm(request.POST, user=request.user)
        if form.is_valid():
            template = form.save(commit=False)
            template.created_by = request.user
            template.save()
            return redirect("templates-detail", pk=template.pk)

        return render(request, self.template_name, {"form": form})


class ConfigTemplateDeleteView(TenantScopedView):
    """Delete a configuration template."""

    def post(self, request, pk):
        check = self.ensure_can_write()
        if check:
            return check

        template = get_object_or_404(ConfigTemplate.objects.select_related("customer"), pk=pk)
        check = self.ensure_customer_access(template.customer_id)
        if check:
            return check

        template.delete()
        return redirect("templates-list")


class ConfigTemplateRenderView(TenantScopedView):
    """Render a configuration template with variables."""

    partial_name = "templates/_render_result.html"

    def post(self, request, pk):
        template = get_object_or_404(ConfigTemplate.objects.select_related("customer"), pk=pk)
        check = self.ensure_customer_access(template.customer_id)
        if check:
            return check

        # Parse variables from request
        variables = {}
        for key, value in request.POST.items():
            if key.startswith("var_"):
                var_name = key[4:]  # Remove "var_" prefix
                variables[var_name] = value

        try:
            rendered = template.render(variables)
            return render(
                request,
                self.partial_name,
                {
                    "template": template,
                    "rendered": rendered,
                    "variables": variables,
                    "success": True,
                },
            )
        except Exception as e:
            logger.exception("Template rendering failed for template %s", template.id)
            return render(
                request,
                self.partial_name,
                {
                    "template": template,
                    "error": str(e),
                    "variables": variables,
                },
            )


# ==============================================================================
# NetBox Integration Views (Issue #9)
# ==============================================================================


class NetBoxConfigForm(forms.ModelForm):
    """Form for NetBox configuration."""

    api_token = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={"placeholder": "Enter API token"}),
        help_text="NetBox API token (leave blank to keep existing)",
    )

    class Meta:
        model = NetBoxConfig
        fields = [
            "customer",
            "name",
            "api_url",
            "api_token",
            "sync_frequency",
            "enabled",
            "site_filter",
            "tenant_filter",
            "role_filter",
            "status_filter",
            "default_credential",
        ]

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        if user and getattr(user, "role", "viewer") != "admin":
            self.fields["customer"].queryset = user.customers.all()
            self.fields["default_credential"].queryset = Credential.objects.filter(
                customer__in=user.customers.all()
            )
        else:
            self.fields["customer"].queryset = Customer.objects.all()
            self.fields["default_credential"].queryset = Credential.objects.all()

    def save(self, commit=True):
        instance = super().save(commit=False)
        api_token = self.cleaned_data.get("api_token")
        if api_token:
            instance.api_token = api_token
        if commit:
            instance.save()
        return instance


class NetBoxSettingsListView(TenantScopedView):
    """List NetBox configurations."""

    template_name = "settings/netbox_list.html"

    def get(self, request):
        configs = self.filter_by_customer(
            NetBoxConfig.objects.select_related("customer", "default_credential").all()
        )
        return render(request, self.template_name, {"configs": configs})


class NetBoxSettingsDetailView(TenantScopedView):
    """View/edit a NetBox configuration."""

    template_name = "settings/netbox_detail.html"
    partial_name = "settings/_netbox_form.html"

    def get(self, request, pk):
        config = get_object_or_404(
            NetBoxConfig.objects.select_related("customer", "default_credential"), pk=pk
        )
        check = self.ensure_customer_access(config.customer_id)
        if check:
            return check

        # Get recent sync logs
        sync_logs = NetBoxSyncLog.objects.filter(config=config).order_by("-started_at")[:10]

        form = NetBoxConfigForm(instance=config, user=request.user)
        return render(
            request,
            self.template_name,
            {"config": config, "form": form, "sync_logs": sync_logs},
        )

    def post(self, request, pk):
        check = self.ensure_can_write()
        if check:
            return check

        config = get_object_or_404(
            NetBoxConfig.objects.select_related("customer", "default_credential"), pk=pk
        )
        check = self.ensure_customer_access(config.customer_id)
        if check:
            return check

        form = NetBoxConfigForm(request.POST, instance=config, user=request.user)
        if form.is_valid():
            form.save()
            if request.headers.get("HX-Request"):
                return render(
                    request,
                    self.partial_name,
                    {"config": config, "form": form, "success": True},
                )
            return redirect("netbox-settings-detail", pk=pk)

        return render(request, self.template_name, {"config": config, "form": form})


class NetBoxSettingsCreateView(TenantScopedView):
    """Create a new NetBox configuration."""

    template_name = "settings/netbox_create.html"

    def get(self, request):
        form = NetBoxConfigForm(user=request.user)
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        check = self.ensure_can_write()
        if check:
            return check

        form = NetBoxConfigForm(request.POST, user=request.user)
        if form.is_valid():
            config = form.save()
            return redirect("netbox-settings-detail", pk=config.pk)

        return render(request, self.template_name, {"form": form})


class NetBoxSettingsDeleteView(TenantScopedView):
    """Delete a NetBox configuration."""

    def post(self, request, pk):
        check = self.ensure_can_write()
        if check:
            return check

        config = get_object_or_404(NetBoxConfig.objects.select_related("customer"), pk=pk)
        check = self.ensure_customer_access(config.customer_id)
        if check:
            return check

        config.delete()
        return redirect("netbox-settings")


class NetBoxSyncView(TenantScopedView):
    """Trigger a manual NetBox sync."""

    partial_name = "settings/_netbox_sync_result.html"

    def post(self, request, pk):
        check = self.ensure_can_write()
        if check:
            return check

        config = get_object_or_404(NetBoxConfig.objects.select_related("customer"), pk=pk)
        check = self.ensure_customer_access(config.customer_id)
        if check:
            return check

        if not config.enabled:
            return render(
                request,
                self.partial_name,
                {"config": config, "error": "NetBox sync is disabled"},
            )

        if not config.has_api_token():
            return render(
                request,
                self.partial_name,
                {"config": config, "error": "API token is not configured"},
            )

        from webnet.jobs.tasks import netbox_sync_job

        full_sync = request.POST.get("full_sync", "").lower() == "true"
        netbox_sync_job.delay(config.id, full_sync=full_sync)

        return render(
            request,
            self.partial_name,
            {"config": config, "success": True, "message": "NetBox sync queued"},
        )


class NetBoxTestConnectionView(TenantScopedView):
    """Test NetBox API connection."""

    partial_name = "settings/_netbox_test_result.html"

    def post(self, request, pk):
        config = get_object_or_404(NetBoxConfig.objects.select_related("customer"), pk=pk)
        check = self.ensure_customer_access(config.customer_id)
        if check:
            return check

        if not config.has_api_token():
            return render(
                request,
                self.partial_name,
                {"config": config, "success": False, "message": "API token not configured"},
            )

        from webnet.devices.netbox_service import NetBoxService

        service = NetBoxService(config)
        result = service.test_connection()

        return render(
            request,
            self.partial_name,
            {
                "config": config,
                "success": result.success,
                "message": result.message,
                "netbox_version": result.netbox_version,
                "error": result.error,
            },
        )


class NetBoxSyncLogsView(TenantScopedView):
    """View NetBox sync logs."""

    template_name = "settings/netbox_sync_logs.html"
    partial_name = "settings/_netbox_sync_logs_table.html"

    def get(self, request, pk):
        config = get_object_or_404(NetBoxConfig.objects.select_related("customer"), pk=pk)
        check = self.ensure_customer_access(config.customer_id)
        if check:
            return check

        logs = NetBoxSyncLog.objects.filter(config=config).order_by("-started_at")[:50]

        if request.headers.get("HX-Request"):
            return render(request, self.partial_name, {"config": config, "sync_logs": logs})

        return render(request, self.template_name, {"config": config, "sync_logs": logs})


# SSH Host Key Management Views


class SSHHostKeyListView(TenantScopedView):
    """View for listing and managing SSH host keys."""

    template_name = "ssh/host_keys_list.html"

    def get(self, request):
        # Get query parameters
        device_filter = request.GET.get("device")
        verified_filter = request.GET.get("verified")

        # Base queryset
        qs = SSHHostKey.objects.select_related(
            "device", "device__customer", "verified_by"
        ).order_by("-verified", "-first_seen_at")

        # Apply customer filtering
        customer_ids = self.get_accessible_customer_ids()
        qs = qs.filter(device__customer_id__in=customer_ids)

        # Apply device filter
        if device_filter:
            qs = qs.filter(device_id=device_filter)

        # Apply verified filter
        if verified_filter == "true":
            qs = qs.filter(verified=True)
        elif verified_filter == "false":
            qs = qs.filter(verified=False)

        # Get statistics with single aggregation query
        stats_agg = qs.aggregate(
            total=Count("id"),
            verified=Count("id", filter=Q(verified=True)),
            unverified=Count("id", filter=Q(verified=False)),
        )

        # Get devices for filter dropdown
        devices = (
            Device.objects.filter(customer_id__in=customer_ids)
            .order_by("hostname")
            .values("id", "hostname")
        )

        context = {
            "host_keys": qs,
            "devices": devices,
            "selected_device": device_filter,
            "selected_verified": verified_filter,
            "stats": {
                "total": stats_agg["total"],
                "verified": stats_agg["verified"],
                "unverified": stats_agg["unverified"],
            },
        }

        if request.headers.get("HX-Request"):
            return render(request, "ssh/_host_keys_table.html", context)

        return render(request, self.template_name, context)


class SSHHostKeyVerifyView(TenantScopedView):
    """View for verifying/unverifying SSH host keys."""

    def post(self, request, pk):
        check = self.ensure_can_write()
        if check:
            return check

        host_key = get_object_or_404(SSHHostKey.objects.select_related("device__customer"), pk=pk)
        check = self.ensure_customer_access(host_key.device.customer_id)
        if check:
            return check

        from webnet.core.ssh_host_keys import SSHHostKeyService

        action = request.POST.get("action")
        if action == "verify":
            SSHHostKeyService.verify_key_manual(host_key, request.user)
        elif action == "unverify":
            SSHHostKeyService.unverify_key(host_key)
        else:
            return HttpResponseBadRequest("Invalid action. Must be 'verify' or 'unverify'.")

        # Return updated row for HTMX swap
        return render(request, "ssh/_host_key_row.html", {"key": host_key})


class SSHHostKeyDeleteView(TenantScopedView):
    """View for deleting SSH host keys."""

    def delete(self, request, pk):
        check = self.ensure_can_write()
        if check:
            return check

        host_key = get_object_or_404(SSHHostKey.objects.select_related("device__customer"), pk=pk)
        check = self.ensure_customer_access(host_key.device.customer_id)
        if check:
            return check

        host_key.delete()
        # Return empty response for HTMX to remove the row
        return HttpResponse(status=204)


# Custom Fields Management Views


class CustomFieldListView(TenantScopedView):
    """View for listing and managing custom field definitions."""

    template_name = "custom_fields/list.html"

    def get(self, request):
        from webnet.core.models import CustomFieldDefinition

        # Get query parameters for filtering
        model_type = request.GET.get("model_type")
        field_type = request.GET.get("field_type")
        is_active = request.GET.get("is_active")

        # Base queryset
        qs = CustomFieldDefinition.objects.select_related("customer").order_by(
            "model_type", "weight", "name"
        )

        # Apply customer filtering
        customer_ids = self.get_accessible_customer_ids()
        qs = qs.filter(customer_id__in=customer_ids)

        # Apply filters
        if model_type:
            qs = qs.filter(model_type=model_type)
        if field_type:
            qs = qs.filter(field_type=field_type)
        if is_active == "true":
            qs = qs.filter(is_active=True)
        elif is_active == "false":
            qs = qs.filter(is_active=False)

        context = {"custom_fields": qs}

        # Return partial for HTMX table updates
        if request.headers.get("HX-Request"):
            return render(request, "custom_fields/_table.html", context)

        return render(request, self.template_name, context)


class CustomFieldCreateView(TenantScopedView):
    """View for creating a new custom field definition."""

    def get(self, request):
        check = self.ensure_can_write()
        if check:
            return check

        # Get available customers
        if self.request.user.role == "admin":
            customers = Customer.objects.all()
            show_customer_field = True
            default_customer_id = None
        else:
            customers = self.request.user.customers.all()
            show_customer_field = len(customers) > 1
            default_customer_id = customers.first().id if customers.count() == 1 else None

        context = {
            "field": None,
            "customers": customers,
            "show_customer_field": show_customer_field,
            "default_customer_id": default_customer_id,
        }
        return render(request, "custom_fields/_form_modal.html", context)

    def post(self, request):
        from webnet.core.models import CustomFieldDefinition

        check = self.ensure_can_write()
        if check:
            return check

        # Parse form data
        customer_id = request.POST.get("customer")
        name = request.POST.get("name")
        label = request.POST.get("label")
        model_type = request.POST.get("model_type")
        field_type = request.POST.get("field_type")
        description = request.POST.get("description", "")
        required = request.POST.get("required") == "on"
        default_value = request.POST.get("default_value", "")
        validation_min = request.POST.get("validation_min", "")
        validation_max = request.POST.get("validation_max", "")
        validation_regex = request.POST.get("validation_regex", "")
        choices_text = request.POST.get("choices", "")
        weight = int(request.POST.get("weight", 100))
        is_active = request.POST.get("is_active") == "on"

        # Verify customer access
        check = self.ensure_customer_access(int(customer_id))
        if check:
            return check

        # Parse choices if applicable
        choices = None
        if field_type in ("select", "multiselect") and choices_text:
            choices = [line.strip() for line in choices_text.split("\n") if line.strip()]

        # Create custom field definition
        CustomFieldDefinition.objects.create(
            customer_id=customer_id,
            name=name,
            label=label,
            model_type=model_type,
            field_type=field_type,
            description=description or None,
            required=required,
            default_value=default_value or None,
            choices=choices,
            validation_regex=validation_regex or None,
            validation_min=validation_min or None,
            validation_max=validation_max or None,
            weight=weight,
            is_active=is_active,
        )

        # Return updated table
        return self._render_table(request)

    def _render_table(self, request):
        from webnet.core.models import CustomFieldDefinition

        customer_ids = self.get_accessible_customer_ids()
        qs = CustomFieldDefinition.objects.filter(customer_id__in=customer_ids).order_by(
            "model_type", "weight", "name"
        )
        context = {"custom_fields": qs}
        return render(request, "custom_fields/_table.html", context)


class CustomFieldEditView(TenantScopedView):
    """View for editing a custom field definition."""

    def get(self, request, pk):
        from webnet.core.models import CustomFieldDefinition

        check = self.ensure_can_write()
        if check:
            return check

        field = get_object_or_404(CustomFieldDefinition, pk=pk)
        check = self.ensure_customer_access(field.customer_id)
        if check:
            return check

        # Get available customers
        if self.request.user.role == "admin":
            customers = Customer.objects.all()
            show_customer_field = True
        else:
            customers = self.request.user.customers.all()
            show_customer_field = len(customers) > 1

        context = {
            "field": field,
            "customers": customers,
            "show_customer_field": show_customer_field,
        }
        return render(request, "custom_fields/_form_modal.html", context)

    def put(self, request, pk):
        from webnet.core.models import CustomFieldDefinition

        check = self.ensure_can_write()
        if check:
            return check

        field = get_object_or_404(CustomFieldDefinition, pk=pk)
        check = self.ensure_customer_access(field.customer_id)
        if check:
            return check

        # Parse PUT data (Django doesn't parse PUT automatically)
        from django.http import QueryDict

        put_data = QueryDict(request.body)

        # Update fields (except name and model_type which are immutable)
        field.label = put_data.get("label", field.label)
        field.field_type = put_data.get("field_type", field.field_type)
        field.description = put_data.get("description", "") or None
        field.required = put_data.get("required") == "on"
        field.default_value = put_data.get("default_value", "") or None
        field.validation_min = put_data.get("validation_min", "") or None
        field.validation_max = put_data.get("validation_max", "") or None
        field.validation_regex = put_data.get("validation_regex", "") or None

        # Parse choices
        choices_text = put_data.get("choices", "")
        if field.field_type in ("select", "multiselect") and choices_text:
            field.choices = [line.strip() for line in choices_text.split("\n") if line.strip()]
        else:
            field.choices = None

        field.weight = int(put_data.get("weight", field.weight))
        field.is_active = put_data.get("is_active") == "on"
        field.save()

        # Return updated table
        customer_ids = self.get_accessible_customer_ids()
        qs = CustomFieldDefinition.objects.filter(customer_id__in=customer_ids).order_by(
            "model_type", "weight", "name"
        )
        context = {"custom_fields": qs}
        return render(request, "custom_fields/_table.html", context)


class CustomFieldDeleteView(TenantScopedView):
    """View for deleting a custom field definition."""

    def delete(self, request, pk):
        from webnet.core.models import CustomFieldDefinition

        check = self.ensure_can_write()
        if check:
            return check

        field = get_object_or_404(CustomFieldDefinition, pk=pk)
        check = self.ensure_customer_access(field.customer_id)
        if check:
            return check

        field.delete()

        # Return updated table
        customer_ids = self.get_accessible_customer_ids()
        qs = CustomFieldDefinition.objects.filter(customer_id__in=customer_ids).order_by(
            "model_type", "weight", "name"
        )
        context = {"custom_fields": qs}
        return render(request, "custom_fields/_table.html", context)


class SSHHostKeyImportView(TenantScopedView):
    """View for importing SSH host keys from known_hosts format."""

    template_name = "ssh/_import_modal.html"

    def get(self, request):
        # Get devices for dropdown
        customer_ids = self.get_accessible_customer_ids()
        devices = (
            Device.objects.filter(customer_id__in=customer_ids)
            .order_by("hostname")
            .values("id", "hostname")
        )
        return render(request, self.template_name, {"devices": devices})

    def post(self, request):
        check = self.ensure_can_write()
        if check:
            return check

        device_id = request.POST.get("device_id")
        known_hosts_line = request.POST.get("known_hosts_line")

        if not device_id:
            return HttpResponseBadRequest("device_id is required")
        if not known_hosts_line:
            return HttpResponseBadRequest("known_hosts_line is required")

        try:
            device_id_int = int(device_id)
        except (ValueError, TypeError):
            return HttpResponseBadRequest("Invalid device_id")

        try:
            device = Device.objects.select_related("customer").get(id=device_id_int)
        except Device.DoesNotExist:
            return HttpResponseBadRequest("Device not found")

        check = self.ensure_customer_access(device.customer_id)
        if check:
            return check

        from webnet.core.ssh_host_keys import SSHHostKeyService

        try:
            host_key = SSHHostKeyService.import_from_openssh_known_hosts(device, known_hosts_line)
            # Return the new row
            return render(request, "ssh/_host_key_row.html", {"key": host_key})
        except ValueError as e:
            logger.error(
                "SSHHostKey import failed for device_id=%s: %s",
                device_id_int,
                repr(e),
            )
            return HttpResponseBadRequest("Could not import SSH host key. Please check your input.")


class RemediationRuleListView(TenantScopedView):
    """List remediation rules for compliance policies."""

    template_name = "compliance/remediation_rules.html"
    partial_name = "compliance/_remediation_rules_table.html"

    def get(self, request):
        qs = RemediationRule.objects.select_related("policy", "policy__customer", "created_by")
        qs = self.filter_by_customer(qs, "policy__customer_id")

        # Convert to list to avoid duplicate query execution
        rules = list(qs)

        rules_payload = [
            {
                "id": r.id,
                "name": r.name,
                "policy": r.policy.name,
                "enabled": r.enabled,
                "approval": r.get_approval_required_display(),
                "max_daily": r.max_daily_executions,
                "updated_at": timezone.localtime(r.updated_at).strftime("%Y-%m-%d %H:%M:%S"),
            }
            for r in rules
        ]

        context = {
            "rules": rules,
            "rules_table_props": json.dumps(
                {
                    "rows": rules_payload,
                    "emptyState": {
                        "title": "No remediation rules found",
                        "description": "Create auto-remediation rules to automatically fix compliance violations.",
                    },
                }
            ),
        }

        if request.headers.get("HX-Request"):
            return render(request, self.partial_name, context)
        return render(request, self.template_name, context)


class RemediationActionListView(TenantScopedView):
    """List remediation action audit log."""

    template_name = "compliance/remediation_actions.html"
    partial_name = "compliance/_remediation_actions_table.html"

    def get(self, request):
        qs = RemediationAction.objects.select_related(
            "rule",
            "rule__policy",
            "rule__policy__customer",
            "device",
            "compliance_result",
            "job",
        ).order_by("-started_at")[
            :100
        ]  # Limit to recent 100
        qs = self.filter_by_customer(qs, "rule__policy__customer_id")

        # Convert to list to avoid duplicate query execution
        actions = list(qs)

        actions_payload = [
            {
                "id": a.id,
                "rule_name": a.rule.name,
                "device": a.device.hostname,
                "status": a.status,
                "verification_passed": a.verification_passed,
                "started_at": timezone.localtime(a.started_at).strftime("%Y-%m-%d %H:%M:%S"),
                "error_message": a.error_message,
            }
            for a in actions
        ]

        context = {
            "actions": actions,
            "actions_table_props": json.dumps(
                {
                    "rows": actions_payload,
                    "emptyState": {
                        "title": "No remediation actions found",
                        "description": "Remediation actions will appear here when auto-remediation is triggered.",
                    },
                }
            ),
        }

        if request.headers.get("HX-Request"):
            return render(request, self.partial_name, context)
        return render(request, self.template_name, context)


# Plugin Management Views


class PluginListView(AdminRequiredMixin, View):
    """Plugin list view."""

    template_name = "plugins/list.html"

    def get(self, request):
        from webnet.plugins.models import PluginConfig
        from webnet.plugins.registry import plugin_registry

        plugins = PluginConfig.objects.all()
        # Annotate with loaded status
        for plugin in plugins:
            plugin.is_loaded = plugin_registry.is_plugin_loaded(plugin.name)

        context = {"plugins": plugins}
        return render(request, self.template_name, context)


class PluginDetailView(AdminRequiredMixin, View):
    """Plugin detail/settings view."""

    template_name = "plugins/detail.html"

    def get(self, request, pk):
        from webnet.plugins.models import PluginConfig
        from webnet.plugins.registry import plugin_registry

        plugin = get_object_or_404(PluginConfig, pk=pk)
        plugin.is_loaded = plugin_registry.is_plugin_loaded(plugin.name)

        context = {"plugin": plugin}
        return render(request, self.template_name, context)


class PluginEnableView(AdminRequiredMixin, View):
    """Enable a plugin (HTMX partial)."""

    def post(self, request, pk):
        from webnet.plugins.models import PluginConfig
        from webnet.plugins.manager import PluginManager
        from webnet.plugins.registry import plugin_registry

        plugin = get_object_or_404(PluginConfig, pk=pk)
        success, message = PluginManager.enable_plugin(plugin.name, user=request.user)

        if success:
            plugin.refresh_from_db()
            plugin.is_loaded = plugin_registry.is_plugin_loaded(plugin.name)
            return render(request, "plugins/_plugin_card.html", {"plugin": plugin})
        else:
            return HttpResponseBadRequest(message)


class PluginDisableView(AdminRequiredMixin, View):
    """Disable a plugin (HTMX partial)."""

    def post(self, request, pk):
        from webnet.plugins.models import PluginConfig
        from webnet.plugins.manager import PluginManager
        from webnet.plugins.registry import plugin_registry

        plugin = get_object_or_404(PluginConfig, pk=pk)
        success, message = PluginManager.disable_plugin(plugin.name, user=request.user)

        if success:
            plugin.refresh_from_db()
            plugin.is_loaded = plugin_registry.is_plugin_loaded(plugin.name)
            return render(request, "plugins/_plugin_card.html", {"plugin": plugin})
        else:
            return HttpResponseBadRequest(message)


class PluginHealthView(AdminRequiredMixin, View):
    """Get plugin health status (HTMX partial)."""

    def get(self, request, pk):
        from webnet.plugins.models import PluginConfig
        from webnet.plugins.manager import PluginManager

        plugin = get_object_or_404(PluginConfig, pk=pk)
        health = PluginManager.get_plugin_health(plugin.name)

        # Format details as JSON string for display
        if health.get("details"):
            health["details"] = json.dumps(health["details"], indent=2)

        context = {"health": health}
        return render(request, "plugins/_health.html", context)


class PluginUpdateSettingsView(AdminRequiredMixin, View):
    """Update plugin settings."""

    def post(self, request, pk):
        from webnet.plugins.models import PluginConfig
        from webnet.plugins.manager import PluginManager

        plugin = get_object_or_404(PluginConfig, pk=pk)

        try:
            settings_str = request.POST.get("settings", "{}")
            settings = json.loads(settings_str)
        except json.JSONDecodeError:
            return HttpResponseBadRequest("Invalid JSON in settings")

        success, message = PluginManager.update_plugin_settings(
            plugin.name, settings, user=request.user
        )

        if success:
            return HttpResponse("Settings updated successfully")
        else:
            return HttpResponseBadRequest(message)


class PluginCustomersView(AdminRequiredMixin, View):
    """Get customer configurations for a plugin (HTMX partial)."""

    def get(self, request, pk):
        from webnet.plugins.models import PluginConfig, CustomerPluginConfig

        plugin = get_object_or_404(PluginConfig, pk=pk)
        customer_configs = CustomerPluginConfig.objects.filter(plugin=plugin).select_related(
            "customer"
        )

        context = {"customer_configs": customer_configs}
        return render(request, "plugins/_customers.html", context)


class PluginAuditLogView(AdminRequiredMixin, View):
    """Get audit logs for a plugin (HTMX partial)."""

    def get(self, request, pk):
        from webnet.plugins.models import PluginConfig, PluginAuditLog

        plugin = get_object_or_404(PluginConfig, pk=pk)
        audit_logs = PluginAuditLog.objects.filter(plugin=plugin).select_related(
            "customer", "user"
        )[:50]

        # Format details as JSON string for display
        for log in audit_logs:
            if log.details:
                log.details = json.dumps(log.details, indent=2)

        context = {"audit_logs": audit_logs}
        return render(request, "plugins/_audit_log.html", context)


class CustomerPluginEnableView(AdminRequiredMixin, View):
    """Enable plugin for a customer (HTMX partial)."""

    def post(self, request, pk):
        from webnet.plugins.models import CustomerPluginConfig
        from webnet.plugins.manager import PluginManager

        config = get_object_or_404(CustomerPluginConfig, pk=pk)
        success, message = PluginManager.enable_plugin(
            config.plugin.name, customer=config.customer, user=request.user
        )

        if success:
            config.refresh_from_db()
            return render(request, "plugins/_customers.html", {"customer_configs": [config]})
        else:
            return HttpResponseBadRequest(message)


class CustomerPluginDisableView(AdminRequiredMixin, View):
    """Disable plugin for a customer (HTMX partial)."""

    def post(self, request, pk):
        from webnet.plugins.models import CustomerPluginConfig
        from webnet.plugins.manager import PluginManager

        config = get_object_or_404(CustomerPluginConfig, pk=pk)
        success, message = PluginManager.disable_plugin(
            config.plugin.name, customer=config.customer, user=request.user
        )

        if success:
            config.refresh_from_db()
            return render(request, "plugins/_customers.html", {"customer_configs": [config]})
        else:
            return HttpResponseBadRequest(message)


class CustomerPluginUpdateSettingsView(AdminRequiredMixin, View):
    """Update customer-specific plugin settings."""

    def post(self, request, pk):
        from webnet.plugins.models import CustomerPluginConfig
        from webnet.plugins.manager import PluginManager

        config = get_object_or_404(CustomerPluginConfig, pk=pk)

        try:
            settings_str = request.POST.get("settings", "{}")
            settings = json.loads(settings_str)
        except json.JSONDecodeError:
            return HttpResponseBadRequest("Invalid JSON in settings")

        success, message = PluginManager.update_plugin_settings(
            config.plugin.name, settings, customer=config.customer, user=request.user
        )

        if success:
            return HttpResponse("Settings updated successfully")
        else:
            return HttpResponseBadRequest(message)


# Webhook Views
class WebhookListView(TenantScopedView):
    """List webhooks."""

    template_name = "settings/webhook_list.html"

    def get(self, request):
        from webnet.webhooks.models import Webhook

        qs = Webhook.objects.select_related("customer", "created_by").order_by("-created_at")
        webhooks = self.filter_by_customer(qs)

        context = {
            "webhooks": webhooks,
        }

        return render(request, self.template_name, context)


class WebhookDeliveryListView(TenantScopedView):
    """List webhook deliveries."""

    template_name = "settings/webhook_deliveries.html"
    customer_field = "webhook__customer_id"

    def get(self, request):
        from webnet.webhooks.models import WebhookDelivery

        qs = WebhookDelivery.objects.select_related("webhook", "webhook__customer").order_by(
            "-created_at"
        )[:100]
        deliveries = self.filter_by_customer(qs)

        context = {
            "deliveries": deliveries,
        }

        return render(request, self.template_name, context)


class ScheduleListView(TenantScopedView):
    template_name = "schedules/list.html"
    partial_name = "schedules/_table.html"

    def get(self, request):
        qs = Schedule.objects.select_related("customer", "created_by")
        qs = self.filter_by_customer(qs).order_by("name")

        schedules_payload = [
            {
                "id": schedule.id,
                "name": schedule.name,
                "job_type": schedule.get_job_type_display(),
                "interval": schedule.get_interval_type_display(),
                "enabled": schedule.enabled,
                "next_run": (
                    timezone.localtime(schedule.next_run).strftime("%Y-%m-%d %H:%M")
                    if schedule.next_run
                    else "N/A"
                ),
                "last_run": (
                    timezone.localtime(schedule.last_run).strftime("%Y-%m-%d %H:%M")
                    if schedule.last_run
                    else "Never"
                ),
                "detailUrl": reverse("schedule-detail", args=[schedule.id]),
            }
            for schedule in qs
        ]

        context = {
            "schedules": qs,
            "schedules_table_props": json.dumps(
                {
                    "rows": schedules_payload,
                    "emptyState": {
                        "title": "No schedules found",
                        "description": "Create a schedule to automate recurring tasks.",
                    },
                }
            ),
        }

        if request.headers.get("HX-Request"):
            return render(request, self.partial_name, context)
        return render(request, self.template_name, context)


class ScheduleDetailView(TenantScopedView):
    template_name = "schedules/detail.html"

    def get(self, request, pk: int):
        schedule = get_object_or_404(
            Schedule.objects.select_related("customer", "created_by"), pk=pk
        )
        forbidden = self.ensure_customer_access(schedule.customer_id)
        if forbidden:
            return forbidden

        # Get recent jobs for this schedule
        recent_jobs = (
            Job.objects.filter(schedule=schedule)
            .select_related("user")
            .order_by("-requested_at")[:10]
        )

        context = {
            "schedule": schedule,
            "recent_jobs": recent_jobs,
        }
        return render(request, self.template_name, context)


class ScheduleCreateView(TenantScopedView):
    template_name = "schedules/form.html"

    def get(self, request):
        customers = self.get_accessible_customers()
        job_types = Job.TYPE_CHOICES
        interval_types = Schedule.INTERVAL_CHOICES

        context = {
            "customers": customers,
            "job_types": job_types,
            "interval_types": interval_types,
            "mode": "create",
        }
        return render(request, self.template_name, context)

    def post(self, request):
        customers = self.get_accessible_customers()
        customer_id = request.POST.get("customer")

        # Validate customer access
        if not any(c.id == int(customer_id) for c in customers):
            return HttpResponseForbidden("Access denied to this customer")

        # Create schedule
        customer = Customer.objects.get(pk=customer_id)
        schedule = Schedule(
            customer=customer,
            created_by=request.user,
            name=request.POST.get("name"),
            description=request.POST.get("description", ""),
            job_type=request.POST.get("job_type"),
            interval_type=request.POST.get("interval_type"),
            cron_expression=request.POST.get("cron_expression", ""),
            enabled="enabled" in request.POST or request.POST.get("enabled") == "on",
        )
        schedule.save()

        return redirect("schedule-detail", pk=schedule.id)


class ScheduleEditView(TenantScopedView):
    template_name = "schedules/form.html"

    def get(self, request, pk: int):
        schedule = get_object_or_404(
            Schedule.objects.select_related("customer", "created_by"), pk=pk
        )
        forbidden = self.ensure_customer_access(schedule.customer_id)
        if forbidden:
            return forbidden

        customers = self.get_accessible_customers()
        job_types = Job.TYPE_CHOICES
        interval_types = Schedule.INTERVAL_CHOICES

        context = {
            "schedule": schedule,
            "customers": customers,
            "job_types": job_types,
            "interval_types": interval_types,
            "mode": "edit",
        }
        return render(request, self.template_name, context)

    def post(self, request, pk: int):
        schedule = get_object_or_404(
            Schedule.objects.select_related("customer", "created_by"), pk=pk
        )
        forbidden = self.ensure_customer_access(schedule.customer_id)
        if forbidden:
            return forbidden

        # Update schedule
        schedule.name = request.POST.get("name")
        schedule.description = request.POST.get("description", "")
        schedule.job_type = request.POST.get("job_type")
        schedule.interval_type = request.POST.get("interval_type")
        schedule.cron_expression = request.POST.get("cron_expression", "")
        schedule.enabled = "enabled" in request.POST or request.POST.get("enabled") == "on"
        schedule.save()

        return redirect("schedule-detail", pk=schedule.id)


class ScheduleDeleteView(TenantScopedView):
    def post(self, request, pk: int):
        schedule = get_object_or_404(Schedule, pk=pk)
        forbidden = self.ensure_customer_access(schedule.customer_id)
        if forbidden:
            return forbidden

        schedule.delete()
        return redirect("schedules-list")


class ScheduleCalendarView(TenantScopedView):
    template_name = "schedules/calendar.html"

    def get(self, request):
        from calendar import monthcalendar, month_name

        # Get year and month from query params
        try:
            year = int(request.GET.get("year", timezone.now().year))
            month = int(request.GET.get("month", timezone.now().month))
        except (ValueError, TypeError):
            year = timezone.now().year
            month = timezone.now().month

        # Get all enabled schedules for the customer
        schedules = Schedule.objects.filter(enabled=True)
        schedules = self.filter_by_customer(schedules).select_related("customer", "created_by")

        # Calculate calendar events
        calendar_weeks = monthcalendar(year, month)
        month_name_str = month_name[month]

        # Create events for the calendar
        events = []
        for schedule in schedules:
            if schedule.next_run:
                next_run = timezone.localtime(schedule.next_run)
                if next_run.year == year and next_run.month == month:
                    events.append(
                        {
                            "id": schedule.id,
                            "name": schedule.name,
                            "day": next_run.day,
                            "time": next_run.strftime("%H:%M"),
                            "job_type": schedule.get_job_type_display(),
                        }
                    )

        context = {
            "year": year,
            "month": month,
            "month_name": month_name_str,
            "calendar_weeks": calendar_weeks,
            "events": events,
            "schedules": schedules,
        }
        return render(request, self.template_name, context)
