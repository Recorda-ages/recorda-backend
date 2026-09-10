from unittest.mock import patch

import pytest

from app.core import security
from app.core.media_validation import MAX_UPLOAD_SIZE_BYTES
from app.models import User
from app.repositories import media_storage_repository

PREFIX = "/api/v1/recordas/media"


@pytest.fixture
def auth_headers(sqlite_db):
    user = User(
        name="Usuário Teste",
        email="teste@example.com",
        username="usuario_teste",
        account_type="common",
    )
    sqlite_db.add(user)
    sqlite_db.commit()
    sqlite_db.refresh(user)

    token = security.create_access_token(
        subject=str(user.id),
        additional_claims={
            "username": user.username,
            "account_type": user.account_type,
        },
    )

    return {"Authorization": f"Bearer {token}"}


def test_upload_returns_201_and_working_url(sqlite_client, auth_headers):
    files = {"file": ("photo.jpg", b"\xff\xd8\xff" + b"\x00" * 100, "image/jpeg")}
    resp = sqlite_client.post(PREFIX, files=files, headers=auth_headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["content_type"] == "image/jpeg"

    get_resp = sqlite_client.get(body["url"], headers=auth_headers)
    assert get_resp.status_code == 200
    assert get_resp.content == b"\xff\xd8\xff" + b"\x00" * 100


def test_upload_without_token_returns_401(sqlite_client):
    files = {"file": ("photo.jpg", b"\xff\xd8\xff" + b"\x00" * 100, "image/jpeg")}
    resp = sqlite_client.post(PREFIX, files=files)
    assert resp.status_code == 401


def test_upload_rejects_unsupported_type(sqlite_client, auth_headers):
    files = {"file": ("doc.txt", b"plain text content", "text/plain")}
    resp = sqlite_client.post(PREFIX, files=files, headers=auth_headers)
    assert resp.status_code == 415


def test_upload_rejects_oversized_file(sqlite_client, auth_headers):
    oversized = b"\xff\xd8\xff" + b"\x00" * MAX_UPLOAD_SIZE_BYTES
    files = {"file": ("big.jpg", oversized, "image/jpeg")}
    resp = sqlite_client.post(PREFIX, files=files, headers=auth_headers)
    assert resp.status_code == 413


def test_upload_returns_502_when_storage_fails(sqlite_client, auth_headers):
    with patch.object(
        media_storage_repository, "save", side_effect=RuntimeError("boom")
    ):
        files = {"file": ("photo.jpg", b"\xff\xd8\xff" + b"\x00" * 100, "image/jpeg")}
        resp = sqlite_client.post(PREFIX, files=files, headers=auth_headers)
        assert resp.status_code == 502


def test_get_media_returns_404_when_missing(sqlite_client, auth_headers):
    resp = sqlite_client.get(f"{PREFIX}/does-not-exist.jpg", headers=auth_headers)
    assert resp.status_code == 404


def test_get_media_without_token_returns_401(sqlite_client):
    resp = sqlite_client.get(f"{PREFIX}/anything.jpg")
    assert resp.status_code == 401
