"""Core configuration module."""

import os

from cryptography.fernet import Fernet
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        case_sensitive=False,
        extra="ignore",
    )

    # API
    api_title: str = "Network Automation API"
    api_version: str = "0.1.0"
    api_prefix: str = "/api/v1"
    environment: str = os.getenv("ENVIRONMENT", "development")

    # Security
    secret_key: str = "change-me-in-production-use-openssl-rand-hex-32"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # Encryption
    encryption_key: str | None = None

    # Database
    database_url: str = "postgresql://netauto:netauto@localhost:5432/netauto"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Celery
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    # Logging
    log_level: str = "INFO"

    # CORS
    cors_origins: list[str] | str = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
    ]

    # SSH streaming
    ssh_connect_timeout: float = 10.0
    ssh_command_timeout: float = 60.0
    ssh_keepalive_interval: float = 30.0
    ssh_max_sessions: int = 32

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value):
        """Allow comma-separated strings or JSON-like lists; tolerate empty."""
        if value is None or value == "":
            return []
        if isinstance(value, str):
            # support comma-separated without JSON brackets
            parts = [origin.strip() for origin in value.split(",") if origin.strip()]
            if parts:
                return parts
            # fallback: try JSON parsing (e.g., '["http://..."]')
            import json

            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return parsed
            except Exception:
                pass
            return []
        return value

    @field_validator("cors_origins", mode="after")
    @classmethod
    def restrict_cors_in_production(cls, value):
        """Disallow wildcard CORS in production deployments."""
        env = os.getenv("ENVIRONMENT", "development").lower()
        if env == "production" and value == ["*"]:
            raise ValueError("CORS origins must be configured for production deployments")
        return value

    @field_validator("database_url")
    @classmethod
    def guard_default_db_credentials(cls, value: str) -> str:
        """Ensure production deployments supply explicit DB credentials."""
        env = os.getenv("ENVIRONMENT", "development").lower()
        if env == "production" and "netauto:netauto" in value:
            raise ValueError("database_url must be provided via environment for production")
        return value

    @field_validator("encryption_key")
    @classmethod
    def require_encryption_key(cls, value: str | None) -> str:
        """Force callers to supply a valid ENCRYPTION_KEY; fail fast otherwise."""
        if not value:
            raise ValueError("ENCRYPTION_KEY must be set to encrypt device credentials")
        try:
            Fernet(value.encode())
        except Exception:
            raise ValueError("ENCRYPTION_KEY must be a valid base64-encoded Fernet key")
        return value


settings = Settings()
