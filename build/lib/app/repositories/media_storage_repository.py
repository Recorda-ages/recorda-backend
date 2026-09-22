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
