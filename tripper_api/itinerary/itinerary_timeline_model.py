from datetime import time
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column

from tripper_api.core.models import Base


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
