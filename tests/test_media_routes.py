from unittest.mock import patch

import pytest

from app.core.media_validation import MAX_UPLOAD_SIZE_BYTES
from app.repositories import media_storage_repository
from tests.factories import auth_headers as make_auth_headers

PREFIX = "/api/v1/recordas/media"


@pytest.fixture
def auth_headers(common_user):
    return make_auth_headers(common_user)


def test_upload_returns_201_and_working_url(client, auth_headers):
    files = {"file": ("photo.jpg", b"\xff\xd8\xff" + b"\x00" * 100, "image/jpeg")}
    resp = client.post(PREFIX, files=files, headers=auth_headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["content_type"] == "image/jpeg"

    get_resp = client.get(body["url"], headers=auth_headers)
    assert get_resp.status_code == 200
    assert get_resp.content == b"\xff\xd8\xff" + b"\x00" * 100


def test_upload_without_token_returns_401(client):
    files = {"file": ("photo.jpg", b"\xff\xd8\xff" + b"\x00" * 100, "image/jpeg")}
    resp = client.post(PREFIX, files=files)
    assert resp.status_code == 401


def test_upload_rejects_unsupported_type(client, auth_headers):
    files = {"file": ("doc.txt", b"plain text content", "text/plain")}
    resp = client.post(PREFIX, files=files, headers=auth_headers)
    assert resp.status_code == 415


def test_upload_rejects_oversized_file(client, auth_headers):
    oversized = b"\xff\xd8\xff" + b"\x00" * MAX_UPLOAD_SIZE_BYTES
    files = {"file": ("big.jpg", oversized, "image/jpeg")}
    resp = client.post(PREFIX, files=files, headers=auth_headers)
    assert resp.status_code == 413


def test_upload_returns_502_when_storage_fails(client, auth_headers):
    with patch.object(
        media_storage_repository, "save", side_effect=RuntimeError("boom")
    ):
        files = {"file": ("photo.jpg", b"\xff\xd8\xff" + b"\x00" * 100, "image/jpeg")}
        resp = client.post(PREFIX, files=files, headers=auth_headers)
        assert resp.status_code == 502


def test_get_media_returns_404_when_missing(client, auth_headers):
    resp = client.get(f"{PREFIX}/does-not-exist.jpg", headers=auth_headers)
    assert resp.status_code == 404


VIDEO_BYTES = b"\x00\x00\x00\x18ftypmp42" + bytes(range(256)) * 4


@pytest.fixture
def video_url(client, auth_headers):
    files = {"file": ("clip.mp4", VIDEO_BYTES, "video/mp4")}
    resp = client.post(PREFIX, files=files, headers=auth_headers)
    assert resp.status_code == 201
    return resp.json()["url"]


def test_get_media_advertises_byte_ranges(client, auth_headers, video_url):
    resp = client.get(video_url, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.headers["accept-ranges"] == "bytes"
    assert resp.content == VIDEO_BYTES


@pytest.mark.parametrize(
    ("range_header", "start", "end"),
    [
        ("bytes=0-1", 0, 1),
        ("bytes=10-", 10, len(VIDEO_BYTES) - 1),
        ("bytes=-5", len(VIDEO_BYTES) - 5, len(VIDEO_BYTES) - 1),
        ("bytes=5-999999", 5, len(VIDEO_BYTES) - 1),
        ("bytes=-999999", 0, len(VIDEO_BYTES) - 1),
    ],
)
def test_get_media_serves_partial_content(
    client, auth_headers, video_url, range_header, start, end
):
    resp = client.get(video_url, headers={**auth_headers, "Range": range_header})
    assert resp.status_code == 206
    assert resp.headers["content-range"] == f"bytes {start}-{end}/{len(VIDEO_BYTES)}"
    assert resp.headers["content-type"] == "video/mp4"
    assert resp.content == VIDEO_BYTES[start : end + 1]


@pytest.mark.parametrize("range_header", ["bytes=99999-", "bytes=9-3", "bytes=-0"])
def test_get_media_rejects_unsatisfiable_range(
    client, auth_headers, video_url, range_header
):
    resp = client.get(video_url, headers={**auth_headers, "Range": range_header})
    assert resp.status_code == 416
    assert resp.headers["content-range"] == f"bytes */{len(VIDEO_BYTES)}"


@pytest.mark.parametrize("range_header", ["items=0-1", "bytes=0-1,4-5", "bytes=-"])
def test_get_media_ignores_unsupported_range(
    client, auth_headers, video_url, range_header
):
    resp = client.get(video_url, headers={**auth_headers, "Range": range_header})
    assert resp.status_code == 200
    assert resp.content == VIDEO_BYTES


def test_get_media_without_token_returns_401(client):
    resp = client.get(f"{PREFIX}/anything.jpg")
    assert resp.status_code == 401
