"""Endpoint tests for comment deletion under /api/v1/comments."""

import uuid

from tests.factories import add_comment, add_recorda, add_user, auth_headers

PREFIX = "/api/v1/comments"


def comment_url(comment) -> str:
    return f"{PREFIX}/{comment.comment_id}"


def test_comment_author_can_delete_immediately(client, db):
    recorda_author = add_user(db, "post_author")
    comment_author = add_user(db, "author")
    recorda = add_recorda(db, recorda_author)
    comment = add_comment(db, comment_author, recorda)

    response = client.delete(comment_url(comment), headers=auth_headers(comment_author))

    assert response.status_code == 204
    db.refresh(comment)
    assert comment.deleted_at is not None

    second_response = client.delete(
        comment_url(comment), headers=auth_headers(comment_author)
    )
    assert second_response.status_code == 404


def test_recorda_author_can_delete_any_comment_on_own_recorda(client, db):
    recorda_author = add_user(db, "recorda_author")
    commenter = add_user(db, "commenter")
    recorda = add_recorda(db, recorda_author)
    comment = add_comment(db, commenter, recorda)

    response = client.delete(comment_url(comment), headers=auth_headers(recorda_author))

    assert response.status_code == 204


def test_other_user_cannot_delete_comment(client, db):
    recorda_author = add_user(db, "recorda_owner")
    commenter = add_user(db, "comment_owner")
    other_user = add_user(db, "other_user")
    recorda = add_recorda(db, recorda_author)
    comment = add_comment(db, commenter, recorda)

    response = client.delete(comment_url(comment), headers=auth_headers(other_user))
    author_response = client.delete(
        comment_url(comment), headers=auth_headers(commenter)
    )

    assert response.status_code == 403
    assert response.json()["error"] == {
        "code": "FORBIDDEN",
        "message": "Você não tem permissão para excluir este comentário.",
        "details": {},
    }
    assert author_response.status_code == 204


def test_delete_comment_requires_authentication(client):
    response = client.delete(f"{PREFIX}/{uuid.uuid4()}")

    assert response.status_code == 401


def test_delete_comment_returns_404_when_missing(client, db):
    user = add_user(db, "missing_comment_user")

    response = client.delete(f"{PREFIX}/{uuid.uuid4()}", headers=auth_headers(user))

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_delete_comment_rejects_non_uuid_id(client, db):
    user = add_user(db, "invalid_comment_id_user")

    response = client.delete(f"{PREFIX}/invalid", headers=auth_headers(user))

    assert response.status_code == 422
