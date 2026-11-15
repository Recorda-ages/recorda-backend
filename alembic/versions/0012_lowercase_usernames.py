"""Normalize usernames to lowercase and enforce case-insensitive uniqueness."""

import sqlalchemy as sa

from alembic import op

revision = "0012_lowercase_usernames"
down_revision = "0011_content_deletion_mentions"
branch_labels = None
depends_on = None

INDEX_NAME = "uq_app_user_username_lower"


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            WITH ranked AS (
                SELECT user_id,
                       lower(username) AS base,
                       row_number() OVER (
                           PARTITION BY lower(username)
                           ORDER BY (username = lower(username)) DESC, created_at, user_id
                       ) AS position
                FROM app_user
            )
            UPDATE app_user
            SET username = CASE
                WHEN ranked.position = 1 THEN ranked.base
                ELSE ranked.base || '_' || ranked.position
            END
            FROM ranked
            WHERE app_user.user_id = ranked.user_id
              AND app_user.username <> CASE
                WHEN ranked.position = 1 THEN ranked.base
                ELSE ranked.base || '_' || ranked.position
              END
            """
        )
    )
    op.execute(
        sa.text(f"CREATE UNIQUE INDEX {INDEX_NAME} ON app_user (lower(username))")
    )


def downgrade() -> None:
    op.execute(sa.text(f"DROP INDEX IF EXISTS {INDEX_NAME}"))
