"""WebSocket support for live log and SSH streaming."""

from __future__ import annotations

import asyncio
import contextlib
import json
from typing import Optional
from uuid import uuid4

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from sqlalchemy.orm import Session

from app.core.auth import decode_token
from app.core.config import settings
from app.core.logging import get_logger
from app.db import Customer, Device, Job, JobLog, User, get_db
from app.dependencies import get_ssh_manager
from app.domain import TenantRequestContext
from app.services.ssh import SSHSessionManager
from app.services.ssh.manager import SSHSessionError

logger = get_logger(__name__)

router = APIRouter(prefix="/ws", tags=["websocket"])


class ConnectionManager:
    """Manage WebSocket connections for job log streaming."""

    def __init__(self) -> None:
        self.active_connections: dict[int, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, job_id: int) -> None:
        """Connect a client to a job's log stream."""
        await websocket.accept()
        if job_id not in self.active_connections:
            self.active_connections[job_id] = []
        self.active_connections[job_id].append(websocket)
        logger.info("WebSocket connected for job %s", job_id)

    def disconnect(self, websocket: WebSocket, job_id: int) -> None:
        """Disconnect a client from a job's log stream."""
        if job_id in self.active_connections:
            try:
                self.active_connections[job_id].remove(websocket)
            except ValueError:
                pass
            if not self.active_connections[job_id]:
                del self.active_connections[job_id]
        logger.info("WebSocket disconnected for job %s", job_id)

    async def broadcast(self, job_id: int, message: dict) -> None:
        """Broadcast a log message to all connected clients for a job."""
        if job_id in self.active_connections:
            disconnected: list[WebSocket] = []
            for connection in self.active_connections[job_id]:
                try:
                    await connection.send_json(message)
                except Exception as exc:  # pragma: no cover - defensive logging
                    logger.error("Error sending to WebSocket: %s", exc)
                    disconnected.append(connection)

            # Clean up disconnected clients
            for conn in disconnected:
                self.disconnect(conn, job_id)


manager = ConnectionManager()


@router.websocket("/jobs/{job_id}")
async def job_logs_websocket(
    websocket: WebSocket,
    job_id: int,
    token: str = Query(..., description="JWT access token"),
    db: Session = Depends(get_db),
) -> None:
    """WebSocket endpoint for live job logs.

    Query parameter 'token' should contain the JWT access token.
    """
    # Require and validate token
    try:
        decode_token(token)
    except Exception:
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
        await websocket.send_json(
            {
                "type": "status",
                "job_id": job_id,
                "status": job.status,
                "started_at": job.started_at.isoformat() if job.started_at else None,
            }
        )

        # Send existing logs
        from app.jobs.manager import get_job_logs

        logs = get_job_logs(db, job_id, limit=100)
        last_ts = logs[-1].ts if logs else None
        for log in logs:
            await websocket.send_json(
                {
                    "type": "log",
                    "ts": log.ts.isoformat(),
                    "level": log.level,
                    "host": log.host,
                    "message": log.message,
                    "extra": log.extra_json,
                }
            )

        # Keep connection alive and wait for messages
        while True:
            # Poll for new logs every second
            await asyncio.sleep(1)

            # Stream incremental logs
            new_logs_query = db.query(JobLog).filter(JobLog.job_id == job_id)
            if last_ts:
                new_logs_query = new_logs_query.filter(JobLog.ts > last_ts)
            new_logs = new_logs_query.order_by(JobLog.ts.asc()).all()
            for log in new_logs:
                await websocket.send_json(
                    {
                        "type": "log",
                        "ts": log.ts.isoformat(),
                        "level": log.level,
                        "host": log.host,
                        "message": log.message,
                        "extra": log.extra_json,
                    }
                )
                last_ts = log.ts

            # Check if job is complete
            db.refresh(job)
            if job.status in ["success", "partial", "failed"]:
                await websocket.send_json(
                    {
                        "type": "complete",
                        "job_id": job_id,
                        "status": job.status,
                        "finished_at": job.finished_at.isoformat() if job.finished_at else None,
                    }
                )
                break

    except WebSocketDisconnect:
        manager.disconnect(websocket, job_id)
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.error("WebSocket error for job %s: %s", job_id, exc)
        manager.disconnect(websocket, job_id)


