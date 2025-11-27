"""Database models."""

from datetime import datetime
from typing import Optional
from sqlalchemy import (
    String,
    Integer,
    DateTime,
    Boolean,
    Text,
    JSON,
    ForeignKey,
    Index,
    Table,
    UniqueConstraint,
    Column,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.core.crypto import decrypt_text, encrypt_text


class Base(DeclarativeBase):
    """Base class for all models."""

    pass


# Association table for User <-> Customer
user_customers = Table(
    "user_customers",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("customer_id", Integer, ForeignKey("customers.id"), primary_key=True),
)


class Customer(Base):
    """Customer (Tenant) model."""

    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    users: Mapped[list["User"]] = relationship(
        "User", secondary=user_customers, back_populates="customers"
    )
    devices: Mapped[list["Device"]] = relationship("Device", back_populates="customer")
    credentials: Mapped[list["Credential"]] = relationship("Credential", back_populates="customer")
    jobs: Mapped[list["Job"]] = relationship("Job", back_populates="customer")
    compliance_policies: Mapped[list["CompliancePolicy"]] = relationship(
        "CompliancePolicy", back_populates="customer"
    )
    ip_ranges: Mapped[list["CustomerIPRange"]] = relationship(
        "CustomerIPRange", back_populates="customer"
    )


class CustomerIPRange(Base):
    """Customer IP Range model for auto-assignment."""

    __tablename__ = "customer_ip_ranges"
    __table_args__ = (Index("ix_customer_ip_ranges_customer_id", "customer_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    customer_id: Mapped[int] = mapped_column(Integer, ForeignKey("customers.id"), nullable=False)
    cidr: Mapped[str] = mapped_column(String(45), nullable=False)  # e.g., "10.0.0.0/24"
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    customer: Mapped["Customer"] = relationship("Customer", back_populates="ip_ranges")


class User(Base):
    """User model."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(
        String(20), nullable=False, default="viewer"
    )  # viewer, operator, admin
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    jobs: Mapped[list["Job"]] = relationship("Job", back_populates="user")
    customers: Mapped[list["Customer"]] = relationship(
        "Customer", secondary=user_customers, back_populates="users"
    )
    api_keys: Mapped[list["APIKey"]] = relationship("APIKey", back_populates="user")


class APIKey(Base):
    """API Key model for automation scripts and programmatic access."""

    __tablename__ = "api_keys"
    __table_args__ = (
        Index("ix_api_keys_user_id", "user_id"),
        Index("ix_api_keys_key_hash", "key_hash"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    key_prefix: Mapped[str] = mapped_column(String(8), nullable=False)  # First 8 chars for display
    key_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)  # SHA-256 hash
    scopes: Mapped[Optional[dict]] = mapped_column(
        JSON, nullable=True
    )  # Optional scope restrictions
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="api_keys")


class Credential(Base):
    """Credential model for device authentication."""

    __tablename__ = "credentials"
    __table_args__ = (UniqueConstraint("customer_id", "name", name="uix_credential_customer_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    customer_id: Mapped[int] = mapped_column(Integer, ForeignKey("customers.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    username: Mapped[str] = mapped_column(String(100), nullable=False)
    _password: Mapped[str] = mapped_column("password", String(255), nullable=False)
    _enable_password: Mapped[Optional[str]] = mapped_column(
        "enable_password",
        String(255),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    devices: Mapped[list["Device"]] = relationship("Device", back_populates="credential")
    customer: Mapped["Customer"] = relationship("Customer", back_populates="credentials")

    @property
    def password(self) -> Optional[str]:
        return decrypt_text(self._password) if self._password else None

    @password.setter
    def password(self, value: str) -> None:
        if value is None:
            raise ValueError("Password cannot be None.")
        self._password = encrypt_text(value)

    @property
    def enable_password(self) -> Optional[str]:
        return decrypt_text(self._enable_password)

    @enable_password.setter
    def enable_password(self, value: Optional[str]) -> None:
        self._enable_password = encrypt_text(value)

    def to_dict(self) -> dict:
        """Serialize Credential without exposing sensitive password fields."""
        return {
            "id": self.id,
            "customer_id": self.customer_id,
            "name": self.name,
            "username": self.username,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Device(Base):
    """Device model."""

    __tablename__ = "devices"
    __table_args__ = (
        Index("ix_devices_role", "role"),
        Index("ix_devices_site", "site"),
        Index("ix_devices_vendor", "vendor"),
        UniqueConstraint("customer_id", "hostname", name="uix_device_customer_hostname"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    customer_id: Mapped[int] = mapped_column(Integer, ForeignKey("customers.id"), nullable=False)
    hostname: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    mgmt_ip: Mapped[str] = mapped_column(String(45), nullable=False)  # Support IPv6
    vendor: Mapped[str] = mapped_column(String(50), nullable=False)
    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    role: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    site: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    tags: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    credentials_ref: Mapped[int] = mapped_column(
        Integer, ForeignKey("credentials.id"), nullable=False
    )
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    reachability_status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    last_reachability_check: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    credential: Mapped["Credential"] = relationship("Credential", back_populates="devices")
    config_snapshots: Mapped[list["ConfigSnapshot"]] = relationship(
        "ConfigSnapshot", back_populates="device"
    )
    compliance_results: Mapped[list["ComplianceResult"]] = relationship(
        "ComplianceResult", back_populates="device"
    )
    customer: Mapped["Customer"] = relationship("Customer", back_populates="devices")


class Job(Base):
    """Job model."""

    __tablename__ = "jobs"
    __table_args__ = (
        Index("ix_jobs_status", "status"),
        Index("ix_jobs_type", "type"),
        Index("ix_jobs_user_id", "user_id"),
        Index("ix_jobs_customer_id", "customer_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    customer_id: Mapped[int] = mapped_column(Integer, ForeignKey("customers.id"), nullable=False)
    type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # run_commands, config_backup, config_deploy, compliance
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="queued"
    )  # queued, scheduled, running, success, partial, failed
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    requested_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    scheduled_for: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    target_summary_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    result_summary_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    payload_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="jobs")
    logs: Mapped[list["JobLog"]] = relationship("JobLog", back_populates="job")
    customer: Mapped["Customer"] = relationship("Customer", back_populates="jobs")


class JobLog(Base):
    """Job log model."""

    # ... unchanged ...
    __tablename__ = "job_logs"
    __table_args__ = (Index("ix_job_logs_job_id", "job_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    job_id: Mapped[int] = mapped_column(Integer, ForeignKey("jobs.id"), nullable=False)
    ts: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    level: Mapped[str] = mapped_column(String(10), nullable=False)  # INFO, WARN, ERROR, DEBUG
    host: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    extra_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Relationships
    job: Mapped["Job"] = relationship("Job", back_populates="logs")


class ConfigSnapshot(Base):
    """Configuration snapshot model."""

    # ... unchanged ...
    __tablename__ = "config_snapshots"
    __table_args__ = (
        Index("ix_config_snapshots_device_id", "device_id"),
        Index("ix_config_snapshots_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    device_id: Mapped[int] = mapped_column(Integer, ForeignKey("devices.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    job_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("jobs.id"), nullable=True)
    source: Mapped[str] = mapped_column(
        String(50), nullable=False, default="manual"
    )  # manual, scheduled
    config_text: Mapped[str] = mapped_column(Text, nullable=False)
    hash: Mapped[str] = mapped_column(String(64), nullable=False)

    # Relationships
    device: Mapped["Device"] = relationship("Device", back_populates="config_snapshots")


class CompliancePolicy(Base):
    """Compliance policy model."""

    __tablename__ = "compliance_policies"
    __table_args__ = (UniqueConstraint("customer_id", "name", name="uix_policy_customer_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    customer_id: Mapped[int] = mapped_column(Integer, ForeignKey("customers.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    scope_json: Mapped[dict] = mapped_column(JSON, nullable=False)  # Filters for device selection
    definition_yaml: Mapped[str] = mapped_column(Text, nullable=False)  # NAPALM validation YAML
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    results: Mapped[list["ComplianceResult"]] = relationship(
        "ComplianceResult", back_populates="policy"
    )
    customer: Mapped["Customer"] = relationship("Customer", back_populates="compliance_policies")


class ComplianceResult(Base):
    """Compliance result model."""

    # ... unchanged ...
    __tablename__ = "compliance_results"
    __table_args__ = (
        Index("ix_compliance_results_policy_id", "policy_id"),
        Index("ix_compliance_results_device_id", "device_id"),
        Index("ix_compliance_results_ts", "ts"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    policy_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("compliance_policies.id"), nullable=False
    )
    device_id: Mapped[int] = mapped_column(Integer, ForeignKey("devices.id"), nullable=False)
    job_id: Mapped[int] = mapped_column(Integer, ForeignKey("jobs.id"), nullable=False)
    ts: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # pass, fail, error
    details_json: Mapped[dict] = mapped_column(JSON, nullable=False)

    # Relationships
    policy: Mapped["CompliancePolicy"] = relationship("CompliancePolicy", back_populates="results")
    device: Mapped["Device"] = relationship("Device", back_populates="compliance_results")


class TopologyLink(Base):
    """Network topology link discovered via CDP/LLDP."""

    __tablename__ = "topology_links"
    __table_args__ = (
        Index("ix_topology_links_local_device_id", "local_device_id"),
        Index("ix_topology_links_remote_device_id", "remote_device_id"),
        Index("ix_topology_links_customer_id", "customer_id"),
        UniqueConstraint(
            "customer_id",
            "local_device_id",
            "local_interface",
            "remote_device_id",
            "remote_interface",
            name="uix_topology_link",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    customer_id: Mapped[int] = mapped_column(Integer, ForeignKey("customers.id"), nullable=False)

    # Local side (our device)
    local_device_id: Mapped[int] = mapped_column(Integer, ForeignKey("devices.id"), nullable=False)
    local_interface: Mapped[str] = mapped_column(String(100), nullable=False)

    # Remote side (neighbor)
    remote_device_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("devices.id"), nullable=True
    )  # May be null if neighbor not in inventory
    remote_hostname: Mapped[str] = mapped_column(String(255), nullable=False)
    remote_interface: Mapped[str] = mapped_column(String(100), nullable=False)
    remote_ip: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    remote_platform: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Discovery metadata
    protocol: Mapped[str] = mapped_column(String(10), nullable=False)  # cdp, lldp
    discovered_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    job_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("jobs.id"), nullable=True)

    # Relationships
    local_device: Mapped["Device"] = relationship(
        "Device", foreign_keys=[local_device_id], backref="outgoing_links"
    )
    remote_device: Mapped[Optional["Device"]] = relationship(
        "Device", foreign_keys=[remote_device_id], backref="incoming_links"
    )
    customer: Mapped["Customer"] = relationship("Customer")
