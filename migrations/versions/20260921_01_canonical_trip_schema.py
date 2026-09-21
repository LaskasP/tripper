"""Create the canonical Trip and membership schema.

This migration creates new tables and does not transform existing data. Its downgrade
drops all three tables and is destructive; operators must authorize that rollback and
back up any data before running it.

Revision ID: 20260921_01
Revises: None
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260921_01"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "trips",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("short_name", sa.String(length=80), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("revision", sa.Integer(), server_default="1", nullable=False),
        sa.Column("content_revision", sa.Integer(), server_default="1", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint("start_date <= end_date", name="valid_trip_date_range"),
        sa.CheckConstraint("revision > 0", name="positive_trip_revision"),
        sa.CheckConstraint(
            "content_revision > 0", name="positive_trip_content_revision"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "destinations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("trip_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("timezone", sa.String(length=100), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("revision", sa.Integer(), server_default="1", nullable=False),
        sa.CheckConstraint("position >= 0", name="nonnegative_destination_position"),
        sa.CheckConstraint("revision > 0", name="positive_destination_revision"),
        sa.ForeignKeyConstraint(["trip_id"], ["trips.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("trip_id", "position", name="uq_destination_trip_position"),
    )
    op.create_table(
        "trip_memberships",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("trip_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("revision", sa.Integer(), server_default="1", nullable=False),
        sa.CheckConstraint(
            "role IN ('creator', 'contributor', 'traveller')",
            name="valid_membership_role",
        ),
        sa.CheckConstraint("revision > 0", name="positive_membership_revision"),
        sa.ForeignKeyConstraint(["trip_id"], ["trips.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("trip_id", "account_id", name="uq_membership_trip_account"),
    )
    op.create_index(
        "uq_membership_one_creator",
        "trip_memberships",
        ["trip_id"],
        unique=True,
        postgresql_where=sa.text("role = 'creator'"),
    )


def downgrade() -> None:
    op.drop_index("uq_membership_one_creator", table_name="trip_memberships")
    op.drop_table("trip_memberships")
    op.drop_table("destinations")
    op.drop_table("trips")
