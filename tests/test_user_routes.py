"""Endpoint tests for the User API under /api/v1/users."""

from app.models import User

PREFIX = "/api/v1/users"


def test_list_users_empty(client):
    resp = client.get(PREFIX)
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_users_returns_users(client, db):
    db._users = {1: User(id=1, name="A", email="a@e.com")}
    resp = client.get(PREFIX)
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["name"] == "A"


def test_create_user_returns_201(client):
    resp = client.post(PREFIX, json={"name": "A", "email": "a@e.com"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["id"] == 1
    assert body["name"] == "A"


def test_create_user_validates_missing_field(client):
    resp = client.post(PREFIX, json={"name": "A"})
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"


def test_get_user_returns_user(client, db):
    db._users = {1: User(id=1, name="A", email="a@e.com")}
    resp = client.get(f"{PREFIX}/1")
    assert resp.status_code == 200
    assert resp.json()["name"] == "A"


def test_get_user_returns_404_when_missing(client):
    resp = client.get(f"{PREFIX}/999")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "NOT_FOUND"


def test_update_user_returns_200(client, db):
    db._users = {1: User(id=1, name="A", email="a@e.com")}
    resp = client.put(f"{PREFIX}/1", json={"name": "B"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "B"
    assert resp.json()["email"] == "a@e.com"


def test_update_user_returns_404_when_missing(client):
    resp = client.put(f"{PREFIX}/999", json={"name": "B"})
    assert resp.status_code == 404


def test_delete_user_returns_204(client, db):
    db._users = {1: User(id=1, name="A", email="a@e.com")}
    resp = client.delete(f"{PREFIX}/1")
    assert resp.status_code == 204
    assert 1 not in db._users


def test_delete_user_returns_404_when_missing(client):
    resp = client.delete(f"{PREFIX}/999")
    assert resp.status_code == 404
