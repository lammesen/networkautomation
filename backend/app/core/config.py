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
    log_level: str = Field("INFO")
    dry_run_mode: bool = Field(True)
    execute_jobs_inline: bool = Field(True)
    websocket_redis_channel_prefix: str = Field("job-log")


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
