from app.core import security
from app.core.config import settings
from app.core.security import decode_access_token, hash_password
from app.models import User

PREFIX = "/api/v1/auth"


def test_reset_password_valid_email_updates_hash_and_returns_success(client, db):
    db._users = {1: auth_user(id=1, username="alice", password="old-password")}

    resp = client.post(
        f"{PREFIX}/reset-password",
        json={"email": "alice@example.com", "new_password": "new-password-123"},
    )

    assert resp.status_code == 200
    assert resp.json() == {"message": "Senha redefinida com sucesso"}

    stored = db._users[1]
    assert security.verify_password("old-password", stored.password_hash) is False
    assert security.verify_password("new-password-123", stored.password_hash) is True
    assert "password" not in resp.json()
    assert "password_hash" not in resp.json()


def test_reset_password_short_password_is_rejected_by_backend(client, db):
    db._users = {1: auth_user(id=1, username="alice", password="old-password")}

    resp = client.post(
        f"{PREFIX}/reset-password",
        json={"email": "alice@example.com", "new_password": "1234567"},
    )

    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"


def test_reset_password_unknown_email_uses_generic_error(client):
    resp = client.post(
        f"{PREFIX}/reset-password",
        json={"email": "missing@example.com", "new_password": "new-password-123"},
    )

    assert resp.status_code == 400
    body = resp.json()
    assert body["error"]["code"] == "BAD_REQUEST"
    assert body["error"]["message"] == "Não foi possível redefinir a senha"
    assert "não encontrado" not in body["error"]["message"].lower()
    assert "usuário" not in body["error"]["message"].lower()
    assert "email" not in body["error"]["message"].lower()


def test_reset_password_then_login_uses_new_password(client, db, monkeypatch):
    monkeypatch.setattr(settings, "password_hash_iterations", 1)
    db._users = {1: auth_user(id=1, username="alice", password="old-password")}

    reset = client.post(
        f"{PREFIX}/reset-password",
        json={"email": "alice@example.com", "new_password": "new-password-123"},
    )
    assert reset.status_code == 200

    old_login = client.post(
        f"{PREFIX}/login", json={"username": "alice", "password": "old-password"}
    )
    new_login = client.post(
        f"{PREFIX}/login",
        json={"username": "alice", "password": "new-password-123"},
    )

    assert old_login.status_code == 401
    assert new_login.status_code == 200
    assert new_login.json()["user"]["username"] == "alice"
    assert "password_hash" not in new_login.json()


