"""Device and credential service layer."""

from __future__ import annotations

import ipaddress
from typing import Dict, Iterable, Sequence

from sqlalchemy.orm import Session

from app.db import Credential, CustomerIPRange, Device
from app.domain.context import TenantRequestContext
from app.domain.devices import DeviceFilters
from app.domain.exceptions import (
    ConflictError,
    DuplicateHostnameError,
    NotFoundError,
    ValidationError,
)
from app.repositories import (
    CredentialRepository,
    CustomerIPRangeRepository,
    DeviceRepository,
)


class DeviceService:
    """Business logic for device lifecycle operations."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.devices = DeviceRepository(session)
        self.credentials = CredentialRepository(session)
        self.ip_ranges = CustomerIPRangeRepository(session)

    # -------------------------------------------------------------------------
    # Queries

    def list_devices(
        self,
        filters: DeviceFilters,
        context: TenantRequestContext,
    ) -> tuple[int, Sequence[Device]]:
        return self.devices.list_for_customer(context.customer_id, filters)

    def get_device(self, device_id: int, context: TenantRequestContext) -> Device:
        device = self.devices.get_by_id(device_id, context.customer_id)
        if not device:
            raise NotFoundError("Device not found")
        return device

    # -------------------------------------------------------------------------
    # Mutations

    def create_device(
        self,
        payload,
        context: TenantRequestContext,
    ) -> Device:
        target_customer_id = self._resolve_customer_for_ip(
            payload.mgmt_ip, context.customer_id
        )
        context.assert_customer_access(target_customer_id)

        self._ensure_hostname_unique(
            hostname=payload.hostname,
            customer_id=target_customer_id,
        )

        credential = self._get_credential_for_customer(
            credential_id=payload.credentials_ref,
            customer_id=target_customer_id,
        )

        device = Device(
            **payload.model_dump(),
            customer_id=target_customer_id,
        )
        device.credentials_ref = credential.id

        self.session.add(device)
        self.session.commit()
        self.session.refresh(device)
        return device

    def update_device(
        self,
        device_id: int,
        payload,
        context: TenantRequestContext,
    ) -> Device:
        device = self.get_device(device_id, context)
        update_data = payload.model_dump(exclude_unset=True)

        if "hostname" in update_data:
            self._ensure_hostname_unique(
                hostname=update_data["hostname"],
                customer_id=context.customer_id,
                exclude_id=device_id,
            )

        if "credentials_ref" in update_data:
            self._get_credential_for_customer(
                credential_id=update_data["credentials_ref"],
                customer_id=context.customer_id,
            )

        for key, value in update_data.items():
            setattr(device, key, value)

        self.session.commit()
        self.session.refresh(device)
        return device

    def disable_device(self, device_id: int, context: TenantRequestContext) -> None:
        device = self.get_device(device_id, context)
        device.enabled = False
        self.session.commit()

    def import_devices(
        self,
        rows: Iterable[Dict[str, str]],
        context: TenantRequestContext,
    ) -> Dict[str, object]:
        ranges = list(self.ip_ranges.list_all())
        summary = {
            "created": 0,
            "skipped": 0,
            "failed": 0,
            "errors": [],
        }

        for idx, row in enumerate(rows, start=1):
            try:
                self._process_import_row(row, ranges, context)
                summary["created"] += 1
            except DuplicateHostnameError:
                summary["skipped"] += 1
            except ConflictError as exc:
                summary["skipped"] += 1
                summary["errors"].append(f"Row {idx}: {exc.message}")
            except ValidationError as exc:
                summary["failed"] += 1
                summary["errors"].append(f"Row {idx}: {exc.message}")
            except Exception as exc:  # pragma: no cover - safeguard
                summary["failed"] += 1
                summary["errors"].append(f"Row {idx}: {exc}")

        self.session.commit()
        return summary

    # -------------------------------------------------------------------------
    # Internal helpers

    def _ensure_hostname_unique(
        self,
        *,
        hostname: str,
        customer_id: int,
        exclude_id: int | None = None,
    ) -> None:
        if self.devices.find_by_hostname(
            customer_id=customer_id,
            hostname=hostname,
            exclude_id=exclude_id,
        ):
            raise ConflictError("Device with this hostname already exists for the customer")

    def _get_credential_for_customer(
        self,
        *,
        credential_id: int,
        customer_id: int,
    ) -> Credential:
        credential = self.credentials.get_by_id_for_customer(credential_id, customer_id)
        if not credential:
            raise NotFoundError("Credential not found for the customer")
        return credential

    def _resolve_customer_for_ip(self, ip: str, default_customer_id: int) -> int:
        try:
            device_ip = ipaddress.ip_address(ip)
        except ValueError:
            return default_customer_id

        for ip_range in self.ip_ranges.list_all():
            try:
                network = ipaddress.ip_network(ip_range.cidr)
            except ValueError:
                continue
            if device_ip in network:
                return ip_range.customer_id

        return default_customer_id

    def _process_import_row(
        self,
        row: Dict[str, str],
        ranges: Sequence[CustomerIPRange],
        context: TenantRequestContext,
    ) -> None:
        required = {"hostname", "mgmt_ip", "vendor", "platform", "credential_name"}
        missing = [field for field in required if not row.get(field)]
        if missing:
            raise ValidationError(f"Missing required fields: {', '.join(missing)}")

        target_customer_id = self._resolve_customer_for_ip_from_ranges(
            row["mgmt_ip"],
            ranges,
            context.customer_id,
        )
        context.assert_customer_access(target_customer_id)

        if self.devices.find_by_hostname(target_customer_id, row["hostname"]):
            raise DuplicateHostnameError("Hostname already exists; skipping import row")

        credential = self.credentials.get_by_name_for_customer(
            row["credential_name"],
            target_customer_id,
        )
        if not credential:
            raise ValidationError(
                f"Credential '{row['credential_name']}' not found for target customer {target_customer_id}"
            )

        device = Device(
            hostname=row["hostname"],
            mgmt_ip=row["mgmt_ip"],
            vendor=row["vendor"],
            platform=row["platform"],
            role=row.get("role"),
            site=row.get("site"),
            credentials_ref=credential.id,
            customer_id=target_customer_id,
            enabled=True,
        )
        self.session.add(device)

    def _resolve_customer_for_ip_from_ranges(
        self,
        ip: str,
        ranges: Sequence[CustomerIPRange],
        default_customer_id: int,
    ) -> int:
        try:
            device_ip = ipaddress.ip_address(ip)
        except ValueError:
            return default_customer_id

        for ip_range in ranges:
            try:
                network = ipaddress.ip_network(ip_range.cidr)
            except ValueError:
                continue
            if device_ip in network:
                return ip_range.customer_id

        return default_customer_id


class CredentialService:
    """Business logic for credential CRUD operations."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.credentials = CredentialRepository(session)

    def list_credentials(self, context: TenantRequestContext) -> Sequence[Credential]:
        return self.credentials.list_for_customer(context.customer_id)

    def get_credential(
        self,
        credential_id: int,
        context: TenantRequestContext,
    ) -> Credential:
        credential = self.credentials.get_by_id_for_customer(
            credential_id,
            context.customer_id,
        )
        if not credential:
            raise NotFoundError("Credential not found")
        return credential

    def create_credential(
        self,
        payload,
        context: TenantRequestContext,
    ) -> Credential:
        existing = self.credentials.get_by_name_for_customer(
            payload.name,
            context.customer_id,
        )
        if existing:
            raise ConflictError("Credential with this name already exists for the customer")

        credential = Credential(
            **payload.model_dump(),
            customer_id=context.customer_id,
        )

        self.session.add(credential)
        self.session.commit()
        self.session.refresh(credential)
        return credential


