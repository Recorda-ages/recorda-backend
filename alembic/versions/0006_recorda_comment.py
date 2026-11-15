"""create recorda_comment table

Revision ID: 0006_recorda_comment
Revises: 0005_notification
Create Date: 2026-09-24
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0006_recorda_comment"
down_revision: str | None = "0005_notification"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "recorda_comment",
        sa.Column(
            "comment_id",
            sa.Uuid(),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("recorda_id", sa.Uuid(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["app_user.user_id"]),
        sa.ForeignKeyConstraint(
            ["recorda_id"], ["recorda.recorda_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("comment_id"),
    )
    op.create_index(
        "ix_recorda_comment_recorda_id",
        "recorda_comment",
        ["recorda_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_recorda_comment_recorda_id", table_name="recorda_comment")
    op.drop_table("recorda_comment")
