from dataclasses import dataclass
from datetime import date
from uuid import UUID

from tripper_api.membership.membership_model import TripRole
from tripper_api.trip.trip_model import Trip


@dataclass(frozen=True)
class TripAccess:
    trip: Trip
    role: TripRole


@dataclass(frozen=True)
class MembershipTripSummary:
    id: UUID
    name: str
    destination: str
    short_name: str
    start_date: date
    end_date: date
    role: TripRole
