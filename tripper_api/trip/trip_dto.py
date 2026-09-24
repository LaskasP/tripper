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


class StayDeleteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    starting_revision: int = Field(ge=1)


class TimelineEntryFields(BaseModel):
    model_config = ConfigDict(extra="forbid")

    destination_id: UUID | None = None
    time: LocalTime
    title: str = Field(min_length=1, max_length=200)
    description: str = ""
    location_name: str | None = Field(default=None, max_length=300)
    location: LocationInput | None = None

    @field_validator("title")
    @classmethod
    def validate_nonblank_title(cls, value: str) -> str:
        return _nonblank(value)

    @field_validator("time")
    @classmethod
    def validate_local_time(cls, value: LocalTime) -> LocalTime:
        return _local_time(value)


class TimelineEntryCreateRequest(TimelineEntryFields):
    starting_revision: int = Field(ge=1)


class TimelineEntryUpdateRequest(TimelineEntryFields):
    starting_revision: int = Field(ge=1)


class TimelineEntryDeleteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    starting_revision: int = Field(ge=1)
    starting_collection_revision: int = Field(ge=1)


class TimelineReorderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    starting_revision: int = Field(ge=1)
    entry_ids: list[UUID]

    @field_validator("entry_ids")
    @classmethod
    def validate_unique_entry_ids(cls, value: list[UUID]) -> list[UUID]:
        if len(value) != len(set(value)):
            raise ValueError("entry_ids must be unique")
        return value


class TimelineEntryMoveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_starting_revision: int = Field(ge=1)
    target_plan_id: UUID
    target_starting_revision: int = Field(ge=1)


def _https_url(value: str) -> str:
    stripped = value.strip()
    parsed = urlparse(stripped)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or any(character.isspace() for character in stripped)
    ):
        raise ValueError("url must be an HTTPS URL")
    return stripped


class PhotoCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    starting_revision: int = Field(ge=1)
    url: str
    caption: str = ""

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        return _https_url(value)


class PhotoDeleteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    starting_revision: int = Field(ge=1)


class PhotoReorderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    starting_revision: int = Field(ge=1)
    photo_ids: list[UUID]

    @field_validator("photo_ids")
    @classmethod
    def validate_unique_photo_ids(cls, value: list[UUID]) -> list[UUID]:
        if len(value) != len(set(value)):
            raise ValueError("photo_ids must be unique")
        return value
