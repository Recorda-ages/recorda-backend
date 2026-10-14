"""Endpoint tests for GET /api/v1/admin/reports (T-E10.US44.BE.01)."""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import event
from sqlalchemy.orm import Session

from app.core.time import now_utc
from app.models import AppUser, Report
from app.models.recorda import VIDEO
from app.models.report import STATUS_DISMISSED, STATUS_RESOLVED
from tests.factories import (
    add_comment,
    add_recorda,
    add_report,
    add_user,
    auth_headers,
)

REPORTS = "/api/v1/admin/reports"
BASE = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)


def _at(minutes: int) -> datetime:
    return BASE + timedelta(minutes=minutes)


def _utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _reporters(db: Session, count: int, prefix: str = "denunciante") -> list[AppUser]:
    return [add_user(db, f"{prefix}{i}") for i in range(count)]


def _list(client, admin: AppUser, **params) -> dict:
    resp = client.get(REPORTS, params=params, headers=auth_headers(admin))
    assert resp.status_code == 200, resp.text
    return resp.json()


def _ids(page: dict) -> list[str]:
    return [item["target_id"] for item in page["items"]]


def test_empty_queue_returns_no_items(client, admin_user):
    assert _list(client, admin_user) == {"items": [], "total": 0}


def test_three_open_reports_on_same_recorda_become_one_item(client, db, admin_user):
    recorda = add_recorda(db, add_user(db, "autor"))
    for minutes, reporter in zip((0, 5, 10), _reporters(db, 3), strict=True):
        add_report(db, reporter, recorda=recorda, created_at=_at(minutes))

    page = _list(client, admin_user)

    assert page["total"] == 1
    [item] = page["items"]
    assert item["target_type"] == "RECORDA"
    assert item["target_id"] == str(recorda.recorda_id)
    assert item["status"] == "OPEN"
    assert item["report_count"] == 3
    assert _utc(item["first_reported_at"]) == _at(0)
    assert _utc(item["last_reported_at"]) == _at(10)


def test_target_type_user_lists_only_profile_reports(client, db, admin_user):
    reporter = add_user(db, "denunciante")
    author = add_user(db, "autor")
    add_report(db, reporter, recorda=add_recorda(db, author))
    add_report(db, reporter, reported_user=author)

    page = _list(client, admin_user, target_type="USER")

    assert _ids(page) == [str(author.user_id)]
    assert page["items"][0]["target_type"] == "USER"
    assert page["total"] == 1


def test_target_type_recorda_lists_only_recorda_reports(client, db, admin_user):
    reporter = add_user(db, "denunciante")
    author = add_user(db, "autor")
    recorda = add_recorda(db, author)
    add_report(db, reporter, recorda=recorda)
    add_report(db, reporter, reported_user=author)

    page = _list(client, admin_user, target_type="RECORDA")

    assert _ids(page) == [str(recorda.recorda_id)]


def test_status_filter_and_open_by_default(client, db, admin_user):
    reporter = add_user(db, "denunciante")
    author = add_user(db, "autor")
    open_recorda = add_recorda(db, author)
    resolved_recorda = add_recorda(db, author)
    dismissed_recorda = add_recorda(db, author)
    add_report(db, reporter, recorda=open_recorda)
    add_report(db, reporter, recorda=resolved_recorda, status=STATUS_RESOLVED)
    add_report(db, reporter, recorda=dismissed_recorda, status=STATUS_DISMISSED)

    assert _ids(_list(client, admin_user)) == [str(open_recorda.recorda_id)]
    assert _ids(_list(client, admin_user, status="RESOLVED")) == [
        str(resolved_recorda.recorda_id)
    ]
    assert _ids(_list(client, admin_user, status="DISMISSED")) == [
        str(dismissed_recorda.recorda_id)
    ]


def test_count_only_includes_reports_in_the_filtered_status(client, db, admin_user):
    recorda = add_recorda(db, add_user(db, "autor"))
    first, second, third = _reporters(db, 3)
    add_report(db, first, recorda=recorda)
    add_report(db, second, recorda=recorda)
    add_report(db, third, recorda=recorda, status=STATUS_RESOLVED)

    [open_group] = _list(client, admin_user)["items"]
    [resolved_group] = _list(client, admin_user, status="RESOLVED")["items"]

    assert open_group["report_count"] == 2
    assert resolved_group["report_count"] == 1


def test_order_asc_inverts_order_by_last_reported_at(client, db, admin_user):
    reporter = add_user(db, "denunciante")
    author = add_user(db, "autor")
    recordas = [add_recorda(db, author) for _ in range(3)]
    for minutes, recorda in zip((0, 10, 20), recordas, strict=True):
        add_report(db, reporter, recorda=recorda, created_at=_at(minutes))
    oldest_first = [str(recorda.recorda_id) for recorda in recordas]

    assert _ids(_list(client, admin_user)) == oldest_first[::-1]
    assert _ids(_list(client, admin_user, order="asc")) == oldest_first


