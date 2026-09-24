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
