from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.core.time import now_utc
from app.models.app_user import ROLE_ADMIN, STATUS_ACTIVE, STATUS_SUSPENDED
from app.models.moderation_action import (
    ACTION_REMOVE_RECORDA,
    ACTION_SUSPEND_USER,
    ModerationAction,
)
from app.models.report import (
    STATUS_DISMISSED,
    STATUS_OPEN,
    STATUS_RESOLVED,
    Report,
)
from tests.factories import (
    add_comment,
    add_recorda,
    add_report,
    add_user,
    auth_headers,
)


def test_user_search_matches_uuid_email_text_and_literal_wildcards(client, db):
    admin = add_user(db, "search_admin", role=ROLE_ADMIN)
    uuid_target = add_user(db, "uuid_target", name="Unique Name")
    email_target = add_user(
        db, "email_target", email="unique@example.test", name="Different"
    )
    email_decoy = add_user(
        db,
        "email_decoy",
        email="elsewhere@example.test",
        name="unique@example.test",
    )
    wildcard_target = add_user(db, "wild%card")
    wildcard_decoy = add_user(db, "wildXcard")
    underscore_target = add_user(db, "under_score")
    underscore_decoy = add_user(db, "underXscore")
    headers = auth_headers(admin)

    uuid_response = client.get(
        "/api/v1/admin/users", params={"q": f" {uuid_target.user_id} "}, headers=headers
    )
    email_response = client.get(
        "/api/v1/admin/users", params={"q": "UNIQUE@example.test"}, headers=headers
    )
    partial_response = client.get(
        "/api/v1/admin/users", params={"q": "uNiQuE nAmE"}, headers=headers
    )
    percent_response = client.get(
        "/api/v1/admin/users", params={"q": "wild%card"}, headers=headers
    )
    underscore_response = client.get(
        "/api/v1/admin/users", params={"q": "under_score"}, headers=headers
    )
    no_match_response = client.get(
        "/api/v1/admin/users", params={"q": "no-such-account"}, headers=headers
    )

    assert uuid_response.status_code == 200
    assert [item["user_id"] for item in uuid_response.json()["items"]] == [
        str(uuid_target.user_id)
    ]
    assert [item["user_id"] for item in email_response.json()["items"]] == [
        str(email_target.user_id)
    ]
    assert str(email_decoy.user_id) not in {
        item["user_id"] for item in email_response.json()["items"]
    }
    assert [item["user_id"] for item in partial_response.json()["items"]] == [
        str(uuid_target.user_id)
    ]
    assert [item["user_id"] for item in percent_response.json()["items"]] == [
        str(wildcard_target.user_id)
    ]
    assert str(wildcard_decoy.user_id) not in {
        item["user_id"] for item in percent_response.json()["items"]
    }
    assert [item["user_id"] for item in underscore_response.json()["items"]] == [
        str(underscore_target.user_id)
    ]
    assert str(underscore_decoy.user_id) not in {
        item["user_id"] for item in underscore_response.json()["items"]
    }
    assert no_match_response.json() == {"items": [], "total": 0}
    assert all("password_hash" not in item for item in email_response.json()["items"])


def test_user_search_trims_empty_query_filters_status_and_paginates(client, db):
    admin = add_user(db, "admin", role=ROLE_ADMIN)
    add_user(db, "active_a", status=STATUS_ACTIVE)
    add_user(db, "active_b", status=STATUS_ACTIVE)
    add_user(db, "suspended", status=STATUS_SUSPENDED)
    add_user(db, "deleted", deleted_at=now_utc())
    headers = auth_headers(admin)

    page_response = client.get(
        "/api/v1/admin/users",
        params={"q": "  ", "limit": 2, "offset": 1},
        headers=headers,
    )
    active_response = client.get(
        "/api/v1/admin/users", params={"status": STATUS_ACTIVE}, headers=headers
    )
    suspended_response = client.get(
        "/api/v1/admin/users", params={"status": STATUS_SUSPENDED}, headers=headers
    )

    assert page_response.status_code == 200
    assert page_response.json()["total"] == 4
    assert [item["username"] for item in page_response.json()["items"]] == [
        "active_b",
        "admin",
    ]
    assert [item["status"] for item in active_response.json()["items"]] == [
        STATUS_ACTIVE,
        STATUS_ACTIVE,
        STATUS_ACTIVE,
    ]
    assert {item["username"] for item in active_response.json()["items"]} == {
        "active_a",
        "active_b",
        "admin",
    }
    assert [item["username"] for item in suspended_response.json()["items"]] == [
        "suspended"
    ]
    assert active_response.json()["total"] == 3
    assert suspended_response.json()["total"] == 1


def test_user_search_counts_profile_and_all_recorda_reports_but_not_comments(
    client, db
):
    admin = add_user(db, "report_count_admin", role=ROLE_ADMIN)
    target = add_user(db, "report_count_target")
    profile_reporter = add_user(db, "profile_reporter")
    recorda_reporter = add_user(db, "recorda_reporter")
    removed_reporter = add_user(db, "removed_recorda_reporter")
    comment_reporter = add_user(db, "comment_reporter")
    recorda = add_recorda(db, target)
    removed_recorda = add_recorda(db, target, deleted_at=now_utc())
    comment = add_comment(db, comment_reporter, recorda)

    add_report(db, profile_reporter, reported_user=target)
    add_report(db, recorda_reporter, recorda=recorda, status=STATUS_RESOLVED)
    add_report(db, removed_reporter, recorda=removed_recorda, status=STATUS_DISMISSED)
    db.add(
        Report(
            reporter_id=comment_reporter.user_id,
            comment_id=comment.comment_id,
            status=STATUS_OPEN,
        )
    )
    db.commit()

    response = client.get(
        "/api/v1/admin/users",
        params={"q": str(target.user_id)},
        headers=auth_headers(admin),
    )

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["reports_count"] == 3


