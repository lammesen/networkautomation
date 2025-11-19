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
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all models."""

    pass


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


class Credential(Base):
    """Credential model for device authentication."""

    __tablename__ = "credentials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    username: Mapped[str] = mapped_column(String(100), nullable=False)
    password: Mapped[str] = mapped_column(String(255), nullable=False)  # Should be encrypted
    enable_password: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    devices: Mapped[list["Device"]] = relationship("Device", back_populates="credential")


class Device(Base):
    """Device model."""

    __tablename__ = "devices"
    __table_args__ = (
        Index("ix_devices_role", "role"),
        Index("ix_devices_site", "site"),
        Index("ix_devices_vendor", "vendor"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    hostname: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
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


class Job(Base):
    """Job model."""

    __tablename__ = "jobs"
    __table_args__ = (
        Index("ix_jobs_status", "status"),
        Index("ix_jobs_type", "type"),
        Index("ix_jobs_user_id", "user_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # run_commands, config_backup, config_deploy, compliance
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="queued"
    )  # queued, running, success, partial, failed
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    requested_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    target_summary_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    result_summary_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    payload_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="jobs")
    logs: Mapped[list["JobLog"]] = relationship("JobLog", back_populates="job")


class JobLog(Base):
    """Job log model."""

    __tablename__ = "job_logs"
    __table_args__ = (Index("ix_job_logs_job_id", "job_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    job_id: Mapped[int] = mapped_column(Integer, ForeignKey("jobs.id"), nullable=False)
    ts: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    level: Mapped[str] = mapped_column(
        String(10), nullable=False
    )  # INFO, WARN, ERROR, DEBUG
    host: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    extra_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Relationships
    job: Mapped["Job"] = relationship("Job", back_populates="logs")


class ConfigSnapshot(Base):
    """Configuration snapshot model."""

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

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    scope_json: Mapped[dict] = mapped_column(
        JSON, nullable=False
    )  # Filters for device selection
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


class ComplianceResult(Base):
    """Compliance result model."""

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
    status: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # pass, fail, error
    details_json: Mapped[dict] = mapped_column(JSON, nullable=False)

    # Relationships
    policy: Mapped["CompliancePolicy"] = relationship(
        "CompliancePolicy", back_populates="results"
    )
    device: Mapped["Device"] = relationship("Device", back_populates="compliance_results")
