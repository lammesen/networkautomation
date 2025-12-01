from django.db import models
from django.db.models import Q
from webnet.core.crypto import encrypt_text, decrypt_text


class NetBoxConfig(models.Model):
    """NetBox API configuration for device inventory sync.

    Enables syncing devices from NetBox as the source of truth,
    with configurable field mappings and sync frequency.
    """

    SYNC_FREQUENCY_CHOICES = [
        ("manual", "Manual Only"),
        ("hourly", "Hourly"),
        ("daily", "Daily"),
        ("weekly", "Weekly"),
    ]

    customer = models.OneToOneField(
        "customers.Customer",
        on_delete=models.CASCADE,
        related_name="netbox_config",
        help_text="Customer this NetBox configuration belongs to",
    )
    name = models.CharField(
        max_length=100,
        default="NetBox",
        help_text="Friendly name for this NetBox instance",
    )
    api_url = models.URLField(
        max_length=500,
        help_text="NetBox API URL (e.g., https://netbox.example.com/api)",
    )
    _api_token = models.TextField(
        db_column="api_token",
        blank=False,
        help_text="Encrypted NetBox API token (required)",
    )
    sync_frequency = models.CharField(
        max_length=20,
        choices=SYNC_FREQUENCY_CHOICES,
        default="manual",
        help_text="How often to sync from NetBox",
    )
    enabled = models.BooleanField(
        default=True,
        help_text="Whether automatic sync is enabled",
    )
    # Filter options
    site_filter = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Only sync devices from these NetBox sites (comma-separated slugs)",
    )
    tenant_filter = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Only sync devices from these NetBox tenants (comma-separated slugs)",
    )
    role_filter = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Only sync devices with these roles (comma-separated slugs)",
    )
    status_filter = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        default="active",
        help_text="Device status filter (e.g., 'active', 'staged')",
    )
    # Field mappings
    field_mappings = models.JSONField(
        default=dict,
        blank=True,
        help_text="Custom field mappings from NetBox to webnet (JSON)",
    )
    # Default credential for synced devices
    default_credential = models.ForeignKey(
        "devices.Credential",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="netbox_configs",
        help_text="Default credential to assign to synced devices",
    )
    # Sync status
    last_sync_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Last successful sync timestamp",
    )
    last_sync_status = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Status of last sync attempt (success, failed, partial)",
    )
    last_sync_message = models.TextField(
        blank=True,
        null=True,
        help_text="Message or error from last sync attempt",
    )
    last_sync_stats = models.JSONField(
        default=dict,
        blank=True,
        help_text="Stats from last sync (created, updated, skipped counts)",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "NetBox Configuration"
        verbose_name_plural = "NetBox Configurations"

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.customer.name} - {self.name}"

    @property
    def api_token(self) -> str | None:
        """Decrypt and return the API token."""
        return decrypt_text(self._api_token)

    @api_token.setter
    def api_token(self, value: str | None) -> None:
        """Encrypt and store the API token."""
        if value is None:
            raise ValueError("API token cannot be None")
        self._api_token = encrypt_text(value)

    def has_api_token(self) -> bool:
        """Check if an API token is configured."""
        return bool(self._api_token)

    def get_site_filters(self) -> list[str]:
        """Return list of site slugs to filter by."""
        if not self.site_filter:
            return []
        return [s.strip() for s in self.site_filter.split(",") if s.strip()]

    def get_tenant_filters(self) -> list[str]:
        """Return list of tenant slugs to filter by."""
        if not self.tenant_filter:
            return []
        return [s.strip() for s in self.tenant_filter.split(",") if s.strip()]

    def get_role_filters(self) -> list[str]:
        """Return list of role slugs to filter by."""
        if not self.role_filter:
            return []
        return [s.strip() for s in self.role_filter.split(",") if s.strip()]


class NetBoxSyncLog(models.Model):
    """Log of NetBox sync operations for audit trail."""

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("running", "Running"),
        ("success", "Success"),
        ("partial", "Partial Success"),
        ("failed", "Failed"),
    ]

    config = models.ForeignKey(
        NetBoxConfig,
        on_delete=models.CASCADE,
        related_name="sync_logs",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
    )
    devices_created = models.IntegerField(default=0)
    devices_updated = models.IntegerField(default=0)
    devices_skipped = models.IntegerField(default=0)
    devices_failed = models.IntegerField(default=0)
    message = models.TextField(
        blank=True,
        null=True,
        help_text="Summary message or error details",
    )
    details = models.JSONField(
        default=dict,
        blank=True,
        help_text="Detailed sync results per device",
    )
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(
        blank=True,
        null=True,
    )

    class Meta:
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["config"]),
            models.Index(fields=["status"]),
            models.Index(fields=["started_at"]),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"Sync {self.id} for {self.config_id} - {self.status}"


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


