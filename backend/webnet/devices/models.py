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
