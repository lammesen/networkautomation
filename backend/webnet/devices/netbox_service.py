"""NetBox integration service for device inventory sync.

This service handles syncing devices from NetBox to webnet,
with support for field mapping and conflict detection.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import httpx
from django.utils import timezone

from webnet.devices.models import Device, NetBoxConfig, NetBoxSyncLog

logger = logging.getLogger(__name__)


@dataclass
class ConnectionTestResult:
    """Result of a NetBox connection test."""

    success: bool
    message: str
    netbox_version: str | None = None
    error: str | None = None


@dataclass
class SyncPreviewResult:
    """Result of a sync preview operation."""

    devices: list[dict[str, Any]]
    total: int
    would_create: int
    would_update: int


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


class NetBoxService:
    """Service for interacting with NetBox API.

    Handles device synchronization, connection testing, and preview operations.
    """

    # Default field mappings from NetBox to webnet Device model
    DEFAULT_FIELD_MAPPINGS = {
        "hostname": "name",  # NetBox device.name -> webnet device.hostname
        "mgmt_ip": "primary_ip4.address",  # NetBox primary_ip4 -> mgmt_ip (strip CIDR)
        "vendor": "device_type.manufacturer.name",
        "platform": "platform.name",
        "role": "role.name",
        "site": "site.name",
    }

    def __init__(self, config: NetBoxConfig):
        self.config = config
        self.api_url = config.api_url.rstrip("/")
        self.headers = {
            "Authorization": f"Token {config.api_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        # Merge custom field mappings with defaults
        self.field_mappings = {**self.DEFAULT_FIELD_MAPPINGS}
        if config.field_mappings:
            self.field_mappings.update(config.field_mappings)

    def _get(self, endpoint: str, params: dict | None = None) -> dict[str, Any]:
        """Make a GET request to NetBox API."""
        url = f"{self.api_url}/{endpoint.lstrip('/')}"
        with httpx.Client(timeout=30) as client:
            response = client.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()

    def test_connection(self) -> ConnectionTestResult:
        """Test the connection to NetBox API."""
        try:
            # Try to get the API root which should return version info
            result = self._get("/")
            version = result.get("x-ntc-nautobot-version") or result.get("version")

            # If no version in root, try status endpoint (fallback for different NetBox versions)
            if not version:
                try:
                    status = self._get("/status/")
                    version = status.get("netbox-version")
                except Exception:
                    # Status endpoint may not exist in all NetBox versions; version is optional
                    pass

            return ConnectionTestResult(
                success=True,
                message="Successfully connected to NetBox",
                netbox_version=version,
            )
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                return ConnectionTestResult(
                    success=False,
                    message="Authentication failed - check API token",
                    error=str(e),
                )
            elif e.response.status_code == 403:
                return ConnectionTestResult(
                    success=False,
                    message="Access forbidden - check API token permissions",
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
                message="Failed to connect - check API URL",
                error=str(e),
            )
        except Exception as e:
            logger.exception("NetBox connection test failed")
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

    def _map_device(self, nb_device: dict) -> dict[str, Any]:
        """Map a NetBox device to webnet device fields."""
        mapped = {}

        for webnet_field, nb_path in self.field_mappings.items():
            value = self._get_nested_value(nb_device, nb_path)
            if value is not None:
                # Special handling for mgmt_ip (strip CIDR notation)
                if webnet_field == "mgmt_ip" and value and "/" in str(value):
                    value = str(value).split("/")[0]
                mapped[webnet_field] = value

        # Add NetBox ID as a tag for tracking
        mapped["netbox_id"] = nb_device.get("id")
        mapped["netbox_url"] = nb_device.get("url")

        return mapped

    def _build_filters(self) -> dict[str, str]:
        """Build query filters from config."""
        params: dict[str, str] = {}

        # Status filter
        if self.config.status_filter:
            params["status"] = self.config.status_filter

        # Site filter
        sites = self.config.get_site_filters()
        if sites:
            params["site"] = ",".join(sites)

        # Tenant filter
        tenants = self.config.get_tenant_filters()
        if tenants:
            params["tenant"] = ",".join(tenants)

        # Role filter
        roles = self.config.get_role_filters()
        if roles:
            params["role"] = ",".join(roles)

        return params

    def fetch_devices(self) -> list[dict[str, Any]]:
        """Fetch devices from NetBox with configured filters."""
        devices = []
        params = self._build_filters()
        params["limit"] = "100"  # Pagination limit
        offset = 0

        while True:
            params["offset"] = str(offset)
            result = self._get("/dcim/devices/", params=params)
            results = result.get("results", [])
            devices.extend(results)

            # Check if there are more pages
            if result.get("next"):
                offset += len(results)
            else:
                break

        return devices

    def preview_sync(self) -> SyncPreviewResult:
        """Preview what devices would be synced."""
        nb_devices = self.fetch_devices()

        # Get existing devices by hostname
        existing = {d.hostname: d for d in Device.objects.filter(customer=self.config.customer)}

        preview_devices = []
        would_create = 0
        would_update = 0

        for nb_device in nb_devices:
            mapped = self._map_device(nb_device)
            hostname = mapped.get("hostname")
            if not hostname:
                continue

            preview_device = {
                "hostname": hostname,
                "netbox_id": mapped.get("netbox_id"),
                "mgmt_ip": mapped.get("mgmt_ip"),
                "vendor": mapped.get("vendor"),
                "platform": mapped.get("platform"),
                "role": mapped.get("role"),
                "site": mapped.get("site"),
            }

            if hostname in existing:
                preview_device["action"] = "update"
                preview_device["existing_id"] = existing[hostname].id
                would_update += 1
            else:
                preview_device["action"] = "create"
                would_create += 1

            preview_devices.append(preview_device)

        return SyncPreviewResult(
            devices=preview_devices,
            total=len(preview_devices),
            would_create=would_create,
            would_update=would_update,
        )

    def sync_devices(self, full_sync: bool = False) -> SyncResult:
        """Sync devices from NetBox.

        Args:
            full_sync: If True, update all devices. If False, only create new ones.

        Returns:
            SyncResult with counts and details.
        """
        # Create sync log entry
        sync_log = NetBoxSyncLog.objects.create(
            config=self.config,
            status="running",
        )

        created = 0
        updated = 0
        skipped = 0
        failed = 0
        errors: list[str] = []
        details: dict[str, Any] = {"devices": []}

        try:
            nb_devices = self.fetch_devices()

            # Get existing devices by hostname
            existing = {d.hostname: d for d in Device.objects.filter(customer=self.config.customer)}

            for nb_device in nb_devices:
                mapped = self._map_device(nb_device)
                hostname = mapped.get("hostname")

                if not hostname:
                    skipped += 1
                    continue

                try:
                    if hostname in existing:
                        if full_sync:
                            # Update existing device
                            device = existing[hostname]
                            changed = False
                            for field in ["mgmt_ip", "vendor", "platform", "role", "site"]:
                                new_val = mapped.get(field)
                                if new_val and getattr(device, field) != new_val:
                                    setattr(device, field, new_val)
                                    changed = True

                            # Store NetBox ID in tags
                            tags = device.tags or {}
                            tags["netbox_id"] = mapped.get("netbox_id")
                            device.tags = tags

                            if changed:
                                device.save()
                                updated += 1
                                details["devices"].append(
                                    {
                                        "hostname": hostname,
                                        "action": "updated",
                                        "device_id": device.id,
                                    }
                                )
                            else:
                                skipped += 1
                        else:
                            skipped += 1
                    else:
                        # Create new device
                        if not self.config.default_credential:
                            errors.append(
                                f"Cannot create {hostname}: no default credential configured"
                            )
                            failed += 1
                            continue

                        device = Device.objects.create(
                            customer=self.config.customer,
                            hostname=hostname,
                            mgmt_ip=mapped.get("mgmt_ip", ""),
                            vendor=mapped.get("vendor", ""),
                            platform=mapped.get("platform", ""),
                            role=mapped.get("role"),
                            site=mapped.get("site"),
                            credential=self.config.default_credential,
                            tags={"netbox_id": mapped.get("netbox_id")},
                        )
                        created += 1
                        details["devices"].append(
                            {
                                "hostname": hostname,
                                "action": "created",
                                "device_id": device.id,
                            }
                        )

                except Exception as e:
                    failed += 1
                    errors.append(f"Failed to sync {hostname}: {e}")
                    logger.exception("Failed to sync device %s", hostname)

            # Update sync log
            sync_log.status = "success" if not errors else "partial"
            sync_log.devices_created = created
            sync_log.devices_updated = updated
            sync_log.devices_skipped = skipped
            sync_log.devices_failed = failed
            sync_log.message = f"Synced {created} created, {updated} updated, {skipped} skipped"
            sync_log.details = details
            sync_log.finished_at = timezone.now()
            sync_log.save()

            # Update config sync status
            self.config.last_sync_at = timezone.now()
            self.config.last_sync_status = sync_log.status
            self.config.last_sync_message = sync_log.message
            self.config.last_sync_stats = {
                "created": created,
                "updated": updated,
                "skipped": skipped,
                "failed": failed,
            }
            self.config.save()

            return SyncResult(
                success=not errors,
                message=sync_log.message,
                created=created,
                updated=updated,
                skipped=skipped,
                failed=failed,
                errors=errors,
                details=details,
            )

        except Exception as e:
            sync_log.status = "failed"
            sync_log.message = str(e)
            sync_log.finished_at = timezone.now()
            sync_log.save()

            self.config.last_sync_status = "failed"
            self.config.last_sync_message = str(e)
            self.config.save()

            logger.exception("NetBox sync failed for config %s", self.config.id)
            return SyncResult(
                success=False,
                message=f"Sync failed: {e}",
                errors=[str(e)],
            )
