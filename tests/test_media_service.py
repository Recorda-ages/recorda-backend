from unittest.mock import patch

import pytest

from app.core.media_validation import MAX_UPLOAD_SIZE_BYTES
from app.repositories import media_storage_repository
from app.services import media_service

JPEG_BYTES = b"\xff\xd8\xff" + b"\x00" * 100


def test_upload_media_persists_and_returns_response(sqlite_db):
    response = media_service.upload_media(sqlite_db, JPEG_BYTES)
    assert response.content_type == "image/jpeg"
    assert response.size_bytes == len(JPEG_BYTES)
    assert response.filename.endswith(".jpg")
    assert response.url == f"/api/v1/recordas/media/{response.filename}"


def test_upload_media_rejects_unsupported_type(sqlite_db):
    with pytest.raises(media_service.UnsupportedMediaTypeError):
        media_service.upload_media(sqlite_db, b"not a real file")


def test_upload_media_rejects_oversized_file(sqlite_db):
    oversized = b"\xff\xd8\xff" + b"\x00" * MAX_UPLOAD_SIZE_BYTES
    with pytest.raises(media_service.MediaTooLargeError):
        media_service.upload_media(sqlite_db, oversized)


def test_upload_media_wraps_storage_failures(sqlite_db):
    with patch.object(
        media_storage_repository, "save", side_effect=RuntimeError("boom")
    ):
        with pytest.raises(media_service.MediaStorageError):
            media_service.upload_media(sqlite_db, JPEG_BYTES)
