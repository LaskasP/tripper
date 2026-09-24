from dataclasses import dataclass
from datetime import date
from uuid import UUID


@dataclass(frozen=True)
class ItineraryTripReferences:
    plan_dates: frozenset[date]
    destination_ids: frozenset[UUID]