class Tag(models.Model):
    """Customer-scoped tag for organizing devices.

    Tags allow flexible grouping of devices beyond the basic site/role/vendor fields.
    Examples: "pci-scope", "maintenance-window-saturday", "legacy-devices"
    """

    customer = models.ForeignKey(
        "customers.Customer", on_delete=models.CASCADE, related_name="tags"
    )
    name = models.CharField(max_length=50)
    color = models.CharField(
        max_length=7, default="#3B82F6", help_text="Hex color code (e.g., #3B82F6)"
    )
    description = models.TextField(blank=True, null=True)
    category = models.CharField(
        max_length=50, blank=True, null=True, help_text="Optional tag category for grouping"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("customer", "name")
        ordering = ["category", "name"]
        indexes = [
            models.Index(fields=["customer"]),
            models.Index(fields=["category"]),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.name}"


class DeviceGroup(models.Model):
    """Customer-scoped device group for organizing and targeting devices.

    Supports both static (explicit device list) and dynamic (filter-based) membership.
    Can be used for maintenance windows, job targeting, and compliance scoping.
    """

    TYPE_STATIC = "static"
    TYPE_DYNAMIC = "dynamic"

    TYPE_CHOICES = [
        (TYPE_STATIC, "Static (explicit device list)"),
        (TYPE_DYNAMIC, "Dynamic (filter-based)"),
    ]

    customer = models.ForeignKey(
        "customers.Customer", on_delete=models.CASCADE, related_name="device_groups"
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    group_type = models.CharField(max_length=10, choices=TYPE_CHOICES, default=TYPE_STATIC)

    # Static membership - M2M relationship to devices
    devices = models.ManyToManyField("Device", blank=True, related_name="static_groups")

    # Dynamic membership - JSON filter rules
    # Example: {"vendor": "cisco", "site": "datacenter-1", "tags": ["production"]}
    filter_rules = models.JSONField(blank=True, null=True)

    # Nested groups support
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True, related_name="children"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("customer", "name")
        ordering = ["name"]
        indexes = [
            models.Index(fields=["customer"]),
            models.Index(fields=["group_type"]),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.name} ({self.group_type})"

    def get_devices(self) -> models.QuerySet["Device"]:
        """Get all devices in this group (static or dynamic).

        For static groups, returns explicitly assigned devices.
        For dynamic groups, evaluates filter rules against customer devices.
        """
        if self.group_type == self.TYPE_STATIC:
            return self.devices.all()

        # Dynamic group - apply filter rules
        qs = Device.objects.filter(customer=self.customer, enabled=True)
        if not self.filter_rules:
            return qs

        rules = self.filter_rules
        if rules.get("vendor"):
            qs = qs.filter(vendor__iexact=rules["vendor"])
        if rules.get("platform"):
            qs = qs.filter(platform__iexact=rules["platform"])
        if rules.get("site"):
            qs = qs.filter(site__iexact=rules["site"])
        if rules.get("role"):
            qs = qs.filter(role__iexact=rules["role"])
        if rules.get("tags"):
            tag_names = rules["tags"]
            qs = qs.filter(device_tags__name__in=tag_names)
        if rules.get("hostname_contains"):
            qs = qs.filter(hostname__icontains=rules["hostname_contains"])

        return qs.distinct()

    @property
    def device_count(self) -> int:
        """Get the number of devices in this group."""
        return self.get_devices().count()


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
    tags = models.JSONField(blank=True, null=True)  # Legacy JSON tags field
    credential = models.ForeignKey(Credential, on_delete=models.PROTECT, related_name="devices")
    enabled = models.BooleanField(default=True)
    reachability_status = models.CharField(max_length=20, blank=True, null=True)
    last_reachability_check = models.DateTimeField(blank=True, null=True)
    # Discovery protocol preference for this device
    discovery_protocol = models.CharField(
        max_length=10, choices=PROTOCOL_CHOICES, default=PROTOCOL_BOTH
    )

    # Tag relationship (Issue #24)
    device_tags = models.ManyToManyField(Tag, blank=True, related_name="devices")

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


class SSHHostKey(models.Model):
    """SSH host key for device authentication and MITM prevention.

    Implements Trust On First Use (TOFU) pattern for SSH host key verification.
    Keys can be manually verified by operators to indicate trust.
    """

    KEY_TYPE_RSA = "ssh-rsa"
    KEY_TYPE_ECDSA_256 = "ecdsa-sha2-nistp256"
    KEY_TYPE_ECDSA_384 = "ecdsa-sha2-nistp384"
    KEY_TYPE_ECDSA_521 = "ecdsa-sha2-nistp521"
    KEY_TYPE_ED25519 = "ssh-ed25519"

    KEY_TYPE_CHOICES = [
        (KEY_TYPE_RSA, "RSA"),
        (KEY_TYPE_ECDSA_256, "ECDSA P-256"),
        (KEY_TYPE_ECDSA_384, "ECDSA P-384"),
        (KEY_TYPE_ECDSA_521, "ECDSA P-521"),
        (KEY_TYPE_ED25519, "Ed25519"),
    ]

    device = models.ForeignKey(
        Device,
        on_delete=models.CASCADE,
        related_name="ssh_host_keys",
        help_text="Device this host key belongs to",
    )
    key_type = models.CharField(
        max_length=30,
        choices=KEY_TYPE_CHOICES,
        help_text="SSH key algorithm type",
    )
    public_key = models.TextField(
        help_text="Base64-encoded public key data",
    )
    fingerprint_sha256 = models.CharField(
        max_length=64,
        help_text="SHA256 fingerprint of the public key",
    )
    first_seen_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this key was first seen",
    )
    last_seen_at = models.DateTimeField(
        auto_now=True,
        help_text="When this key was last seen",
    )
    verified = models.BooleanField(
        default=False,
        help_text="Whether this key has been manually verified by an operator",
    )
    verified_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="verified_host_keys",
        help_text="User who verified this key",
    )
    verified_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this key was verified",
    )

    class Meta:
        unique_together = ("device", "key_type", "fingerprint_sha256")
        ordering = ["-verified", "-first_seen_at"]
        indexes = [
            models.Index(fields=["device"]),
            models.Index(fields=["fingerprint_sha256"]),
            models.Index(fields=["verified"]),
        ]

    def __str__(self) -> str:  # pragma: no cover
        status = "verified" if self.verified else "unverified"
        return f"{self.device.hostname} - {self.key_type} ({status})"

    @property
    def fingerprint_display(self) -> str:
        """Return fingerprint in human-readable format (SHA256:base64)."""
        return f"SHA256:{self.fingerprint_sha256}"


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
    """Discovered but not-yet-added devices from topology discovery or bulk scanning.

    Devices discovered via CDP/LLDP, IP range scanning, or SNMP discovery that are
    not in the inventory are queued here for review and approval.
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

    SOURCE_TOPOLOGY = "topology"
    SOURCE_IP_SCAN = "ip_scan"
    SOURCE_SNMP = "snmp"
    SOURCE_MANUAL = "manual"

    SOURCE_CHOICES = [
        (SOURCE_TOPOLOGY, "CDP/LLDP Topology Discovery"),
        (SOURCE_IP_SCAN, "IP Range Scan"),
        (SOURCE_SNMP, "SNMP Discovery"),
        (SOURCE_MANUAL, "Manual Entry"),
    ]

    customer = models.ForeignKey(
        "customers.Customer", on_delete=models.CASCADE, related_name="discovered_devices"
    )
    hostname = models.CharField(max_length=255)
    mgmt_ip = models.CharField(max_length=45, blank=True, null=True)
    platform = models.CharField(max_length=100, blank=True, null=True)
    vendor = models.CharField(max_length=50, blank=True, null=True)

    # Enhanced discovery fields (Issue #40)
    serial_number = models.CharField(max_length=100, blank=True, null=True)
    software_version = models.CharField(max_length=100, blank=True, null=True)
    interfaces_json = models.JSONField(
        blank=True, null=True, help_text="Discovered interfaces as JSON list"
    )
    discovery_source = models.CharField(
        max_length=20, choices=SOURCE_CHOICES, default=SOURCE_TOPOLOGY
    )

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

    # Credential testing results (Issue #40)
    credential_tested = models.ForeignKey(
        Credential,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tested_discoveries",
        help_text="Last credential successfully tested",
    )
    credential_test_status = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Result of credential testing: success, failed, untested",
    )

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
            models.Index(fields=["discovery_source"]),
            models.Index(fields=["mgmt_ip"]),
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

    @classmethod
    def check_duplicate(cls, customer_id: int, hostname: str, mgmt_ip: str | None) -> bool:
        """Check if a device with this hostname or IP already exists.

        Returns True if duplicate exists in either Device or DiscoveredDevice tables.
        """
        # Check existing devices
        if Device.objects.filter(customer_id=customer_id, hostname=hostname).exists():
            return True
        if mgmt_ip and Device.objects.filter(customer_id=customer_id, mgmt_ip=mgmt_ip).exists():
            return True

        # Check pending discoveries
        pending_q = Q(customer_id=customer_id, status=cls.STATUS_PENDING)
        if cls.objects.filter(pending_q, hostname=hostname).exists():
            return True
        if mgmt_ip and cls.objects.filter(pending_q, mgmt_ip=mgmt_ip).exists():
            return True

        return False
