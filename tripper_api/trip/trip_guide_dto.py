from datetime import date
from datetime import time as LocalTime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from tripper_api.membership.membership_dto import TripRosterMemberResponse
from tripper_api.membership.membership_model import TripRole


class GuideLocationResponse(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)


class TripCalendarDateResponse(BaseModel):
    date: date
    day_number: int
    is_planned: bool = False


class DestinationDetailsResponse(BaseModel):
    id: UUID
    name: str
    timezone: str
    location: GuideLocationResponse | None
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
    location: GuideLocationResponse | None
    location_name: str | None


class StayResponse(BaseModel):
    id: UUID
    revision: int
    name: str
    address: str
    location: GuideLocationResponse | None
    check_in: LocalTime | None
    check_out: LocalTime | None
    public_listing_url: str | None
    booking_platform: str | None


class PhotoResponse(BaseModel):
    id: UUID
    position: int
    url: str
    caption: str


class DailyPlanResponse(BaseModel):
    id: UUID
    destination_id: UUID
    revision: int
    timeline_revision: int
    photo_revision: int
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
    location: GuideLocationResponse | None
    start_date: date
    end_date: date
    destinations: list[DestinationDetailsResponse]
    calendar: list[TripCalendarDateResponse]
    daily_plans: list[DailyPlanResponse]
    roster: list[TripRosterMemberResponse]


class PublicTimelineEntryResponse(BaseModel):
    time: LocalTime
    timezone: str
    title: str
    description: str
    location: GuideLocationResponse | None
    location_name: str | None


class PublicStayResponse(BaseModel):
    name: str
    address: str
    location: GuideLocationResponse | None
    check_in: LocalTime | None
    check_out: LocalTime | None
    public_listing_url: str | None
    booking_platform: str | None


class PublicPhotoResponse(BaseModel):
    url: str
    caption: str


class PublicDailyPlanResponse(BaseModel):
    date: date
    day_number: int
    title: str
    summary: str
    background_image: str
    stay: PublicStayResponse | None
    timeline: list[PublicTimelineEntryResponse]
    photos: list[PublicPhotoResponse]


class PublicTripGuideResponse(BaseModel):
    name: str
    destination: str
    short_name: str
    description: str
    timezone: str
    location: GuideLocationResponse | None
    start_date: date
    end_date: date
    calendar: list[TripCalendarDateResponse]
    daily_plans: list[PublicDailyPlanResponse]
