"""create notification table

Revision ID: 0004_notification
Revises: 0003_follow_and_recorda_like
Create Date: 2026-09-22 19:40:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0004_notification"
down_revision: str | None = "0003_follow_and_recorda_like"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "notification",
        sa.Column(
            "notification_id",
            sa.Uuid(),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("recipient_id", sa.Uuid(), nullable=False),
        sa.Column("sender_id", sa.Uuid(), nullable=True),
        sa.Column("recorda_id", sa.Uuid(), nullable=True),
        sa.Column("comment_id", sa.Uuid(), nullable=True),
        sa.Column("follow_id", sa.Uuid(), nullable=True),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column(
            "is_read",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "type IN ('FOLLOW_REQUEST', 'FOLLOW_ACCEPTED', 'NEW_FOLLOWER', "
            "'LIKE', 'COMMENT', 'MENTION')",
            name="ck_notification_type",
        ),
        sa.CheckConstraint(
            "recipient_id <> sender_id", name="ck_notification_no_self_notification"
        ),
        sa.ForeignKeyConstraint(
            ["recipient_id"], ["app_user.user_id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["sender_id"], ["app_user.user_id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["recorda_id"], ["recorda.recorda_id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["follow_id"], ["follow.follow_id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("notification_id"),
    )
    op.create_index(
        "ix_notification_recipient_id_is_read_created_at",
        "notification",
        ["recipient_id", "is_read", sa.text("created_at DESC")],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_notification_recipient_id_is_read_created_at", table_name="notification"
    )
    op.drop_table("notification")
