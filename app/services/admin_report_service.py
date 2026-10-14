"""Fila de moderação: denúncias agrupadas por alvo (T-E10.US44.BE.01)."""

from uuid import UUID

from sqlalchemy import Row
from sqlalchemy.orm import Session

from app.models import AppUser, Recorda
from app.models.recorda import PHOTO
from app.models.report import TARGET_RECORDA, TARGET_USER
from app.repositories import recorda_repository, report_repository, user_repository
from app.repositories.report_repository import GroupOrder
from app.schemas.moderation import AdminSummary
from app.schemas.recorda import RecordaRead
from app.schemas.report import (
    ReportAuthor,
    ReportDetail,
    ReportGroup,
    ReportGroupDetail,
    ReportGroupPage,
    ReportRecordaTarget,
    ReportTargetPreview,
    ReportUserTarget,
)
from app.services import moderation_service

PreviewKey = tuple[str, UUID]


class NoReportsForTargetError(Exception):
    """The administrative detail exists only for reported targets."""


def get_detail(db: Session, *, target_type: str, target_id: UUID) -> ReportGroupDetail:
    rows = report_repository.list_for_target(
        db, target_type=target_type, target_id=target_id
    )
    if not rows:
        raise NoReportsForTargetError

    if target_type == TARGET_RECORDA:
        recorda = recorda_repository.get_by_id_including_deleted(db, target_id)
        author = user_repository.get_by_id_including_deleted(db, recorda.user_id)
        # Reports retain their targets through non-cascading foreign keys.
        # Administrative reads deliberately bypass viewer visibility rules.
        target = ReportRecordaTarget(
            **RecordaRead.model_validate(recorda).model_dump(),
            deleted_at=recorda.deleted_at,
            author=ReportAuthor.model_validate(author),
        )
    else:
        user = user_repository.get_by_id_including_deleted(db, target_id)
        target = ReportUserTarget.model_validate(user)
    return ReportGroupDetail(
        target_type=target_type,
        target=target,
        reports=[
            ReportDetail(
                report_id=row.Report.report_id,
                reporter=AdminSummary(
                    user_id=row.Report.reporter_id, username=row.reporter_username
                ),
                description=row.Report.description,
                status=row.Report.status,
                created_at=row.Report.created_at,
                resolved_at=row.Report.resolved_at,
            )
            for row in rows
        ],
        actions=moderation_service.list_target_actions(
            db, target_type=target_type, target_id=target_id
        ),
    )


def list_groups(
    db: Session,
    *,
    target_type: str | None,
    status: str,
    order: GroupOrder,
    limit: int,
    offset: int,
) -> ReportGroupPage:
    rows = report_repository.list_groups(
        db,
        target_type=target_type,
        status=status,
        order=order,
        limit=limit,
        offset=offset,
    )
    previews = _load_previews(db, rows)

    return ReportGroupPage(
        items=[_to_group(row, previews) for row in rows],
        total=report_repository.count_groups(
            db, target_type=target_type, status=status
        ),
    )


def _load_previews(
    db: Session, rows: list[Row]
) -> dict[PreviewKey, ReportTargetPreview]:
    recorda_ids = {row.target_id for row in rows if row.target_type == TARGET_RECORDA}
    user_ids = {row.target_id for row in rows if row.target_type == TARGET_USER}
    previews: dict[PreviewKey, ReportTargetPreview] = {}

    if recorda_ids:
        for recorda, author_username in recorda_repository.list_with_author_by_ids(
            db, recorda_ids
        ):
            previews[(TARGET_RECORDA, recorda.recorda_id)] = _recorda_preview(
                recorda, author_username
            )

    if user_ids:
        for user in user_repository.list_by_ids(db, user_ids):
            previews[(TARGET_USER, user.user_id)] = _user_preview(user)

    return previews


def _recorda_preview(recorda: Recorda, author_username: str) -> ReportTargetPreview:
    image_url = (
        recorda.media_url if recorda.media_type == PHOTO else recorda.song_cover_url
    )
    return ReportTargetPreview(
        title=recorda.song_title,
        subtitle=f"@{author_username}",
        image_url=image_url,
    )


def _user_preview(user: AppUser) -> ReportTargetPreview:
    return ReportTargetPreview(
        title=user.name,
        subtitle=f"@{user.username}",
        image_url=user.profile_picture_url,
    )


def _to_group(row: Row, previews: dict[PreviewKey, ReportTargetPreview]) -> ReportGroup:
    return ReportGroup(
        target_type=row.target_type,
        target_id=row.target_id,
        status=row.status,
        report_count=row.report_count,
        first_reported_at=row.first_reported_at,
        last_reported_at=row.last_reported_at,
        preview=previews[(row.target_type, row.target_id)],
    )
