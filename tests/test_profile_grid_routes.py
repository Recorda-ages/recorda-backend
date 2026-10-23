"""Testes da grade de Recordas do perfil: GET /api/v1/users/{user_id}/recordas."""

import uuid
from datetime import timedelta

from app.core.time import now_utc
from app.models.app_user import STATUS_SUSPENDED
from app.models.follow import STATUS_PENDING
from tests.factories import add_follow, add_recorda, add_user, auth_headers


def grid_url(user) -> str:
    return f"/api/v1/users/{user.user_id}/recordas"


def recorda_ids(response) -> list[str]:
    return [item["recorda_id"] for item in response.json()["items"]]


# ---------------------------------------------------------------------------
# Autenticação
# ---------------------------------------------------------------------------


class TestAuthentication:
    def test_requires_authentication(self, client, db):
        owner = add_user(db, "owner")
        assert client.get(grid_url(owner)).status_code == 401


# ---------------------------------------------------------------------------
# Usuário não encontrado / excluído / suspenso
# ---------------------------------------------------------------------------


class TestOwnerNotFound:
    def test_unknown_user_returns_404(self, client, db):
        viewer = add_user(db, "viewer")
        unknown_id = uuid.uuid4()

        response = client.get(
            f"/api/v1/users/{unknown_id}/recordas", headers=auth_headers(viewer)
        )

        assert response.status_code == 404
        assert response.json()["error"]["message"] == "Usuário não encontrado."

    def test_deleted_user_returns_404(self, client, db):
        viewer = add_user(db, "viewer")
        ghost = add_user(db, "ghost", deleted_at=now_utc())

        response = client.get(grid_url(ghost), headers=auth_headers(viewer))

        assert response.status_code == 404
        assert response.json()["error"]["message"] == "Usuário não encontrado."

    def test_suspended_user_returns_404(self, client, db):
        viewer = add_user(db, "viewer")
        banned = add_user(db, "banned", status=STATUS_SUSPENDED)

        response = client.get(grid_url(banned), headers=auth_headers(viewer))

        assert response.status_code == 404
        assert response.json()["error"]["message"] == "Usuário não encontrado."


# ---------------------------------------------------------------------------
# Acesso público
# ---------------------------------------------------------------------------


class TestPublicAccess:
    def test_any_authenticated_user_can_view_public_profile(self, client, db):
        owner = add_user(db, "owner")
        viewer = add_user(db, "viewer")
        add_recorda(db, owner)

        response = client.get(grid_url(owner), headers=auth_headers(viewer))

        assert response.status_code == 200
        assert len(response.json()["items"]) == 1

    def test_owner_can_view_own_grid(self, client, db):
        owner = add_user(db, "owner")
        add_recorda(db, owner)

        response = client.get(grid_url(owner), headers=auth_headers(owner))

        assert response.status_code == 200

    def test_empty_grid_returns_200_with_no_items(self, client, db):
        owner = add_user(db, "owner")
        viewer = add_user(db, "viewer")

        response = client.get(grid_url(owner), headers=auth_headers(viewer))

        assert response.status_code == 200
        assert response.json() == {"items": [], "next_cursor": None}


# ---------------------------------------------------------------------------
# Privacidade
# ---------------------------------------------------------------------------


