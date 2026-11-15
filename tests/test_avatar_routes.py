"""PUT e DELETE /users/me/avatar (issue #108)."""

import re
from unittest.mock import patch

import pytest

from app.core.media_validation import MAX_AVATAR_SIZE_BYTES
from app.repositories import media_storage_repository
from tests.factories import add_user, auth_headers

URL = "/api/v1/users/me/avatar"
JPEG = b"\xff\xd8\xff" + b"\x00" * 100
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
WEBP = b"RIFF\x00\x00\x00\x00WEBP" + b"\x00" * 100
MP4 = b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 100
UNSUPPORTED_MESSAGE = "Envie uma imagem JPG, PNG ou WEBP."


def _put(client, user, content: bytes):
    files = {"file": ("avatar", content, "application/octet-stream")}
    return client.put(URL, files=files, headers=auth_headers(user))


@pytest.mark.parametrize(
    ("content", "ext"), [(JPEG, "jpg"), (PNG, "png"), (WEBP, "webp")]
)
def test_put_avatar_updates_user_and_url_serves_image(
    client, db, common_user, content, ext
):
    resp = _put(client, common_user, content)

    assert resp.status_code == 200
    url = resp.json()["profile_picture_url"]
    assert re.fullmatch(rf"/api/v1/recordas/media/avatar-[0-9a-f-]{{36}}\.{ext}", url)
    db.refresh(common_user)
    assert common_user.profile_picture_url == url

    image = client.get(url, headers=auth_headers(common_user))
    assert image.status_code == 200
    assert image.content == content


def test_put_avatar_accepts_exactly_the_size_limit(client, common_user):
    content = JPEG + b"\x00" * (MAX_AVATAR_SIZE_BYTES - len(JPEG))

    assert _put(client, common_user, content).status_code == 200


@pytest.mark.parametrize("content", [MP4, b"plain text content"])
def test_put_avatar_rejects_non_images_without_changing_user(
    client, db, common_user, content
):
    resp = _put(client, common_user, content)

    assert resp.status_code == 415
    assert resp.json()["error"]["message"] == UNSUPPORTED_MESSAGE
    db.refresh(common_user)
    assert common_user.profile_picture_url is None


def test_put_avatar_rejects_oversized_image_without_changing_user(
    client, db, common_user
):
    content = JPEG + b"\x00" * (MAX_AVATAR_SIZE_BYTES - len(JPEG) + 1)

    assert _put(client, common_user, content).status_code == 413
    db.refresh(common_user)
    assert common_user.profile_picture_url is None


def test_put_avatar_returns_502_when_storage_fails(client, db, common_user):
    with patch.object(
        media_storage_repository, "save", side_effect=RuntimeError("boom")
    ):
        resp = _put(client, common_user, JPEG)

    assert resp.status_code == 502
    db.refresh(common_user)
    assert common_user.profile_picture_url is None


def test_delete_avatar_clears_photo_and_is_idempotent(client, db, common_user):
    old_url = _put(client, common_user, JPEG).json()["profile_picture_url"]
    viewer = add_user(db, "viewer")

    assert client.delete(URL, headers=auth_headers(common_user)).status_code == 204
    assert client.delete(URL, headers=auth_headers(common_user)).status_code == 204

    db.refresh(common_user)
    assert common_user.profile_picture_url is None
    results = client.get(
        "/api/v1/users/search",
        params={"q": common_user.username},
        headers=auth_headers(viewer),
    ).json()
    assert [r["avatar_url"] for r in results] == [None]
    # O arquivo antigo fica no banco: a tabela media não tem dono (dívida técnica).
    old_filename = old_url.rsplit("/", 1)[1]
    assert media_storage_repository.get_by_filename(db, old_filename) is not None


def test_avatar_routes_require_authentication(client):
    files = {"file": ("avatar", JPEG, "image/jpeg")}

    assert client.put(URL, files=files).status_code == 401
    assert client.delete(URL).status_code == 401
