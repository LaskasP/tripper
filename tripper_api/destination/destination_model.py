from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column

from tripper_api.core.models import Base


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
