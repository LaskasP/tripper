"""Add atomic Trip publication and Public-link state.

Data impact: existing Trips remain unpublished and have no Public link. Their
publication revision starts at 1.
Rollback: removes Public-link state; any issued links are irrecoverably lost.

Revision ID: 20260926_07
Revises: 20260923_06
Create Date: 2026-09-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260926_07"
down_revision: str | None = "20260923_06"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("trips", sa.Column("public_token", sa.String(64), nullable=True))
    op.add_column(
        "trips", sa.Column("published_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "trips",
        sa.Column(
            "publication_revision", sa.Integer(), server_default="1", nullable=False
        ),
    )
    op.create_unique_constraint("uq_trips_public_token", "trips", ["public_token"])
    op.create_check_constraint(
        "positive_trip_publication_revision",
        "trips",
        "publication_revision > 0",
    )


def downgrade() -> None:
    op.drop_constraint("positive_trip_publication_revision", "trips", type_="check")
    op.drop_constraint("uq_trips_public_token", "trips", type_="unique")
    op.drop_column("trips", "publication_revision")
    op.drop_column("trips", "published_at")
    op.drop_column("trips", "public_token")
