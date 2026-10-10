"""Allow system notifications for content removed by moderation.

Revision ID: 0009_content_removed
Revises: 0008_moderation_action
"""

from collections.abc import Sequence

from alembic import op

# Alembic armazena o identificador em VARCHAR(32).
revision: str = "0009_content_removed"
down_revision: str | None = "0008_moderation_action"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PREVIOUS_TYPES = (
    "'FOLLOW_REQUEST', 'FOLLOW_ACCEPTED', 'NEW_FOLLOWER', 'LIKE', 'COMMENT', 'MENTION'"
)


def upgrade() -> None:
    op.drop_constraint("ck_notification_type", "notification", type_="check")
    op.create_check_constraint(
        "ck_notification_type",
        "notification",
        f"type IN ({PREVIOUS_TYPES}, 'CONTENT_REMOVED')",
    )


def downgrade() -> None:
    # O tipo deixa de existir na versão anterior do contrato.
    op.execute("DELETE FROM notification WHERE type = 'CONTENT_REMOVED'")
    op.drop_constraint("ck_notification_type", "notification", type_="check")
    op.create_check_constraint(
        "ck_notification_type", "notification", f"type IN ({PREVIOUS_TYPES})"
    )
