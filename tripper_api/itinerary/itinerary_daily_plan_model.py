from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    Date,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from tripper_api.core.models import Base

if TYPE_CHECKING:
    from tripper_api.itinerary.itinerary_photo_model import Photo
    from tripper_api.itinerary.itinerary_stay_model import Stay
    from tripper_api.itinerary.itinerary_timeline_model import TimelineEntry


class DailyPlan(Base):
    __tablename__ = "daily_plans"
    __table_args__ = (
        CheckConstraint("revision > 0", name="positive_daily_plan_revision"),
        CheckConstraint(
            "timeline_revision > 0", name="positive_timeline_collection_revision"
        ),
        CheckConstraint(
            "photo_revision > 0", name="positive_photo_collection_revision"
        ),
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
    timeline_revision: Mapped[int] = mapped_column(Integer, server_default="1")
    photo_revision: Mapped[int] = mapped_column(Integer, server_default="1")

    timeline_entries: Mapped[list[TimelineEntry]] = relationship(
        lazy="raise",
        order_by="(TimelineEntry.local_time, TimelineEntry.position, TimelineEntry.id)",
        passive_deletes="all",
    )
    stay: Mapped[Stay | None] = relationship(
        lazy="raise", uselist=False, passive_deletes="all"
    )
    photos: Mapped[list[Photo]] = relationship(
        lazy="raise", order_by="(Photo.position, Photo.id)", passive_deletes="all"
    )
