from datetime import time as LocalTime
from typing import Literal
from urllib.parse import urlparse
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from tripper_api.destination.destination_dto import LocationInput
from tripper_api.destination.destination_dto import nonblank as _nonblank


def _local_time(value: LocalTime) -> LocalTime:
    if value.tzinfo is not None:
        raise ValueError("time must be a local time without an offset")
    return value


class StayWriteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID | None = None
    starting_revision: int = Field(ge=1)
    name: str = Field(min_length=1, max_length=200)
    address: str = ""
    location: LocationInput | None = None
    check_in: LocalTime | None = None
    check_out: LocalTime | None = None
    public_listing_url: str | None = None
    booking_platform: Literal["booking.com", "airbnb"] | None = None

    @field_validator("name")
    @classmethod
    def validate_nonblank_name(cls, value: str) -> str:
        return _nonblank(value)

    @field_validator("address")
    @classmethod
    def normalize_address(cls, value: str) -> str:
        return value.strip()

    @field_validator("check_in", "check_out")
    @classmethod
    def validate_local_time(cls, value: LocalTime | None) -> LocalTime | None:
        return _local_time(value) if value is not None else None

    @field_validator("public_listing_url")
    @classmethod
    def validate_public_listing_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        parsed = urlparse(value)
        if parsed.scheme != "https" or not parsed.netloc:
            raise ValueError("public_listing_url must be an HTTPS URL")
        return value


class StayRevisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    starting_revision: int = Field(ge=1)
