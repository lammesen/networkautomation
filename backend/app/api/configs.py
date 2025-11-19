from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.config_backup.diff import diff_configs
from app.config_backup.models import ConfigSnapshot
from app.core.deps import get_current_user
from app.db.session import get_db

router = APIRouter(
    prefix="/config",
    tags=["configuration"],
    dependencies=[Depends(get_current_user)],
)


@router.get("/devices/{device_id}/snapshots")
def list_snapshots(device_id: int, db: Session = Depends(get_db)):
    snapshots = (
        db.query(ConfigSnapshot)
        .filter(ConfigSnapshot.device_id == device_id)
        .order_by(ConfigSnapshot.created_at.desc())
        .all()
    )
    return [
        {
            "id": snap.id,
            "job_id": snap.job_id,
            "source": snap.source,
            "created_at": snap.created_at,
            "hash": snap.hash,
        }
        for snap in snapshots
    ]


@router.get("/snapshots/{snapshot_id}")
def read_snapshot(snapshot_id: int, db: Session = Depends(get_db)):
    snapshot = db.get(ConfigSnapshot, snapshot_id)
    if not snapshot:
        raise HTTPException(status_code=404)
    return {
        "id": snapshot.id,
        "device_id": snapshot.device_id,
        "job_id": snapshot.job_id,
        "created_at": snapshot.created_at,
        "source": snapshot.source,
        "hash": snapshot.hash,
        "config_text": snapshot.config_text,
    }


@router.get("/devices/{device_id}/diff")
def diff_snapshot(
    device_id: int,
    from_snapshot: int = Query(..., description="Older snapshot ID"),
    to_snapshot: int = Query(..., description="Newer snapshot ID"),
    db: Session = Depends(get_db),
):
    old = db.get(ConfigSnapshot, from_snapshot)
    new = db.get(ConfigSnapshot, to_snapshot)
    if not old or not new or old.device_id != device_id or new.device_id != device_id:
        raise HTTPException(status_code=404)
    diff = diff_configs(old.config_text, new.config_text, str(from_snapshot), str(to_snapshot))
    return {"diff": diff}
