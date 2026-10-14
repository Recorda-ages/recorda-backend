"""Consulta do log de auditoria: GET /admin/audit-log e GET /admin/admins (T-E10.US47.BE.02)."""

from datetime import UTC, datetime, timedelta

import pytest

from app.core.time import now_utc
from app.models.app_user import ROLE_ADMIN
from app.models.moderation_action import (
    ACTION_CHANGE_REPORT_STATUS,
    ACTION_REMOVE_RECORDA,
    ACTION_SUSPEND_USER,
)
from tests.factories import add_moderation_action, add_recorda, add_user, auth_headers

AUDIT_LOG = "/api/v1/admin/audit-log"
ADMINS = "/api/v1/admin/admins"


@pytest.fixture
def target(db):
    return add_user(db, "alvo")


def _get(client, admin, **params):
    return client.get(AUDIT_LOG, params=params, headers=auth_headers(admin))


def test_entry_shows_who_what_target_when_and_reason(client, db, admin_user, target):
    action = add_moderation_action(
        db, admin_user, target_user=target, reason="Spam reiterado"
    )

    resp = _get(client, admin_user)

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    entry = body["items"][0]
    assert entry["action_id"] == str(action.action_id)
    assert entry["action_type"] == ACTION_SUSPEND_USER
    assert entry["admin"] == {
        "user_id": str(admin_user.user_id),
        "username": "usuario_admin",
    }
    assert entry["target_user_id"] == str(target.user_id)
    assert entry["target_recorda_id"] is None
    assert entry["target_label"] == "alvo"
    assert entry["reason"] == "Spam reiterado"
    assert entry["created_at"]


def test_remove_recorda_is_labeled_by_song_title_and_keeps_details(
    client, db, admin_user
):
    author = add_user(db, "autor")
    recorda = add_recorda(db, author, song_title="Hurt")
    add_moderation_action(
        db,
        admin_user,
        action_type=ACTION_REMOVE_RECORDA,
        target_recorda=recorda,
        target_user=author,
    )
    details = {"from": "OPEN", "to": "DISMISSED", "report_count": 3}
    add_moderation_action(
        db,
        admin_user,
        action_type=ACTION_CHANGE_REPORT_STATUS,
        target_recorda=recorda,
        details=details,
    )

    items = _get(client, admin_user).json()["items"]

    assert [item["target_label"] for item in items] == ["Hurt", "Hurt"]
    assert {item["action_type"]: item["details"] for item in items}[
        ACTION_CHANGE_REPORT_STATUS
    ] == details


def test_deleted_admin_and_targets_are_still_labeled(client, db, admin_user):
    gone_admin = add_user(db, "ex_admin", role=ROLE_ADMIN)
    author = add_user(db, "autor")
    recorda = add_recorda(db, author, song_title="Hurt")
    add_moderation_action(db, gone_admin, target_user=author)
    add_moderation_action(
        db, gone_admin, action_type=ACTION_REMOVE_RECORDA, target_recorda=recorda
    )
    for row in (gone_admin, author, recorda):
        row.deleted_at = now_utc()
    db.commit()

    items = _get(client, admin_user).json()["items"]

    assert {item["admin"]["username"] for item in items} == {"ex_admin"}
    assert sorted(item["target_label"] for item in items) == ["Hurt", "autor"]


def test_admin_filter_returns_only_that_admins_actions(client, db, admin_user, target):
    other = add_user(db, "outro_admin", role=ROLE_ADMIN)
    mine = add_moderation_action(db, admin_user, target_user=target)
    add_moderation_action(db, other, target_user=target)

    body = _get(client, admin_user, admin_id=str(admin_user.user_id)).json()

    assert body["total"] == 1
    assert [item["action_id"] for item in body["items"]] == [str(mine.action_id)]


def test_action_type_filter(client, db, admin_user, target):
    add_moderation_action(db, admin_user, target_user=target)
    author = add_user(db, "autor")
    removed = add_moderation_action(
        db,
        admin_user,
        action_type=ACTION_REMOVE_RECORDA,
        target_recorda=add_recorda(db, author),
    )

    body = _get(client, admin_user, action_type=ACTION_REMOVE_RECORDA).json()

    assert [item["action_id"] for item in body["items"]] == [str(removed.action_id)]


