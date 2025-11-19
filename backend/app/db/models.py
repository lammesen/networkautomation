import enum
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    JSON,
    Boolean,
    Text,
    Enum,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base


class UserRole(enum.Enum):
    viewer = "viewer"
    operator = "operator"
    admin = "admin"


class JobStatus(enum.Enum):
    queued = "queued"
    running = "running"
    success = "success"
    failed = "failed"
    partial_fail = "partial_fail"


class JobType(enum.Enum):
    run_commands = "run_commands"
    config_backup = "config_backup"
    config_deploy_preview = "config_deploy_preview"
    config_deploy_commit = "config_deploy_commit"
    compliance_run = "compliance_run"


class ComplianceStatus(enum.Enum):
    compliant = "compliant"
    non_compliant = "non_compliant"
    error = "error"


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.viewer)


class Credential(Base):
    __tablename__ = "credentials"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    username = Column(String)
    password = Column(String)  # Note: In production, this should be encrypted
    ssh_private_key = Column(Text)  # Note: In production, this should be encrypted


class Device(Base):
    __tablename__ = "devices"
    id = Column(Integer, primary_key=True, index=True)
    hostname = Column(String, unique=True, index=True, nullable=False)
    mgmt_ip = Column(String, unique=True, nullable=False)
    vendor = Column(String, nullable=False)
    platform = Column(String, nullable=False)
    role = Column(String)
    site = Column(String)
    tags = Column(JSON)
    credentials_ref = Column(String, ForeignKey("credentials.name"))
    credential = relationship("Credential")
    enabled = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class Job(Base):
    __tablename__ = "jobs"
    id = Column(Integer, primary_key=True, index=True)
    type = Column(Enum(JobType), nullable=False)
    status = Column(Enum(JobStatus), nullable=False, default=JobStatus.queued)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user = relationship("User")
    requested_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True))
    finished_at = Column(DateTime(timezone=True))
    target_summary_json = Column(JSON)
    result_summary_json = Column(JSON)


class JobLog(Base):
    __tablename__ = "job_logs"
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    job = relationship("Job")
    ts = Column(DateTime(timezone=True), server_default=func.now())
    level = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    host = Column(String)
    extra_json = Column(JSON)


class ConfigSnapshot(Base):
    __tablename__ = "config_snapshots"
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False)
    device = relationship("Device")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    job_id = Column(Integer, ForeignKey("jobs.id"))
    job = relationship("Job")
    source = Column(String)
    config_text = Column(Text, nullable=False)
    hash = Column(String, nullable=False)


class CompliancePolicy(Base):
    __tablename__ = "compliance_policies"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    scope_json = Column(JSON, nullable=False)
    definition_yaml = Column(Text, nullable=False)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_by = relationship("User")


class ComplianceResult(Base):
    __tablename__ = "compliance_results"
    id = Column(Integer, primary_key=True, index=True)
    policy_id = Column(Integer, ForeignKey("compliance_policies.id"), nullable=False)
    policy = relationship("CompliancePolicy")
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False)
    device = relationship("Device")
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    job = relationship("Job")
    ts = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(Enum(ComplianceStatus), nullable=False)
    details_json = Column(JSON)
