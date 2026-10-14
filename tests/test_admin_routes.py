from app.models.app_user import ROLE_ADMIN, STATUS_ACTIVE, STATUS_SUSPENDED
from app.models.report import STATUS_RESOLVED
from tests.factories import add_report, add_user, auth_headers


def suspend_url(target) -> str:
    return f"/api/v1/admin/users/{target.user_id}/suspend"


def reactivate_url(target) -> str:
    return f"/api/v1/admin/users/{target.user_id}/reactivate"


def test_suspend_user(client, db):
    admin_user = add_user(db, "admin_user", role=ROLE_ADMIN)
    admin_headers = auth_headers(admin_user)

    suspend_target = add_user(db, "suspend_target", status=STATUS_SUSPENDED)
    target = add_user(db, "target_user")
    payload = {"reason": "Reactivating user"}

    self_suspend = client.post(
        suspend_url(admin_user), json=payload, headers=admin_headers
    )

    unknown_user = client.post(
        "/api/v1/admin/users/00000000-0000-0000-0000-000000000000/suspend",
        json=payload,
        headers=admin_headers,
    )

    first_suspend = client.post(
        suspend_url(target), json=payload, headers=admin_headers
    )

    already_suspended = client.post(
        suspend_url(suspend_target),
        json=payload,
        headers=admin_headers,
    )

    assert self_suspend.status_code == 400
    assert unknown_user.status_code == 404
    assert first_suspend.status_code == 200
    assert already_suspended.status_code == 409


def test_reactivate_user(client, db):
    admin_user = add_user(db, "admin_user", role=ROLE_ADMIN)
    admin_headers = auth_headers(admin_user)
    suspend_target = add_user(db, "suspend_target", status=STATUS_SUSPENDED)
    target = add_user(db, "target_user")
    payload = {"reason": "Reactivating user"}

    unknown_user = client.post(
        "/api/v1/admin/users/00000000-0000-0000-0000-000000000000/reactivate",
        json=payload,
        headers=admin_headers,
    )

    first_reactivate = client.post(
        reactivate_url(suspend_target),
        json=payload,
        headers=admin_headers,
    )

    not_suspended = client.post(
        reactivate_url(target),
        json=payload,
        headers=admin_headers,
    )

    assert unknown_user.status_code == 404
    assert first_reactivate.status_code == 200
    assert not_suspended.status_code == 409


def test_suspend_and_reactivate_require_authentication(client, common_user):
    assert client.post(suspend_url(common_user)).status_code == 401
    assert client.post(reactivate_url(common_user)).status_code == 401


def test_suspend_and_reactivate_require_admin(client, db):
    common_user = add_user(db, "common_user")
    common_headers = auth_headers(common_user)
    target_user = add_user(db, "target_user")
    payload = {"reason": "Testing"}

    suspend_response = client.post(
        suspend_url(target_user), json=payload, headers=common_headers
    )
    reactivate_response = client.post(
        reactivate_url(target_user), json=payload, headers=common_headers
    )

    assert suspend_response.status_code == 403
    assert reactivate_response.status_code == 403


def test_suspend_and_reactivate_require_reason(client, db):
    admin_user = add_user(db, "admin_user", role=ROLE_ADMIN)
    admin_headers = auth_headers(admin_user)
    target_user = add_user(db, "target_user")

    suspend_response_empty = client.post(
        suspend_url(target_user), json={"reason": ""}, headers=admin_headers
    )
    suspend_response_full = client.post(
        suspend_url(target_user),
        json={
            "reason": "Test reason abcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyz"
        },
        headers=admin_headers,
    )
    reactivate_response_empty = client.post(
        reactivate_url(target_user), json={"reason": ""}, headers=admin_headers
    )
    reactivate_response_full = client.post(
        reactivate_url(target_user),
        json={
            "reason": "Test reason abcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyz"
        },
        headers=admin_headers,
    )

    assert suspend_response_empty.status_code == 422
    assert suspend_response_full.status_code == 422
    assert reactivate_response_empty.status_code == 422
    assert reactivate_response_full.status_code == 422


def test_suspend_and_reactivate_return_user_status(client, db):
    admin_user = add_user(db, "admin_user", role=ROLE_ADMIN)
    admin_headers = auth_headers(admin_user)
    target_user = add_user(db, "target_user")

    suspend_response = client.post(
        suspend_url(target_user),
        json={"reason": "Suspending user"},
        headers=admin_headers,
    )
    assert suspend_response.status_code == 200
    assert suspend_response.json()["status"] == STATUS_SUSPENDED

    reactivate_response = client.post(
        reactivate_url(target_user),
        json={"reason": "Reactivating user"},
        headers=admin_headers,
    )
    assert reactivate_response.status_code == 200
    assert reactivate_response.json()["status"] == STATUS_ACTIVE


def test_resolving_reports_on_suspend(client, db):
    admin_user = add_user(db, "admin_user", role=ROLE_ADMIN)
    admin_headers = auth_headers(admin_user)
    reporter = add_user(db, "reporter")
    target_user = add_user(db, "reported_target")

    report = add_report(db, reporter=reporter, reported_user=target_user)

    suspend_response = client.post(
        suspend_url(target_user),
        json={"reason": "Suspending user"},
        headers=admin_headers,
    )
    assert suspend_response.status_code == 200

    db.refresh(report)
    assert report.status == STATUS_RESOLVED
    assert report.resolved_at is not None


def test_admin_suspend_invalidates_existing_user_token(client, db):
    admin_user = add_user(db, "admin_user", role=ROLE_ADMIN)
    target_user = add_user(db, "target_user")
    admin_headers = auth_headers(admin_user)
    target_headers = auth_headers(target_user)

    suspend_response = client.post(
        suspend_url(target_user),
        json={"reason": "Suspending user"},
        headers=admin_headers,
    )
    assert suspend_response.status_code == 200

    profile_response = client.get(
        "/api/v1/users/me/profile",
        headers=target_headers,
    )
    assert profile_response.status_code == 401
