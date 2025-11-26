"""Tests for ad-hoc network endpoints."""


def test_viewer_cannot_run_adhoc_commands(client, viewer_headers):
    """Viewer role should be denied for ad-hoc operations."""
    response = client.post(
        "/api/v1/network/run_commands",
        headers=viewer_headers,
        json={
            "devices": [],
            "commands": ["show version"],
        },
    )
    assert response.status_code == 403


def test_operator_runs_adhoc_commands(monkeypatch, client, operator_headers):
    """Operators can execute ad-hoc commands when provided."""
    called = {}

    def fake_execute(request):
        called["request"] = request
        return {"status": "ok"}

    monkeypatch.setattr("app.api.network.execute_adhoc_commands", fake_execute)

    response = client.post(
        "/api/v1/network/run_commands",
        headers=operator_headers,
        json={
            "devices": [
                {
                    "hostname": "r1",
                    "ip": "192.0.2.1",
                    "platform": "ios",
                    "username": "u",
                    "password": "p",
                }
            ],
            "commands": ["show version"],
        },
    )

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert called["request"].devices[0].hostname == "r1"
