from __future__ import annotations

import json
from typing import AsyncIterator, Dict

import redis.asyncio as redis_async
from redis import Redis

from app.core.config import settings

_sync_client: Redis | None = None
_async_client: redis_async.Redis | None = None


def _channel(job_id: int) -> str:
    return f"{settings.websocket_redis_channel_prefix}:{job_id}"


def _get_sync_client() -> Redis:
    global _sync_client
    if _sync_client is None:
        _sync_client = Redis.from_url(settings.redis_url)
    return _sync_client


async def _get_async_client() -> redis_async.Redis:
    global _async_client
    if _async_client is None:
        _async_client = redis_async.from_url(settings.redis_url)
    return _async_client


def publish_job_event(job_id: int, payload: Dict) -> None:
    client = _get_sync_client()
    client.publish(_channel(job_id), json.dumps(payload))


async def stream_job_events(job_id: int) -> AsyncIterator[Dict]:
    client = await _get_async_client()
    pubsub = client.pubsub()
    channel = _channel(job_id)
    await pubsub.subscribe(channel)
    try:
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            data = message.get("data")
            if isinstance(data, bytes):
                yield json.loads(data.decode())
            elif isinstance(data, str):
                yield json.loads(data)
    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.close()
