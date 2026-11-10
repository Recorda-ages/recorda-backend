"""Preserve historical content IDs and add friend mentions.

Historical references deliberately have no FK: content can be physically removed
without modifying immutable audit entries or deleting reports. Existing soft-deleted
rows are not purged by this migration.
"""

import sqlalchemy as sa

from alembic import op

revision = "0011_content_deletion_mentions"
down_revision = "0010_recorda_song_genre_name"
branch_labels = None
depends_on = None

HISTORICAL_REFERENCES = (
    ("report", "recorda_id", "recorda", "recorda_id"),
    ("report", "comment_id", "recorda_comment", "comment_id"),
    ("moderation_action", "target_recorda_id", "recorda", "recorda_id"),
)


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    for table, column, _, _ in HISTORICAL_REFERENCES:
        for fk in inspector.get_foreign_keys(table):
            if fk["constrained_columns"] == [column]:
                op.drop_constraint(fk["name"], table, type_="foreignkey")
    op.create_table(
        "recorda_mention",
        sa.Column(
            "recorda_id",
            sa.Uuid(),
            sa.ForeignKey("recorda.recorda_id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "user_id", sa.Uuid(), sa.ForeignKey("app_user.user_id"), primary_key=True
        ),
    )
    op.create_index("ix_recorda_mention_user_id", "recorda_mention", ["user_id"])


def downgrade() -> None:
    # Refuse downgrade before dropping anything when historical IDs outlive content.
    for table, column, target, target_column in HISTORICAL_REFERENCES:
        missing = (
            op.get_bind()
            .execute(
                sa.text(
                    f"SELECT 1 FROM {table} h WHERE h.{column} IS NOT NULL AND NOT EXISTS "
                    f"(SELECT 1 FROM {target} t WHERE t.{target_column} = h.{column}) LIMIT 1"
                )
            )
            .first()
        )
        if missing:
            raise RuntimeError(
                "Cannot restore content FKs while retained historical references exist"
            )
    op.drop_index("ix_recorda_mention_user_id", table_name="recorda_mention")
    op.drop_table("recorda_mention")
    for table, column, target, target_column in HISTORICAL_REFERENCES:
        op.create_foreign_key(
            f"{table}_{column}_fkey", table, target, [column], [target_column]
        )
