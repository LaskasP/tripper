from datetime import date
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from tripper_api.trip.trip_domain import ParticipantTrip, PublicTripView, TripRole
from tripper_api.trip.trip_model import Destination, Trip, TripMembership
from tripper_api.trip.trip_repository import TripRepository


class TripNotFoundError(Exception):
    pass


class TripService:
    def __init__(self, session: AsyncSession, repository: TripRepository) -> None:
        self._session = session
        self._repository = repository

    async def create(
        self,
        *,
        account_id: UUID,
        name: str,
        destination_name: str,
        short_name: str,
        description: str,
        timezone: str,
        latitude: float,
        longitude: float,
        start_date: date,
        end_date: date,
    ) -> ParticipantTrip:
        trip = Trip(
            id=uuid4(),
            name=name,
            short_name=short_name,
            description=description,
            start_date=start_date,
            end_date=end_date,
        )
        destination = Destination(
            id=uuid4(),
            trip_id=trip.id,
            name=destination_name,
            timezone=timezone,
            latitude=latitude,
            longitude=longitude,
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
        return ParticipantTrip(
            id=trip.id,
            name=trip.name,
            destination=destination.name,
            short_name=trip.short_name,
            start_date=trip.start_date,
            end_date=trip.end_date,
            role=membership.role,
        )

    async def list_for_account(self, account_id: UUID) -> list[ParticipantTrip]:
        async with self._session.begin():
            return await self._repository.list_for_account(account_id)

    async def get_public(self, trip_id: UUID) -> PublicTripView:
        async with self._session.begin():
            trip = await self._repository.get_public(trip_id)
        if trip is None:
            raise TripNotFoundError
        return trip
