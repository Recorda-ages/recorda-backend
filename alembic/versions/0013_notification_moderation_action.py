"""Link content removal notices to the moderation action that caused them."""

import sqlalchemy as sa

from alembic import op

revision = "0013_notification_moderation"
down_revision = "0012_lowercase_usernames"
branch_labels = None
depends_on = None

FK_NAME = "fk_notification_moderation_action_id"


def upgrade() -> None:
    op.add_column(
        "notification", sa.Column("moderation_action_id", sa.Uuid(), nullable=True)
    )
    op.create_foreign_key(
        FK_NAME,
        "notification",
        "moderation_action",
        ["moderation_action_id"],
        ["action_id"],
    )


def downgrade() -> None:
    op.drop_constraint(FK_NAME, "notification", type_="foreignkey")
    op.drop_column("notification", "moderation_action_id")
