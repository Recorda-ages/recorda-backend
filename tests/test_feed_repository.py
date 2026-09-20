"""Testes do app/repositories/feed_repository.py.

Verificam a *forma* do SQL gerado (compilado com literal_binds), não o
resultado de execução — úteis para pegar erros de construção da query,
mas não substituem um teste de integração contra um banco real.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.dialects import postgresql

from app.repositories.feed_repository import (
    _is_liked_subquery,
    _likes_count_subquery,
    _visibility_condition,
    apply_cursor,
    get_following_feed_query,
)


def compiled_sql(query):
    # Compila a query pro SQL final com os valores já substituídos no
    # lugar dos parâmetros — facilita checar substring no texto.
    return str(
        query.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True})
    )


class TestVisibilityCondition:
    def test_includes_accepted_follow_status_clause(self):
        condition = _visibility_condition(uuid.uuid4())
        sql = compiled_sql(select(condition))

        assert "ACCEPTED" in sql


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

    def test_excludes_soft_deleted_recordas_and_authors(self):
        query = get_following_feed_query(uuid.uuid4())
        sql = compiled_sql(query)

        # Um filtro para Recorda.deleted_at, outro para AppUser.deleted_at.
        assert sql.count("deleted_at IS NULL") == 2

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


class TestApplyCursor:
    def test_without_cursor_returns_query_unchanged(self):
        query = get_following_feed_query(uuid.uuid4())

        result = apply_cursor(query, None, None)

        assert compiled_sql(result) == compiled_sql(query)

    def test_with_cursor_adds_tuple_comparison_clause(self):
        query = get_following_feed_query(uuid.uuid4())
        cursor_created_at = datetime(2026, 1, 1, tzinfo=UTC)
        cursor_recorda_id = uuid.uuid4()

        result = apply_cursor(query, cursor_created_at, cursor_recorda_id)
        sql = compiled_sql(result)

        assert str(cursor_recorda_id) in sql
        # Comparação de tupla: garante que o desempate por recorda_id
        # está presente, não só o filtro por created_at.
        assert "created_at" in sql and "recorda_id" in sql
