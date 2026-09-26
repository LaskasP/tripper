from datetime import datetime
from re import fullmatch
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from tripper_api.invitation.invitation_model import OutboxStatus
from tripper_api.membership.membership_model import TripRole


class InvitationCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=3, max_length=320)
    role: TripRole

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        normalized = value.strip().casefold()
        if fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", normalized) is None:
            raise ValueError("email must be valid")
        return normalized

    @field_validator("role")
    @classmethod
    def reject_creator_role(cls, value: TripRole) -> TripRole:
        if value is TripRole.CREATOR:
            raise ValueError("Creator invitations are not permitted")
        return value


class InvitationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    role: TripRole
    created_at: datetime
    expires_at: datetime
    delivery_status: OutboxStatus
