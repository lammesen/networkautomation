"""ServiceNow CMDB integration service.

This service handles bi-directional sync with ServiceNow CMDB,
incident creation on job failures, and change request management.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import httpx
from django.utils import timezone

from webnet.devices.models import Device, ServiceNowConfig, ServiceNowSyncLog

logger = logging.getLogger(__name__)


@dataclass
class ConnectionTestResult:
    """Result of a ServiceNow connection test."""

    success: bool
    message: str
    servicenow_version: str | None = None
    error: str | None = None


@dataclass
class SyncPreviewResult:
    """Result of a sync preview operation."""

    devices: list[dict[str, Any]]
    total: int
    would_create: int
    would_update: int
    conflicts: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class SyncResult:
    """Result of a sync operation."""

    success: bool
    message: str
    created: int = 0
    updated: int = 0
    skipped: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class IncidentResult:
    """Result of an incident creation/update operation."""

    success: bool
    incident_number: str | None = None
    incident_sys_id: str | None = None
    message: str = ""
    error: str | None = None


@dataclass
class ChangeRequestResult:
    """Result of a change request operation."""

    success: bool
    change_number: str | None = None
    change_sys_id: str | None = None
    message: str = ""
    error: str | None = None


class ServiceNowService:
    """Service for interacting with ServiceNow API.

    Handles CMDB synchronization, incident management, and change requests.
    """

    # Default field mappings from webnet Device to ServiceNow CI
    DEFAULT_DEVICE_TO_CMDB_MAPPINGS = {
        "name": "hostname",  # webnet hostname -> ServiceNow CI name
        "ip_address": "mgmt_ip",
        "manufacturer": "vendor",
        "os": "platform",
        "location": "site",
        "u_role": "role",
    }

    # Default field mappings from ServiceNow CI to webnet Device
    DEFAULT_CMDB_TO_DEVICE_MAPPINGS = {
        "hostname": "name",
        "mgmt_ip": "ip_address",
        "vendor": "manufacturer.display_value",
        "platform": "os",
        "site": "location.display_value",
        "role": "u_role",
    }

    def __init__(self, config: ServiceNowConfig):
        self.config = config
        self.instance_url = config.instance_url.rstrip("/")
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        # Merge custom field mappings with defaults
        self.device_to_cmdb_mappings = {**self.DEFAULT_DEVICE_TO_CMDB_MAPPINGS}
        if config.device_to_cmdb_mappings:
            self.device_to_cmdb_mappings.update(config.device_to_cmdb_mappings)

        self.cmdb_to_device_mappings = {**self.DEFAULT_CMDB_TO_DEVICE_MAPPINGS}
        if config.cmdb_to_device_mappings:
            self.cmdb_to_device_mappings.update(config.cmdb_to_device_mappings)

    def _request(
        self,
        method: str,
        endpoint: str,
        params: dict | None = None,
        json_data: dict | None = None,
    ) -> dict[str, Any]:
        """Make a request to ServiceNow API."""
        url = f"{self.instance_url}/{endpoint.lstrip('/')}"

        # Access password only when needed
        auth = (self.config.username, self.config.password)

        # Use configurable timeout, with longer timeout for potentially slow operations
        timeout = 60 if params and params.get("sysparm_limit") else 30

        with httpx.Client(timeout=timeout) as client:
            response = client.request(
                method=method,
                url=url,
                headers=self.headers,
                auth=auth,
                params=params,
                json=json_data,
            )
            response.raise_for_status()
            return response.json()

    def test_connection(self) -> ConnectionTestResult:
        """Test the connection to ServiceNow API."""
        try:
            # Test by querying the user table (should always have access)
            self._request(
                "GET",
                "/api/now/table/sys_user",
                params={"sysparm_limit": 1},
            )

            # Try to get instance info if available
            version = None
            try:
                stats = self._request("GET", "/api/now/stats")
                version = stats.get("result", {}).get("version")
            except Exception:
                # Stats endpoint may not be available on all instances
                pass

            return ConnectionTestResult(
                success=True,
                message="Successfully connected to ServiceNow",
                servicenow_version=version,
            )
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                return ConnectionTestResult(
                    success=False,
                    message="Authentication failed - check username and password",
                    error=str(e),
                )
            elif e.response.status_code == 403:
                return ConnectionTestResult(
                    success=False,
                    message="Access forbidden - check user permissions",
                    error=str(e),
                )
            return ConnectionTestResult(
                success=False,
                message=f"HTTP error: {e.response.status_code}",
                error=str(e),
            )
        except httpx.ConnectError as e:
            return ConnectionTestResult(
                success=False,
                message="Failed to connect - check instance URL",
                error=str(e),
            )
        except Exception as e:
            logger.exception("ServiceNow connection test failed")
            return ConnectionTestResult(
                success=False,
                message=f"Connection failed: {e}",
                error=str(e),
            )

    def _get_nested_value(self, obj: dict, path: str) -> Any:
        """Get a nested value from a dictionary using dot notation."""
        parts = path.split(".")
        current = obj
        for part in parts:
            if current is None:
                return None
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return None
        return current

    def _map_device_to_ci(self, device: Device) -> dict[str, Any]:
        """Map a webnet Device to ServiceNow CI fields."""
        mapped = {}

        for snow_field, device_attr in self.device_to_cmdb_mappings.items():
            value = getattr(device, device_attr, None)
            if value is not None:
                mapped[snow_field] = str(value)

        # Add customer reference as company if available
        if self.config.company_sys_id:
            mapped["company"] = self.config.company_sys_id

        return mapped

    def _map_ci_to_device(self, ci: dict) -> dict[str, Any]:
        """Map a ServiceNow CI to webnet Device fields."""
        mapped = {}

        for device_field, snow_path in self.cmdb_to_device_mappings.items():
            value = self._get_nested_value(ci, snow_path)
            if value is not None:
                mapped[device_field] = value

        # Add ServiceNow sys_id for tracking
        mapped["servicenow_sys_id"] = ci.get("sys_id")
        mapped["servicenow_url"] = f"{self.instance_url}/cmdb_ci_list.do?sys_id={ci.get('sys_id')}"

        return mapped

    def fetch_cis(self) -> list[dict[str, Any]]:
        """Fetch Configuration Items from ServiceNow CMDB."""
        cis = []
        query_parts = []

        # Build query based on filters
        if self.config.ci_class:
            query_parts.append(f"sys_class_name={self.config.ci_class}")

        if self.config.ci_query_filter:
            query_parts.append(self.config.ci_query_filter)

        query = "^".join(query_parts) if query_parts else ""

        params = {
            "sysparm_query": query,
            "sysparm_limit": 100,
            "sysparm_offset": 0,
            "sysparm_display_value": "true",
        }

        max_pages = 1000  # Safety limit to prevent infinite loops
        page_count = 0

        while page_count < max_pages:
            result = self._request(
                "GET",
                f"/api/now/table/{self.config.cmdb_table}",
                params=params,
            )
            results = result.get("result", [])
            cis.extend(results)

            # Check if there are more pages
            if len(results) < 100:
                break
            page_count += 1
            params["sysparm_offset"] += 100

        return cis

    def export_device_to_cmdb(self, device: Device) -> SyncResult:
        """Export a single device to ServiceNow CMDB."""
        try:
            ci_data = self._map_device_to_ci(device)

            # Check if CI already exists by looking for sys_id in device tags
            tags = device.tags or {}
            existing_sys_id = tags.get("servicenow_sys_id")

            if existing_sys_id:
                # Update existing CI
                self._request(
                    "PATCH",
                    f"/api/now/table/{self.config.cmdb_table}/{existing_sys_id}",
                    json_data=ci_data,
                )

                return SyncResult(
                    success=True,
                    message=f"Updated CI for {device.hostname}",
                    updated=1,
                )
            else:
                # Create new CI
                result = self._request(
                    "POST",
                    f"/api/now/table/{self.config.cmdb_table}",
                    json_data=ci_data,
                )

                # Store sys_id in device tags
                sys_id = result["result"]["sys_id"]
                tags["servicenow_sys_id"] = sys_id
                device.tags = tags
                device.save()

                return SyncResult(
                    success=True,
                    message=f"Created CI for {device.hostname}",
                    created=1,
                    details={"sys_id": sys_id},
                )

        except Exception as e:
            logger.exception(
                "Failed to export device %s (ID: %s) to CMDB", device.hostname, device.id
            )
            return SyncResult(
                success=False,
                message=f"Failed to export {device.hostname}: {e}",
                failed=1,
                errors=[str(e)],
            )

    def import_ci_to_device(self, ci: dict) -> SyncResult:
        """Import a ServiceNow CI as a webnet Device."""
        try:
            mapped = self._map_ci_to_device(ci)
            hostname = mapped.get("hostname")

            if not hostname:
                return SyncResult(
                    success=False,
                    message="CI missing hostname",
                    skipped=1,
                )

            # Check if device already exists
            try:
                device = Device.objects.get(
                    customer=self.config.customer,
                    hostname=hostname,
                )
                # Update device if full sync is enabled
                if self.config.bidirectional_sync:
                    changed = False
                    for field in ["mgmt_ip", "vendor", "platform", "role", "site"]:
                        new_val = mapped.get(field)
                        if new_val and getattr(device, field) != new_val:
                            setattr(device, field, new_val)
                            changed = True

                    # Store ServiceNow sys_id in tags
                    tags = device.tags or {}
                    tags["servicenow_sys_id"] = mapped.get("servicenow_sys_id")
                    device.tags = tags

                    if changed:
                        device.save()
                        return SyncResult(
                            success=True,
                            message=f"Updated device {hostname}",
                            updated=1,
                        )
                    else:
                        device.save()  # Save tags even if no other fields changed
                        return SyncResult(
                            success=True,
                            message=f"No changes for {hostname}",
                            skipped=1,
                        )
                else:
                    return SyncResult(
                        success=True,
                        message=f"Device {hostname} already exists",
                        skipped=1,
                    )

            except Device.DoesNotExist:
                # Create new device
                if not self.config.default_credential:
                    return SyncResult(
                        success=False,
                        message=f"Cannot create {hostname}: no default credential",
                        failed=1,
                        errors=["No default credential configured"],
                    )

                device = Device.objects.create(
                    customer=self.config.customer,
                    hostname=hostname,
                    mgmt_ip=mapped.get("mgmt_ip", ""),
                    vendor=mapped.get("vendor", ""),
                    platform=mapped.get("platform", ""),
                    role=mapped.get("role"),
                    site=mapped.get("site"),
                    credential=self.config.default_credential,
                    tags={"servicenow_sys_id": mapped.get("servicenow_sys_id")},
                )

                return SyncResult(
                    success=True,
                    message=f"Created device {hostname}",
                    created=1,
                    details={"device_id": device.id},
                )

        except Exception as e:
            logger.exception(
                "Failed to import CI %s (name: %s) to device",
                ci.get("sys_id"),
                ci.get("name"),
            )
            return SyncResult(
                success=False,
                message=f"Failed to import CI: {e}",
                failed=1,
                errors=[str(e)],
            )

    def sync_to_cmdb(self, devices: list[Device] | None = None) -> SyncResult:
        """Export devices to ServiceNow CMDB.

        Args:
            devices: List of devices to export. If None, exports all customer devices.

        Returns:
            SyncResult with counts and details.
        """
        # Create sync log entry
        sync_log = ServiceNowSyncLog.objects.create(
            config=self.config,
            status="running",
            direction="export",
        )

        created = 0
        updated = 0
        skipped = 0
        failed = 0
        errors: list[str] = []

        try:
            if devices is None:
                devices = list(
                    Device.objects.filter(
                        customer=self.config.customer,
                        enabled=True,
                    )
                )

            for device in devices:
                result = self.export_device_to_cmdb(device)
                created += result.created
                updated += result.updated
                skipped += result.skipped
                failed += result.failed
                errors.extend(result.errors)

            # Update sync log
            sync_log.status = "success" if not errors else "partial"
            sync_log.devices_created = created
            sync_log.devices_updated = updated
            sync_log.devices_skipped = skipped
            sync_log.devices_failed = failed
            sync_log.message = f"Exported {created} created, {updated} updated, {skipped} skipped"
            sync_log.finished_at = timezone.now()
            sync_log.save()

            # Update config sync status
            self.config.last_sync_at = timezone.now()
            self.config.last_sync_status = sync_log.status
            self.config.last_sync_message = sync_log.message
            self.config.save()

            return SyncResult(
                success=(failed == 0) or (created > 0 or updated > 0),
                message=sync_log.message,
                created=created,
                updated=updated,
                skipped=skipped,
                failed=failed,
                errors=errors,
            )

        except Exception as e:
            sync_log.status = "failed"
            sync_log.message = str(e)
            sync_log.finished_at = timezone.now()
            sync_log.save()

            self.config.last_sync_status = "failed"
            self.config.last_sync_message = str(e)
            self.config.save()

            logger.exception("ServiceNow export sync failed for config %s", self.config.id)
            return SyncResult(
                success=False,
                message=f"Sync failed: {e}",
                errors=[str(e)],
            )

    def sync_from_cmdb(self) -> SyncResult:
        """Import devices from ServiceNow CMDB.

        Returns:
            SyncResult with counts and details.
        """
        # Create sync log entry
        sync_log = ServiceNowSyncLog.objects.create(
            config=self.config,
            status="running",
            direction="import",
        )

        created = 0
        updated = 0
        skipped = 0
        failed = 0
        errors: list[str] = []

        try:
            cis = self.fetch_cis()

            for ci in cis:
                result = self.import_ci_to_device(ci)
                created += result.created
                updated += result.updated
                skipped += result.skipped
                failed += result.failed
                errors.extend(result.errors)

            # Update sync log
            sync_log.status = "success" if not errors else "partial"
            sync_log.devices_created = created
            sync_log.devices_updated = updated
            sync_log.devices_skipped = skipped
            sync_log.devices_failed = failed
            sync_log.message = f"Imported {created} created, {updated} updated, {skipped} skipped"
            sync_log.finished_at = timezone.now()
            sync_log.save()

            # Update config sync status
            self.config.last_sync_at = timezone.now()
            self.config.last_sync_status = sync_log.status
            self.config.last_sync_message = sync_log.message
            self.config.save()

            return SyncResult(
                success=(failed == 0) or (created > 0 or updated > 0),
                message=sync_log.message,
                created=created,
                updated=updated,
                skipped=skipped,
                failed=failed,
                errors=errors,
            )

        except Exception as e:
            sync_log.status = "failed"
            sync_log.message = str(e)
            sync_log.finished_at = timezone.now()
            sync_log.save()

            self.config.last_sync_status = "failed"
            self.config.last_sync_message = str(e)
            self.config.save()

            logger.exception("ServiceNow import sync failed for config %s", self.config.id)
            return SyncResult(
                success=False,
                message=f"Sync failed: {e}",
                errors=[str(e)],
            )

    def create_incident(
        self,
        short_description: str,
        description: str,
        impact: int = 3,
        urgency: int = 3,
        caller: str | None = None,
        assignment_group: str | None = None,
        configuration_item: str | None = None,
    ) -> IncidentResult:
        """Create an incident in ServiceNow.

        Args:
            short_description: Brief summary of the incident
            description: Detailed description
            impact: Impact level (1-3, where 1 is highest)
            urgency: Urgency level (1-3, where 1 is highest)
            caller: Caller sys_id or username
            assignment_group: Assignment group sys_id
            configuration_item: CI sys_id to link to the incident

        Returns:
            IncidentResult with incident details
        """
        # Validate input parameters
        if not 1 <= impact <= 3:
            raise ValueError("Impact must be between 1 and 3")
        if not 1 <= urgency <= 3:
            raise ValueError("Urgency must be between 1 and 3")

        try:
            incident_data = {
                "short_description": short_description,
                "description": description,
                "impact": str(impact),
                "urgency": str(urgency),
            }

            if caller:
                incident_data["caller_id"] = caller

            if assignment_group:
                incident_data["assignment_group"] = assignment_group

            if configuration_item:
                incident_data["cmdb_ci"] = configuration_item

            # Add category if configured
            if self.config.incident_category:
                incident_data["category"] = self.config.incident_category

            result = self._request(
                "POST",
                "/api/now/table/incident",
                json_data=incident_data,
            )

            incident = result["result"]

            return IncidentResult(
                success=True,
                incident_number=incident.get("number"),
                incident_sys_id=incident.get("sys_id"),
                message=f"Created incident {incident.get('number')}",
            )

        except Exception as e:
            logger.exception("Failed to create ServiceNow incident")
            return IncidentResult(
                success=False,
                message="Failed to create incident",
                error=str(e),
            )

    def update_incident(
        self,
        incident_sys_id: str,
        state: int | None = None,
        work_notes: str | None = None,
        resolution_notes: str | None = None,
    ) -> IncidentResult:
        """Update an existing incident.

        Args:
            incident_sys_id: Incident sys_id
            state: New state (1=New, 2=In Progress, 6=Resolved, 7=Closed)
            work_notes: Work notes to add
            resolution_notes: Resolution notes (when resolving)

        Returns:
            IncidentResult with update status
        """
        try:
            update_data = {}

            if state is not None:
                update_data["state"] = str(state)

            if work_notes:
                update_data["work_notes"] = work_notes

            if resolution_notes:
                update_data["close_notes"] = resolution_notes

            result = self._request(
                "PATCH",
                f"/api/now/table/incident/{incident_sys_id}",
                json_data=update_data,
            )

            incident = result["result"]

            return IncidentResult(
                success=True,
                incident_number=incident.get("number"),
                incident_sys_id=incident.get("sys_id"),
                message=f"Updated incident {incident.get('number')}",
            )

        except Exception as e:
            logger.exception("Failed to update ServiceNow incident")
            return IncidentResult(
                success=False,
                message="Failed to update incident",
                error=str(e),
            )

    def create_change_request(
        self,
        short_description: str,
        description: str,
        justification: str,
        risk: int = 3,
        impact: int = 3,
        assignment_group: str | None = None,
        configuration_items: list[str] | None = None,
    ) -> ChangeRequestResult:
        """Create a change request in ServiceNow.

        Args:
            short_description: Brief summary of the change
            description: Detailed description
            justification: Business justification
            risk: Risk level (1-3, where 1 is highest)
            impact: Impact level (1-3, where 1 is highest)
            assignment_group: Assignment group sys_id
            configuration_items: List of CI sys_ids affected by the change

        Returns:
            ChangeRequestResult with change details
        """
        # Validate input parameters
        if not 1 <= risk <= 3:
            raise ValueError("Risk must be between 1 and 3")
        if not 1 <= impact <= 3:
            raise ValueError("Impact must be between 1 and 3")

        try:
            change_data = {
                "short_description": short_description,
                "description": description,
                "justification": justification,
                "risk": str(risk),
                "impact": str(impact),
                "type": "Normal",  # Can be Normal, Standard, or Emergency
            }

            if assignment_group:
                change_data["assignment_group"] = assignment_group

            # Add category if configured
            if self.config.change_category:
                change_data["category"] = self.config.change_category

            result = self._request(
                "POST",
                "/api/now/table/change_request",
                json_data=change_data,
            )

            change = result["result"]
            change_sys_id = change.get("sys_id")

            # Link CIs to the change if provided
            if configuration_items and change_sys_id:
                for ci_sys_id in configuration_items:
                    try:
                        self._request(
                            "POST",
                            "/api/now/table/task_ci",
                            json_data={
                                "task": change_sys_id,
                                "ci_item": ci_sys_id,
                            },
                        )
                    except Exception as e:
                        logger.warning("Failed to link CI %s to change: %s", ci_sys_id, e)

            return ChangeRequestResult(
                success=True,
                change_number=change.get("number"),
                change_sys_id=change_sys_id,
                message=f"Created change request {change.get('number')}",
            )

        except Exception as e:
            logger.exception("Failed to create ServiceNow change request")
            return ChangeRequestResult(
                success=False,
                message="Failed to create change request",
                error=str(e),
            )

    def update_change_request(
        self,
        change_sys_id: str,
        state: int | None = None,
        work_notes: str | None = None,
        close_notes: str | None = None,
    ) -> ChangeRequestResult:
        """Update an existing change request.

        Args:
            change_sys_id: Change request sys_id
            state: New state (-5=New, 0=Assess, 1=Authorize, 2=Scheduled, 3=Implement, 4=Review, 6=Closed)
            work_notes: Work notes to add
            close_notes: Closing notes (when closing)

        Returns:
            ChangeRequestResult with update status
        """
        try:
            update_data = {}

            if state is not None:
                update_data["state"] = str(state)

            if work_notes:
                update_data["work_notes"] = work_notes

            if close_notes:
                update_data["close_notes"] = close_notes

            result = self._request(
                "PATCH",
                f"/api/now/table/change_request/{change_sys_id}",
                json_data=update_data,
            )

            change = result["result"]

            return ChangeRequestResult(
                success=True,
                change_number=change.get("number"),
                change_sys_id=change.get("sys_id"),
                message=f"Updated change request {change.get('number')}",
            )

        except Exception as e:
            logger.exception("Failed to update ServiceNow change request")
            return ChangeRequestResult(
                success=False,
                message="Failed to update change request",
                error=str(e),
            )
