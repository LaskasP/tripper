from datetime import date

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from tripper_api.destination.destination_dto import (
    DestinationDetailsInput,
    LocationInput,
    iana_timezone,
    nonblank,
)


class TripDetailsUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    starting_revision: int = Field(ge=1)
    name: str = Field(min_length=1, max_length=200)
    short_name: str = Field(default="", max_length=80)
    description: str = ""
    start_date: date
    end_date: date
    destinations: list[DestinationDetailsInput] = Field(min_length=1)

    @field_validator("name")
    @classmethod
    def validate_nonblank_name(cls, value: str) -> str:
        return nonblank(value)

    @model_validator(mode="after")
    def validate_details(self) -> "TripDetailsUpdateRequest":
        if self.start_date > self.end_date:
            raise ValueError("start_date must be on or before end_date")
        destination_ids = [
            destination.id
            for destination in self.destinations
            if destination.id is not None
        ]
        if len(destination_ids) != len(set(destination_ids)):
            raise ValueError("destination ids must be unique")
        return self


class TripCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=200)
    destination: str = Field(min_length=1, max_length=200)
    short_name: str = Field(default="", max_length=80)
    description: str = ""
    timezone: str = Field(min_length=1, max_length=100)
    location: LocationInput | None = None
    start_date: date
    end_date: date

    @field_validator("name", "destination")
    @classmethod
    def validate_nonblank_text(cls, value: str) -> str:
        return nonblank(value)

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        return iana_timezone(value)

    @model_validator(mode="after")
    def validate_date_range(self) -> "TripCreateRequest":
        if self.start_date > self.end_date:
            raise ValueError("start_date must be on or before end_date")
        return self