class TestPrivateAccountAccess:
    def test_stranger_cannot_see_private_profile_grid(self, client, db):
        owner = add_user(db, "owner", is_private=True)
        stranger = add_user(db, "stranger")
        add_recorda(db, owner)

        response = client.get(grid_url(owner), headers=auth_headers(stranger))

        assert response.status_code == 403
        assert response.json()["error"]["message"] == "Esta conta é privada."

    def test_pending_follower_cannot_see_private_grid(self, client, db):
        owner = add_user(db, "owner", is_private=True)
        bob = add_user(db, "bob")
        add_follow(db, bob, owner, status=STATUS_PENDING)

        response = client.get(grid_url(owner), headers=auth_headers(bob))

        assert response.status_code == 403

    def test_accepted_follower_can_see_private_grid(self, client, db):
        owner = add_user(db, "owner", is_private=True)
        bob = add_user(db, "bob")
        add_follow(db, bob, owner)
        add_recorda(db, owner)

        response = client.get(grid_url(owner), headers=auth_headers(bob))

        assert response.status_code == 200
        assert len(response.json()["items"]) == 1

    def test_owner_always_sees_own_private_grid(self, client, db):
        owner = add_user(db, "owner", is_private=True)
        add_recorda(db, owner)

        response = client.get(grid_url(owner), headers=auth_headers(owner))

        assert response.status_code == 200

    def test_following_private_account_is_not_enough_in_reverse(self, client, db):
        """owner seguir bob não dá a bob acesso à grade dela."""
        owner = add_user(db, "owner", is_private=True)
        bob = add_user(db, "bob")
        add_follow(db, owner, bob)

        response = client.get(grid_url(owner), headers=auth_headers(bob))

        assert response.status_code == 403

    def test_making_account_private_immediately_blocks_non_followers(self, client, db):
        """Tornar a conta privada retroativamente bloqueia não-seguidores (T-E6.US32.BE.01)."""
        owner = add_user(db, "owner")
        stranger = add_user(db, "stranger")
        add_recorda(db, owner)

        # Antes de tornar privado: acesso liberado
        assert (
            client.get(grid_url(owner), headers=auth_headers(stranger)).status_code
            == 200
        )

        # Tornar a conta privada
        owner.is_private = True
        db.commit()

        # Agora: bloqueado
        response = client.get(grid_url(owner), headers=auth_headers(stranger))
        assert response.status_code == 403

    def test_making_account_private_does_not_block_accepted_followers(self, client, db):
        owner = add_user(db, "owner")
        bob = add_user(db, "bob")
        add_follow(db, bob, owner)

        owner.is_private = True
        db.commit()

        response = client.get(grid_url(owner), headers=auth_headers(bob))
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Conteúdo e ordenação
# ---------------------------------------------------------------------------


class TestContent:
    def test_returns_expected_fields(self, client, db):
        owner = add_user(db, "owner")
        viewer = add_user(db, "viewer")
        r = add_recorda(db, owner)

        response = client.get(grid_url(owner), headers=auth_headers(viewer))
        item = response.json()["items"][0]

        assert item["recorda_id"] == str(r.recorda_id)
        assert item["media_url"] == r.media_url
        assert item["media_type"] == r.media_type
        assert item["song_title"] == r.song_title
        assert item["song_artist_name"] == r.song_artist_name
        assert item["song_cover_url"] == r.song_cover_url
        assert "created_at" in item
        # Campos enxutos: sem curtidas nem descrição
        assert "likes_count" not in item
        assert "is_liked" not in item
        assert "description" not in item

    def test_only_owner_recordas_appear(self, client, db):
        owner = add_user(db, "owner")
        other = add_user(db, "other")
        viewer = add_user(db, "viewer")
        r_owner = add_recorda(db, owner)
        add_recorda(db, other)

        response = client.get(grid_url(owner), headers=auth_headers(viewer))

        assert recorda_ids(response) == [str(r_owner.recorda_id)]

    def test_deleted_recordas_do_not_appear(self, client, db):
        owner = add_user(db, "owner")
        viewer = add_user(db, "viewer")
        r_live = add_recorda(db, owner)
        r_deleted = add_recorda(db, owner)
        r_deleted.deleted_at = now_utc()
        db.commit()

        response = client.get(grid_url(owner), headers=auth_headers(viewer))

        ids = recorda_ids(response)
        assert str(r_live.recorda_id) in ids
        assert str(r_deleted.recorda_id) not in ids

    def test_ordered_most_recent_first(self, client, db):
        owner = add_user(db, "owner")
        viewer = add_user(db, "viewer")
        base = now_utc()
        r1 = add_recorda(db, owner, created_at=base - timedelta(days=2))
        r2 = add_recorda(db, owner, created_at=base - timedelta(days=1))
        r3 = add_recorda(db, owner, created_at=base)

        response = client.get(grid_url(owner), headers=auth_headers(viewer))

        assert recorda_ids(response) == [
            str(r3.recorda_id),
            str(r2.recorda_id),
            str(r1.recorda_id),
        ]


# ---------------------------------------------------------------------------
# Paginação por cursor
# ---------------------------------------------------------------------------


