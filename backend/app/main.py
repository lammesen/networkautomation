from __future__ import annotations

from fastapi import FastAPI

from app.api import auth, devices, jobs, automation, configs, compliance, ws
from app.core.config import settings
from app.core.logging import setup_logging

setup_logging()
app = FastAPI(title=settings.app_name)
app.include_router(auth.router, prefix=settings.api_prefix)
app.include_router(devices.router, prefix=settings.api_prefix)
app.include_router(jobs.router, prefix=settings.api_prefix)
app.include_router(automation.router, prefix=settings.api_prefix)
app.include_router(configs.router, prefix=settings.api_prefix)
app.include_router(compliance.router, prefix=settings.api_prefix)
app.include_router(ws.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
