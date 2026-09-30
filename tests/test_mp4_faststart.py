import struct

import pytest

from app.core.mp4_faststart import move_moov_to_front


def atom(kind: bytes, body: bytes) -> bytes:
    return struct.pack(">I4s", 8 + len(body), kind) + body


def chunk_table(kind: bytes, offsets: list[int]) -> bytes:
    fmt = ">I" if kind == b"stco" else ">Q"
    entries = b"".join(struct.pack(fmt, value) for value in offsets)
    return atom(kind, b"\x00\x00\x00\x00" + struct.pack(">I", len(offsets)) + entries)


def moov_with(table: bytes) -> bytes:
    stbl = atom(b"stbl", table)
    return atom(b"moov", atom(b"trak", atom(b"mdia", atom(b"minf", stbl))))


def read_offsets(data: bytes, kind: bytes = b"stco") -> list[int]:
    position = data.index(kind) + 4
    (count,) = struct.unpack(">I", data[position + 4 : position + 8])
    width, fmt = (4, ">I") if kind == b"stco" else (8, ">Q")
    start = position + 8
    return [
        struct.unpack(fmt, data[start + i * width : start + (i + 1) * width])[0]
        for i in range(count)
    ]


FTYP = atom(b"ftyp", b"isom\x00\x00\x02\x00")
SAMPLES = [b"frame-one", b"frame-two!!", b"frame-3"]


def camera_style_file(kind: bytes = b"stco") -> tuple[bytes, list[int]]:
    """ftyp + mdat + moov, with moov last like an iPhone recording."""
    mdat_body = b"".join(SAMPLES)
    mdat_start = len(FTYP) + 8
    offsets, cursor = [], mdat_start
    for sample in SAMPLES:
        offsets.append(cursor)
        cursor += len(sample)
    data = FTYP + atom(b"mdat", mdat_body) + moov_with(chunk_table(kind, offsets))
    return data, offsets


def top_level_kinds(data: bytes) -> list[bytes]:
    kinds, offset = [], 0
    while offset < len(data):
        size, kind = struct.unpack(">I4s", data[offset : offset + 8])
        kinds.append(kind)
        offset += size
    return kinds


@pytest.mark.parametrize("kind", [b"stco", b"co64"])
def test_moves_moov_ahead_of_mdat_and_keeps_offsets_on_the_same_samples(kind):
    original, _ = camera_style_file(kind)

    result = move_moov_to_front(original)

    assert top_level_kinds(result) == [b"ftyp", b"moov", b"mdat"]
    assert len(result) == len(original)
    for offset, sample in zip(read_offsets(result, kind), SAMPLES, strict=True):
        assert result[offset : offset + len(sample)] == sample


def test_leaves_files_that_already_start_with_moov_untouched():
    original, _ = camera_style_file()
    fast = move_moov_to_front(original)

    assert move_moov_to_front(fast) == fast


@pytest.mark.parametrize(
    "data",
    [
        b"\xff\xd8\xff" + b"\x00" * 64,  # not an mp4
        FTYP + atom(b"mdat", b"payload"),  # no moov
        FTYP + struct.pack(">I4s", 999, b"mdat"),  # declared size past the end
    ],
)
def test_returns_unreadable_or_incomplete_files_unchanged(data):
    assert move_moov_to_front(data) == data


def test_gives_up_when_a_32_bit_offset_would_overflow():
    table = chunk_table(b"stco", [0xFFFFFFF0])
    data = FTYP + atom(b"mdat", b"x") + moov_with(table)

    assert move_moov_to_front(data) == data


def test_gives_up_when_the_offset_table_is_truncated():
    broken_table = atom(b"stco", b"\x00\x00\x00\x00" + struct.pack(">I", 50))
    data = FTYP + atom(b"mdat", b"x") + moov_with(broken_table)

    assert move_moov_to_front(data) == data


def test_upload_stores_videos_with_moov_first(db):
    from app.repositories import media_storage_repository
    from app.services import media_service

    original, _ = camera_style_file()
    video = original[:4] + b"ftypmp42" + original[12:]

    response = media_service.upload_media(db, video)

    stored = media_storage_repository.get_by_filename(db, response.filename)
    assert top_level_kinds(bytes(stored.content)) == [b"ftyp", b"moov", b"mdat"]
