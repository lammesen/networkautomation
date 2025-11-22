"""Core configuration module."""

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    # API
    api_title: str = "Network Automation API"
    api_version: str = "0.1.0"
    api_prefix: str = "/api/v1"

    # Security
    secret_key: str = "change-me-in-production-use-openssl-rand-hex-32"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

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
    cors_origins: list[str] = [
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
        """Allow comma-separated strings in env to populate list."""
        if isinstance(value, str):
            parts = [origin.strip() for origin in value.split(",") if origin.strip()]
            return parts or ["*"]
        return value


settings = Settings()
