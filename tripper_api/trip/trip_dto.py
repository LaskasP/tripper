from datetime import date
from datetime import time as LocalTime
from urllib.parse import urlparse
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from tripper_api.trip.trip_model import TripRole


def _nonblank(value: str) -> str:
    stripped = value.strip()
    if not stripped:
        raise ValueError("value must not be blank")
    return stripped


def _iana_timezone(value: str) -> str:
    stripped = value.strip()
    try:
        ZoneInfo(stripped)
    except ZoneInfoNotFoundError as error:
        raise ValueError("timezone must be a valid IANA timezone") from error
    return stripped


def _local_time(value: LocalTime) -> LocalTime:
    if value.tzinfo is not None:
        raise ValueError("time must be a local time without an offset")
    return value


class LocationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)


class DestinationDetailsInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID | None = None
    name: str = Field(min_length=1, max_length=200)
    timezone: str = Field(min_length=1, max_length=100)
    location: LocationInput | None = None

    @field_validator("name")
    @classmethod
    def validate_nonblank_name(cls, value: str) -> str:
        return _nonblank(value)

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        return _iana_timezone(value)


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
        return _nonblank(value)

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
        return _nonblank(value)

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        return _iana_timezone(value)

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


class TripCalendarDateResponse(BaseModel):
    date: date
    day_number: int
    is_planned: bool = False


class TripRosterMemberResponse(BaseModel):
    display_name: str
    role: TripRole


class DestinationDetailsResponse(BaseModel):
    id: UUID
    name: str
    timezone: str
    location: LocationInput | None
    position: int
    revision: int


class TimelineEntryResponse(BaseModel):
    id: UUID
    destination_id: UUID | None
    revision: int
    position: int
    time: LocalTime
    timezone: str
    title: str
    description: str
    location: LocationInput | None
    location_name: str | None


class StayResponse(BaseModel):
    name: str
    address: str
    location: LocationInput | None
    check_in: LocalTime | None
    check_out: LocalTime | None
    public_listing_url: str | None
    booking_platform: str | None


class PhotoResponse(BaseModel):
    url: str
    caption: str


class DailyPlanResponse(BaseModel):
    id: UUID
    destination_id: UUID
    revision: int
    timeline_revision: int
    date: date
    day_number: int
    title: str
    summary: str
    background_image: str
    stay: StayResponse | None
    timeline: list[TimelineEntryResponse]
    photos: list[PhotoResponse]


class TripDetailResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: UUID
    revision: int
    content_revision: int
    role: TripRole
    name: str
    destination: str
    short_name: str
    description: str
    timezone: str
    location: LocationInput | None
    start_date: date
    end_date: date
    destinations: list[DestinationDetailsResponse]
    calendar: list[TripCalendarDateResponse]
    daily_plans: list[DailyPlanResponse]
    roster: list[TripRosterMemberResponse]


class DailyPlanWriteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID | None = None
    starting_revision: int = Field(ge=1)
    destination_id: UUID
    title: str = Field(max_length=200)
    summary: str = ""
    background_image: str = ""

    @field_validator("background_image")
    @classmethod
    def validate_background_image(cls, value: str) -> str:
        value = value.strip()
        parsed = urlparse(value)
        if value and (parsed.scheme != "https" or not parsed.netloc):
            raise ValueError("background_image must be an HTTPS URL")
        return value


class DailyPlanRevisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    starting_revision: int = Field(ge=1)


class DailyPlanMoveRequest(DailyPlanRevisionRequest):
    target_date: date


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
