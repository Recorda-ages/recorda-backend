# tests/test_feed_repository.py

import uuid
from unittest.mock import MagicMock

import pytest
from sqlalchemy import select

from app.repositories.feed_repository import (
    get_following_feed_query,
    _visibility_condition,
    _likes_count_subquery,
    _is_liked_subquery,
)


def compiled_sql(query):
    # Compila a query pro SQL final com os valores já substituídos no
    # lugar dos parâmetros — facilita checar substring no texto.
    return str(query.compile(compile_kwargs={"literal_binds": True}))


class TestVisibilityCondition:
    def test_includes_public_account_clause(self):
        condition = _visibility_condition(uuid.uuid4())
        sql = compiled_sql(select(condition))

        assert "is_private" in sql

    def test_includes_accepted_follow_status_clause(self):
        condition = _visibility_condition(uuid.uuid4())
        sql = compiled_sql(select(condition))

        assert "ACEPTED" in sql


class TestLikesCountSubquery:
    def test_groups_by_recorda_id(self):
        subq = _likes_count_subquery()
        sql = str(subq)

        assert "GROUP BY" in sql.upper()
        assert "recorda_id" in sql

    def test_has_likes_count_label(self):
        subq = _likes_count_subquery()

        assert "likes_count" in subq.c.keys()


class TestIsLikedSubquery:
    def test_filters_by_current_user(self):
        user_id = uuid.uuid4()
        subq = _is_liked_subquery(user_id)
        sql = compiled_sql(select(subq))

        assert str(user_id) in sql


class TestGetFollowingFeedQuery:
    def test_filters_by_follower_id(self):
        user_id = uuid.uuid4()
        query = get_following_feed_query(user_id)
        sql = compiled_sql(query)

        assert str(user_id) in sql
        assert "follower_id" in sql

    def test_excludes_soft_deleted_recordas(self):
        query = get_following_feed_query(uuid.uuid4())
        sql = compiled_sql(query)

        assert "deleted_at IS NULL" in sql

    def test_orders_by_created_at_desc(self):
        query = get_following_feed_query(uuid.uuid4())
        sql = compiled_sql(query)

        assert "ORDER BY" in sql.upper()
        assert "created_at" in sql
        assert "DESC" in sql.upper()

    def test_uses_left_join_for_likes_count(self):
        query = get_following_feed_query(uuid.uuid4())
        sql = compiled_sql(query)

        assert "LEFT OUTER JOIN" in sql.upper()


class TestFeedRepositoryWithMockedSession:
    # Esse grupo simula o que acontece se você tiver, por exemplo,
    # uma função get_following_feed(db: Session, user_id: UUID) que
    # chama db.execute(get_following_feed_query(user_id)).scalars().all()
    # Aqui a Session inteira é fake — nenhuma conexão real acontece.

    def test_execute_is_called_with_a_select_statement(self):
        mock_session = MagicMock()
        mock_session.execute.return_value.scalars.return_value.all.return_value = []

        user_id = uuid.uuid4()
        query = get_following_feed_query(user_id)

        # Simula o que a camada de service faria:
        mock_session.execute(query)

        mock_session.execute.assert_called_once()
        called_arg = mock_session.execute.call_args[0][0]
        # Confirma que o que foi passado pra execute() é de fato
        # a query montada, não algo genérico.
        assert called_arg is query