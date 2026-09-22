from datetime import date, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy import (
    Enum as SqlEnum,
)
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column

from tripper_api.core.models import Base


class TripRole(StrEnum):
    CREATOR = "creator"
    CONTRIBUTOR = "contributor"
    TRAVELLER = "traveller"


class Trip(Base):
    __tablename__ = "trips"
    __table_args__ = (
        CheckConstraint("start_date <= end_date", name="valid_trip_date_range"),
        CheckConstraint("revision > 0", name="positive_trip_revision"),
        CheckConstraint("content_revision > 0", name="positive_trip_content_revision"),
    )

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    name: Mapped[str] = mapped_column(String(200))
    short_name: Mapped[str] = mapped_column(String(80))
    description: Mapped[str] = mapped_column(Text)
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    revision: Mapped[int] = mapped_column(Integer, server_default="1")
    content_revision: Mapped[int] = mapped_column(Integer, server_default="1")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP")
    )


class Destination(Base):
    __tablename__ = "destinations"
    __table_args__ = (
        CheckConstraint("position >= 0", name="nonnegative_destination_position"),
        CheckConstraint(
            "(latitude IS NULL) = (longitude IS NULL)",
            name="complete_destination_location",
        ),
        CheckConstraint("revision > 0", name="positive_destination_revision"),
        UniqueConstraint("trip_id", "position", name="uq_destination_trip_position"),
    )

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    trip_id: Mapped[UUID] = mapped_column(ForeignKey("trips.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(200))
    timezone: Mapped[str] = mapped_column(String(100))
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    position: Mapped[int] = mapped_column(Integer)
    revision: Mapped[int] = mapped_column(Integer, server_default="1")


class TripMembership(Base):
    __tablename__ = "trip_memberships"
    __table_args__ = (
        CheckConstraint(
            "role IN ('creator', 'contributor', 'traveller')",
            name="valid_membership_role",
        ),
        CheckConstraint("revision > 0", name="positive_membership_revision"),
        UniqueConstraint("trip_id", "account_id", name="uq_membership_trip_account"),
        Index(
            "uq_membership_one_creator",
            "trip_id",
            unique=True,
            postgresql_where=text("role = 'creator'"),
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    trip_id: Mapped[UUID] = mapped_column(ForeignKey("trips.id", ondelete="CASCADE"))
    account_id: Mapped[UUID] = mapped_column(PostgresUUID(as_uuid=True))
    role: Mapped[TripRole] = mapped_column(
        SqlEnum(
            TripRole,
            name="valid_membership_role",
            native_enum=False,
            create_constraint=False,
            validate_strings=True,
            values_callable=lambda roles: [role.value for role in roles],
            length=20,
        )
    )
    revision: Mapped[int] = mapped_column(Integer, server_default="1")
