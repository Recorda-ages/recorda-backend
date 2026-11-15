from app.core.media_validation import (
    MAX_UPLOAD_SIZE_BYTES,
    detect_content_type,
    is_size_allowed,
)

JPEG_HEADER = b"\xff\xd8\xff" + b"\x00" * 13
PNG_HEADER = b"\x89PNG\r\n\x1a\n" + b"\x00" * 8
WEBP_HEADER = b"RIFF" + b"\x00" * 4 + b"WEBP" + b"\x00" * 4
MP4_HEADER = b"\x00" * 4 + b"ftyp" + b"\x00" * 8


def test_detects_jpeg():
    assert detect_content_type(JPEG_HEADER) == "image/jpeg"


def test_detects_png():
    assert detect_content_type(PNG_HEADER) == "image/png"


def test_detects_webp():
    assert detect_content_type(WEBP_HEADER) == "image/webp"


def test_detects_mp4():
    assert detect_content_type(MP4_HEADER) == "video/mp4"


def test_unknown_type_returns_none():
    assert detect_content_type(b"not a real file") is None


def test_size_within_limit_is_allowed():
    assert is_size_allowed(1024) is True


def test_size_at_limit_is_allowed():
    assert is_size_allowed(MAX_UPLOAD_SIZE_BYTES) is True


def test_size_over_limit_is_rejected():
    assert is_size_allowed(MAX_UPLOAD_SIZE_BYTES + 1) is False


def test_zero_size_is_rejected():
    assert is_size_allowed(0) is False
