"""Prometheus metrics and request ID helpers."""

from __future__ import annotations

import time
import uuid
from typing import Callable

from django.http import HttpRequest, HttpResponse
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST


REQUEST_COUNTER = Counter(
    "webnet_http_requests_total",
    "Total HTTP requests",
    labelnames=("method", "path"),
)

REQUEST_LATENCY = Histogram(
    "webnet_http_request_duration_seconds",
    "HTTP request latency seconds",
    labelnames=("method", "path"),
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1, 2, 5),
)


def normalize_path(request: HttpRequest) -> str:
    match = getattr(request, "resolver_match", None)
    if match and match.view_name:
        return match.view_name
    return request.path


class RequestIdMiddleware:
    """Attach/propagate X-Request-ID per request for trace correlation."""

    def __init__(self, get_response: Callable):
        self.get_response = get_response

    def __call__(self, request: HttpRequest):
        rid = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        request.request_id = rid
        request.META["HTTP_X_REQUEST_ID"] = rid
        response = self.get_response(request)
        response.headers["X-Request-ID"] = rid
        return response


class MetricsMiddleware:
    """Record request counts and latency for Prometheus scraping."""

    def __init__(self, get_response: Callable):
        self.get_response = get_response

    def __call__(self, request: HttpRequest):
        path_label = normalize_path(request)
        method = request.method
        start = time.monotonic()
        response = self.get_response(request)
        duration = time.monotonic() - start
        REQUEST_COUNTER.labels(method=method, path=path_label).inc()
        REQUEST_LATENCY.labels(method=method, path=path_label).observe(duration)
        return response


def metrics_view(_: HttpRequest) -> HttpResponse:
    return HttpResponse(generate_latest(), content_type=CONTENT_TYPE_LATEST)
