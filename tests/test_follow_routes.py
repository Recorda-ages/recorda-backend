"""Endpoint tests for the follower/following lists under /api/v1/users."""

from sqlalchemy import select

from app.core.time import now_utc
from app.models import Follow
from app.models.app_user import STATUS_SUSPENDED
from app.models.follow import STATUS_PENDING
from tests.factories import add_follow, add_user, auth_headers


def followers_url(user) -> str:
    return f"/api/v1/users/{user.user_id}/followers"


def following_url(user) -> str:
    return f"/api/v1/users/{user.user_id}/following"


def remove_url(follower) -> str:
    return f"/api/v1/users/me/followers/{follower.user_id}"


def usernames(response) -> list[str]:
    return [item["username"] for item in response.json()]


def relation_exists(db, follower, following) -> bool:
    stmt = select(Follow).where(
        Follow.follower_id == follower.user_id,
        Follow.following_id == following.user_id,
    )
    return db.scalars(stmt).first() is not None


class TestListFollowers:
    def test_lists_accepted_followers_sorted_by_username(self, client, db):
        alice = add_user(db, "alice")
        for username in ("carol", "bob"):
            add_follow(db, add_user(db, username), alice)
        add_user(db, "dave")

        response = client.get(followers_url(alice), headers=auth_headers(alice))

        assert response.status_code == 200
        assert usernames(response) == ["bob", "carol"]

    def test_returns_the_fields_the_list_screen_needs(self, client, db):
        alice = add_user(db, "alice")
        bob = add_user(db, "bob", name="Bob Dylan", profile_picture_url="/b.jpg")
        add_follow(db, bob, alice)

        response = client.get(followers_url(alice), headers=auth_headers(alice))

        assert response.json() == [
            {
                "user_id": str(bob.user_id),
                "username": "bob",
                "name": "Bob Dylan",
                "profile_picture_url": "/b.jpg",
            }
        ]

    def test_pending_requests_are_not_followers(self, client, db):
        alice = add_user(db, "alice")
        add_follow(db, add_user(db, "bob"), alice, status=STATUS_PENDING)

        response = client.get(followers_url(alice), headers=auth_headers(alice))

        assert usernames(response) == []

    def test_hides_suspended_and_deleted_followers(self, client, db):
        alice = add_user(db, "alice")
        add_follow(db, add_user(db, "bob", status=STATUS_SUSPENDED), alice)
        add_follow(db, add_user(db, "carol", deleted_at=now_utc()), alice)
        add_follow(db, add_user(db, "dave"), alice)

        response = client.get(followers_url(alice), headers=auth_headers(alice))

        assert usernames(response) == ["dave"]

    def test_requires_authentication(self, client, db):
        alice = add_user(db, "alice")

        assert client.get(followers_url(alice)).status_code == 401


class TestListFollowing:
    def test_lists_only_who_the_user_follows(self, client, db):
        alice = add_user(db, "alice")
        bob = add_user(db, "bob")
        carol = add_user(db, "carol")
        add_follow(db, alice, bob)
        add_follow(db, carol, alice)

        response = client.get(following_url(alice), headers=auth_headers(alice))

        assert response.status_code == 200
        assert usernames(response) == ["bob"]

    def test_pending_requests_sent_are_not_following(self, client, db):
        alice = add_user(db, "alice")
        add_follow(db, alice, add_user(db, "bob"), status=STATUS_PENDING)

        response = client.get(following_url(alice), headers=auth_headers(alice))

        assert usernames(response) == []

    def test_requires_authentication(self, client, db):
        alice = add_user(db, "alice")

        assert client.get(following_url(alice)).status_code == 401


class TestSearchAndPagination:
    def setup_followers(self, db, *usernames_to_add):
        alice = add_user(db, "alice")
        for username in usernames_to_add:
            add_follow(db, add_user(db, username), alice)
        return alice

    def test_filters_by_username_fragment(self, client, db):
        alice = self.setup_followers(db, "bob", "bobby", "carol")

        response = client.get(
            followers_url(alice), params={"q": "BOB"}, headers=auth_headers(alice)
        )

        assert usernames(response) == ["bob", "bobby"]

    def test_wildcards_in_the_query_are_literal(self, client, db):
        alice = self.setup_followers(db, "bob", "100%pop", "ro_ck", "back\\slash")
        headers = auth_headers(alice)

        for term, expected in (
            ("%", ["100%pop"]),
            ("_", ["ro_ck"]),
            ("\\", ["back\\slash"]),
        ):
            response = client.get(
                followers_url(alice), params={"q": term}, headers=headers
            )
            assert usernames(response) == expected, term

    def test_filters_the_following_list_too(self, client, db):
        alice = add_user(db, "alice")
        for username in ("bob", "carol"):
            add_follow(db, alice, add_user(db, username))

        response = client.get(
            following_url(alice), params={"q": "car"}, headers=auth_headers(alice)
        )

        assert usernames(response) == ["carol"]

    def test_blank_query_does_not_filter(self, client, db):
        alice = self.setup_followers(db, "bob")

        response = client.get(
            followers_url(alice), params={"q": "  "}, headers=auth_headers(alice)
        )

        assert usernames(response) == ["bob"]

    def test_limit_and_offset_walk_the_list(self, client, db):
        alice = self.setup_followers(db, "bob", "carol", "dave")
        headers = auth_headers(alice)

        first = client.get(followers_url(alice), params={"limit": 2}, headers=headers)
        second = client.get(
            followers_url(alice), params={"limit": 2, "offset": 2}, headers=headers
        )

        assert usernames(first) == ["bob", "carol"]
        assert usernames(second) == ["dave"]

    def test_rejects_out_of_range_paging(self, client, db):
        alice = self.setup_followers(db, "bob")
        headers = auth_headers(alice)

        for params in ({"limit": 0}, {"limit": 51}, {"offset": -1}):
            assert (
                client.get(followers_url(alice), params=params, headers=headers)
            ).status_code == 422


