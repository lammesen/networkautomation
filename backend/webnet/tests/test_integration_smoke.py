import pytest
from django.test import Client


@pytest.mark.django_db
def test_metrics_endpoint_returns_prometheus_payload():
    client = Client()
    resp = client.get("/metrics/")
    assert resp.status_code == 200
    # Basic sanity checks for Prometheus exposition format
    body = resp.content.decode()
    assert "webnet_http_requests_total" in body
    assert "webnet_http_request_duration_seconds" in body
    assert "X-Request-ID" in resp.headers
