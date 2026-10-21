from app.models.app_user import ROLE_ADMIN, STATUS_ACTIVE, STATUS_SUSPENDED
from app.models.report import STATUS_RESOLVED
from tests.factories import (
    add_moderation_action,
    add_recorda,
    add_report,
    add_user,
    auth_headers,
)


def suspend_url(target) -> str:
    return f"/api/v1/admin/users/{target.user_id}/suspend"


def reactivate_url(target) -> str:
    return f"/api/v1/admin/users/{target.user_id}/reactivate"


def test_list_admin_users_returns_page_with_report_counts(client, db):
    admin_user = add_user(db, "admin_user", role=ROLE_ADMIN)
    reported_user = add_user(db, "reported_user")
    add_report(db, add_user(db, "reporter_one"), reported_user=reported_user)
    add_report(
        db,
        add_user(db, "reporter_two"),
        reported_user=reported_user,
        status=STATUS_RESOLVED,
    )

    response = client.get(
        "/api/v1/admin/users",
        params={"q": "reported"},
        headers=auth_headers(admin_user),
    )

    assert response.status_code == 200, response.text
    assert response.json() == {
        "items": [
            {
                "user_id": str(reported_user.user_id),
                "username": "reported_user",
                "name": "Reported_User",
                "email": "reported_user@example.com",
                "profile_picture_url": None,
                "role": "USER",
                "status": STATUS_ACTIVE,
                "reports_count": 2,
                "deleted_at": None,
            }
        ],
        "total": 1,
    }


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


def test_list_admin_users_requires_admin(client, db):
    common_user = add_user(db, "common_user")
    common_headers = auth_headers(common_user)

    response = client.get("/api/v1/admin/users", headers=common_headers)
    assert response.status_code == 403


def test_list_admin_users_invalid_status(client, db):
    admin_user = add_user(db, "admin_user", role=ROLE_ADMIN)
    admin_headers = auth_headers(admin_user)

    statusinvalid_response = client.get(
        "/api/v1/admin/users",
        params={"status": "INVALID_STATUS"},
        headers=admin_headers,
    )
    statusempty_response = client.get(
        "/api/v1/admin/users",
        params={"status": ""},
        headers=admin_headers,
    )
    offset_response = client.get(
        "/api/v1/admin/users",
        params={"offset": -1},
        headers=admin_headers,
    )

    limit_invalid_response = client.get(
        "/api/v1/admin/users",
        params={"limit": 100},
        headers=admin_headers,
    )
    limit_negative_response = client.get(
        "/api/v1/admin/users",
        params={"limit": -1},
        headers=admin_headers,
    )
    limit_min_response = client.get(
        "/api/v1/admin/users",
        params={"limit": 1},
        headers=admin_headers,
    )
    limit_max_response = client.get(
        "/api/v1/admin/users",
        params={"limit": 50},
        headers=admin_headers,
    )

    assert statusinvalid_response.status_code == 422
    assert statusempty_response.status_code == 422
    assert offset_response.status_code == 422
    assert limit_min_response.status_code == 200
    assert limit_max_response.status_code == 200
    assert limit_negative_response.status_code == 422
    assert limit_invalid_response.status_code == 422


def test_list_users_invalid_query(client, db):
    simbols = "!@#$%^&*()_+{}|:\"<>?[]\\;',./`~"
    admin_user = add_user(db, "admin_user", role=ROLE_ADMIN)
    admin_headers = auth_headers(admin_user)
    simbols_response = client.get(
        "/api/v1/admin/users",
        params={"q": simbols},
        headers=admin_headers,
    )
    assert simbols_response.status_code == 422


def test_get_user_requires_authentication_or_common_user(client, db):
    target_user = add_user(db, "target_user")
    admin_user = add_user(db, "admin_user", role=ROLE_ADMIN)
    admin_headers = auth_headers(admin_user)

    authentication_response = client.get(f"/api/v1/admin/users/{target_user.user_id}")

    common_user = add_user(db, "common_user")
    common_headers = auth_headers(common_user)
    common_user_response = client.get(
        f"/api/v1/admin/users/{target_user.user_id}", headers=common_headers
    )
    admin_user = add_user(db, "admin_user", role=ROLE_ADMIN)
    admin_headers = auth_headers(admin_user)
    admin_user_response = client.get(
        f"/api/v1/admin/users/{admin_user.user_id}", headers=admin_headers
    )
    deleted_user = add_user(db, "deleted_user", deleted_at="2023-01-01T00:00:00Z")
    deleted_user_response = client.get(
        f"/api/v1/admin/users/{deleted_user.user_id}", headers=common_headers
    )

    assert authentication_response.status_code == 401
    assert common_user_response.status_code == 403
    assert admin_user_response.status_code == 200
    assert deleted_user_response.status_code == 404


def test_get_admin_user_returns_detail_counts_reports_and_actions(client, db):
    admin = add_user(db, "detail_admin", role=ROLE_ADMIN)
    target = add_user(db, "detail_target")
    reporter = add_user(db, "detail_reporter")
    add_recorda(db, target)
    add_report(db, reporter, reported_user=target)
    add_moderation_action(db, admin, target_user=target)

    response = client.get(
        f"/api/v1/admin/users/{target.user_id}",
        headers=auth_headers(admin),
    )

    assert response.status_code == 200, response.text
    detail = response.json()
    assert detail["user_id"] == str(target.user_id)
    assert detail["recordas_count"] == 1
    assert detail["reports_count"] == 1
    assert detail["reports_received"][0]["target_id"] == str(target.user_id)
    assert detail["reports_received"][0]["report_count"] == 1
    assert len(detail["actions"]) == 1
    assert detail["actions"][0]["admin_username"] == admin.username
    assert detail["actions"][0]["target_user_id"] == str(target.user_id)
