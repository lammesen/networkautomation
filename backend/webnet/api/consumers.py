"""Channels consumers for websockets."""

from __future__ import annotations

from typing import Any

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.contrib.auth.models import AnonymousUser

from webnet.jobs.models import Job, JobLog
from webnet.jobs.serializers import JobLogSerializer


class UpdatesConsumer(AsyncJsonWebsocketConsumer):
    """
    Unified WebSocket consumer for real-time UI updates.
    Clients subscribe to entity updates scoped by customer.

    Message format sent to client:
    {
        "type": "update",
        "entity": "job" | "device" | "config" | "compliance" | "topology",
        "action": "created" | "updated" | "deleted",
        "id": <entity_id>,
        "html": "<rendered partial html>" (optional, for HTMX swap)
    }
    """

    async def connect(self) -> None:
        user = self.scope.get("user")
        if not user or isinstance(user, AnonymousUser) or not user.is_authenticated:
            await self.close(code=4001)
            return

        self.user = user
        self.groups: list[str] = []

        # Subscribe to updates for all customer groups user has access to
        customer_ids = await self._get_customer_ids(user)
        for cid in customer_ids:
            group = f"updates_customer_{cid}"
            await self.channel_layer.group_add(group, self.channel_name)
            self.groups.append(group)

        # Admins also get global updates group
        if getattr(user, "role", "viewer") == "admin":
            await self.channel_layer.group_add("updates_global", self.channel_name)
            self.groups.append("updates_global")

        await self.accept()

    async def disconnect(self, close_code: int) -> None:
        for group in getattr(self, "groups", []):
            await self.channel_layer.group_discard(group, self.channel_name)

    async def receive_json(self, content: dict[str, Any]) -> None:
        # Client can send ping to keep alive
        if content.get("type") == "ping":
            await self.send_json({"type": "pong"})

    async def entity_update(self, event: dict[str, Any]) -> None:
        """Handler for entity_update messages from channel layer."""
        await self.send_json(event["data"])

    @database_sync_to_async
    def _get_customer_ids(self, user) -> list[int]:
        if getattr(user, "role", "viewer") == "admin":
            from webnet.customers.models import Customer

            return list(Customer.objects.values_list("id", flat=True))
        return list(user.customers.values_list("id", flat=True))


class JobLogConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user")
        if not user or isinstance(user, AnonymousUser) or not user.is_authenticated:
            await self.close(code=4001)
            return
        try:
            job_id = int(self.scope["url_route"]["kwargs"]["job_id"])
        except (KeyError, TypeError, ValueError):
            await self.close(code=4002)
            return
        self.job_id = job_id
        self.group_name = f"job_{job_id}"
        # Basic tenancy: allow if admin or job.customer in user's customers
        if not await self._has_access(user, job_id):
            await self.close(code=4003)
            return
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await self._send_initial_logs()

    async def disconnect(self, close_code):  # pragma: no cover - lifecycle
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):  # pragma: no cover - server push only
        return

    async def job_log(self, event: dict[str, Any]):
        await self.send_json(event["data"])

    async def _send_initial_logs(self):
        logs = await self._get_recent_logs(self.job_id, limit=200)
        for log in logs:
            await self.send_json(JobLogSerializer(log).data)

    @database_sync_to_async
    def _has_access(self, user, job_id: int) -> bool:
        job = Job.objects.filter(pk=job_id).first()
        if not job:
            return False
        if getattr(user, "role", "viewer") == "admin":
            return True
        return job.customer in user.customers.all()

    @database_sync_to_async
    def _get_recent_logs(self, job_id: int, *, limit: int = 200):
        return list(JobLog.objects.filter(job_id=job_id).order_by("-ts")[:limit][::-1])
