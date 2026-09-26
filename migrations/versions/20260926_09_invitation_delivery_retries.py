"""Add safe retry scheduling for rejected invitation-email attempts.

Data impact: pending outbox rows become immediately eligible with zero attempts.
Rollback: removes retry history and scheduling metadata.

Revision ID: 20260926_09
Revises: 20260926_08
Create Date: 2026-09-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260926_09"
down_revision: str | None = "20260926_08"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "invitation_email_outbox",
        sa.Column(
            "next_attempt_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.alter_column("invitation_email_outbox", "next_attempt_at", server_default=None)
    op.add_column(
        "invitation_email_outbox",
        sa.Column("attempt_count", sa.Integer(), server_default="0", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("invitation_email_outbox", "attempt_count")
    op.drop_column("invitation_email_outbox", "next_attempt_at")
