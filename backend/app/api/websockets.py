import asyncio
from fastapi import APIRouter, WebSocket, Depends
from typing import List

from app.db.session import get_db
from app.crud.job import get_job
from app.api.auth import get_current_user
from app.schemas.auth import User

import redis.asyncio as redis

router = APIRouter()


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)


manager = ConnectionManager()


@router.websocket("/ws/jobs/{job_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    job_id: int,
    # This is a simplified auth for websockets. In a real app, you might pass the token in the query params.
    # current_user: User = Depends(get_current_user),
):
    await manager.connect(websocket)
    # db = next(get_db())
    # job = get_job(db, job_id)
    # if not job or job.user_id != current_user.id:
    #     await websocket.close(code=4001)
    #     return

    r = redis.from_url("redis://localhost:6379", encoding="utf-8", decode_responses=True)
    pubsub = r.pubsub()
    await pubsub.subscribe(f"job_{job_id}")

    try:
        while True:
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if message:
                await websocket.send_text(message['data'])
            # Keep the connection alive
            await asyncio.sleep(0.1)
    except Exception:
        manager.disconnect(websocket)
    finally:
        await pubsub.unsubscribe(f"job_{job_id}")
        await r.close()
