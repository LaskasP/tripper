from datetime import date, time
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from tripper_api.trip.trip_model import TripRole


class LocationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)


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
        stripped = value.strip()
        if not stripped:
            raise ValueError("value must not be blank")
        return stripped

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        stripped = value.strip()
        try:
            ZoneInfo(stripped)
        except ZoneInfoNotFoundError as error:
            raise ValueError("timezone must be a valid IANA timezone") from error
        return stripped

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


class TimelineEntryResponse(BaseModel):
    time: time
    title: str
    description: str
    location: LocationInput | None
    location_name: str | None


class StayResponse(BaseModel):
    name: str
    address: str
    location: LocationInput | None
    check_in: time | None
    check_out: time | None
    public_listing_url: str | None
    booking_platform: str | None


class PhotoResponse(BaseModel):
    url: str
    caption: str


class DailyPlanResponse(BaseModel):
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
    name: str
    destination: str
    short_name: str
    description: str
    timezone: str
    location: LocationInput | None
    start_date: date
    end_date: date
    calendar: list[TripCalendarDateResponse]
    daily_plans: list[DailyPlanResponse]
    roster: list[TripRosterMemberResponse]
