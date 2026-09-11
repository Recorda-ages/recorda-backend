MAX_UPLOAD_SIZE_BYTES = 50 * 1024 * 1024


def detect_content_type(header: bytes) -> str | None:
    if header.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"

    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"

    if header[:4] == b"RIFF" and header[8:12] == b"WEBP":
        return "image/webp"

    if header[4:8] == b"ftyp":
        return "video/mp4"

    return None


def is_size_allowed(size_bytes: int) -> bool:
    return 0 < size_bytes <= MAX_UPLOAD_SIZE_BYTES