class TestPrivateAccountVisibility:
    def test_stranger_cannot_see_lists_of_a_private_account(self, client, db):
        alice = add_user(db, "alice", is_private=True)
        stranger = add_user(db, "stranger")

        for url in (followers_url(alice), following_url(alice)):
            response = client.get(url, headers=auth_headers(stranger))
            assert response.status_code == 403
            assert response.json()["error"]["message"] == "Esta conta é privada."

    def test_owner_always_sees_own_lists(self, client, db):
        alice = add_user(db, "alice", is_private=True)

        for url in (followers_url(alice), following_url(alice)):
            assert client.get(url, headers=auth_headers(alice)).status_code == 200

    def test_accepted_follower_sees_the_lists(self, client, db):
        alice = add_user(db, "alice", is_private=True)
        bob = add_user(db, "bob")
        add_follow(db, bob, alice)

        for url in (followers_url(alice), following_url(alice)):
            assert client.get(url, headers=auth_headers(bob)).status_code == 200

    def test_pending_follower_still_blocked(self, client, db):
        alice = add_user(db, "alice", is_private=True)
        bob = add_user(db, "bob")
        add_follow(db, bob, alice, status=STATUS_PENDING)

        assert (
            client.get(followers_url(alice), headers=auth_headers(bob)).status_code
            == 403
        )

    def test_following_the_private_account_is_not_enough_in_reverse(self, client, db):
        """Alice seguir Bob não dá a Bob acesso às listas dela."""
        alice = add_user(db, "alice", is_private=True)
        bob = add_user(db, "bob")
        add_follow(db, alice, bob)

        assert (
            client.get(followers_url(alice), headers=auth_headers(bob)).status_code
            == 403
        )

    def test_public_account_lists_are_open(self, client, db):
        alice = add_user(db, "alice")
        stranger = add_user(db, "stranger")

        assert (
            client.get(followers_url(alice), headers=auth_headers(stranger)).status_code
            == 200
        )


class TestUnreachableTargets:
    def test_unknown_user_returns_404(self, client, db):
        alice = add_user(db, "alice")
        unknown = "00000000-0000-0000-0000-000000000000"

        response = client.get(
            f"/api/v1/users/{unknown}/followers", headers=auth_headers(alice)
        )

        assert response.status_code == 404

    def test_deleted_user_returns_404(self, client, db):
        alice = add_user(db, "alice")
        ghost = add_user(db, "ghost", deleted_at=now_utc())

        response = client.get(followers_url(ghost), headers=auth_headers(alice))

        assert response.status_code == 404

    def test_suspended_user_returns_404(self, client, db):
        alice = add_user(db, "alice")
        banned = add_user(db, "banned", status=STATUS_SUSPENDED)

        response = client.get(followers_url(banned), headers=auth_headers(alice))

        assert response.status_code == 404


class TestRemoveFollower:
    def test_removing_a_follower_deletes_the_relation(self, client, db):
        alice = add_user(db, "alice")
        bob = add_user(db, "bob")
        add_follow(db, bob, alice)

        response = client.delete(remove_url(bob), headers=auth_headers(alice))

        assert response.status_code == 204
        assert not relation_exists(db, bob, alice)

    def test_does_not_touch_the_reverse_relation(self, client, db):
        alice = add_user(db, "alice")
        bob = add_user(db, "bob")
        add_follow(db, bob, alice)
        add_follow(db, alice, bob)

        client.delete(remove_url(bob), headers=auth_headers(alice))

        assert relation_exists(db, alice, bob)

    def test_removing_someone_who_does_not_follow_returns_404(self, client, db):
        alice = add_user(db, "alice")
        bob = add_user(db, "bob")

        response = client.delete(remove_url(bob), headers=auth_headers(alice))

        assert response.status_code == 404

    def test_pending_request_is_not_removable_here(self, client, db):
        """Recusar solicitação é da BE#44; aqui só sai seguidor aceito."""
        alice = add_user(db, "alice")
        bob = add_user(db, "bob")
        add_follow(db, bob, alice, status=STATUS_PENDING)

        response = client.delete(remove_url(bob), headers=auth_headers(alice))

        assert response.status_code == 404
        assert relation_exists(db, bob, alice)

    def test_suspended_follower_can_still_be_removed(self, client, db):
        """Some da listagem, mas a relação existe e o dono pode apagá-la."""
        alice = add_user(db, "alice")
        bob = add_user(db, "bob", status=STATUS_SUSPENDED)
        add_follow(db, bob, alice)

        response = client.delete(remove_url(bob), headers=auth_headers(alice))

        assert response.status_code == 204
        assert not relation_exists(db, bob, alice)

    def test_requires_authentication(self, client, db):
        bob = add_user(db, "bob")

        assert client.delete(remove_url(bob)).status_code == 401
