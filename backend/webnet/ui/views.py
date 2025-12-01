from __future__ import annotations

from difflib import unified_diff
import json

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Count
from django.http import HttpResponseForbidden
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.views import View

from django import forms
from django.contrib.auth import logout
from django.http import HttpResponseBadRequest
from django.urls import reverse

from webnet.api.permissions import user_has_customer_access
from webnet.compliance.models import CompliancePolicy, ComplianceResult
from webnet.config_mgmt.models import ConfigSnapshot
from webnet.customers.models import Customer
from webnet.devices.models import Device, TopologyLink, Credential
from webnet.jobs.models import Job, JobLog
from webnet.jobs.services import JobService


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
