from __future__ import annotations

import secrets
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    app_name: str = "NetAuto"
    api_prefix: str = "/api"
    database_url: str = Field("sqlite:///./netauto.db")
    secret_key: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    access_token_expire_minutes: int = 30
    refresh_token_expire_minutes: int = 60 * 24
    redis_url: str = Field("redis://redis:6379/0")
    celery_broker_url: str = Field("redis://redis:6379/1")
    celery_result_backend: str = Field("redis://redis:6379/2")
    celery_backup_schedule_cron: str = Field("0 2 * * *", description="Default daily backup schedule")
    enable_celery_beat: bool = Field(True)
    log_level: str = Field("INFO")
    dry_run_mode: bool = Field(True)
    execute_jobs_inline: bool = Field(True)
    websocket_redis_channel_prefix: str = Field("job-log")
    enable_metrics: bool = Field(True)
    metrics_path: str = Field("/metrics")
    netbox_url: str | None = Field(default=None)
    netbox_token: str | None = Field(default=None)
    netbox_tls_verify: bool = Field(default=True)
    vault_addr: str | None = Field(default=None)
    vault_token: str | None = Field(default=None)
    vault_kv_mount: str = Field("secret")


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
