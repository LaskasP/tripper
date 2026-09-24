from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, Date, DateTime, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from tripper_api.core.models import Base

if TYPE_CHECKING:
    from tripper_api.destination.destination_model import Destination
    from tripper_api.itinerary.itinerary_daily_plan_model import DailyPlan


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

    destinations: Mapped[list[Destination]] = relationship(
        lazy="raise",
        order_by="(Destination.position, Destination.id)",
        passive_deletes="all",
    )
    daily_plans: Mapped[list[DailyPlan]] = relationship(
        lazy="raise",
        order_by="(DailyPlan.date, DailyPlan.id)",
        passive_deletes="all",
    )
