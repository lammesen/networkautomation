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
    testing: bool = os.getenv("TESTING", "false").lower() == "true"

    # Security
    secret_key: str = "change-me-in-production-use-openssl-rand-hex-32"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    admin_default_password: str = os.getenv("ADMIN_DEFAULT_PASSWORD", "Admin123!")

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
    log_format: str | None = None  # "json", "console", or None (auto-detect based on environment)

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
                # If JSON parsing fails, treat as no valid origins; fallback to empty list.
                pass
            return []
        return value

    @field_validator("cors_origins", mode="after")
    @classmethod
    def validate_cors_origins(cls, value: list[str]) -> list[str]:
        """Validate CORS origins for security.

        In production:
        - Rejects empty CORS origins list
        - Rejects wildcard "*" origins
        - Requires all origins to be valid URLs (http:// or https://)
        """
        env = os.getenv("ENVIRONMENT", "development").lower()
        is_production = env == "production"

        # Check for empty origins in production
        if is_production and not value:
            raise ValueError(
                "CORS_ORIGINS must be configured for production deployments. "
                "Set CORS_ORIGINS to a comma-separated list of allowed origins."
            )

        # Validate each origin
        for origin in value:
            # Check for wildcard
            if origin == "*":
                if is_production:
                    raise ValueError(
                        "Wildcard '*' CORS origin is not allowed in production. "
                        "Specify explicit origins instead."
                    )
                # Allow wildcard in development but log a warning
                continue

            # Validate origin format (must be http:// or https://)
            if not origin.startswith(("http://", "https://")):
                raise ValueError(
                    f"Invalid CORS origin '{origin}': must start with http:// or https://"
                )

            # Basic URL validation - check for common mistakes
            if " " in origin:
                raise ValueError(f"Invalid CORS origin '{origin}': contains spaces")

        return value

    @field_validator("database_url")
    @classmethod
    def guard_default_db_credentials(cls, value: str) -> str:
        """Ensure production deployments supply explicit DB credentials."""
        env = os.getenv("ENVIRONMENT", "development").lower()
        if env == "production" and "netauto:netauto" in value:
            raise ValueError("database_url must be provided via environment for production")
        return value

    @field_validator("secret_key")
    @classmethod
    def require_secret_key(cls, value: str) -> str:
        """Reject the placeholder secret in production deployments."""
        env = os.getenv("ENVIRONMENT", "development").lower()
        if env == "production" and value.startswith("change-me"):
            raise ValueError("SECRET_KEY must be set via environment for production")
        return value

    @field_validator("admin_default_password")
    @classmethod
    def require_strong_admin_password(cls, value: str) -> str:
        """Ensure a non-default admin password in production."""
        env = os.getenv("ENVIRONMENT", "development").lower()
        if env == "production" and value == "Admin123!":
            raise ValueError("ADMIN_DEFAULT_PASSWORD must be overridden in production")
        return value

    @field_validator("encryption_key")
    @classmethod
    def require_encryption_key(cls, value: str | None) -> str:
        """Force callers to supply a valid ENCRYPTION_KEY; fail fast otherwise."""
        if not value:
            raise ValueError(
                "ENCRYPTION_KEY must be set to encrypt device credentials.\n"
                'Generate one with: python -c "from cryptography.fernet import Fernet; '
                'print(Fernet.generate_key().decode())"'
            )
        try:
            Fernet(value.encode())
        except Exception:
            raise ValueError(
                "ENCRYPTION_KEY must be a valid base64-encoded Fernet key.\n"
                'Generate one with: python -c "from cryptography.fernet import Fernet; '
                'print(Fernet.generate_key().decode())"'
            )
        return value


settings = Settings()
