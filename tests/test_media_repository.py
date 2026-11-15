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


def test_get_info_reports_type_and_size_without_the_content(db):
    media_storage_repository.save(db, "clip.mp4", bytes(range(200)), "video/mp4")

    assert media_storage_repository.get_info(db, "clip.mp4") == ("video/mp4", 200)
    assert media_storage_repository.get_info(db, "missing.mp4") is None


def test_get_bytes_reads_an_inclusive_range(db):
    content = bytes(range(200))
    media_storage_repository.save(db, "clip.mp4", content, "video/mp4")

    assert media_storage_repository.get_bytes(db, "clip.mp4", 0, 0) == content[:1]
    assert media_storage_repository.get_bytes(db, "clip.mp4", 10, 19) == content[10:20]
    assert media_storage_repository.get_bytes(db, "clip.mp4", 190, 199) == content[190:]
