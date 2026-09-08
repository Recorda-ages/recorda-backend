from app.repositories import media_storage_repository


def test_save_persists_media(sqlite_db):
    media = media_storage_repository.save(
        sqlite_db, "abc.jpg", b"fake-bytes", "image/jpeg"
    )
    assert media.id is not None
    assert media.filename == "abc.jpg"
    assert media.content == b"fake-bytes"


def test_get_by_filename_returns_saved_media(sqlite_db):
    media_storage_repository.save(sqlite_db, "abc.jpg", b"fake-bytes", "image/jpeg")
    found = media_storage_repository.get_by_filename(sqlite_db, "abc.jpg")
    assert found is not None
    assert found.content == b"fake-bytes"


def test_get_by_filename_returns_none_when_missing(sqlite_db):
    assert media_storage_repository.get_by_filename(sqlite_db, "missing.jpg") is None
