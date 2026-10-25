"""Contratos de persistência e integridade no PostgreSQL migrado."""

import uuid

import pytest
from sqlalchemy import delete, select, text
from sqlalchemy.exc import IntegrityError

from app.models import AppUser, Notification, Recorda, RecordaComment, RecordaLike
from app.repositories import recorda_repository
from tests.factories import add_comment, add_notification, add_recorda, add_user

pytestmark = pytest.mark.postgres


def test_recorda_crud_and_soft_delete(pg_db):
    author = add_user(pg_db, "author")
    recorda = add_recorda(pg_db, author)
    recorda_id = recorda.recorda_id
    pg_db.expunge_all()
    stored = recorda_repository.get_by_id(pg_db, recorda_id)
    assert stored.song_title == "Song of Silence"
    stored.description = "Descrição atualizada"
    recorda_repository.save(pg_db, stored)
    pg_db.expunge_all()
    stored = recorda_repository.get_by_id(pg_db, recorda_id)
    assert stored.description == "Descrição atualizada"
    recorda_repository.soft_delete(pg_db, stored)
    pg_db.expunge_all()
    assert recorda_repository.get_by_id(pg_db, recorda_id) is None
    assert recorda_repository.get_all(pg_db) == []
    preserved = recorda_repository.get_by_id_including_deleted(pg_db, recorda_id)
    assert preserved.deleted_at is not None


@pytest.mark.parametrize(
    ("field", "value", "sqlstate"),
    [
        ("username", "author", "23505"),
        ("email", "author@example.com", "23505"),
        ("role", "INVALID", "23514"),
        ("name", None, "23502"),
    ],
)
def test_user_constraints(pg_db, field, value, sqlstate):
    add_user(pg_db, "author")
    fields = {"username": "other", "email": "other@example.com", "name": "Other"}
    fields[field] = value
    pg_db.add(AppUser(**fields))
    with pytest.raises(IntegrityError) as error:
        pg_db.commit()
    assert error.value.orig.sqlstate == sqlstate
    pg_db.rollback()
    assert len(list(pg_db.scalars(select(AppUser)))) == 1


@pytest.mark.parametrize("invalid", ["author", "media_type"])
def test_recorda_constraints(pg_db, invalid):
    author = add_user(pg_db, "author")
    if invalid == "author":
        pg_db.expunge(author)
        author.user_id = uuid.uuid4()
    fields = {"media_type": "GIF"} if invalid == "media_type" else {}
    with pytest.raises(IntegrityError) as error:
        add_recorda(pg_db, author, **fields)
    assert error.value.orig.sqlstate == ("23514" if fields else "23503")
    pg_db.rollback()
    assert recorda_repository.get_all(pg_db) == []


def test_hard_delete_cascades_and_clears_notification_target(pg_db):
    author = add_user(pg_db, "author")
    recorda = add_recorda(pg_db, author)
    comment = add_comment(pg_db, author, recorda)
    notice = add_notification(pg_db, author, "MENTION", recorda_id=recorda.recorda_id)
    like = RecordaLike(user_id=author.user_id, recorda_id=recorda.recorda_id)
    pg_db.add(like)
    pg_db.commit()
    comment_id, notice_id = comment.comment_id, notice.notification_id
    pg_db.execute(delete(Recorda).where(Recorda.recorda_id == recorda.recorda_id))
    pg_db.commit()
    pg_db.expunge_all()
    assert pg_db.get(RecordaComment, comment_id) is None
    assert list(pg_db.scalars(select(RecordaLike))) == []
    assert pg_db.get(Notification, notice_id).recorda_id is None


@pytest.mark.parametrize("attempt", range(2))
def test_fixture_starts_clean_even_after_commits(pg_db, attempt):
    assert pg_db.scalar(text("SELECT count(*) FROM app_user")) == 0
    add_user(pg_db, "same_username")
    assert pg_db.scalar(text("SELECT count(*) FROM app_user")) == 1


def test_soft_delete_preserves_references(pg_db):
    author = add_user(pg_db, "author")
    recorda = add_recorda(pg_db, author)
    comment = add_comment(pg_db, author, recorda)
    comment_id, recorda_id = comment.comment_id, recorda.recorda_id
    recorda_repository.soft_delete(pg_db, recorda)
    pg_db.expunge_all()
    assert pg_db.get(RecordaComment, comment_id).recorda_id == recorda_id
    assert recorda_repository.get_by_id(pg_db, recorda_id) is None


def test_author_with_recordas_cannot_be_hard_deleted(pg_db):
    author = add_user(pg_db, "author")
    recorda = add_recorda(pg_db, author)
    author_id, recorda_id = author.user_id, recorda.recorda_id
    with pytest.raises(IntegrityError) as error:
        pg_db.execute(delete(AppUser).where(AppUser.user_id == author_id))
        pg_db.commit()
    assert error.value.orig.sqlstate == "23503"
    pg_db.rollback()
    assert recorda_repository.get_by_id(pg_db, recorda_id) is not None
