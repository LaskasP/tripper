"""Add independent Timeline collection revisions.

Data impact: existing Daily plans receive revision 1, preserving all Timeline data.
Rollback: dropping the column preserves Timeline entries but discards their collection
revision history.

Revision ID: 20260923_05
Revises: 20260922_04
Create Date: 2026-09-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260923_05"
down_revision: str | None = "20260922_04"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "daily_plans",
        sa.Column(
            "timeline_revision", sa.Integer(), server_default="1", nullable=False
        ),
    )
    op.create_check_constraint(
        "positive_timeline_collection_revision",
        "daily_plans",
        "timeline_revision > 0",
    )


def downgrade() -> None:
    op.drop_constraint(
        "positive_timeline_collection_revision", "daily_plans", type_="check"
    )
    op.drop_column("daily_plans", "timeline_revision")
