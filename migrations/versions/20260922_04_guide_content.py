"""Add canonical guide content.

The migration only adds empty tables. Downgrade deletes imported guide content and is
therefore destructive.

Revision ID: 20260922_04
Revises: 20260922_03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260922_04"
down_revision: str | None = "20260922_03"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _location_constraints(prefix: str) -> list[sa.CheckConstraint]:
    return [
        sa.CheckConstraint(
            "(latitude IS NULL) = (longitude IS NULL)",
            name=f"complete_{prefix}_location",
        )
    ]


def upgrade() -> None:
    op.create_table(
        "daily_plans",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("trip_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("destination_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("background_image", sa.Text(), nullable=False),
        sa.Column("revision", sa.Integer(), server_default="1", nullable=False),
        sa.CheckConstraint("revision > 0", name="positive_daily_plan_revision"),
        sa.ForeignKeyConstraint(["trip_id"], ["trips.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["destination_id"], ["destinations.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("trip_id", "date", name="uq_daily_plan_trip_date"),
    )
    op.create_table(
        "timeline_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("daily_plan_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("destination_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("local_time", sa.Time(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("location_name", sa.String(length=300), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("revision", sa.Integer(), server_default="1", nullable=False),
        *_location_constraints("timeline_entry"),
        sa.CheckConstraint("position >= 0", name="nonnegative_timeline_position"),
        sa.CheckConstraint("revision > 0", name="positive_timeline_revision"),
        sa.ForeignKeyConstraint(
            ["daily_plan_id"], ["daily_plans.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["destination_id"], ["destinations.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "daily_plan_id", "position", name="uq_timeline_daily_plan_position"
        ),
    )
    op.create_table(
        "stays",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("daily_plan_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("address", sa.Text(), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("check_in", sa.Time(), nullable=True),
        sa.Column("check_out", sa.Time(), nullable=True),
        sa.Column("public_listing_url", sa.Text(), nullable=True),
        sa.Column("booking_platform", sa.String(length=80), nullable=True),
        sa.Column("revision", sa.Integer(), server_default="1", nullable=False),
        *_location_constraints("stay"),
        sa.CheckConstraint("revision > 0", name="positive_stay_revision"),
        sa.ForeignKeyConstraint(
            ["daily_plan_id"], ["daily_plans.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("daily_plan_id", name="uq_stay_daily_plan"),
    )
    op.create_table(
        "photos",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("daily_plan_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("caption", sa.Text(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("revision", sa.Integer(), server_default="1", nullable=False),
        sa.CheckConstraint("position >= 0", name="nonnegative_photo_position"),
        sa.CheckConstraint("revision > 0", name="positive_photo_revision"),
        sa.ForeignKeyConstraint(
            ["daily_plan_id"], ["daily_plans.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "daily_plan_id", "position", name="uq_photo_daily_plan_position"
        ),
    )


def downgrade() -> None:
    op.drop_table("photos")
    op.drop_table("stays")
    op.drop_table("timeline_entries")
    op.drop_table("daily_plans")
