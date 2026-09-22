from datetime import date, datetime, time
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
    Time,
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


class DailyPlan(Base):
    __tablename__ = "daily_plans"
    __table_args__ = (
        CheckConstraint("revision > 0", name="positive_daily_plan_revision"),
        UniqueConstraint("trip_id", "date", name="uq_daily_plan_trip_date"),
    )

    id: Mapped[UUID] = mapped_column(PostgresUUID(as_uuid=True), primary_key=True)
    trip_id: Mapped[UUID] = mapped_column(ForeignKey("trips.id", ondelete="CASCADE"))
    destination_id: Mapped[UUID] = mapped_column(
        ForeignKey("destinations.id", ondelete="RESTRICT")
    )
    date: Mapped[date] = mapped_column(Date)
    title: Mapped[str] = mapped_column(String(200))
    summary: Mapped[str] = mapped_column(Text)
    background_image: Mapped[str] = mapped_column(Text)
    revision: Mapped[int] = mapped_column(Integer, server_default="1")


class TimelineEntry(Base):
    __tablename__ = "timeline_entries"
    __table_args__ = (
        CheckConstraint(
            "(latitude IS NULL) = (longitude IS NULL)",
            name="complete_timeline_entry_location",
        ),
        CheckConstraint("position >= 0", name="nonnegative_timeline_position"),
        CheckConstraint("revision > 0", name="positive_timeline_revision"),
        UniqueConstraint(
            "daily_plan_id", "position", name="uq_timeline_daily_plan_position"
        ),
    )

    id: Mapped[UUID] = mapped_column(PostgresUUID(as_uuid=True), primary_key=True)
    daily_plan_id: Mapped[UUID] = mapped_column(
        ForeignKey("daily_plans.id", ondelete="CASCADE")
    )
    destination_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("destinations.id", ondelete="RESTRICT"), nullable=True
    )
    local_time: Mapped[time] = mapped_column(Time)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    location_name: Mapped[str | None] = mapped_column(String(300), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    position: Mapped[int] = mapped_column(Integer)
    revision: Mapped[int] = mapped_column(Integer, server_default="1")


class Stay(Base):
    __tablename__ = "stays"
    __table_args__ = (
        CheckConstraint(
            "(latitude IS NULL) = (longitude IS NULL)", name="complete_stay_location"
        ),
        CheckConstraint("revision > 0", name="positive_stay_revision"),
        UniqueConstraint("daily_plan_id", name="uq_stay_daily_plan"),
    )

    id: Mapped[UUID] = mapped_column(PostgresUUID(as_uuid=True), primary_key=True)
    daily_plan_id: Mapped[UUID] = mapped_column(
        ForeignKey("daily_plans.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String(200))
    address: Mapped[str] = mapped_column(Text)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    check_in: Mapped[time | None] = mapped_column(Time, nullable=True)
    check_out: Mapped[time | None] = mapped_column(Time, nullable=True)
    public_listing_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    booking_platform: Mapped[str | None] = mapped_column(String(80), nullable=True)
    revision: Mapped[int] = mapped_column(Integer, server_default="1")


class Photo(Base):
    __tablename__ = "photos"
    __table_args__ = (
        CheckConstraint("position >= 0", name="nonnegative_photo_position"),
        CheckConstraint("revision > 0", name="positive_photo_revision"),
        UniqueConstraint(
            "daily_plan_id", "position", name="uq_photo_daily_plan_position"
        ),
    )

    id: Mapped[UUID] = mapped_column(PostgresUUID(as_uuid=True), primary_key=True)
    daily_plan_id: Mapped[UUID] = mapped_column(
        ForeignKey("daily_plans.id", ondelete="CASCADE")
    )
    url: Mapped[str] = mapped_column(Text)
    caption: Mapped[str] = mapped_column(Text)
    position: Mapped[int] = mapped_column(Integer)
    revision: Mapped[int] = mapped_column(Integer, server_default="1")
