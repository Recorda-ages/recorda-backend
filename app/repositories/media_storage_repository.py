from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.media import Media


def save(db: Session, filename: str, content: bytes, content_type: str) -> Media:
    media = Media(filename=filename, content_type=content_type, content=content)
    db.add(media)
    db.commit()
    db.refresh(media)
    return media


def get_by_filename(db: Session, filename: str) -> Media | None:
    return db.query(Media).filter(Media.filename == filename).first()


def get_info(db: Session, filename: str) -> tuple[str, int] | None:
    """(content_type, size in bytes) without loading the content itself."""
    row = db.execute(
        select(Media.content_type, func.length(Media.content)).where(
            Media.filename == filename
        )
    ).first()
    return (row[0], row[1]) if row else None


def get_bytes(db: Session, filename: str, start: int, end: int) -> bytes:
    """Inclusive byte range [start, end] of the content, read by the database.

    Video players fetch a file in many small ranges; loading the whole blob for each
    of them wastes memory and time.
    """
    # SQL substring is 1-based.
    chunk = db.execute(
        select(func.substr(Media.content, start + 1, end - start + 1)).where(
            Media.filename == filename
        )
    ).scalar_one()
    return bytes(chunk)
