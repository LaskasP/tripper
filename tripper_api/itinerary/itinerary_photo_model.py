from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column

from tripper_api.core.models import Base


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
