"""Endpoint tests for the account data under /api/v1/users/me/account (US34)."""

import pytest

from app.core import security
from app.core.config import settings
from app.services import user_service
from tests.factories import add_user, auth_headers

ACCOUNT = "/api/v1/users/me/account"
LOGIN = "/api/v1/auth/login"


@pytest.fixture(autouse=True)
def fast_hashing(monkeypatch):
    monkeypatch.setattr(settings, "password_hash_iterations", 1)


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _field_errors(response) -> dict[str, str]:
    return {
        field["field"]: field["message"]
        for field in response.json()["error"]["details"]["fields"]
    }


def test_get_account_requires_authentication(client):
    assert client.get(ACCOUNT).status_code == 401


def test_patch_account_requires_authentication(client):
    assert client.patch(ACCOUNT, json={"name": "Novo"}).status_code == 401


def test_get_account_returns_editable_fields(client, db):
    alice = add_user(db, "alice", name="Alice Silva", email="alice@example.com")

    response = client.get(ACCOUNT, headers=auth_headers(alice))

    assert response.status_code == 200
    assert response.json() == {
        "user_id": str(alice.user_id),
        "name": "Alice Silva",
        "username": "alice",
        "email": "alice@example.com",
    }


def test_patch_account_updates_fields_and_following_reads(client, db):
    alice = add_user(db, "alice")

    response = client.patch(
        ACCOUNT,
        headers=auth_headers(alice),
        json={"name": "Alice Nova", "username": "alice_nova", "email": "N@E.com "},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["account"] == {
        "user_id": str(alice.user_id),
        "name": "Alice Nova",
        "username": "alice_nova",
        "email": "n@e.com",
    }

    following = client.get(ACCOUNT, headers=_bearer(body["access_token"]))
    assert following.status_code == 200
    assert following.json() == body["account"]


def test_patch_username_reissues_token_and_invalidates_previous(client, db):
    alice = add_user(db, "alice")
    old_headers = auth_headers(alice)

    response = client.patch(ACCOUNT, headers=old_headers, json={"username": "alicia"})

    assert response.status_code == 200
    assert client.get(ACCOUNT, headers=old_headers).status_code == 401
    new_token = response.json()["access_token"]
    me = client.get("/api/v1/auth/me", headers=_bearer(new_token))
    assert me.json()["username"] == "alicia"


def test_patch_keeps_omitted_and_null_fields(client, db):
    alice = add_user(db, "alice", name="Alice", password="senha-antiga")
    original_hash = alice.password_hash

    response = client.patch(
        ACCOUNT,
        headers=auth_headers(alice),
        json={"name": "Alice Nova", "email": None, "password": None},
    )

    assert response.status_code == 200
    db.refresh(alice)
    assert alice.name == "Alice Nova"
    assert alice.username == "alice"
    assert alice.email == "alice@example.com"
    assert alice.password_hash == original_hash


def test_patch_empty_body_changes_nothing(client, db):
    alice = add_user(db, "alice")

    response = client.patch(ACCOUNT, headers=auth_headers(alice), json={})

    assert response.status_code == 200
    assert response.json()["account"]["username"] == "alice"


def test_patch_accepts_own_current_username_and_email(client, db):
    alice = add_user(db, "alice")

    response = client.patch(
        ACCOUNT,
        headers=auth_headers(alice),
        json={"username": "alice", "email": "alice@example.com"},
    )

    assert response.status_code == 200


@pytest.mark.parametrize(
    ("payload", "field", "message"),
    [
        ({"email": "sem-arroba"}, "email", "Informe um email válido."),
        ({"username": "com espaco"}, "username", "O usuário não pode conter espaços."),
        ({"username": "   "}, "username", "Informe seu usuário."),
        ({"name": "   "}, "name", "Informe seu nome."),
        ({"password": "curta"}, "password", "Deve ter pelo menos 8 caracteres."),
    ],
)
def test_patch_rejects_invalid_values_without_changes(
    client, db, payload, field, message
):
    alice = add_user(db, "alice", password="senha-antiga")
    original_hash = alice.password_hash

    response = client.patch(
        ACCOUNT, headers=auth_headers(alice), json={"name": "Outro", **payload}
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert _field_errors(response)[field] == message
    db.refresh(alice)
    assert alice.name == "Alice"
    assert alice.username == "alice"
    assert alice.email == "alice@example.com"
    assert alice.password_hash == original_hash


def test_patch_rejects_taken_username_and_email_without_changes(client, db):
    alice = add_user(db, "alice")
    add_user(db, "bob")

    response = client.patch(
        ACCOUNT,
        headers=auth_headers(alice),
        json={"name": "Outro", "username": "bob", "email": "bob@example.com"},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CONFLICT"
    assert _field_errors(response) == {
        "username": user_service.USERNAME_TAKEN_MESSAGE,
        "email": user_service.EMAIL_TAKEN_MESSAGE,
    }
    db.refresh(alice)
    assert (alice.name, alice.username, alice.email) == (
        "Alice",
        "alice",
        "alice@example.com",
    )


def test_patch_rejects_email_of_soft_deleted_user(client, db):
    alice = add_user(db, "alice")
    ghost = add_user(db, "ghost")
    user_service.delete_own_account(db, ghost)

    response = client.patch(
        ACCOUNT, headers=auth_headers(alice), json={"email": "ghost@example.com"}
    )

    assert response.status_code == 409
    assert _field_errors(response) == {"email": user_service.EMAIL_TAKEN_MESSAGE}


def test_patch_password_hashes_and_allows_login_with_new_one(client, db):
    alice = add_user(db, "alice", password="senha-antiga")

    response = client.patch(
        ACCOUNT, headers=auth_headers(alice), json={"password": "senha-nova-123"}
    )

    assert response.status_code == 200
    assert "password" not in response.json()["account"]
    db.refresh(alice)
    assert alice.password_hash != "senha-nova-123"
    assert security.verify_password("senha-nova-123", alice.password_hash) is True

    login = {"username": "alice", "password": "senha-nova-123"}
    assert client.post(LOGIN, json=login).status_code == 200
    login["password"] = "senha-antiga"
    assert client.post(LOGIN, json=login).status_code == 401
