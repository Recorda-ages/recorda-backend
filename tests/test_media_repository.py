from app.repositories import media_storage_repository


def test_save_persists_media(db):
    media = media_storage_repository.save(db, "abc.jpg", b"fake-bytes", "image/jpeg")
    assert media.id is not None
    assert media.filename == "abc.jpg"
    assert media.content == b"fake-bytes"


def test_get_by_filename_returns_saved_media(db):
    media_storage_repository.save(db, "abc.jpg", b"fake-bytes", "image/jpeg")
    found = media_storage_repository.get_by_filename(db, "abc.jpg")
    assert found is not None
    assert found.content == b"fake-bytes"


def test_get_by_filename_returns_none_when_missing(db):
    assert media_storage_repository.get_by_filename(db, "missing.jpg") is None
