from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from tripper_api.trip.trip_domain import TripRole


class LocationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)


class TripInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=200)
    destination: str = Field(min_length=1, max_length=200)
    short_name: str = Field(alias="shortName", min_length=1, max_length=80)
    description: str
    timezone: str = Field(min_length=1, max_length=100)
    location: LocationInput
    start_date: date = Field(alias="startDate")
    end_date: date = Field(alias="endDate")

    @model_validator(mode="after")
    def validate_date_range(self) -> "TripInput":
        if self.start_date > self.end_date:
            raise ValueError("startDate must be on or before endDate")
        return self


class TripSummary(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: UUID
    name: str
    destination: str
    short_name: str = Field(serialization_alias="shortName")
    start_date: date = Field(serialization_alias="startDate")
    end_date: date = Field(serialization_alias="endDate")
    role: TripRole


class PublicTrip(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: UUID
    name: str
    destination: str
    short_name: str = Field(serialization_alias="shortName")
    description: str
    timezone: str
    location: LocationInput
    start_date: date = Field(serialization_alias="startDate")
    end_date: date = Field(serialization_alias="endDate")