@pytest.mark.parametrize("order", ["desc", "asc"])
def test_pagination_is_stable_on_ties(client, db, admin_user, order):
    reporter = add_user(db, "denunciante")
    author = add_user(db, "autor")
    for _ in range(5):
        add_report(db, reporter, recorda=add_recorda(db, author), created_at=_at(0))

    full = _list(client, admin_user, order=order, limit=50)
    pages = [
        _list(client, admin_user, order=order, limit=2, offset=offset)
        for offset in (0, 2, 4)
    ]
    paged_ids = [target_id for page in pages for target_id in _ids(page)]

    assert paged_ids == _ids(full)
    assert len(set(paged_ids)) == 5
    assert paged_ids == sorted(paged_ids, reverse=order == "desc")
    assert {page["total"] for page in pages} == {5}


def test_group_of_deleted_recorda_is_still_listed_with_preview(client, db, admin_user):
    recorda = add_recorda(db, add_user(db, "autor"), song_title="Removida")
    add_report(db, add_user(db, "denunciante"), recorda=recorda)
    recorda.deleted_at = now_utc()
    db.commit()

    [item] = _list(client, admin_user)["items"]

    assert item["target_id"] == str(recorda.recorda_id)
    assert item["preview"]["title"] == "Removida"
    assert item["preview"]["subtitle"] == "@autor"


def test_recorda_preview_uses_photo_and_author(client, db, admin_user):
    recorda = add_recorda(
        db,
        add_user(db, "autor"),
        song_title="Song of Silence",
        media_url="/api/v1/recordas/media/foto.jpg",
    )
    add_report(db, add_user(db, "denunciante"), recorda=recorda)

    [item] = _list(client, admin_user)["items"]

    assert item["preview"] == {
        "title": "Song of Silence",
        "subtitle": "@autor",
        "image_url": "/api/v1/recordas/media/foto.jpg",
    }


def test_video_recorda_preview_uses_song_cover(client, db, admin_user):
    recorda = add_recorda(
        db,
        add_user(db, "autor"),
        media_type=VIDEO,
        media_url="/api/v1/recordas/media/video.mp4",
        song_cover_url="https://e.deezer.com/capa.jpg",
    )
    add_report(db, add_user(db, "denunciante"), recorda=recorda)

    [item] = _list(client, admin_user)["items"]

    assert item["preview"]["image_url"] == "https://e.deezer.com/capa.jpg"


def test_user_preview_uses_name_username_and_picture(client, db, admin_user):
    reported = add_user(
        db,
        "denunciado",
        name="Fulano de Tal",
        profile_picture_url="https://cdn.example.com/fulano.jpg",
    )
    add_report(db, add_user(db, "denunciante"), reported_user=reported)

    [item] = _list(client, admin_user)["items"]

    assert item["preview"] == {
        "title": "Fulano de Tal",
        "subtitle": "@denunciado",
        "image_url": "https://cdn.example.com/fulano.jpg",
    }


def test_comment_reports_are_not_listed(client, db, admin_user):
    author = add_user(db, "autor")
    comment = add_comment(db, author, add_recorda(db, author))
    db.add(
        Report(
            reporter_id=add_user(db, "denunciante").user_id,
            comment_id=comment.comment_id,
        )
    )
    db.commit()

    assert _list(client, admin_user) == {"items": [], "total": 0}


def test_previews_are_loaded_without_n_plus_one(client, db, admin_user):
    author = add_user(db, "autor")
    reporters = _reporters(db, 4)

    def add_groups(start: int, count: int) -> None:
        for i in range(start, start + count):
            add_report(db, reporters[0], recorda=add_recorda(db, author))
            add_report(db, reporters[0], reported_user=add_user(db, f"alvo{i}"))

    add_groups(0, 1)
    few = _count_selects(db, lambda: _list(client, admin_user))
    add_groups(1, 4)
    many = _count_selects(db, lambda: _list(client, admin_user))

    assert many == few


def _count_selects(db: Session, call: Callable[[], object]) -> int:
    statements: list[str] = []

    def record(_conn, _cursor, statement, *_args) -> None:
        statements.append(statement)

    engine = db.get_bind()
    event.listen(engine, "before_cursor_execute", record)
    try:
        call()
    finally:
        event.remove(engine, "before_cursor_execute", record)

    return sum(
        1 for statement in statements if statement.lstrip().upper().startswith("SELECT")
    )


@pytest.mark.parametrize(
    "params",
    [
        {"status": "ALL"},
        {"target_type": "COMMENT"},
        {"order": "up"},
        {"limit": 0},
        {"limit": 51},
        {"offset": -1},
    ],
)
def test_invalid_query_params_return_422(client, admin_user, params):
    resp = client.get(REPORTS, params=params, headers=auth_headers(admin_user))

    assert resp.status_code == 422
