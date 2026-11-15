import pytest

from app.core.config import settings
from app.models import AppUser
from tests.test_auth_routes import register_payload


@pytest.mark.parametrize("language", [None, "pt-BR", "en", "es"])
def test_register_language_is_persisted_and_returned_by_auth(
    client, db, monkeypatch, language
):
    monkeypatch.setattr(settings, "password_hash_iterations", 1)
    payload = register_payload()
    if language is not None:
        payload["language"] = language
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    expected = language or "pt-BR"
    assert response.json()["user"]["language"] == expected
    db.expire_all()
    assert db.query(AppUser).filter_by(username="alice").one().language == expected
    headers = {"Authorization": f"Bearer {response.json()['access_token']}"}
    for path in ("me", "verify"):
        result = client.get(f"/api/v1/auth/{path}", headers=headers)
        assert result.status_code == 200
        assert result.json()["language"] == expected
    login = client.post(
        "/api/v1/auth/login", json={"username": "alice", "password": "password123"}
    )
    assert login.status_code == 200
    assert login.json()["user"]["language"] == expected


@pytest.mark.parametrize("language", ["fr", "pt", "EN", "", 123])
def test_register_rejects_invalid_language(client, db, language):
    response = client.post(
        "/api/v1/auth/register", json=register_payload(language=language)
    )
    assert response.status_code == 422
    assert db.query(AppUser).filter_by(username="alice").first() is None


@pytest.mark.parametrize("language", ["pt-BR", "en", "es"])
@pytest.mark.parametrize("with_privacy", [False, True])
def test_patch_settings_persists_language(
    client, db, common_user, common_user_token, language, with_privacy
):
    headers = {"Authorization": f"Bearer {common_user_token}"}
    payload = {"language": language}
    if with_privacy:
        payload["is_private"] = True
    response = client.patch("/api/v1/users/me/settings", json=payload, headers=headers)
    assert response.status_code == 200
    assert response.json() == {
        "language": language,
        "is_private": with_privacy,
        "accepted_requests": 0,
    }
    db.expire_all()
    assert db.get(AppUser, common_user.user_id).language == language
    for path in ("me", "verify"):
        result = client.get(f"/api/v1/auth/{path}", headers=headers)
        assert result.status_code == 200
        assert result.json()["language"] == language


@pytest.mark.parametrize("payload", [{}, {"language": None}, {"is_private": False}])
def test_patch_settings_preserves_omitted_or_null_language(
    client, db, common_user, common_user_token, payload
):
    common_user.language = "es"
    db.commit()
    response = client.patch(
        "/api/v1/users/me/settings",
        json=payload,
        headers={"Authorization": f"Bearer {common_user_token}"},
    )
    assert response.status_code == 200
    assert response.json()["language"] == "es"


@pytest.mark.parametrize("language", ["fr", "pt", "EN", "", 123])
def test_patch_settings_rejects_invalid_language(
    client, db, common_user, common_user_token, language
):
    response = client.patch(
        "/api/v1/users/me/settings",
        json={"language": language, "is_private": True},
        headers={"Authorization": f"Bearer {common_user_token}"},
    )
    assert response.status_code == 422
    db.refresh(common_user)
    assert common_user.language == "pt-BR"
    assert common_user.is_private is False


def test_patch_settings_requires_authentication(client):
    response = client.patch("/api/v1/users/me/settings", json={"language": "es"})
    assert response.status_code == 401
