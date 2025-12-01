"""Channels websocket URL routing."""

from django.urls import path

from webnet.api.consumers import JobLogConsumer, UpdatesConsumer
from webnet.api.ssh_consumer import SSHConsumer

websocket_urlpatterns = [
    path("ws/updates/", UpdatesConsumer.as_asgi()),
    path("ws/jobs/<int:job_id>/", JobLogConsumer.as_asgi()),
    path("ws/devices/<int:device_id>/ssh/", SSHConsumer.as_asgi()),
]
