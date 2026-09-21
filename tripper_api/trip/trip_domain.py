from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from uuid import UUID


class TripRole(StrEnum):
    CREATOR = "creator"
    CONTRIBUTOR = "contributor"
    TRAVELLER = "traveller"


@dataclass(frozen=True)
class ParticipantTrip:
    id: UUID
    name: str
    destination: str
    short_name: str
    start_date: date
    end_date: date
    role: TripRole


@dataclass(frozen=True)
class PublicTripView:
    id: UUID
    name: str
    destination: str
    short_name: str
    description: str
    timezone: str
    latitude: float | None
    longitude: float | None
    start_date: date
    end_date: date