class TestCursorPagination:
    def test_first_page_has_no_next_cursor_when_under_limit(self, client, db):
        owner = add_user(db, "owner")
        viewer = add_user(db, "viewer")
        for _ in range(3):
            add_recorda(db, owner)

        response = client.get(
            grid_url(owner), params={"limit": 5}, headers=auth_headers(viewer)
        )

        assert response.json()["next_cursor"] is None

    def test_first_page_has_next_cursor_when_more_items_exist(self, client, db):
        owner = add_user(db, "owner")
        viewer = add_user(db, "viewer")
        for _ in range(5):
            add_recorda(db, owner)

        response = client.get(
            grid_url(owner), params={"limit": 3}, headers=auth_headers(viewer)
        )

        assert response.json()["next_cursor"] is not None
        assert len(response.json()["items"]) == 3

    def test_second_page_continues_without_overlap(self, client, db):
        owner = add_user(db, "owner")
        viewer = add_user(db, "viewer")
        base = now_utc()
        recordas = [
            add_recorda(db, owner, created_at=base - timedelta(seconds=i))
            for i in range(5)
        ]

        first = client.get(
            grid_url(owner), params={"limit": 3}, headers=auth_headers(viewer)
        )
        cursor = first.json()["next_cursor"]
        second = client.get(
            grid_url(owner),
            params={"limit": 3, "cursor": cursor},
            headers=auth_headers(viewer),
        )

        first_ids = set(recorda_ids(first))
        second_ids = set(recorda_ids(second))
        all_ids = {str(r.recorda_id) for r in recordas}

        assert first_ids.isdisjoint(second_ids), "Páginas não devem ter itens em comum"
        assert first_ids | second_ids == all_ids

    def test_last_page_has_no_next_cursor(self, client, db):
        owner = add_user(db, "owner")
        viewer = add_user(db, "viewer")
        for _ in range(4):
            add_recorda(db, owner)

        first = client.get(
            grid_url(owner), params={"limit": 3}, headers=auth_headers(viewer)
        )
        cursor = first.json()["next_cursor"]
        second = client.get(
            grid_url(owner),
            params={"limit": 3, "cursor": cursor},
            headers=auth_headers(viewer),
        )

        assert second.json()["next_cursor"] is None
        assert len(second.json()["items"]) == 1

    def test_invalid_cursor_returns_400(self, client, db):
        owner = add_user(db, "owner")
        viewer = add_user(db, "viewer")

        response = client.get(
            grid_url(owner),
            params={"cursor": "isto_nao_e_valido!!!"},
            headers=auth_headers(viewer),
        )

        assert response.status_code == 400
        assert response.json()["error"]["message"] == "Cursor inválido."

    def test_limit_defaults_to_24(self, client, db):
        owner = add_user(db, "owner")
        viewer = add_user(db, "viewer")
        for _ in range(30):
            add_recorda(db, owner)

        response = client.get(grid_url(owner), headers=auth_headers(viewer))

        assert len(response.json()["items"]) == 24
        assert response.json()["next_cursor"] is not None

    def test_limit_max_is_60(self, client, db):
        owner = add_user(db, "owner")
        viewer = add_user(db, "viewer")

        response = client.get(
            grid_url(owner), params={"limit": 61}, headers=auth_headers(viewer)
        )
        assert response.status_code == 422

    def test_limit_min_is_1(self, client, db):
        owner = add_user(db, "owner")
        viewer = add_user(db, "viewer")

        response = client.get(
            grid_url(owner), params={"limit": 0}, headers=auth_headers(viewer)
        )
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# /search e /suggestions não conflitam com /{user_id}/recordas
# ---------------------------------------------------------------------------


class TestNoRouteConflict:
    def test_search_still_works(self, client, db):
        add_user(db, "alice")
        viewer = add_user(db, "viewer")

        response = client.get(
            "/api/v1/users/search", params={"q": "ali"}, headers=auth_headers(viewer)
        )

        assert response.status_code == 200

    def test_suggestions_still_works(self, client, db):
        viewer = add_user(db, "viewer")

        response = client.get(
            "/api/v1/users/suggestions", headers=auth_headers(viewer)
        )

        assert response.status_code == 200
