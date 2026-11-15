"""create moderation_action table

Revision ID: 0008_moderation_action
Revises: 0007_report
Create Date: 2026-10-03
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0008_moderation_action"
down_revision: str | None = "0007_report"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

HAS_TARGET = "target_user_id IS NOT NULL OR target_recorda_id IS NOT NULL"

# A trilha de auditoria é append-only: o trigger recusa qualquer UPDATE ou
# DELETE. É específico do PostgreSQL e não tem equivalente no SQLite dos testes.
CREATE_IMMUTABLE_FUNCTION = """
CREATE OR REPLACE FUNCTION moderation_action_immutable()
RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'moderation_action é imutável';
END;
$$ LANGUAGE plpgsql;
"""

CREATE_IMMUTABLE_TRIGGER = """
CREATE TRIGGER trg_moderation_action_immutable
BEFORE UPDATE OR DELETE ON moderation_action
FOR EACH ROW EXECUTE FUNCTION moderation_action_immutable();
"""


def upgrade() -> None:
    op.create_table(
        "moderation_action",
        sa.Column(
            "action_id",
            sa.Uuid(),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("admin_id", sa.Uuid(), nullable=False),
        sa.Column("action_type", sa.String(), nullable=False),
        sa.Column("target_user_id", sa.Uuid(), nullable=True),
        sa.Column("target_recorda_id", sa.Uuid(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "action_type IN ('REMOVE_RECORDA', 'CHANGE_REPORT_STATUS', "
            "'SUSPEND_USER', 'REACTIVATE_USER')",
            name="ck_moderation_action_type",
        ),
        sa.CheckConstraint(HAS_TARGET, name="ck_moderation_action_has_target"),
        sa.ForeignKeyConstraint(["admin_id"], ["app_user.user_id"]),
        sa.ForeignKeyConstraint(["target_user_id"], ["app_user.user_id"]),
        sa.ForeignKeyConstraint(["target_recorda_id"], ["recorda.recorda_id"]),
        sa.PrimaryKeyConstraint("action_id"),
    )
    op.create_index(
        "ix_moderation_action_created_at",
        "moderation_action",
        [sa.text("created_at DESC")],
        unique=False,
    )
    op.create_index(
        "ix_moderation_action_admin_id_created_at",
        "moderation_action",
        ["admin_id", sa.text("created_at DESC")],
        unique=False,
    )
    op.create_index(
        "ix_moderation_action_target_user_id",
        "moderation_action",
        ["target_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_moderation_action_target_recorda_id",
        "moderation_action",
        ["target_recorda_id"],
        unique=False,
    )
    op.execute(CREATE_IMMUTABLE_FUNCTION)
    op.execute(CREATE_IMMUTABLE_TRIGGER)


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS trg_moderation_action_immutable ON moderation_action"
    )
    op.execute("DROP FUNCTION IF EXISTS moderation_action_immutable()")
    op.drop_index(
        "ix_moderation_action_target_recorda_id", table_name="moderation_action"
    )
    op.drop_index("ix_moderation_action_target_user_id", table_name="moderation_action")
    op.drop_index(
        "ix_moderation_action_admin_id_created_at", table_name="moderation_action"
    )
    op.drop_index("ix_moderation_action_created_at", table_name="moderation_action")
    op.drop_table("moderation_action")
