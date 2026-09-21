"""Add Google Accounts and server-side Tripper Sessions.

Existing membership identities are preserved as unlinked legacy Accounts. They do
not impersonate Google identities and must be reconciled deliberately. Downgrade
deletes all Session and Account data.

Revision ID: 20260921_02
Revises: 20260921_01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260921_02"
down_revision: str | None = "20260921_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("issuer", sa.String(length=200), nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("display_name", sa.String(length=200), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("issuer", "subject", name="uq_account_google_identity"),
    )
    op.execute(
        """INSERT INTO accounts (id, issuer, subject, email, display_name)
        SELECT DISTINCT account_id,
            'legacy-unlinked',
            account_id::text,
            'unlinked-' || account_id::text || '@invalid',
            'Unlinked account'
        FROM trip_memberships"""
    )
    op.create_foreign_key(
        "fk_membership_account", "trip_memberships", "accounts", ["account_id"], ["id"]
    )
    op.create_table(
        "sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("csrf_token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )


def downgrade() -> None:
    op.drop_table("sessions")
    op.drop_constraint("fk_membership_account", "trip_memberships", type_="foreignkey")
    op.drop_table("accounts")
