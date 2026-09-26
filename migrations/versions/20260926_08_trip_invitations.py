"""Add Trip invitations and the durable invitation-email outbox.

Data impact: creates empty tables; existing Trips and memberships are unchanged.
Rollback: destructive and irreversible once used; drops every invitation and all
delivery history.

Revision ID: 20260926_08
Revises: 20260926_07
Create Date: 2026-09-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260926_08"
down_revision: str | None = "20260926_07"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "trip_invitations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("trip_id", sa.UUID(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("replaced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "role IN ('contributor', 'traveller')", name="valid_invitation_role"
        ),
        sa.CheckConstraint("expires_at > created_at", name="valid_invitation_expiry"),
        sa.ForeignKeyConstraint(["trip_id"], ["trips.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index(
        "uq_active_invitation_trip_email",
        "trip_invitations",
        ["trip_id", "email"],
        unique=True,
        postgresql_where=sa.text(
            "revoked_at IS NULL AND replaced_at IS NULL AND accepted_at IS NULL"
        ),
    )
    op.create_table(
        "invitation_email_outbox",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("invitation_id", sa.UUID(), nullable=False),
        sa.Column("deduplication_key", sa.String(length=100), nullable=False),
        sa.Column("recipient_email", sa.String(length=320), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_code", sa.String(length=80), nullable=True),
        sa.CheckConstraint(
            "status IN ('pending', 'delivering', 'sent', 'failed', "
            "'ambiguous', 'cancelled', 'delivered', 'complained')",
            name="valid_invitation_outbox_status",
        ),
        sa.ForeignKeyConstraint(
            ["invitation_id"], ["trip_invitations.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("deduplication_key"),
    )
    op.create_table(
        "invitation_email_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("outbox_id", sa.UUID(), nullable=False),
        sa.Column("provider_event_id", sa.String(length=200), nullable=False),
        sa.Column("event_type", sa.String(length=30), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "event_type IN ('delivered', 'temporary_failure', "
            "'permanent_failure', 'complained')",
            name="valid_invitation_delivery_event_type",
        ),
        sa.ForeignKeyConstraint(
            ["outbox_id"], ["invitation_email_outbox.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider_event_id"),
    )


def downgrade() -> None:
    op.drop_table("invitation_email_events")
    op.drop_table("invitation_email_outbox")
    op.drop_index("uq_active_invitation_trip_email", table_name="trip_invitations")
    op.drop_table("trip_invitations")