def test_unknown_action_type_returns_422(client, admin_user):
    assert _get(client, admin_user, action_type="DELETE_ALL").status_code == 422


def test_period_respects_the_sao_paulo_day(client, db, admin_user, target):
    """23:30 de 18/09 em São Paulo é 02:30 de 19/09 em UTC: pertence ao dia 18."""
    late_night = add_moderation_action(
        db,
        admin_user,
        target_user=target,
        created_at=datetime(2026, 9, 19, 2, 30, tzinfo=UTC),
    )
    # 00:00 local de 18/09, o primeiro instante incluído.
    first_instant = add_moderation_action(
        db,
        admin_user,
        target_user=target,
        created_at=datetime(2026, 9, 18, 3, 0, tzinfo=UTC),
    )
    # 23:59 local de 17/09, fora do período.
    add_moderation_action(
        db,
        admin_user,
        target_user=target,
        created_at=datetime(2026, 9, 18, 2, 59, tzinfo=UTC),
    )

    on_18 = _get(client, admin_user, date_from="2026-09-18", date_to="2026-09-18")
    on_19 = _get(client, admin_user, date_from="2026-09-19", date_to="2026-09-19")

    assert [item["action_id"] for item in on_18.json()["items"]] == [
        str(late_night.action_id),
        str(first_instant.action_id),
    ]
    assert on_19.json()["total"] == 0


def test_open_ended_periods(client, db, admin_user, target):
    base = datetime(2026, 9, 18, 15, 0, tzinfo=UTC)
    older = add_moderation_action(
        db, admin_user, target_user=target, created_at=base - timedelta(days=2)
    )
    newer = add_moderation_action(db, admin_user, target_user=target, created_at=base)

    since = _get(client, admin_user, date_from="2026-09-18").json()["items"]
    until = _get(client, admin_user, date_to="2026-09-17").json()["items"]

    assert [item["action_id"] for item in since] == [str(newer.action_id)]
    assert [item["action_id"] for item in until] == [str(older.action_id)]


def test_date_from_after_date_to_returns_422(client, admin_user):
    resp = _get(client, admin_user, date_from="2026-09-19", date_to="2026-09-18")

    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"
    assert resp.json()["error"]["details"]["fields"][0]["field"] == "date_from"


def test_orders_newest_first_and_paginates_with_total(client, db, admin_user, target):
    base = now_utc()
    actions = [
        add_moderation_action(
            db, admin_user, target_user=target, created_at=base - timedelta(hours=i)
        )
        for i in range(5)
    ]
    same_instant = [
        add_moderation_action(
            db, admin_user, target_user=target, created_at=base + timedelta(hours=1)
        )
        for _ in range(2)
    ]

    first = _get(client, admin_user, limit=4, offset=0).json()
    second = _get(client, admin_user, limit=4, offset=4).json()

    assert first["total"] == second["total"] == 7
    ids = [item["action_id"] for item in first["items"] + second["items"]]
    tie = sorted((str(a.action_id) for a in same_instant), reverse=True)
    assert ids == tie + [str(a.action_id) for a in actions]


@pytest.mark.parametrize("method", ["PUT", "PATCH", "DELETE"])
def test_audit_entries_cannot_be_edited_or_deleted(
    client, db, admin_user, target, method
):
    action = add_moderation_action(db, admin_user, target_user=target)

    for path in (f"{AUDIT_LOG}/{action.action_id}", AUDIT_LOG):
        resp = client.request(method, path, headers=auth_headers(admin_user))
        assert resp.status_code in (404, 405)

    assert _get(client, admin_user).json()["total"] == 1


def test_admins_lists_every_admin_account(client, db, admin_user, common_user):
    gone = add_user(db, "ex_admin", role=ROLE_ADMIN)
    gone.deleted_at = now_utc()
    db.commit()

    resp = client.get(ADMINS, headers=auth_headers(admin_user))

    assert resp.status_code == 200
    assert resp.json() == [
        {"user_id": str(gone.user_id), "username": "ex_admin"},
        {"user_id": str(admin_user.user_id), "username": "usuario_admin"},
    ]
