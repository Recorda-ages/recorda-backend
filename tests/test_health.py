"""Endpoint tests for the health check."""

from app.core.config import settings


def test_health(client):
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["app"] == settings.app_name
    assert body["version"] == settings.version


def test_root(client):
    resp = client.get("/api/v1")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
