from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from tripper_api.membership.membership_model import TripRole


class TripSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    destination: str
    short_name: str
    start_date: date
    end_date: date
    role: TripRole


class TripRosterMemberResponse(BaseModel):
    display_name: str
    role: TripRole
