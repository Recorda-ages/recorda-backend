from app.models.app_user import ROLE_ADMIN
from tests.factories import add_user, auth_headers


def admin_url(user) -> str:
    return f"/api/v1/admin/users/{user.user_id}/suspend"


#
def test_suspend_rejects_self_unknown_admin_and_already_suspended_user(
    client, common_user
):
    headers = auth_headers(common_user)

    self_suspend = client.post(admin_url(common_user), headers=headers)
    unknown_user = client.post(
        "/api/v1/admin/users/00000000-0000-0000-0000-000000000000/suspend",
        headers=headers,
    )
    already_suspended = client.post(admin_url(common_user), headers=headers)
    admin_user = add_user(common_user.db, "admin_user", role=ROLE_ADMIN)
    admin_headers = auth_headers(admin_user)
    assert self_suspend.status_code == 400
    assert unknown_user.status_code == 404
    assert already_suspended.status_code == 409
    assert client.post(admin_url(common_user), headers=admin_headers).status_code == 200


def test_reactivate_rejects_self_unknown_admin_and_not_suspended_user(
    client, common_user
):
    headers = auth_headers(common_user)

    self_reactivate = client.post(
        f"/api/v1/admin/users/{common_user.user_id}/reactivate", headers=headers
    )
    unknown_user = client.post(
        "/api/v1/admin/users/00000000-0000-0000-0000-000000000000/reactivate",
        headers=headers,
    )
    not_suspended = client.post(
        f"/api/v1/admin/users/{common_user.user_id}/reactivate", headers=headers
    )
    admin_user = add_user(common_user.db, "admin_user", role=ROLE_ADMIN)
    admin_headers = auth_headers(admin_user)
    assert self_reactivate.status_code == 400
    assert unknown_user.status_code == 404
    assert not_suspended.status_code == 409
    assert (
        client.post(
            f"/api/v1/admin/users/{common_user.user_id}/reactivate",
            headers=admin_headers,
        ).status_code
        == 200
    )


#
def test_suspend_and_reactivate_require_authentication(client, common_user):
    assert client.post(admin_url(common_user)).status_code == 401
    assert client.delete(admin_url(common_user)).status_code == 401
