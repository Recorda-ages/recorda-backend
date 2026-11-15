"""create report table

Revision ID: 0007_report
Revises: 0006_recorda_comment
Create Date: 2026-10-03
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0007_report"
down_revision: str | None = "0006_recorda_comment"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SINGLE_TARGET = """(CASE WHEN reported_user_id IS NOT NULL THEN 1 ELSE 0 END
 + CASE WHEN recorda_id IS NOT NULL THEN 1 ELSE 0 END
 + CASE WHEN comment_id IS NOT NULL THEN 1 ELSE 0 END) = 1"""


def upgrade() -> None:
    op.create_table(
        "report",
        sa.Column(
            "report_id",
            sa.Uuid(),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("reporter_id", sa.Uuid(), nullable=False),
        sa.Column("reported_user_id", sa.Uuid(), nullable=True),
        sa.Column("recorda_id", sa.Uuid(), nullable=True),
        sa.Column("comment_id", sa.Uuid(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.String(),
            nullable=False,
            server_default="OPEN",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('OPEN', 'RESOLVED', 'DISMISSED')",
            name="ck_report_status",
        ),
        sa.CheckConstraint(SINGLE_TARGET, name="ck_report_single_target"),
        sa.ForeignKeyConstraint(["reporter_id"], ["app_user.user_id"]),
        sa.ForeignKeyConstraint(["reported_user_id"], ["app_user.user_id"]),
        sa.ForeignKeyConstraint(["recorda_id"], ["recorda.recorda_id"]),
        sa.ForeignKeyConstraint(["comment_id"], ["recorda_comment.comment_id"]),
        sa.PrimaryKeyConstraint("report_id"),
    )
    op.create_index(
        "uq_report_reporter_recorda",
        "report",
        ["reporter_id", "recorda_id"],
        unique=True,
        postgresql_where=sa.text("recorda_id IS NOT NULL"),
    )
    op.create_index(
        "uq_report_reporter_user",
        "report",
        ["reporter_id", "reported_user_id"],
        unique=True,
        postgresql_where=sa.text("reported_user_id IS NOT NULL"),
    )
    op.create_index(
        "ix_report_status_created_at",
        "report",
        ["status", sa.text("created_at DESC")],
        unique=False,
    )
    op.create_index("ix_report_recorda_id", "report", ["recorda_id"], unique=False)
    op.create_index(
        "ix_report_reported_user_id", "report", ["reported_user_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_report_reported_user_id", table_name="report")
    op.drop_index("ix_report_recorda_id", table_name="report")
    op.drop_index("ix_report_status_created_at", table_name="report")
    op.drop_index("uq_report_reporter_user", table_name="report")
    op.drop_index("uq_report_reporter_recorda", table_name="report")
    op.drop_table("report")
