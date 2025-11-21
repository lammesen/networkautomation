"""Core configuration module."""

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
    cors_origins: list[str] = ["*"]


settings = Settings()