def test_login_valid_common_user_returns_token_and_user_data(client, db, monkeypatch):
    monkeypatch.setattr(settings, "password_hash_iterations", 1)
    db._users = {1: auth_user(id=1, username="alice", account_type="common")}

    resp = client.post(
        f"{PREFIX}/login", json={"username": "alice", "password": "correct"}
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["access_token"]
    assert body["token_type"] == "bearer"
    assert body["user"] == {
        "id": 1,
        "username": "alice",
        "account_type": "common",
    }


def test_login_valid_admin_uses_same_token_contract(client, db, monkeypatch):
    monkeypatch.setattr(settings, "password_hash_iterations", 1)
    db._users = {2: auth_user(id=2, username="admin", account_type="admin")}

    resp = client.post(
        f"{PREFIX}/login", json={"username": "admin", "password": "correct"}
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"].count(".") == 2
    assert body["user"]["account_type"] == "admin"


def test_login_unknown_username_returns_invalid_credentials(client, monkeypatch):
    monkeypatch.setattr(settings, "password_hash_iterations", 1)

    resp = client.post(
        f"{PREFIX}/login", json={"username": "missing", "password": "correct"}
    )

    assert resp.status_code == 401
    assert resp.json() == invalid_credentials_body()


def test_login_wrong_password_returns_invalid_credentials(client, db, monkeypatch):
    monkeypatch.setattr(settings, "password_hash_iterations", 1)
    db._users = {1: auth_user(id=1, username="alice")}

    resp = client.post(f"{PREFIX}/login", json={"username": "alice", "password": "bad"})

    assert resp.status_code == 401
    assert resp.json() == invalid_credentials_body()


def test_invalid_login_errors_are_indistinguishable(client, db, monkeypatch):
    monkeypatch.setattr(settings, "password_hash_iterations", 1)
    db._users = {1: auth_user(id=1, username="alice")}

    missing = client.post(
        f"{PREFIX}/login", json={"username": "missing", "password": "correct"}
    )
    wrong_password = client.post(
        f"{PREFIX}/login", json={"username": "alice", "password": "bad"}
    )

    assert missing.status_code == wrong_password.status_code == 401
    assert missing.json() == wrong_password.json() == invalid_credentials_body()


def test_login_token_works_immediately_on_auth_me(client, db, monkeypatch):
    monkeypatch.setattr(settings, "password_hash_iterations", 1)
    db._users = {1: auth_user(id=1, username="alice", account_type="common")}

    login_resp = client.post(
        f"{PREFIX}/login", json={"username": "alice", "password": "correct"}
    )
    token = login_resp.json()["access_token"]
    me_resp = client.get(f"{PREFIX}/me", headers={"Authorization": f"Bearer {token}"})

    assert me_resp.status_code == 200
    assert me_resp.json() == {
        "id": 1,
        "username": "alice",
        "account_type": "common",
    }


def test_login_response_does_not_expose_password_or_hash(client, db, monkeypatch):
    monkeypatch.setattr(settings, "password_hash_iterations", 1)
    db._users = {1: auth_user(id=1, username="alice")}

    resp = client.post(
        f"{PREFIX}/login", json={"username": "alice", "password": "correct"}
    )

    body = resp.json()
    assert "password" not in body
    assert "password_hash" not in body
    assert "hashed_password" not in body
    assert "password" not in body["user"]
    assert "password_hash" not in body["user"]
    assert "hashed_password" not in body["user"]


def test_common_and_admin_tokens_use_same_expiration(client, db, monkeypatch):
    monkeypatch.setattr(settings, "password_hash_iterations", 1)
    db._users = {
        1: auth_user(id=1, username="alice", account_type="common"),
        2: auth_user(id=2, username="admin", account_type="admin"),
    }

    common = client.post(
        f"{PREFIX}/login", json={"username": "alice", "password": "correct"}
    ).json()
    admin = client.post(
        f"{PREFIX}/login", json={"username": "admin", "password": "correct"}
    ).json()

    common_payload = decode_access_token(common["access_token"])
    admin_payload = decode_access_token(admin["access_token"])
    assert common["token_type"] == admin["token_type"] == "bearer"
    assert common_payload is not None
    assert admin_payload is not None
    assert common_payload["exp"] - common_payload["iat"] == (
        admin_payload["exp"] - admin_payload["iat"]
    )
    assert common_payload["exp"] - common_payload["iat"] == (
        settings.access_token_expire_minutes * 60
    )


def test_login_token_expiration_follows_settings(client, db, monkeypatch):
    monkeypatch.setattr(settings, "password_hash_iterations", 1)
    monkeypatch.setattr(settings, "access_token_expire_minutes", 60 * 24 * 45)
    db._users = {1: auth_user(id=1, username="alice")}

    resp = client.post(
        f"{PREFIX}/login", json={"username": "alice", "password": "correct"}
    )

    payload = decode_access_token(resp.json()["access_token"])
    assert payload is not None
    assert payload["exp"] - payload["iat"] == 60 * 24 * 45 * 60


def auth_user(
    id: int,
    username: str,
    password: str = "correct",
    account_type: str = "common",
) -> User:
    return User(
        id=id,
        name=username.title(),
        email=f"{username}@example.com",
        username=username,
        password_hash=hash_password(password),
        account_type=account_type,
    )


def invalid_credentials_body():
    return {
        "error": {
            "code": "UNAUTHORIZED",
            "message": "Credenciais inválidas",
            "details": {},
        }
    }
