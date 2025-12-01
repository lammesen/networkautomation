"""WSGI config for webnet."""

import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "webnet.settings")

application = get_wsgi_application()
