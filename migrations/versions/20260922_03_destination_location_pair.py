"""Require complete optional Destination locations.

This migration does not rewrite product data. It rejects upgrade if existing
Destinations contain only one coordinate so operators can repair that ambiguous data
deliberately. Downgrade removes only the constraint and does not alter stored values.

Revision ID: 20260922_03
Revises: 20260921_02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260922_03"
down_revision: str | None = "20260921_02"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_check_constraint(
        "complete_destination_location",
        "destinations",
        sa.text("(latitude IS NULL) = (longitude IS NULL)"),
    )


def downgrade() -> None:
    op.drop_constraint("complete_destination_location", "destinations", type_="check")