def test_user_detail_returns_complete_report_groups_previews_and_action_history(
    client, db
):
    start = datetime(2025, 1, 1, tzinfo=UTC)
    admin = add_user(db, "detail_admin", role=ROLE_ADMIN)
    target = add_user(
        db,
        "detail_target",
        name="Detail Target",
        profile_picture_url="https://example.test/profile.jpg",
        is_private=True,
        created_at=start,
    )
    live_recorda = add_recorda(
        db,
        target,
        song_title="Visible song",
        media_url="https://example.test/visible.jpg",
    )
    removed_recorda = add_recorda(
        db,
        target,
        song_title="Removed song",
        media_url="https://example.test/removed.jpg",
        deleted_at=now_utc(),
    )

    reporters = [add_user(db, f"detail_reporter_{index}") for index in range(8)]
    comment = add_comment(db, reporters[7], live_recorda)
    add_report(
        db,
        reporters[0],
        reported_user=target,
        status=STATUS_OPEN,
        created_at=start + timedelta(days=1),
    )
    add_report(
        db,
        reporters[1],
        reported_user=target,
        status=STATUS_OPEN,
        created_at=start + timedelta(days=2),
    )
    add_report(
        db,
        reporters[2],
        reported_user=target,
        status=STATUS_RESOLVED,
        created_at=start + timedelta(days=3),
    )
    add_report(
        db,
        reporters[3],
        reported_user=target,
        status=STATUS_DISMISSED,
        created_at=start + timedelta(days=4),
    )
    add_report(
        db,
        reporters[4],
        recorda=live_recorda,
        status=STATUS_OPEN,
        created_at=start + timedelta(days=5),
    )
    add_report(
        db,
        reporters[5],
        recorda=removed_recorda,
        status=STATUS_DISMISSED,
        created_at=start + timedelta(days=6),
    )
    add_report(
        db,
        reporters[6],
        recorda=removed_recorda,
        status=STATUS_DISMISSED,
        created_at=start + timedelta(days=7),
    )
    db.add(
        Report(
            reporter_id=reporters[7].user_id,
            comment_id=comment.comment_id,
            status=STATUS_OPEN,
            created_at=start + timedelta(days=8),
        )
    )

    action_rows = [
        ModerationAction(
            action_id=UUID(int=index),
            admin_id=admin.user_id,
            action_type=ACTION_SUSPEND_USER,
            target_user_id=target.user_id,
            reason="history entry",
            created_at=start + timedelta(seconds=(index + 1) // 2),
        )
        for index in range(1, 102)
    ]
    remove_action_id = UUID(int=200)
    remove_action_time = start + timedelta(seconds=200)
    action_rows.append(
        ModerationAction(
            action_id=remove_action_id,
            admin_id=admin.user_id,
            action_type=ACTION_REMOVE_RECORDA,
            target_user_id=target.user_id,
            target_recorda_id=removed_recorda.recorda_id,
            reason="recorda removed",
            created_at=remove_action_time,
        )
    )
    db.add_all(action_rows)
    db.commit()

    response = client.get(
        f"/api/v1/admin/users/{target.user_id}", headers=auth_headers(admin)
    )

    assert response.status_code == 200, response.text
    detail = response.json()
    assert detail["is_private"] is True
    assert detail["created_at"].startswith("2025-01-01T00:00:00")
    assert detail["recordas_count"] == 1
    assert detail["reports_count"] == 7

    groups = {
        (group["target_type"], group["target_id"], group["status"]): group
        for group in detail["reports_received"]
    }
    profile_open = groups[("USER", str(target.user_id), STATUS_OPEN)]
    assert profile_open["report_count"] == 2
    assert datetime.fromisoformat(profile_open["first_reported_at"]).replace(
        tzinfo=UTC
    ) == start + timedelta(days=1)
    assert datetime.fromisoformat(profile_open["last_reported_at"]).replace(
        tzinfo=UTC
    ) == start + timedelta(days=2)
    assert profile_open["preview"] == {
        "title": target.name,
        "subtitle": f"@{target.username}",
        "image_url": target.profile_picture_url,
    }
    assert ("USER", str(target.user_id), STATUS_RESOLVED) in groups
    assert ("USER", str(target.user_id), STATUS_DISMISSED) in groups
    assert (
        "RECORDA",
        str(live_recorda.recorda_id),
        STATUS_OPEN,
    ) in groups
    removed_group = groups[
        ("RECORDA", str(removed_recorda.recorda_id), STATUS_DISMISSED)
    ]
    assert removed_group["report_count"] == 2
    assert removed_group["preview"] == {
        "title": "Removed song",
        "subtitle": f"@{target.username}",
        "image_url": "https://example.test/removed.jpg",
    }

    actions = detail["actions"]
    assert len(actions) == 102
    expected_ids = [str(remove_action_id)] + [
        str(UUID(int=index))
        for index in sorted(
            range(1, 102), key=lambda value: ((value + 1) // 2, value), reverse=True
        )
    ]
    assert [action["action_id"] for action in actions] == expected_ids
    assert actions[0]["target_user_id"] == str(target.user_id)
    assert actions[0]["target_recorda_id"] == str(removed_recorda.recorda_id)
    assert actions[0]["admin_username"] == admin.username
