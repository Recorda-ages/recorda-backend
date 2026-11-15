"""Recover missing snapshots using each track's own Deezer album."""

import httpx
from sqlalchemy import or_, select, update
from sqlalchemy.orm import Session

from app.models import Recorda
from app.services.music_service import get_track_genre_name


def backfill_genres(
    db: Session, client: httpx.Client, *, limit: int = 500
) -> tuple[int, int]:
    missing = or_(Recorda.song_genre_name.is_(None), Recorda.song_genre_name == "")
    track_ids = list(
        db.scalars(
            select(Recorda.deezer_track_id)
            .where(missing, Recorda.deleted_at.is_(None))
            .distinct()
            .order_by(Recorda.deezer_track_id)
            .limit(limit)
        )
    )
    updated = 0
    for track_id in track_ids:
        name = get_track_genre_name(client, track_id)
        if name:
            result = db.execute(
                update(Recorda)
                .where(
                    Recorda.deezer_track_id == track_id,
                    missing,
                    Recorda.deleted_at.is_(None),
                )
                .values(song_genre_name=name)
            )
            updated += result.rowcount
    db.commit()
    return len(track_ids), updated
