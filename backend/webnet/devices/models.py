from django.db import models
from webnet.core.crypto import encrypt_text, decrypt_text


class Credential(models.Model):
    customer = models.ForeignKey(
        "customers.Customer", on_delete=models.CASCADE, related_name="credentials"
    )
    name = models.CharField(max_length=100)
    username = models.CharField(max_length=100)
    _password = models.TextField(db_column="password")
    _enable_password = models.TextField(db_column="enable_password", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("customer", "name")
        ordering = ["name"]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.customer_id}:{self.name}"

    @property
    def password(self) -> str | None:
        return decrypt_text(self._password)

    @password.setter
    def password(self, value: str | None) -> None:
        if value is None:
            raise ValueError("Password cannot be None")
        self._password = encrypt_text(value)

    @property
    def enable_password(self) -> str | None:
        return decrypt_text(self._enable_password)

    @enable_password.setter
    def enable_password(self, value: str | None) -> None:
        self._enable_password = encrypt_text(value) if value else ""


class Device(models.Model):
    PROTOCOL_CDP = "cdp"
    PROTOCOL_LLDP = "lldp"
    PROTOCOL_BOTH = "both"

    PROTOCOL_CHOICES = [
        (PROTOCOL_CDP, "CDP only"),
        (PROTOCOL_LLDP, "LLDP only"),
        (PROTOCOL_BOTH, "Both CDP and LLDP"),
    ]

    customer = models.ForeignKey(
        "customers.Customer", on_delete=models.CASCADE, related_name="devices"
    )
    hostname = models.CharField(max_length=255)
    mgmt_ip = models.CharField(max_length=45)
    vendor = models.CharField(max_length=50)
    platform = models.CharField(max_length=50)
    role = models.CharField(max_length=50, blank=True, null=True)
    site = models.CharField(max_length=100, blank=True, null=True)
    tags = models.JSONField(blank=True, null=True)
    credential = models.ForeignKey(Credential, on_delete=models.PROTECT, related_name="devices")
    enabled = models.BooleanField(default=True)
    reachability_status = models.CharField(max_length=20, blank=True, null=True)
    last_reachability_check = models.DateTimeField(blank=True, null=True)
    # Discovery protocol preference for this device
    discovery_protocol = models.CharField(
        max_length=10, choices=PROTOCOL_CHOICES, default=PROTOCOL_BOTH
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("customer", "hostname")
        indexes = [
            models.Index(fields=["role"]),
            models.Index(fields=["site"]),
            models.Index(fields=["vendor"]),
        ]
        ordering = ["hostname"]

    def __str__(self) -> str:  # pragma: no cover
        return self.hostname


class TopologyLink(models.Model):
    customer = models.ForeignKey("customers.Customer", on_delete=models.CASCADE)
    local_device = models.ForeignKey(
        Device, on_delete=models.CASCADE, related_name="outgoing_links"
    )
    local_interface = models.CharField(max_length=100)
    remote_device = models.ForeignKey(
        Device,
        on_delete=models.SET_NULL,
        related_name="incoming_links",
        null=True,
        blank=True,
    )
    remote_hostname = models.CharField(max_length=255)
    remote_interface = models.CharField(max_length=100)
    remote_ip = models.CharField(max_length=45, blank=True, null=True)
    remote_platform = models.CharField(max_length=100, blank=True, null=True)
    protocol = models.CharField(max_length=10, default="lldp")
    discovered_at = models.DateTimeField(auto_now_add=True)
    job_id = models.IntegerField(blank=True, null=True)

    class Meta:
        unique_together = (
            "customer",
            "local_device",
            "local_interface",
            "remote_hostname",
            "remote_interface",
        )
        indexes = [
            models.Index(fields=["local_device"]),
            models.Index(fields=["remote_device"]),
            models.Index(fields=["customer"]),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.local_device_id}:{self.local_interface}->{self.remote_hostname}"


class DiscoveredDevice(models.Model):
    """Discovered but not-yet-added devices from topology discovery.

    Devices discovered via CDP/LLDP that are not in the inventory are
    queued here for review and approval.
    """

    STATUS_PENDING = "pending"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"
    STATUS_IGNORED = "ignored"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending Review"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_REJECTED, "Rejected"),
        (STATUS_IGNORED, "Ignored"),
    ]

    customer = models.ForeignKey(
        "customers.Customer", on_delete=models.CASCADE, related_name="discovered_devices"
    )
    hostname = models.CharField(max_length=255)
    mgmt_ip = models.CharField(max_length=45, blank=True, null=True)
    platform = models.CharField(max_length=100, blank=True, null=True)
    vendor = models.CharField(max_length=50, blank=True, null=True)

    # Discovery metadata
    discovered_via_device = models.ForeignKey(
        Device,
        on_delete=models.SET_NULL,
        related_name="discovered_neighbors",
        null=True,
        blank=True,
    )
    discovered_via_protocol = models.CharField(max_length=10, default="lldp")
    discovered_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now=True)
    job_id = models.IntegerField(blank=True, null=True)

    # Review status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    reviewed_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_discoveries",
    )
    reviewed_at = models.DateTimeField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    # If approved and converted to Device, link here
    created_device = models.ForeignKey(
        Device,
        on_delete=models.SET_NULL,
        related_name="discovery_source",
        null=True,
        blank=True,
    )

    class Meta:
        unique_together = ("customer", "hostname")
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["customer"]),
            models.Index(fields=["discovered_at"]),
        ]
        ordering = ["-discovered_at"]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.hostname} ({self.status})"

    def approve_and_create_device(
        self,
        credential: Credential,
        user: "User",  # type: ignore[name-defined]  # noqa: F821
        vendor: str | None = None,
        platform: str | None = None,
        role: str | None = None,
        site: str | None = None,
    ) -> Device:
        """Approve this discovery and create a Device from it.

        Args:
            credential: Credential to assign to the new device
            user: User performing the approval
            vendor: Device vendor (required if not auto-detected)
            platform: Device platform (uses discovered if not provided)
            role: Optional role for the device
            site: Optional site for the device

        Returns:
            The newly created Device instance

        Raises:
            ValueError: If device was already approved or vendor is missing
        """
        from django.utils import timezone

        # Prevent re-approval which would create duplicate devices
        if self.status == self.STATUS_APPROVED:
            raise ValueError("Device has already been approved")

        if not vendor and not self.vendor:
            raise ValueError("Vendor is required for device creation")

        device = Device.objects.create(
            customer=self.customer,
            hostname=self.hostname,
            mgmt_ip=self.mgmt_ip or "",
            vendor=vendor or self.vendor or "",
            platform=platform or self.platform or "",
            credential=credential,
            role=role,
            site=site,
        )

        self.status = self.STATUS_APPROVED
        self.reviewed_by = user
        self.reviewed_at = timezone.now()
        self.created_device = device
        self.save()

        return device

    def reject(self, user: "User", notes: str | None = None) -> None:  # type: ignore[name-defined]  # noqa: F821,E501
        """Reject this discovered device."""
        from django.utils import timezone

        self.status = self.STATUS_REJECTED
        self.reviewed_by = user
        self.reviewed_at = timezone.now()
        if notes:
            self.notes = notes
        self.save()

    def ignore(self, user: "User", notes: str | None = None) -> None:  # type: ignore[name-defined]  # noqa: F821,E501
        """Mark this discovered device as ignored (e.g., non-network device)."""
        from django.utils import timezone

        self.status = self.STATUS_IGNORED
        self.reviewed_by = user
        self.reviewed_at = timezone.now()
        if notes:
            self.notes = notes
        self.save()
