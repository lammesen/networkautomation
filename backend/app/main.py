from fastapi import FastAPI
from app.api import auth, devices, jobs, websockets, commands, config, compliance

app = FastAPI()

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(devices.router, prefix="/devices", tags=["devices"])
app.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
app.include_router(commands.router, prefix="/commands", tags=["commands"])
app.include_router(config.router, prefix="/config", tags=["config"])
app.include_router(compliance.router, prefix="/compliance", tags=["compliance"])
app.include_router(websockets.router)


@app.get("/health")
def health_check():
    return {"status": "ok"}
