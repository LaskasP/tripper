from dataclasses import dataclass
from datetime import date
from enum import StrEnum


class TripRole(StrEnum):
    CREATOR = "creator"
    CONTRIBUTOR = "contributor"
    TRAVELLER = "traveller"


@dataclass(frozen=True)
class CreateTrip:
    name: str
    destination: str
    short_name: str
    description: str
    timezone: str
    latitude: float
    longitude: float
    start_date: date
    end_date: date
