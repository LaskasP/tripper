from dataclasses import dataclass
from datetime import date
from uuid import UUID

from tripper_api.destination.destination_model import Destination
from tripper_api.trip.trip_model import Trip


@dataclass(frozen=True)
class TripForUpdate:
    trip: Trip
    destinations: tuple[Destination, ...]
    plan_dates: frozenset[date]
    referenced_destination_ids: frozenset[UUID]
