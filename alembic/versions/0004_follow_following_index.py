"""index follow.following_id for the followers list

Revision ID: 0004_follow_following_index
Revises: 0003_follow_and_recorda_like
Create Date: 2026-09-21 00:00:00.000000

A migration 0003 indexou apenas follower_id, que serve à lista "Seguindo".
A lista "Seguidores" filtra por following_id e sem este índice varre a
tabela inteira a cada abertura da tela.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0004_follow_following_index"
down_revision: str | None = "0003_follow_and_recorda_like"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index("ix_follow_following_id", "follow", ["following_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_follow_following_id", table_name="follow")
