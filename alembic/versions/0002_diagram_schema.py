"""schema do diagrama oficial: app_user, recorda, genre e favoritos

Revision ID: 0002_diagram_schema
Revises: 0001_baseline
Create Date: 2026-09-18

Recria as tabelas em vez de convertê-las: PK int -> UUID, `data` em texto
dd/mm/YYYY -> created_at TIMESTAMPTZ e colunas que passam a ser NOT NULL não
têm conversão confiável. Os dados de users, recordas e music_preferences NÃO
são preservados (nem no upgrade, nem no downgrade). A tabela media não muda.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
from app.db.seed_data import GENRE_SEED

revision: str = "0002_diagram_schema"
down_revision: str | None = "0001_baseline"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TRIGRAM_INDEXES = (
    ("ix_recorda_song_title_trgm", "recorda", "song_title"),
    ("ix_recorda_song_artist_name_trgm", "recorda", "song_artist_name"),
    ("ix_app_user_username_trgm", "app_user", "username"),
)


def _uuid_pk(name: str) -> sa.Column:
    return sa.Column(
        name,
        sa.Uuid(),
        primary_key=True,
        server_default=sa.text("gen_random_uuid()"),
    )


def _timestamp(name: str, nullable: bool = False) -> sa.Column:
    return sa.Column(
        name,
        sa.DateTime(timezone=True),
        nullable=nullable,
        server_default=None if nullable else sa.func.now(),
    )


def upgrade() -> None:
    op.drop_table("music_preferences")
    op.drop_table("recordas")
    op.drop_table("users")

    op.create_table(
        "app_user",
        _uuid_pk("user_id"),
        sa.Column("username", sa.String(), nullable=False, unique=True),
        sa.Column("email", sa.String(), nullable=False, unique=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("password_hash", sa.String(), nullable=True),
        sa.Column("profile_picture_url", sa.String(), nullable=True),
        sa.Column("language", sa.String(), nullable=False, server_default="pt-BR"),
        sa.Column(
            "is_private", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("role", sa.String(), nullable=False, server_default="USER"),
        sa.Column("status", sa.String(), nullable=False, server_default="ACTIVE"),
        sa.Column("fav_song_deezer_track_id", sa.String(), nullable=True),
        sa.Column("fav_song_title", sa.String(), nullable=True),
        sa.Column("fav_song_artist_name", sa.String(), nullable=True),
        sa.Column("fav_song_cover_url", sa.String(), nullable=True),
        sa.Column("fav_song_preview_url", sa.String(), nullable=True),
        _timestamp("created_at"),
        _timestamp("updated_at"),
        _timestamp("deleted_at", nullable=True),
        sa.CheckConstraint("role IN ('USER', 'ADMIN')", name="ck_app_user_role"),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'SUSPENDED')", name="ck_app_user_status"
        ),
    )

    op.create_table(
        "recorda",
        _uuid_pk("recorda_id"),
        sa.Column(
            "user_id", sa.Uuid(), sa.ForeignKey("app_user.user_id"), nullable=False
        ),
        sa.Column("media_url", sa.String(), nullable=False),
        sa.Column("media_type", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("deezer_track_id", sa.String(), nullable=False),
        sa.Column("song_title", sa.String(), nullable=False),
        sa.Column("song_artist_name", sa.String(), nullable=False),
        sa.Column("song_cover_url", sa.String(), nullable=False),
        sa.Column("song_preview_url", sa.String(), nullable=True),
        _timestamp("created_at"),
        _timestamp("deleted_at", nullable=True),
        sa.CheckConstraint(
            "media_type IN ('PHOTO', 'VIDEO')", name="ck_recorda_media_type"
        ),
    )
    op.create_index(
        "ix_recorda_user_id_created_at",
        "recorda",
        ["user_id", sa.text("created_at DESC")],
    )
    op.create_index("ix_recorda_deezer_track_id", "recorda", ["deezer_track_id"])

    genre = op.create_table(
        "genre",
        _uuid_pk("genre_id"),
        sa.Column("name", sa.String(), nullable=False, unique=True),
        sa.Column("deezer_genre_id", sa.String(), nullable=True, unique=True),
        sa.Column("picture_url", sa.String(), nullable=True),
    )
    op.bulk_insert(
        genre, [{"genre_id": genre_id, "name": name} for genre_id, name in GENRE_SEED]
    )

    op.create_table(
        "user_favorite_genre",
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("app_user.user_id"),
            primary_key=True,
        ),
        sa.Column(
            "genre_id", sa.Uuid(), sa.ForeignKey("genre.genre_id"), primary_key=True
        ),
        _timestamp("selected_at"),
    )
    op.create_index(
        "ix_user_favorite_genre_genre_id", "user_favorite_genre", ["genre_id"]
    )

    op.create_table(
        "user_favorite_artist",
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("app_user.user_id"),
            primary_key=True,
        ),
        sa.Column("deezer_artist_id", sa.String(), primary_key=True),
        sa.Column("artist_name", sa.String(), nullable=False),
        sa.Column("artist_image_url", sa.String(), nullable=True),
        _timestamp("selected_at"),
    )
    op.create_index(
        "ix_user_favorite_artist_deezer_artist_id",
        "user_favorite_artist",
        ["deezer_artist_id"],
    )

    if op.get_bind().dialect.name == "postgresql":
        for index_name, table, column in TRIGRAM_INDEXES:
            op.execute(
                f"CREATE INDEX {index_name} ON {table} "
                f"USING gin ({column} gin_trgm_ops)"
            )


def downgrade() -> None:
    op.drop_table("user_favorite_artist")
    op.drop_table("user_favorite_genre")
    op.drop_table("genre")
    op.drop_table("recorda")
    op.drop_table("app_user")

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
