"""Channels consumer for interactive SSH sessions (placeholder)."""

from __future__ import annotations

import asyncio
import json
import contextlib
from typing import Optional

from channels.generic.websocket import AsyncJsonWebsocketConsumer
from webnet.core.ssh import SSHSessionError, SSHSessionManager
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser

from webnet.devices.models import Device
from webnet.users.models import User


class SSHConsumer(AsyncJsonWebsocketConsumer):
    manager_cls = SSHSessionManager

    async def connect(self):
        user = self.scope.get("user")
        if not user or isinstance(user, AnonymousUser) or not user.is_authenticated:
            await self.close(code=4001)
            return
        try:
            self.device_id = int(self.scope["url_route"]["kwargs"]["device_id"])
        except (KeyError, TypeError, ValueError):
            await self.close(code=4002)
            return
        device = await self._get_device(self.device_id)
        if not device:
            await self.close(code=4004)
            return
        if not await self._has_access(user, device):
            await self.close(code=4003)
            return
        if not device.credential:
            await self.close(code=4005)
            return
        self.device = device
        self.manager = self.manager_cls() if callable(self.manager_cls) else self.manager_cls
        await self.accept()
        await self.send_json(
            {"type": "connected", "device_id": device.id, "hostname": device.hostname}
        )
        self.keepalive = asyncio.create_task(self._keepalive())
        self.session = None

    async def disconnect(self, close_code):  # pragma: no cover
        if hasattr(self, "keepalive"):
            self.keepalive.cancel()
            with contextlib.suppress(Exception, asyncio.CancelledError):
                await self.keepalive
        if hasattr(self, "session"):
            with contextlib.suppress(Exception):
                await self.session.close()

    async def receive(self, text_data=None, bytes_data=None):
        if not text_data:
            return
        try:
            payload = json.loads(text_data)
        except json.JSONDecodeError:
            await self.send_json({"type": "error", "detail": "invalid json"})
            return
        if payload.get("type") != "command":
            await self.send_json({"type": "error", "detail": "unsupported message"})
            return
        cmd = (payload.get("command") or "").strip()
        if not cmd:
            return
        if cmd.lower() in {"exit", "quit", "logout"}:
            await self.close()
            return
        try:
            if getattr(self, "session", None) is None:
                cred = self.device.credential
                self.session = await self.manager.open_session(
                    host=self.device.mgmt_ip,
                    port=22,
                    username=cred.username,
                    password=cred.password or "",
                )
            result = await self.session.run_command(cmd)
            await self.send_json(
                {
                    "type": "output",
                    "command": cmd,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "exit_status": result.exit_status,
                }
            )
        except SSHSessionError as exc:
            await self.send_json({"type": "error", "detail": str(exc)})
        except Exception as exc:  # pragma: no cover - defensive
            await self.send_json({"type": "error", "detail": str(exc)})

    async def _keepalive(self):  # pragma: no cover - timer loop
        try:
            while True:
                await asyncio.sleep(10)
                await self.send_json({"type": "keepalive"})
        except asyncio.CancelledError:
            raise
        except Exception:
            return

    @database_sync_to_async
    def _get_device(self, device_id: int) -> Optional[Device]:
        return Device.objects.select_related("credential", "customer").filter(pk=device_id).first()

    @database_sync_to_async
    def _has_access(self, user: User, device: Device) -> bool:
        if getattr(user, "role", "viewer") == "admin":
            return True
        return device.customer in user.customers.all()
