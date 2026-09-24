from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    UniqueConstraint,
    text,
)
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column

from tripper_api.core.models import Base


class TripRole(StrEnum):
    CREATOR = "creator"
    CONTRIBUTOR = "contributor"
    TRAVELLER = "traveller"


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
    account_id: Mapped[UUID] = mapped_column(
        ForeignKey("accounts.id", name="fk_membership_account")
    )
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
