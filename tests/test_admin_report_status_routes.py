"""Tests for PATCH /api/v1/admin/reports/{target_type}/{target_id}/status (T-E10.US46.BE.01)."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from app.models.report import STATUS_DISMISSED, STATUS_OPEN, STATUS_RESOLVED
from tests.factories import (
    add_recorda,
    add_report,
    add_user,
    auth_headers,
)

BASE_URL = "/api/v1/admin/reports"


def _patch_url(target_type: str, target_id) -> str:
    return f"{BASE_URL}/{target_type}/{target_id}/status"


def _change(client, admin, target_type, target_id, status, reason="Motivo válido"):
    return client.patch(
        _patch_url(target_type, target_id),
        json={"status": status, "reason": reason},
        headers=auth_headers(admin),
    )


# ---------------------------------------------------------------------------
# DISMISS group (OPEN → DISMISSED)
# ---------------------------------------------------------------------------


def test_dismiss_three_open_reports_changes_all_to_dismissed(client, db, admin_user):
    author = add_user(db, "autor")
    recorda = add_recorda(db, author)
    reporters = [add_user(db, f"rep{i}") for i in range(3)]
    for reporter in reporters:
        add_report(db, reporter, recorda=recorda)

    resp = _change(client, admin_user, "RECORDA", recorda.recorda_id, "DISMISSED")

    assert resp.status_code == 200
    body = resp.json()
    assert body["updated_count"] == 3
    assert body["status"] == "DISMISSED"

    db.expire_all()
    from app.models import Report
    reports = db.query(Report).filter_by(recorda_id=recorda.recorda_id).all()
    assert all(r.status == STATUS_DISMISSED for r in reports)
    assert all(r.resolved_at is not None for r in reports)


def test_dismiss_creates_single_audit_record_with_report_count(client, db, admin_user):
    author = add_user(db, "autor")
    recorda = add_recorda(db, author)
    reporters = [add_user(db, f"rep{i}") for i in range(3)]
    for reporter in reporters:
        add_report(db, reporter, recorda=recorda)

    _change(client, admin_user, "RECORDA", recorda.recorda_id, "DISMISSED")

    from app.models.moderation_action import ModerationAction
    actions = db.query(ModerationAction).all()
    assert len(actions) == 1
    action = actions[0]
    assert action.action_type == "CHANGE_REPORT_STATUS"
    assert action.details["report_count"] == 3
    assert action.details["from"] == "OPEN"
    assert action.details["to"] == "DISMISSED"
    assert action.details["target_type"] == "RECORDA"
    assert action.target_recorda_id == recorda.recorda_id


def test_resolve_open_reports_on_user_target(client, db, admin_user):
    reported_user = add_user(db, "alvo")
    reporters = [add_user(db, f"rep{i}") for i in range(2)]
    for reporter in reporters:
        add_report(db, reporter, reported_user=reported_user)

    resp = _change(client, admin_user, "USER", reported_user.user_id, "RESOLVED")

    assert resp.status_code == 200
    body = resp.json()
    assert body["updated_count"] == 2
    assert body["status"] == "RESOLVED"

    from app.models.moderation_action import ModerationAction
    action = db.query(ModerationAction).one()
    assert action.target_user_id == reported_user.user_id
    assert action.target_recorda_id is None
    assert action.details["report_count"] == 2
    assert action.details["from"] == "OPEN"
    assert action.details["to"] == "RESOLVED"


# ---------------------------------------------------------------------------
# REOPEN group (RESOLVED/DISMISSED → OPEN)
# ---------------------------------------------------------------------------


def test_reopen_clears_resolved_at_and_restores_open_status(client, db, admin_user):
    author = add_user(db, "autor")
    recorda = add_recorda(db, author)
    reporters = [add_user(db, f"rep{i}") for i in range(2)]
    add_report(db, reporters[0], recorda=recorda, status=STATUS_RESOLVED)
    add_report(db, reporters[1], recorda=recorda, status=STATUS_DISMISSED)

    resp = _change(client, admin_user, "RECORDA", recorda.recorda_id, "OPEN")

    assert resp.status_code == 200
    body = resp.json()
    assert body["updated_count"] == 2
    assert body["status"] == "OPEN"

    db.expire_all()
    from app.models import Report
    reports = db.query(Report).filter_by(recorda_id=recorda.recorda_id).all()
    assert all(r.status == STATUS_OPEN for r in reports)
    assert all(r.resolved_at is None for r in reports)


def test_reopen_does_not_affect_already_open_reports(client, db, admin_user):
    author = add_user(db, "autor")
    recorda = add_recorda(db, author)
    reporters = [add_user(db, f"rep{i}") for i in range(2)]
    add_report(db, reporters[0], recorda=recorda, status=STATUS_RESOLVED)
    add_report(db, reporters[1], recorda=recorda, status=STATUS_OPEN)

    resp = _change(client, admin_user, "RECORDA", recorda.recorda_id, "OPEN")

    assert resp.status_code == 200
    assert resp.json()["updated_count"] == 1


# ---------------------------------------------------------------------------
# 409 when no matching reports
# ---------------------------------------------------------------------------


def test_409_when_no_open_reports_to_dismiss(client, db, admin_user):
    author = add_user(db, "autor")
    recorda = add_recorda(db, author)
    reporter = add_user(db, "rep")
    add_report(db, reporter, recorda=recorda, status=STATUS_RESOLVED)

    resp = _change(client, admin_user, "RECORDA", recorda.recorda_id, "DISMISSED")

    assert resp.status_code == 409
    assert "Não há denúncias" in resp.json()["error"]["message"]


def test_409_when_no_closed_reports_to_reopen(client, db, admin_user):
    author = add_user(db, "autor")
    recorda = add_recorda(db, author)
    reporter = add_user(db, "rep")
    add_report(db, reporter, recorda=recorda, status=STATUS_OPEN)

    resp = _change(client, admin_user, "RECORDA", recorda.recorda_id, "OPEN")

    assert resp.status_code == 409


def test_409_when_target_has_no_reports_at_all(client, db, admin_user):
    recorda = add_recorda(db, add_user(db, "autor"))

    resp = _change(client, admin_user, "RECORDA", recorda.recorda_id, "DISMISSED")

    assert resp.status_code == 409


# ---------------------------------------------------------------------------
# Validation — 422 for missing/empty reason
# ---------------------------------------------------------------------------


def test_422_when_reason_is_absent(client, db, admin_user):
    recorda = add_recorda(db, add_user(db, "autor"))
    reporter = add_user(db, "rep")
    add_report(db, reporter, recorda=recorda)

    resp = client.patch(
        _patch_url("RECORDA", recorda.recorda_id),
        json={"status": "DISMISSED"},
        headers=auth_headers(admin_user),
    )

    assert resp.status_code == 422


def test_422_when_reason_is_empty_string(client, db, admin_user):
    recorda = add_recorda(db, add_user(db, "autor"))
    reporter = add_user(db, "rep")
    add_report(db, reporter, recorda=recorda)

    resp = client.patch(
        _patch_url("RECORDA", recorda.recorda_id),
        json={"status": "DISMISSED", "reason": ""},
        headers=auth_headers(admin_user),
    )

    assert resp.status_code == 422


def test_422_when_reason_exceeds_500_chars(client, db, admin_user):
    recorda = add_recorda(db, add_user(db, "autor"))
    reporter = add_user(db, "rep")
    add_report(db, reporter, recorda=recorda)

    resp = client.patch(
        _patch_url("RECORDA", recorda.recorda_id),
        json={"status": "DISMISSED", "reason": "x" * 501},
        headers=auth_headers(admin_user),
    )

    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Atomicity — audit failure rolls back status change
# ---------------------------------------------------------------------------


def test_status_unchanged_when_audit_recording_fails(client, db, admin_user):
    author = add_user(db, "autor")
    recorda = add_recorda(db, author)
    reporter = add_user(db, "rep")
    add_report(db, reporter, recorda=recorda)

    # Use raise_server_exceptions=False so the 500 is returned as a response,
    # not re-raised, letting us verify the DB state after a server-side failure.
    no_raise_client = TestClient(client.app, raise_server_exceptions=False)
    with patch(
        "app.services.moderation_service.moderation_action_repository.add",
        side_effect=RuntimeError("DB failure"),
    ):
        resp = no_raise_client.patch(
            _patch_url("RECORDA", recorda.recorda_id),
            json={"status": "DISMISSED", "reason": "Motivo"},
            headers=auth_headers(admin_user),
        )

    assert resp.status_code == 500

    # In production (Postgres) the uncommitted transaction is rolled back when
    # the connection is returned to the pool. In the SQLite StaticPool test
    # environment the connection is reused, so we roll back explicitly to match
    # the production semantics before asserting the DB state.
    db.rollback()

    from app.models import Report
    report = db.query(Report).filter_by(recorda_id=recorda.recorda_id).one()
    assert report.status == STATUS_OPEN
    assert report.resolved_at is None


# ---------------------------------------------------------------------------
# Auth guards
# ---------------------------------------------------------------------------


def test_unauthenticated_request_returns_401(client, db):
    recorda = add_recorda(db, add_user(db, "autor"))
    resp = client.patch(
        _patch_url("RECORDA", recorda.recorda_id),
        json={"status": "DISMISSED", "reason": "Motivo"},
    )
    assert resp.status_code == 401


def test_non_admin_request_returns_403(client, db, common_user):
    recorda = add_recorda(db, add_user(db, "autor"))
    reporter = add_user(db, "rep")
    add_report(db, reporter, recorda=recorda)

    resp = client.patch(
        _patch_url("RECORDA", recorda.recorda_id),
        json={"status": "DISMISSED", "reason": "Motivo"},
        headers=auth_headers(common_user),
    )
    assert resp.status_code == 403