def _resolve_tenant_context(
    db: Session,
    token: str,
    requested_customer_id: Optional[int],
) -> TenantRequestContext:
    """Decode the token and ensure the user has access to the requested customer."""
    token_data = decode_token(token)
    user = db.query(User).filter(User.username == token_data.username).first()
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Inactive user")

    if requested_customer_id:
        customer = db.query(Customer).filter(Customer.id == requested_customer_id).first()
        if not customer:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Customer not found")
        if user.role != "admin" and customer not in user.customers:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Access to this customer denied")
        return TenantRequestContext(user=user, customer=customer)

    if len(user.customers) == 1:
        return TenantRequestContext(user=user, customer=user.customers[0])

    raise HTTPException(
        status.HTTP_400_BAD_REQUEST,
        "customer_id query parameter required when user has multiple customers",
    )


async def _send_error_and_close(websocket: WebSocket, detail: str, code: int = 1011) -> None:
    """Send an error payload and close the socket."""
    try:
        await websocket.send_json({"type": "error", "detail": detail})
    finally:
        await websocket.close(code=code, reason=detail)


async def _keepalive_loop(websocket: WebSocket) -> None:
    """Emit keepalive frames so clients can detect broken tunnels."""
    interval = max(5.0, float(settings.ssh_keepalive_interval))
    try:
        while True:
            await asyncio.sleep(interval)
            await websocket.send_json({"type": "keepalive"})
    except asyncio.CancelledError:
        # Task cancelled during shutdown; suppress to avoid noisy traces
        raise
    except Exception:
        pass


@router.websocket("/devices/{device_id}/ssh")
async def device_ssh_websocket(
    websocket: WebSocket,
    device_id: int,
    token: Optional[str] = Query(default=None),
    customer_id: Optional[int] = Query(default=None),
    db: Session = Depends(get_db),
    ssh_manager: SSHSessionManager = Depends(get_ssh_manager),
) -> None:
    """Interactive (command/response) SSH session to a device via websocket."""
    if not token:
        await websocket.close(code=1008, reason="Missing token")
        return

    await websocket.accept()
    session = None
    keepalive_task: Optional[asyncio.Task] = None
    try:
        try:
            tenant = _resolve_tenant_context(db, token, customer_id)
        except HTTPException as exc:
            await _send_error_and_close(websocket, exc.detail, code=1008)
            return

        device = (
            db.query(Device)
            .filter(Device.id == device_id, Device.customer_id == tenant.customer.id)
            .first()
        )
        if not device:
            await _send_error_and_close(websocket, "Device not found for this customer", code=1008)
            return
        if not device.enabled:
            await _send_error_and_close(websocket, "Device is disabled", code=1008)
            return

        credential = device.credential
        if not credential:
            await _send_error_and_close(websocket, "Device has no credential attached", code=1008)
            return

        session_id = f"{tenant.user.id}:{device.id}:{uuid4().hex}"
        try:
            session = await ssh_manager.open_session(
                host=device.mgmt_ip,
                port=22,
                username=credential.username,
                password=credential.password,
                session_id=session_id,
            )
        except SSHSessionError as exc:
            await _send_error_and_close(websocket, f"SSH connection failed: {exc}", code=1011)
            return

        await websocket.send_json(
            {
                "type": "connected",
                "device_id": device_id,
                "prompt": device.hostname,
                "device_name": device.hostname,
                "customer_id": tenant.customer.id,
                "user": tenant.user.username,
                "session_id": session_id,
            }
        )

        keepalive_task = asyncio.create_task(_keepalive_loop(websocket))

        while True:
            try:
                raw_message = await websocket.receive_text()
            except WebSocketDisconnect:
                break
            except Exception as exc:  # pragma: no cover
                logger.error("Websocket receive error: %s", exc)
                break

            try:
                payload = json.loads(raw_message)
            except json.JSONDecodeError:
                await websocket.send_json(
                    {"type": "error", "detail": "Commands must be JSON encoded"}
                )
                continue

            if payload.get("type") != "command":
                await websocket.send_json({"type": "error", "detail": "Unsupported message type"})
                continue

            command = (payload.get("command") or "").strip()
            if not command:
                continue
            if command.lower() in {"exit", "quit", "logout"}:
                await websocket.send_json({"type": "closed", "reason": "Client requested"})
                break

            await websocket.send_json({"type": "command_ack", "command": command})
            try:
                result = await session.run_command(command)
            except SSHSessionError as exc:
                await websocket.send_json(
                    {"type": "error", "detail": f"Command failed: {exc}", "command": command}
                )
                continue

            await websocket.send_json(
                {
                    "type": "output",
                    "command": command,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "exit_status": result.exit_status,
                }
            )

    finally:
        if keepalive_task:
            keepalive_task.cancel()
            with contextlib.suppress(Exception, asyncio.CancelledError):
                await keepalive_task
        if session:
            with contextlib.suppress(Exception):
                await session.close()
        with contextlib.suppress(Exception):
            await websocket.close()
