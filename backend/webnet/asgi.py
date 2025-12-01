"""ASGI entrypoint for Django + Channels."""

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "webnet.settings")

django_app = get_asgi_application()

try:  # Lazy import to avoid circular issues during early scaffolding
    from . import routing

    websocket_urlpatterns = getattr(routing, "websocket_urlpatterns", [])
except Exception:  # pragma: no cover - defensive
    websocket_urlpatterns = []

application = ProtocolTypeRouter(
    {
        "http": django_app,
        "websocket": AuthMiddlewareStack(URLRouter(websocket_urlpatterns)),
    }
)
