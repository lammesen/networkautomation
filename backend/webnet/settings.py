"""Django settings for webnet project (Django + HTMX + DRF)."""

from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path
from urllib.parse import urlparse

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")


def env(key: str, default: str | None = None) -> str:
    val = os.getenv(key, default)
    return "" if val is None else str(val)


# Core settings
DEBUG = env("DEBUG", "false").lower() == "true"

# SECRET_KEY is required in production
SECRET_KEY = env("SECRET_KEY")
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = "insecure-dev-key-do-not-use-in-production"
    else:
        raise ImproperlyConfigured("SECRET_KEY environment variable is required in production")

# ENCRYPTION_KEY is required for credential encryption in production
ENCRYPTION_KEY = env("ENCRYPTION_KEY")
if not ENCRYPTION_KEY and not DEBUG:
    raise ImproperlyConfigured(
        "ENCRYPTION_KEY environment variable is required for credential encryption"
    )

# ALLOWED_HOSTS must be explicitly configured in production
ALLOWED_HOSTS = [h for h in (env("ALLOWED_HOSTS", "").split(",")) if h]
if not ALLOWED_HOSTS:
    if DEBUG:
        ALLOWED_HOSTS = ["localhost", "127.0.0.1", "[::1]"]
    else:
        raise ImproperlyConfigured("ALLOWED_HOSTS environment variable is required in production")

# Applications
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "whitenoise.runserver_nostatic",
    "rest_framework",
    "rest_framework.authtoken",
    "rest_framework_simplejwt",
    "channels",
    "django_filters",
    "webnet.core",
    "webnet.users",
    "webnet.customers",
    "webnet.devices",
    "webnet.jobs",
    "webnet.config_mgmt",
    "webnet.compliance",
    "webnet.networkops",
    "webnet.api",
    "webnet.ui",
]

MIDDLEWARE = [
    "webnet.core.metrics.RequestIdMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "webnet.core.middleware.RequireLoginMiddleware",
    "webnet.core.metrics.MetricsMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "webnet.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "webnet.wsgi.application"
ASGI_APPLICATION = "webnet.asgi.application"


def _parse_database_url(url: str | None):
    if not url:
        return {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    if url.startswith("sqlite:"):
        return {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": url.replace("sqlite:///", ""),
        }
    parsed = urlparse(url)
    engine_map = {
        "postgres": "django.db.backends.postgresql",
        "postgresql": "django.db.backends.postgresql",
        "postgresql+psycopg2": "django.db.backends.postgresql",
    }
    engine = engine_map.get(parsed.scheme)
    if not engine:
        raise ValueError(f"Unsupported database scheme: {parsed.scheme}")
    return {
        "ENGINE": engine,
        "NAME": parsed.path.lstrip("/"),
        "USER": parsed.username,
        "PASSWORD": parsed.password,
        "HOST": parsed.hostname,
        "PORT": parsed.port,
    }


DATABASES = {
    "default": _parse_database_url(env("DATABASE_URL")),
}

AUTH_USER_MODEL = "users.User"

# Authentication backends - LDAP with local fallback
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",  # Local authentication (fallback)
]

# Load LDAP configuration if enabled
from webnet.ldap_config import LDAP_ENABLED, LDAP_CONFIG  # noqa: E402

if LDAP_ENABLED:
    # Add LDAP backend before local backend for priority
    AUTHENTICATION_BACKENDS.insert(0, "webnet.core.ldap_backend.WebnetLDAPBackend")
    # Apply LDAP configuration to settings
    globals().update(LDAP_CONFIG)

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# Security/CORS/CSRF
CORS_ALLOWED_ORIGINS = [o for o in (env("CORS_ALLOWED_ORIGINS", "").split(",")) if o]
CSRF_TRUSTED_ORIGINS = [o for o in (env("CSRF_TRUSTED_ORIGINS", "").split(",")) if o]
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = (
    env("SESSION_COOKIE_SECURE", "true" if not DEBUG else "false").lower() == "true"
)
CSRF_COOKIE_SECURE = env("CSRF_COOKIE_SECURE", "true" if not DEBUG else "false").lower() == "true"
SECURE_SSL_REDIRECT = env("SECURE_SSL_REDIRECT", "true" if not DEBUG else "false").lower() == "true"
SECURE_HSTS_SECONDS = int(env("SECURE_HSTS_SECONDS", "31536000" if not DEBUG else "0"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = (
    env("SECURE_HSTS_INCLUDE_SUBDOMAINS", "true").lower() == "true" if not DEBUG else False
)
SECURE_HSTS_PRELOAD = env("SECURE_HSTS_PRELOAD", "true" if not DEBUG else "false").lower() == "true"
SSH_STRICT_HOST_VERIFY = env("SSH_STRICT_HOST_VERIFY", "true").lower() == "true"
SSH_KNOWN_HOSTS_PATH = env("SSH_KNOWN_HOSTS_PATH", "") or None

LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/login/"
LOGIN_EXEMPT_PREFIXES = (
    "/login",
    "/logout",
    "/api/",
    "/ws/",  # WebSocket paths - auth handled by Channels AuthMiddlewareStack
    "/static/",
    "/admin/login",
    "/admin/logout",
    "/favicon.ico",
    "/metrics",
)

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# REST framework
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "webnet.api.authentication.APIKeyAuthentication",
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.BasicAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": int(env("PAGE_SIZE", "50")),
}

# JWT
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=int(env("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=int(env("REFRESH_TOKEN_EXPIRE_DAYS", "7"))),
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# Channels
REDIS_URL = env("REDIS_URL", "redis://localhost:6379/0")
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [REDIS_URL],
        },
    },
}

# Celery
CELERY_BROKER_URL = env("CELERY_BROKER_URL", REDIS_URL)
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_ACKS_LATE = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_BEAT_SCHEDULE = {}

# Logging (minimal; extend later)
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
}
