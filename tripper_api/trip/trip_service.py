from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from tripper_api.trip.trip_domain import CreateTrip, TripRole
from tripper_api.trip.trip_model import Destination, Trip, TripMembership
from tripper_api.trip.trip_repository import (
    StoredParticipantTrip,
    StoredTrip,
    TripRepository,
)


class TripNotFoundError(Exception):
    pass


class TripService:
    def __init__(self, session: AsyncSession, repository: TripRepository) -> None:
        self._session = session
        self._repository = repository

    async def create(
        self, trip_input: CreateTrip, account_id: UUID
    ) -> StoredParticipantTrip:
        trip = Trip(
            id=uuid4(),
            name=trip_input.name,
            short_name=trip_input.short_name,
            description=trip_input.description,
            start_date=trip_input.start_date,
            end_date=trip_input.end_date,
        )
        destination = Destination(
            id=uuid4(),
            trip_id=trip.id,
            name=trip_input.destination,
            timezone=trip_input.timezone,
            latitude=trip_input.latitude,
            longitude=trip_input.longitude,
            position=0,
        )
        membership = TripMembership(
            id=uuid4(),
            trip_id=trip.id,
            account_id=account_id,
            role=TripRole.CREATOR,
        )
        async with self._session.begin():
            await self._repository.add(trip, destination, membership)
        return StoredParticipantTrip(trip, destination, membership.role)

    async def list_for_account(self, account_id: UUID) -> list[StoredParticipantTrip]:
        async with self._session.begin():
            return await self._repository.list_for_account(account_id)

    async def get_public(self, trip_id: UUID) -> StoredTrip:
        async with self._session.begin():
            stored_trip = await self._repository.get(trip_id)
        if stored_trip is None:
            raise TripNotFoundError
        return stored_trip
