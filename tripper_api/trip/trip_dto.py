from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from tripper_api.trip.trip_model import TripRole


class LocationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)


class TripCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=200)
    destination: str = Field(min_length=1, max_length=200)
    short_name: str = Field(min_length=1, max_length=80)
    description: str
    timezone: str = Field(min_length=1, max_length=100)
    location: LocationInput
    start_date: date
    end_date: date

    @model_validator(mode="after")
    def validate_date_range(self) -> "TripCreateRequest":
        if self.start_date > self.end_date:
            raise ValueError("start_date must be on or before end_date")
        return self


class TripSummaryResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    id: UUID
    name: str
    destination: str
    short_name: str
    start_date: date
    end_date: date
    role: TripRole


class PublicTripResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: UUID
    name: str
    destination: str
    short_name: str
    description: str
    timezone: str
    location: LocationInput
    start_date: date
    end_date: date
