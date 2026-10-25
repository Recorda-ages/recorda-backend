"""Build previews shared by report moderation and admin user details."""

from collections.abc import Collection
from uuid import UUID

from sqlalchemy.orm import Session

from app.models import AppUser, Recorda
from app.models.recorda import PHOTO
from app.repositories import recorda_repository, user_repository
from app.schemas.report import ReportTargetPreview

PreviewKey = tuple[str, UUID]


def load_target_previews(
    db: Session,
    *,
    user_ids: Collection[UUID],
    recorda_ids: Collection[UUID],
) -> dict[PreviewKey, ReportTargetPreview]:
    previews: dict[PreviewKey, ReportTargetPreview] = {}

    if recorda_ids:
        for recorda, author_username in recorda_repository.list_with_author_by_ids(
            db, recorda_ids
        ):
            previews[("RECORDA", recorda.recorda_id)] = recorda_preview(
                recorda, author_username
            )

    if user_ids:
        for user in user_repository.list_by_ids(db, user_ids):
            previews[("USER", user.user_id)] = user_preview(user)

    return previews


def recorda_preview(recorda: Recorda, author_username: str) -> ReportTargetPreview:
    image_url = (
        recorda.media_url if recorda.media_type == PHOTO else recorda.song_cover_url
    )
    return ReportTargetPreview(
        title=recorda.song_title,
        subtitle=f"@{author_username}",
        image_url=image_url,
    )


def user_preview(user: AppUser) -> ReportTargetPreview:
    return ReportTargetPreview(
        title=user.name,
        subtitle=f"@{user.username}",
        image_url=user.profile_picture_url,
    )
