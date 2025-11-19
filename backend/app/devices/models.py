from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Credential(Base):
    __tablename__ = "credentials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    username: Mapped[str] = mapped_column(String(128), nullable=False)
    password: Mapped[str] = mapped_column(String(256), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    devices: Mapped[List["Device"]] = relationship(back_populates="credentials")


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    hostname: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    mgmt_ip: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    vendor: Mapped[Optional[str]] = mapped_column(String(64))
    platform: Mapped[Optional[str]] = mapped_column(String(64))
    role: Mapped[Optional[str]] = mapped_column(String(64))
    site: Mapped[Optional[str]] = mapped_column(String(64))
    tags: Mapped[Optional[str]] = mapped_column(String(256))
    napalm_driver: Mapped[Optional[str]] = mapped_column(String(64))
    netmiko_device_type: Mapped[Optional[str]] = mapped_column(String(64))
    port: Mapped[Optional[int]] = mapped_column(Integer, default=22)
    metadata_json: Mapped[Optional[str]] = mapped_column(Text)
    credentials_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("credentials.id"), nullable=True
    )
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    credentials: Mapped[Optional[Credential]] = relationship(back_populates="devices")
