from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    text,
)
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column

from tripper_api.core.models import Base
from tripper_api.membership.membership_model import TripRole


class OutboxStatus(StrEnum):
    PENDING = "pending"
    DELIVERING = "delivering"
    SENT = "sent"
    FAILED = "failed"
    AMBIGUOUS = "ambiguous"
    CANCELLED = "cancelled"
    DELIVERED = "delivered"
    COMPLAINED = "complained"


class DeliveryEventType(StrEnum):
    DELIVERED = "delivered"
    TEMPORARY_FAILURE = "temporary_failure"
    PERMANENT_FAILURE = "permanent_failure"
    COMPLAINED = "complained"


class TripInvitation(Base):
    __tablename__ = "trip_invitations"
    __table_args__ = (
        CheckConstraint(
            "role IN ('contributor', 'traveller')",
            name="valid_invitation_role",
        ),
        CheckConstraint("expires_at > created_at", name="valid_invitation_expiry"),
        Index(
            "uq_active_invitation_trip_email",
            "trip_id",
            "email",
            unique=True,
            postgresql_where=text(
                "revoked_at IS NULL AND replaced_at IS NULL AND accepted_at IS NULL"
            ),
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    trip_id: Mapped[UUID] = mapped_column(ForeignKey("trips.id", ondelete="CASCADE"))
    email: Mapped[str] = mapped_column(String(320))
    role: Mapped[TripRole] = mapped_column(
        SqlEnum(
            TripRole,
            name="valid_invitation_role",
            native_enum=False,
            create_constraint=False,
            validate_strings=True,
            values_callable=lambda roles: [role.value for role in roles],
            length=20,
        )
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    replaced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class InvitationEmailOutbox(Base):
    __tablename__ = "invitation_email_outbox"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'delivering', 'sent', 'failed', "
            "'ambiguous', 'cancelled', 'delivered', 'complained')",
            name="valid_invitation_outbox_status",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    invitation_id: Mapped[UUID] = mapped_column(
        ForeignKey("trip_invitations.id", ondelete="CASCADE")
    )
    deduplication_key: Mapped[str] = mapped_column(String(100), unique=True)
    recipient_email: Mapped[str] = mapped_column(String(320))
    status: Mapped[OutboxStatus] = mapped_column(
        SqlEnum(
            OutboxStatus,
            name="valid_invitation_outbox_status",
            native_enum=False,
            create_constraint=False,
            validate_strings=True,
            values_callable=lambda statuses: [status.value for status in statuses],
            length=20,
        ),
        default=OutboxStatus.PENDING,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    next_attempt_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    attempt_count: Mapped[int] = mapped_column(Integer, server_default="0")
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error_code: Mapped[str | None] = mapped_column(String(80))


class InvitationEmailEvent(Base):
    __tablename__ = "invitation_email_events"

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    outbox_id: Mapped[UUID] = mapped_column(
        ForeignKey("invitation_email_outbox.id", ondelete="CASCADE")
    )
    provider_event_id: Mapped[str] = mapped_column(String(200), unique=True)
    event_type: Mapped[DeliveryEventType] = mapped_column(
        SqlEnum(
            DeliveryEventType,
            name="valid_invitation_delivery_event_type",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            values_callable=lambda events: [event.value for event in events],
            length=30,
        )
    )
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
