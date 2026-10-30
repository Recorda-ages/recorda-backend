"""Add song_genre_name column to recorda table.

Revision ID: 0010_recorda_song_genre_name
Revises: 0009_content_removed
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010_recorda_song_genre_name"
down_revision: str | None = "0009_content_removed"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "recorda",
        sa.Column("song_genre_name", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("recorda", "song_genre_name")
