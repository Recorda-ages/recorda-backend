"""Endpoint tests for the Recorda API under /api/v1/recordas."""

from app.models import Recorda

PREFIX = "/api/v1/recordas"


def test_list_recordas_empty(client):
    resp = client.get(PREFIX)
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_recordas_returns_recordas(client, db):
    db._recordas = {
        1: Recorda(
            id=1, midia="Song", music="Song of Silence", description="By Disturbed"
        )
    }
    resp = client.get(PREFIX)
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["midia"] == "Song"


def test_create_recordas_returns_201(client):
    resp = client.post(PREFIX, json={"midia": "Song", "music": "Song of Silence"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["id"] == 1
    assert body["midia"] == "Song"


def test_create_recordas_validates_missing_field(client):
    resp = client.post(PREFIX, json={"midia": "Song"})
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"


def test_get_recordas_returns_recordas(client, db):
    db._recordas = {1: Recorda(id=1, midia="Song", music="Song of Silence")}
    resp = client.get(f"{PREFIX}/1")
    assert resp.status_code == 200
    assert resp.json()["midia"] == "Song"


def test_get_recordas_returns_404_when_missing(client):
    resp = client.get(f"{PREFIX}/999")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "NOT_FOUND"


def test_update_recorda_returns_200(client, db):
    db._recordas = {
        1: Recorda(
            id=1, midia="Song", music="Song of Silence", description="By Disturbed"
        )
    }
    resp = client.put(f"{PREFIX}/1", json={"midia": "Hills"})
    assert resp.status_code == 200
    assert resp.json()["midia"] == "Hills"
    assert resp.json()["music"] == "Song of Silence"
    assert resp.json()["description"] == "By Disturbed"


def test_update_recorda_returns_404_when_missing(client):
    resp = client.put(f"{PREFIX}/999", json={"midia": "Hills"})
    assert resp.status_code == 404


def test_delete_recorda_returns_204(client, db):
    db._recordas = {
        1: Recorda(
            id=1, midia="Song", music="Song of Silence", description="By Disturbed"
        )
    }
    resp = client.delete(f"{PREFIX}/1")
    assert resp.status_code == 204
    assert 1 not in db._recordas


def test_delete_recorda_returns_404_when_missing(client):
    resp = client.delete(f"{PREFIX}/999")
    assert resp.status_code == 404
