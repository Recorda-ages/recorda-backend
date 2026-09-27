"""Endpoint tests for GET /api/v1/users/suggestions (T-E5.US27.BE.01)."""

from app.models.follow import STATUS_PENDING
from app.repositories import user_favorite_repository
from tests.factories import (
    add_favorite_artists,
    add_favorite_genres,
    add_follow,
    add_user,
    auth_headers,
)

URL = "/api/v1/users/suggestions"


def usernames(response) -> list[str]:
    return [item["username"] for item in response.json()]


class TestSuggestionsRoute:
    def test_requires_authentication(self, client):
        assert client.get(URL).status_code == 401

    def test_suggests_a_user_sharing_a_genre(self, client, db):
        me = add_user(db, "eu")
        add_favorite_genres(db, me, "Rock")
        other = add_user(db, "outro")
        add_favorite_genres(db, other, "Rock")

        response = client.get(URL, headers=auth_headers(me))

        assert response.status_code == 200
        body = response.json()
        assert len(body) == 1
        assert body[0]["username"] == "outro"
        assert body[0]["user_id"] == str(other.user_id)
        assert body[0]["affinity"] == 100.0

    # Critério: "Retornar artistas/gêneros em comum."
    def test_returns_only_the_genres_and_artists_actually_shared(self, client, db):
        me = add_user(db, "eu")
        add_favorite_genres(db, me, "Rock", "Jazz")
        add_favorite_artists(db, me, "Radiohead", "Miles Davis")
        other = add_user(db, "outro")
        add_favorite_genres(db, other, "Rock", "Pop")
        add_favorite_artists(db, other, "Radiohead", "Beyonce")

        body = client.get(URL, headers=auth_headers(me)).json()

        assert body[0]["common_genres"] == ["Rock"]
        assert body[0]["common_artists"] == ["Radiohead"]

    # Critério: "Não sugerir o próprio usuário."
    def test_never_suggests_the_requesting_user(self, client, db):
        me = add_user(db, "eu")
        add_favorite_genres(db, me, "Rock")

        assert usernames(client.get(URL, headers=auth_headers(me))) == []

    # Critério: "Não sugerir usuário já seguido."
    def test_skips_users_already_followed(self, client, db):
        me = add_user(db, "eu")
        add_favorite_genres(db, me, "Rock")
        followed = add_user(db, "ja_seguido")
        add_favorite_genres(db, followed, "Rock")
        add_follow(db, me, followed)

        assert usernames(client.get(URL, headers=auth_headers(me))) == []

    # Critério: "Não sugerir usuário com solicitação pendente."
    def test_skips_users_with_a_pending_request(self, client, db):
        me = add_user(db, "eu")
        add_favorite_genres(db, me, "Rock")
        requested = add_user(db, "solicitado")
        add_favorite_genres(db, requested, "Rock")
        add_follow(db, me, requested, status=STATUS_PENDING)

        assert usernames(client.get(URL, headers=auth_headers(me))) == []

    def test_still_suggests_someone_who_follows_me(self, client, db):
        """Quem me segue continua sugerível: o vínculo que exclui é o meu para ele."""
        me = add_user(db, "eu")
        add_favorite_genres(db, me, "Rock")
        fan = add_user(db, "me_segue")
        add_favorite_genres(db, fan, "Rock")
        add_follow(db, fan, me)

        assert usernames(client.get(URL, headers=auth_headers(me))) == ["me_segue"]

    # Critério: "Ordenar da maior afinidade para a menor."
    def test_orders_from_highest_to_lowest_affinity(self, client, db):
        me = add_user(db, "eu")
        add_favorite_genres(db, me, "Rock", "Jazz")

        twin = add_user(db, "identico")
        add_favorite_genres(db, twin, "Rock", "Jazz")
        partial = add_user(db, "parcial")
        add_favorite_genres(db, partial, "Rock", "Pop")

        body = client.get(URL, headers=auth_headers(me)).json()

        assert [item["username"] for item in body] == ["identico", "parcial"]
        assert body[0]["affinity"] > body[1]["affinity"]

    def test_omits_users_without_anything_in_common(self, client, db):
        me = add_user(db, "eu")
        add_favorite_genres(db, me, "Rock")
        add_favorite_genres(db, add_user(db, "sem_relacao"), "Samba / Pagode")
        add_user(db, "sem_perfil")

        assert usernames(client.get(URL, headers=auth_headers(me))) == []

    def test_returns_empty_when_the_requester_has_no_musical_profile(self, client, db):
        me = add_user(db, "eu")
        add_favorite_genres(db, add_user(db, "outro"), "Rock")

        response = client.get(URL, headers=auth_headers(me))

        assert response.status_code == 200
        assert response.json() == []

    def test_hides_soft_deleted_users(self, client, db):
        """D34 do modelo de dados cita sugestões entre os filtros de apagados."""
        me = add_user(db, "eu")
        add_favorite_genres(db, me, "Rock")

        deleted = add_user(db, "apagado")
        add_favorite_genres(db, deleted, "Rock")
        deleted.deleted_at = deleted.created_at
        db.commit()

        assert usernames(client.get(URL, headers=auth_headers(me))) == []

    def test_suggestions_path_is_not_parsed_as_a_user_id(self, client, db):
        """A rota precisa ser declarada antes de /users/{user_id}."""
        me = add_user(db, "eu")

        assert client.get(URL, headers=auth_headers(me)).status_code == 200


class TestBulkFavouriteLoaders:
    """Os carregadores em bloco que evitam uma consulta por candidato."""

    def test_return_empty_without_hitting_the_database_for_no_users(self, db):
        assert user_favorite_repository.get_genres_by_user(db, []) == {}
        assert user_favorite_repository.get_artists_by_user(db, []) == {}

    def test_group_favourites_by_user(self, db):
        ana = add_user(db, "ana")
        bruno = add_user(db, "bruno")
        add_favorite_genres(db, ana, "Rock", "Jazz")
        add_favorite_genres(db, bruno, "Pop")
        add_favorite_artists(db, ana, "Radiohead")

        genres = user_favorite_repository.get_genres_by_user(
            db, [ana.user_id, bruno.user_id]
        )
        artists = user_favorite_repository.get_artists_by_user(
            db, [ana.user_id, bruno.user_id]
        )

        assert sorted(genres[ana.user_id].values()) == ["Jazz", "Rock"]
        assert list(genres[bruno.user_id].values()) == ["Pop"]
        assert list(artists[ana.user_id].values()) == ["Radiohead"]
        assert bruno.user_id not in artists
