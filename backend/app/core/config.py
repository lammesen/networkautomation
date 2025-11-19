from __future__ import annotations

import secrets
from functools import lru_cache
from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "NetAuto"
    api_prefix: str = "/api"
    database_url: str = Field(
        "sqlite:///./netauto.db", env="DATABASE_URL"
    )
    secret_key: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    access_token_expire_minutes: int = 30
    refresh_token_expire_minutes: int = 60 * 24
    redis_url: str = Field("redis://redis:6379/0", env="REDIS_URL")
    celery_broker_url: str = Field("redis://redis:6379/1", env="CELERY_BROKER_URL")
    celery_result_backend: str = Field(
        "redis://redis:6379/2", env="CELERY_RESULT_BACKEND"
    )
    log_level: str = Field("INFO", env="LOG_LEVEL")
    dry_run_mode: bool = Field(True, env="DRY_RUN_MODE")
    execute_jobs_inline: bool = Field(True, env="EXECUTE_JOBS_INLINE")
    websocket_redis_channel_prefix: str = Field(
        "job-log", env="WS_REDIS_CHANNEL_PREFIX"
    )

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
