"""Smoke HTTP against a local development API. Creates and deletes its own accounts.

Run after compose + migrations + seed. Does not change seeded users or profiles.
Set INTEGRATION_ADMIN_PASSWORD if the seed password was overridden.
"""

import json
import os
import secrets
from datetime import UTC, datetime
from uuid import uuid4

import httpx

BASE_URL = os.getenv("INTEGRATION_API_URL", "http://127.0.0.1:8000")


def main():
    results = []
    accounts = []
    admin_token = None
    password = secrets.token_urlsafe(18)
    with httpx.Client(base_url=BASE_URL, timeout=20) as client:

        def call(method, path, token=None, expected=200, **kwargs):
            headers = kwargs.pop("headers", {})
            if token:
                headers["Authorization"] = f"Bearer {token}"
            url = path if path.startswith("/api/") else f"/api/v1{path}"
            response = client.request(method, url, headers=headers, **kwargs)
            assert response.status_code == expected, (
                method,
                path,
                response.status_code,
                response.text[:300],
            )
            results.append({"method": method, "path": path, "status": expected})
            if response.status_code == 204:
                assert not response.content
                return None
            if "application/json" in response.headers.get("content-type", ""):
                return response.json()
            return response.content

        try:
            call("GET", "/health")
            for suffix in ("a", "b"):
                username = f"verify_{uuid4().hex[:12]}_{suffix}"
                account = call(
                    "POST",
                    "/auth/register",
                    expected=201,
                    json={
                        "name": "Integration verification",
                        "username": username,
                        "email": f"{username}@example.com",
                        "password": password,
                        "language": "pt-BR",
                    },
                )
                accounts.append(account)
            a, b = accounts
            ta, tb = a["access_token"], b["access_token"]
            ua, ub = a["user"]["user_id"], b["user"]["user_id"]
            admin = call(
                "POST",
                "/auth/login",
                json={
                    "username": "admin",
                    "password": os.getenv("INTEGRATION_ADMIN_PASSWORD", "Admin@1234"),
                },
            )
            tm = admin["access_token"]
            admin_token = tm
            call("GET", "/auth/me", expected=401)
            call("GET", "/admin/users", ta, expected=403)
            call(
                "PATCH", "/users/me/settings", ta, expected=422, json={"language": "fr"}
            )
            for language in ("en", "es", "pt-BR"):
                call("PATCH", "/users/me/settings", ta, json={"language": language})
                assert call("GET", "/auth/me", ta)["language"] == language
            call("PATCH", "/users/me/settings", ta, json={"is_private": True})
            assert (
                call("POST", f"/users/{ua}/follow", tb)["follow_status"] == "solicitado"
            )
            changed = call(
                "PATCH", "/users/me/settings", ta, json={"is_private": False}
            )
            assert changed["accepted_requests"] == 1
            assert not call("GET", "/users/me/settings", ta)["is_private"]
            call("GET", f"/users/{ua}/followers", ta)
            genres = [
                {"deezer_id": i, "name": name}
                for i, name in [(132, "Pop"), (152, "Rock"), (113, "Dance")]
            ]
            artists = [
                {"deezer_id": i, "name": name}
                for i, name in [(13, "Eminem"), (27, "Daft Punk"), (66, "Green Day")]
            ]
            track = {
                "deezer_id": 3135556,
                "title": "Harder Better Faster Stronger",
                "artist_name": "Daft Punk",
                "cover_url": "",
            }
            call(
                "POST",
                "/users/me/music-preferences",
                ta,
                json={"genres": genres, "artists": artists, "favorite_track": track},
            )
            assert call("GET", "/users/me/music-preferences", ta)[
                "onboarding_completed"
            ]
            photo = b"\xff\xd8\xff" + bytes(100)
            video = b"\x00\x00\x00\x18ftypmp42" + bytes(range(256)) * 4
            for kind, content, mime in [
                ("PHOTO", photo, "image/jpeg"),
                ("VIDEO", video, "video/mp4"),
            ]:
                uploaded = call(
                    "POST",
                    "/recordas/media",
                    ta,
                    expected=201,
                    files={"file": ("media", content, mime)},
                )
                recorda = call(
                    "POST",
                    "/recordas",
                    ta,
                    expected=201,
                    json={
                        "media_url": uploaded["url"],
                        "media_type": kind,
                        "deezer_track_id": "3135556",
                        "song_title": track["title"],
                        "song_artist_name": track["artist_name"],
                    },
                )
                rid = recorda["recorda_id"]
                call("GET", f"/recordas/{rid}", tb)
                call("GET", uploaded["url"], expected=401)
                assert call("GET", uploaded["url"], tb) == content
                if kind == "VIDEO":
                    assert (
                        call(
                            "GET",
                            uploaded["url"],
                            tb,
                            expected=206,
                            headers={"Range": "bytes=0-7"},
                        )
                        == content[:8]
                    )
                assert call("POST", f"/recordas/{rid}/likes", tb)["is_liked"]
                assert not call("DELETE", f"/recordas/{rid}/likes", tb)["is_liked"]
                comment = call(
                    "POST",
                    f"/recordas/{rid}/comments",
                    tb,
                    expected=201,
                    json={"content": "Verification"},
                )
                call("DELETE", f"/comments/{comment['comment_id']}", tb, expected=204)
                comment = call(
                    "POST",
                    f"/recordas/{rid}/comments",
                    ta,
                    expected=201,
                    json={"content": "Owner comment"},
                )
                call("DELETE", f"/comments/{comment['comment_id']}", tb, expected=403)
                call("DELETE", f"/comments/{comment['comment_id']}", ta, expected=204)
                comment = call(
                    "POST",
                    f"/recordas/{rid}/comments",
                    tb,
                    expected=201,
                    json={"content": "Owner can moderate"},
                )
                call("DELETE", f"/comments/{comment['comment_id']}", ta, expected=204)
                call("DELETE", f"/comments/{comment['comment_id']}", ta, expected=404)
                call("DELETE", f"/recordas/{rid}", ta, expected=204)
                call("GET", f"/recordas/{rid}", tb, expected=404)
            for feed in ("general", "following"):
                call("GET", f"/feed/{feed}", ta)
            call("GET", "/notifications", ta)
            call("GET", f"/users/search?q={b['user']['username']}", ta)
            page = call(
                "GET", f"/admin/users?q={b['user']['username']}&limit=1&offset=0", tm
            )
            assert page["items"][0]["user_id"] == ub
            call("GET", f"/admin/users/{ub}", tm)
            call(
                "POST",
                f"/admin/users/{ub}/suspend",
                tm,
                json={
                    "reason": "Integration verification",
                    "resolve_open_reports": True,
                },
            )
            assert call("GET", f"/admin/users/{ub}", tm)["status"] == "SUSPENDED"
            call("GET", "/auth/me", tb, expected=401)
            page = call(
                "GET", f"/admin/users?q={b['user']['username']}&status=SUSPENDED", tm
            )
            assert page["total"] == 1
            call(
                "POST",
                f"/admin/users/{ub}/reactivate",
                tm,
                json={"reason": "Verification complete"},
            )
            assert call("GET", f"/admin/users/{ub}", tm)["status"] == "ACTIVE"
            call("GET", "/admin/audit-log", tm)
            call("GET", "/admin/reports", tm)
            call(
                "POST",
                f"/admin/users/{admin['user']['user_id']}/suspend",
                tm,
                expected=400,
                json={"reason": "Guard verification"},
            )
            # Re-login proves preferences and identity persisted beyond a token response.
            fresh = call(
                "POST",
                "/auth/login",
                json={"username": a["user"]["username"], "password": password},
            )
            assert fresh["user"]["onboarding_completed"]
        finally:
            for account in accounts:
                if admin_token:
                    detail = call(
                        "GET", f"/admin/users/{account['user']['user_id']}", admin_token
                    )
                    if detail["status"] == "SUSPENDED":
                        call(
                            "POST",
                            f"/admin/users/{account['user']['user_id']}/reactivate",
                            admin_token,
                            json={"reason": "Verification cleanup"},
                        )
                call("DELETE", "/users/me", account["access_token"], expected=204)
                call("GET", "/auth/me", account["access_token"], expected=401)
    print(
        json.dumps(
            {
                "at": datetime.now(UTC).isoformat(),
                "base_url": BASE_URL,
                "requests": len(results),
                "results": results,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
