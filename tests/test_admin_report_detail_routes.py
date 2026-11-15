"""Acceptance tests for the administrative detail of a reported target (#85)."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from app.core.time import now_utc
from app.models import ModerationAction, Report
from tests.factories import (
    add_moderation_action,
    add_recorda,
    add_report,
    add_user,
    auth_headers,
)


def detail_url(target_type: str, target_id: UUID | str) -> str:
    return f"/api/v1/admin/reports/{target_type}/{target_id}"


def as_utc(value: str) -> datetime:
    # SQLite returns naive timestamps; the application's dates are UTC.
    parsed = datetime.fromisoformat(value)
    return (
        parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)
    )


def test_admin_can_view_private_recorda_without_following(client, db, admin_user):
    author = add_user(db, "private_author", is_private=True)
    recorda = add_recorda(db, author)
    add_report(db, add_user(db, "reporter"), recorda=recorda)

    response = client.get(
        detail_url("RECORDA", recorda.recorda_id), headers=auth_headers(admin_user)
    )

    assert response.status_code == 200
    target = response.json()["target"]
    assert target["recorda_id"] == str(recorda.recorda_id)
    assert target["media_url"] == recorda.media_url
    assert target["description"] == recorda.description
    assert target["song_title"] == recorda.song_title
    assert target["song_artist_name"] == recorda.song_artist_name
    assert target["song_cover_url"] == recorda.song_cover_url
    assert target["author"]["username"] == author.username
    assert target["author"]["status"] == "ACTIVE"
    assert response.json()["actions"] == []


def test_deleted_suspended_user_remains_visible(client, db, admin_user):
    created_at = datetime(2026, 9, 1, 12, 30, tzinfo=UTC)
    deleted_at = datetime(2026, 10, 1, 15, 45, tzinfo=UTC)
    user = add_user(
        db,
        "removed_user",
        status="SUSPENDED",
        created_at=created_at,
        deleted_at=deleted_at,
    )
    add_report(db, add_user(db, "reporter"), reported_user=user)

    response = client.get(
        detail_url("USER", user.user_id), headers=auth_headers(admin_user)
    )

    assert response.status_code == 200
    target = response.json()["target"]
    assert target["user_id"] == str(user.user_id)
    assert target["status"] == "SUSPENDED"
    assert as_utc(target["deleted_at"]) == deleted_at
    assert target["email"] == user.email
    assert as_utc(target["created_at"]) == created_at
    assert "password_hash" not in target


@pytest.mark.parametrize("target_type", ["RECORDA", "USER"])
def test_actions_match_target_and_are_newest_first(client, db, admin_user, target_type):
    author = add_user(db, "author")
    recorda = add_recorda(db, author)
    reporter = add_user(db, "reporter")
    add_report(db, reporter, recorda=recorda)
    add_report(db, reporter, reported_user=author)
    base = datetime(2026, 10, 1, tzinfo=UTC)
    removed = add_moderation_action(
        db,
        admin_user,
        action_type="REMOVE_RECORDA",
        target_recorda=recorda,
        target_user=author,
        created_at=base,
        reason="Conteúdo ofensivo",
        details={"source": "report"},
    )
    other_recorda = add_recorda(db, author)
    user_action = add_moderation_action(
        db,
        admin_user,
        target_user=author,
        target_recorda=other_recorda,
        created_at=base + timedelta(days=1),
    )
    add_moderation_action(db, admin_user, target_user=add_user(db, "other_target"))

    target_id = recorda.recorda_id if target_type == "RECORDA" else author.user_id
    response = client.get(
        detail_url(target_type, target_id), headers=auth_headers(admin_user)
    )

    assert response.status_code == 200
    actions = response.json()["actions"]
    expected = (
        [str(removed.action_id)]
        if target_type == "RECORDA"
        else [str(user_action.action_id), str(removed.action_id)]
    )
    assert [action["action_id"] for action in actions] == expected
    expected_dates = (
        [base] if target_type == "RECORDA" else [base + timedelta(days=1), base]
    )
    assert [as_utc(action["created_at"]) for action in actions] == expected_dates
    assert actions[-1]["admin"]["username"] == admin_user.username
    assert actions[-1]["reason"] == "Conteúdo ofensivo"
    assert actions[-1]["details"] == {"source": "report"}
    assert actions[-1]["target_label"] == recorda.song_title


@pytest.mark.parametrize("target_type", ["RECORDA", "USER"])
def test_reports_include_all_statuses_and_only_selected_target(
    client, db, admin_user, target_type
):
    author = add_user(db, "author")
    recorda = add_recorda(db, author)
    base = datetime(2026, 10, 1, tzinfo=UTC)
    reports = []
    for index, status in enumerate(("OPEN", "RESOLVED", "DISMISSED")):
        reporter = add_user(db, f"reporter{index}", deleted_at=now_utc())
        kwargs = (
            {"recorda": recorda}
            if target_type == "RECORDA"
            else {"reported_user": author}
        )
        report = add_report(
            db,
            reporter,
            **kwargs,
            status=status,
            description="Spam" if index == 1 else None,
            created_at=base + timedelta(hours=index),
        )
        if status != "OPEN":
            report.resolved_at = base + timedelta(days=1, hours=index)
            db.commit()
        reports.append(report)
    unrelated = add_user(db, "unrelated")
    add_report(db, unrelated, recorda=add_recorda(db, author))
    add_report(db, unrelated, reported_user=add_user(db, "other_user"))
    # The other target type must not leak into this detail.
    add_report(
        db,
        unrelated,
        **(
            {"reported_user": author}
            if target_type == "RECORDA"
            else {"recorda": recorda}
        ),
    )
    target_id = recorda.recorda_id if target_type == "RECORDA" else author.user_id

    response = client.get(
        detail_url(target_type, target_id), headers=auth_headers(admin_user)
    )

    assert response.status_code == 200
    items = response.json()["reports"]
    assert [item["report_id"] for item in items] == [
        str(report.report_id) for report in reports[::-1]
    ]
    assert [item["status"] for item in items] == ["DISMISSED", "RESOLVED", "OPEN"]
    assert [item["description"] for item in items] == [None, "Spam", None]
    assert [item["reporter"]["username"] for item in items] == [
        "reporter2",
        "reporter1",
        "reporter0",
    ]
    assert [as_utc(item["created_at"]) for item in items] == [
        datetime(2026, 10, 1, 2, tzinfo=UTC),
        datetime(2026, 10, 1, 1, tzinfo=UTC),
        datetime(2026, 10, 1, tzinfo=UTC),
    ]
    assert as_utc(items[0]["resolved_at"]) == datetime(2026, 10, 2, 2, tzinfo=UTC)
    assert as_utc(items[1]["resolved_at"]) == datetime(2026, 10, 2, 1, tzinfo=UTC)
    assert items[2]["resolved_at"] is None


def test_removed_recorda_and_deleted_suspended_author_are_visible(
    client, db, admin_user
):
    author_deleted_at = datetime(2026, 10, 2, 12, tzinfo=UTC)
    recorda_deleted_at = datetime(2026, 10, 1, 18, tzinfo=UTC)
    recorda_created_at = datetime(2026, 9, 1, 10, tzinfo=UTC)
    author = add_user(
        db, "removed_author", status="SUSPENDED", deleted_at=author_deleted_at
    )
    recorda = add_recorda(
        db,
        author,
        deleted_at=recorda_deleted_at,
        created_at=recorda_created_at,
        media_type="VIDEO",
        song_preview_url="https://example.com/expired.mp3",
    )
    add_report(db, add_user(db, "reporter"), recorda=recorda, status="RESOLVED")

    response = client.get(
        detail_url("RECORDA", recorda.recorda_id), headers=auth_headers(admin_user)
    )

    assert response.status_code == 200
    target = response.json()["target"]
    assert as_utc(target["deleted_at"]) == recorda_deleted_at
    assert as_utc(target["created_at"]) == recorda_created_at
    assert as_utc(target["author"]["deleted_at"]) == author_deleted_at
    assert target["author"]["status"] == "SUSPENDED"
    assert target["media_type"] == "VIDEO"
    assert (
        target["song_preview_url"]
        == f"/api/v1/music/tracks/{recorda.deezer_track_id}/preview"
    )


@pytest.mark.parametrize("target_type", ["RECORDA", "USER"])
@pytest.mark.parametrize("exists", [False, True])
def test_target_without_reports_returns_exact_404(
    client, db, admin_user, target_type, exists
):
    target_id = UUID("00000000-0000-0000-0000-000000000001")
    if exists:
        user = add_user(db, "target")
        recorda = add_recorda(db, user)
        target_id = recorda.recorda_id if target_type == "RECORDA" else user.user_id
        add_moderation_action(db, admin_user, target_user=user, target_recorda=recorda)

    response = client.get(
        detail_url(target_type, target_id), headers=auth_headers(admin_user)
    )

    assert response.status_code == 404
    assert response.json()["error"]["message"] == "Nenhuma denúncia para este alvo."


@pytest.mark.parametrize(
    ("target_type", "target_id"),
    [
        ("COMMENT", "00000000-0000-0000-0000-000000000001"),
        ("recorda", "00000000-0000-0000-0000-000000000001"),
        ("RECORDA", "not-a-uuid"),
    ],
)
def test_invalid_path_params_return_422(client, admin_user, target_type, target_id):
    response = client.get(
        detail_url(target_type, target_id), headers=auth_headers(admin_user)
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.parametrize("target_type", ["RECORDA", "USER"])
@pytest.mark.parametrize("collection", ["reports", "actions"])
def test_equal_dates_are_ordered_by_id_descending(
    client, db, admin_user, target_type, collection
):
    author = add_user(db, "author")
    recorda = add_recorda(db, author)
    target_id = recorda.recorda_id if target_type == "RECORDA" else author.user_id
    base = datetime(2026, 10, 1, 12, 30, 45, 123456, tzinfo=UTC)
    # Fixed IDs deliberately oppose date order and differ from insertion order.
    ids = {
        number: UUID(f"00000000-0000-0000-0000-{number:012d}")
        for number in (0, 1, 2, 3, 9)
    }
    for number, created_at in (
        (2, base),
        (1, base),
        (3, base),
        (9, base - timedelta(days=1)),
        (0, base + timedelta(days=1)),
    ):
        reporter = add_user(db, f"reporter{number}")
        if collection == "reports":
            row = Report(
                report_id=ids[number],
                reporter_id=reporter.user_id,
                recorda_id=recorda.recorda_id if target_type == "RECORDA" else None,
                reported_user_id=author.user_id if target_type == "USER" else None,
                created_at=created_at,
            )
        else:
            row = ModerationAction(
                action_id=ids[number],
                admin_id=admin_user.user_id,
                action_type="CHANGE_REPORT_STATUS",
                reason="Motivo de teste",
                target_recorda_id=recorda.recorda_id
                if target_type == "RECORDA"
                else None,
                target_user_id=author.user_id if target_type == "USER" else None,
                created_at=created_at,
            )
        db.add(row)
        db.commit()
    if collection == "actions":
        reporter = add_user(db, "detail_reporter")
        add_report(
            db,
            reporter,
            **(
                {"recorda": recorda}
                if target_type == "RECORDA"
                else {"reported_user": author}
            ),
        )

    response = client.get(
        detail_url(target_type, target_id), headers=auth_headers(admin_user)
    )

    assert response.status_code == 200
    items = response.json()[collection]
    id_field = "report_id" if collection == "reports" else "action_id"
    assert [item[id_field] for item in items] == [
        str(ids[number]) for number in (0, 3, 2, 1, 9)
    ]
    assert [as_utc(item["created_at"]) for item in items] == [
        base + timedelta(days=1),
        base,
        base,
        base,
        base - timedelta(days=1),
    ]
