"""adiciona tabela follow (seguir/solicitar)

Revision ID: 0003_follow
Revises: 0002_diagram_schema
Create Date: 2026-09-22
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003_follow"
down_revision: str | None = "0002_diagram_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "follow",
        sa.Column(
            "follow_id",
            sa.Uuid(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "follower_id",
            sa.Uuid(),
            sa.ForeignKey("app_user.user_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "following_id",
            sa.Uuid(),
            sa.ForeignKey("app_user.user_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column(
            "requested_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint(
            "follower_id", "following_id", name="uq_follow_follower_following"
        ),
        sa.CheckConstraint(
            "follower_id <> following_id", name="ck_follow_no_self_follow"
        ),
        sa.CheckConstraint("status IN ('PENDING', 'ACCEPTED')", name="ck_follow_status"),
    )
    op.create_index("ix_follow_follower_id", "follow", ["follower_id"])
    op.create_index("ix_follow_following_id", "follow", ["following_id"])


def downgrade() -> None:
    op.drop_table("follow")