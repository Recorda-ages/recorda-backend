"""Moves an MP4's index (`moov`) ahead of its media data, like `ffmpeg -movflags faststart`.

Phone cameras write `moov` at the end of the file. A player can't start without it, so over
HTTP it first has to fetch the tail of the file before playing anything. Moving `moov` to the
front makes playback start after the first request. The media samples are not re-encoded:
only the chunk offset tables (`stco`/`co64`) are shifted by the size of the moved atom.
"""

import struct
from collections.abc import Iterator

_CONTAINERS = {b"moov", b"trak", b"mdia", b"minf", b"stbl"}
_MAX_UINT32 = 0xFFFFFFFF


class _MalformedMp4(Exception):
    pass


def _atoms(
    buf: bytes | bytearray, start: int, end: int
) -> Iterator[tuple[bytes, int, int, int]]:
    """Yields (type, offset, size, header_size) for each atom between start and end."""
    offset = start
    while offset + 8 <= end:
        size, kind = struct.unpack(">I4s", buf[offset : offset + 8])
        header = 8
        if size == 1:
            if offset + 16 > end:
                raise _MalformedMp4
            size = struct.unpack(">Q", buf[offset + 8 : offset + 16])[0]
            header = 16
        elif size == 0:
            size = end - offset
        if size < header or offset + size > end:
            raise _MalformedMp4
        yield kind, offset, size, header
        offset += size


def _shift_chunk_offsets(moov: bytearray, start: int, end: int, delta: int) -> None:
    for kind, offset, size, header in _atoms(moov, start, end):
        body = offset + header
        if kind in _CONTAINERS:
            _shift_chunk_offsets(moov, body, offset + size, delta)
        elif kind in (b"stco", b"co64"):
            (count,) = struct.unpack(">I", moov[body + 4 : body + 8])
            width, fmt = (4, ">I") if kind == b"stco" else (8, ">Q")
            entries = body + 8
            if entries + count * width > offset + size:
                raise _MalformedMp4
            for index in range(count):
                position = entries + index * width
                (value,) = struct.unpack(fmt, moov[position : position + width])
                shifted = value + delta
                if kind == b"stco" and shifted > _MAX_UINT32:
                    # Would need promoting the table to co64; not worth it for app uploads.
                    raise _MalformedMp4
                moov[position : position + width] = struct.pack(fmt, shifted)


def move_moov_to_front(data: bytes) -> bytes:
    """Returns the file with `moov` before `mdat`, or the input unchanged when it already
    is, isn't a plain MP4, or can't be rewritten safely."""
    try:
        top_level = list(_atoms(data, 0, len(data)))
        kinds = [kind for kind, *_ in top_level]
        if b"moov" not in kinds or b"mdat" not in kinds:
            return data

        moov_index = kinds.index(b"moov")
        first_mdat_index = kinds.index(b"mdat")
        if moov_index < first_mdat_index:
            return data

        _, moov_offset, moov_size, _ = top_level[moov_index]
        insert_at = top_level[first_mdat_index][1]
        moov = bytearray(data[moov_offset : moov_offset + moov_size])
        # Everything from the first mdat up to the old moov position moves forward by the
        # size of moov; that's where every chunk offset points.
        _shift_chunk_offsets(moov, 8, len(moov), moov_size)
    except (_MalformedMp4, struct.error):
        return data

    return b"".join(
        (
            data[:insert_at],
            bytes(moov),
            data[insert_at:moov_offset],
            data[moov_offset + moov_size :],
        )
    )
