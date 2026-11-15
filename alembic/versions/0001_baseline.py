"""baseline: schema legado criado por create_all + _ADDED_COLUMNS

Revision ID: 0001_baseline
Revises:
Create Date: 2026-09-18

Reproduz o schema que existia antes da adoção do Alembic. Bancos criados pelo
antigo init_db() devem rodar `alembic stamp 0001_baseline` antes do upgrade.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0001_baseline"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("username", sa.String(), nullable=True),
        sa.Column("password_hash", sa.String(), nullable=True),
        sa.Column("account_type", sa.String(), nullable=False),
        sa.Column(
            "onboarding_completed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_username", "users", ["username"], unique=True)

    op.create_table(
        "recordas",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("midia", sa.String(), nullable=True),
        sa.Column("media_type", sa.String(), nullable=True),
        sa.Column("music", sa.String(), nullable=True),
        sa.Column("deezer_track_id", sa.String(), nullable=True),
        sa.Column("song_artist_name", sa.String(), nullable=True),
        sa.Column("song_cover_url", sa.String(), nullable=True),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("data", sa.String(), nullable=True),
    )
    op.create_index("ix_recordas_user_id", "recordas", ["user_id"])

    op.create_table(
        "music_preferences",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("deezer_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.UniqueConstraint("user_id", "kind", "deezer_id", name="uq_music_preference"),
    )
    op.create_index("ix_music_preferences_user_id", "music_preferences", ["user_id"])

    op.create_table(
        "media",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("filename", sa.String(), nullable=False, unique=True),
        sa.Column("content_type", sa.String(), nullable=False),
        sa.Column("content", sa.LargeBinary(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("media")
    op.drop_table("music_preferences")
    op.drop_table("recordas")
    op.drop_table("users")
