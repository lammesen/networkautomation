from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.jobs.events import stream_job_events

router = APIRouter()


@router.websocket("/ws/jobs/{job_id}")
async def job_log_socket(websocket: WebSocket, job_id: int) -> None:
    await websocket.accept()
    try:
        async for event in stream_job_events(job_id):
            await websocket.send_json(event)
    except WebSocketDisconnect:  # pragma: no cover - network specific
        return
