"""WebSocket support for live job log streaming."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session
import json
import asyncio
from typing import Optional

from app.db import get_db, Job
from app.core.auth import decode_token
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/ws", tags=["websocket"])


class ConnectionManager:
    """Manage WebSocket connections for job log streaming."""
    
    def __init__(self):
        self.active_connections: dict[int, list[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, job_id: int):
        """Connect a client to a job's log stream."""
        await websocket.accept()
        if job_id not in self.active_connections:
            self.active_connections[job_id] = []
        self.active_connections[job_id].append(websocket)
        logger.info(f"WebSocket connected for job {job_id}")
    
    def disconnect(self, websocket: WebSocket, job_id: int):
        """Disconnect a client from a job's log stream."""
        if job_id in self.active_connections:
            self.active_connections[job_id].remove(websocket)
            if not self.active_connections[job_id]:
                del self.active_connections[job_id]
        logger.info(f"WebSocket disconnected for job {job_id}")
    
    async def broadcast(self, job_id: int, message: dict):
        """Broadcast a log message to all connected clients for a job."""
        if job_id in self.active_connections:
            disconnected = []
            for connection in self.active_connections[job_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Error sending to WebSocket: {e}")
                    disconnected.append(connection)
            
            # Clean up disconnected clients
            for conn in disconnected:
                self.disconnect(conn, job_id)


manager = ConnectionManager()


@router.websocket("/jobs/{job_id}")
async def job_logs_websocket(
    websocket: WebSocket,
    job_id: int,
    token: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """WebSocket endpoint for live job logs.
    
    Query parameter 'token' should contain the JWT access token.
    """
    # Validate token
    if token:
        try:
            decode_token(token)
        except Exception as e:
            await websocket.close(code=1008, reason="Invalid token")
            return
    
    # Verify job exists
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        await websocket.close(code=1008, reason="Job not found")
        return
    
    await manager.connect(websocket, job_id)
    
    try:
        # Send initial job status
        await websocket.send_json({
            "type": "status",
            "job_id": job_id,
            "status": job.status,
            "started_at": job.started_at.isoformat() if job.started_at else None,
        })
        
        # Send existing logs
        from app.jobs.manager import get_job_logs
        logs = get_job_logs(db, job_id, limit=100)
        for log in logs:
            await websocket.send_json({
                "type": "log",
                "ts": log.ts.isoformat(),
                "level": log.level,
                "host": log.host,
                "message": log.message,
                "extra": log.extra_json,
            })
        
        # Keep connection alive and wait for messages
        while True:
            # Poll for new logs every second
            await asyncio.sleep(1)
            
            # Check if job is complete
            db.refresh(job)
            if job.status in ["success", "partial", "failed"]:
                await websocket.send_json({
                    "type": "complete",
                    "job_id": job_id,
                    "status": job.status,
                    "finished_at": job.finished_at.isoformat() if job.finished_at else None,
                })
                break
    
    except WebSocketDisconnect:
        manager.disconnect(websocket, job_id)
    except Exception as e:
        logger.error(f"WebSocket error for job {job_id}: {e}")
        manager.disconnect(websocket, job_id)
