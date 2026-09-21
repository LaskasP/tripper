from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tripper_api.trip.trip_domain import TripRole
from tripper_api.trip.trip_model import Destination, Trip, TripMembership


@dataclass(frozen=True)
class StoredTrip:
    trip: Trip
    destination: Destination


@dataclass(frozen=True)
class StoredParticipantTrip:
    trip: Trip
    destination: Destination
    role: TripRole


class TripRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(
        self,
        trip: Trip,
        destination: Destination,
        membership: TripMembership,
    ) -> None:
        self._session.add(trip)
        await self._session.flush()
        self._session.add_all((destination, membership))
        await self._session.flush()

    async def list_for_account(self, account_id: UUID) -> list[StoredParticipantTrip]:
        statement = (
            select(Trip, Destination, TripMembership.role)
            .join(TripMembership, TripMembership.trip_id == Trip.id)
            .join(
                Destination,
                (Destination.trip_id == Trip.id) & (Destination.position == 0),
            )
            .where(TripMembership.account_id == account_id)
            .order_by(Trip.created_at, Trip.id)
        )
        rows = (await self._session.execute(statement)).all()
        return [
            StoredParticipantTrip(trip, destination, role)
            for trip, destination, role in rows
        ]

    async def get(self, trip_id: UUID) -> StoredTrip | None:
        statement = (
            select(Trip, Destination)
            .join(
                Destination,
                (Destination.trip_id == Trip.id) & (Destination.position == 0),
            )
            .where(Trip.id == trip_id)
        )
        row = (await self._session.execute(statement)).one_or_none()
        if row is None:
            return None
        trip, destination = row
        return StoredTrip(trip, destination)
