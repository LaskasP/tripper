from datetime import time as LocalTime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from tripper_api.destination.destination_dto import LocationInput
from tripper_api.destination.destination_dto import nonblank as _nonblank


def _local_time(value: LocalTime) -> LocalTime:
    if value.tzinfo is not None:
        raise ValueError("time must be a local time without an offset")
    return value


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
