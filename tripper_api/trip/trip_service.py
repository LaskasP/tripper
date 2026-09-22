from dataclasses import dataclass
from datetime import date, timedelta
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from tripper_api.trip.trip_dto import (
    TripCreateRequest,
    TripSummaryResponse,
)
from tripper_api.trip.trip_model import Destination, Trip, TripMembership, TripRole
from tripper_api.trip.trip_repository import TripDetailRecord, TripRepository


@dataclass(frozen=True)
class TripCalendarDateRecord:
    date: date
    day_number: int
    is_planned: bool = False


@dataclass(frozen=True)
class ParticipantTripGuideRecord:
    trip: TripDetailRecord
    calendar: tuple[TripCalendarDateRecord, ...]


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
        request: TripCreateRequest,
    ) -> TripSummaryResponse:
        trip = Trip(
            id=uuid4(),
            name=request.name,
            short_name=request.short_name,
            description=request.description,
            start_date=request.start_date,
            end_date=request.end_date,
        )
        destination = Destination(
            id=uuid4(),
            trip_id=trip.id,
            name=request.destination,
            timezone=request.timezone,
            latitude=request.location.lat if request.location is not None else None,
            longitude=request.location.lng if request.location is not None else None,
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
        return TripSummaryResponse(
            id=trip.id,
            name=trip.name,
            destination=destination.name,
            short_name=trip.short_name,
            start_date=trip.start_date,
            end_date=trip.end_date,
            role=membership.role,
        )

    async def list_for_account(self, account_id: UUID) -> list[TripSummaryResponse]:
        async with self._session.begin():
            return await self._repository.list_for_account(account_id)

    async def get_for_account(
        self, trip_id: UUID, account_id: UUID
    ) -> ParticipantTripGuideRecord:
        async with self._session.begin():
            trip = await self._repository.get_for_account(trip_id, account_id)
        if trip is None:
            raise TripNotFoundError
        return ParticipantTripGuideRecord(
            trip=trip,
            calendar=tuple(
                TripCalendarDateRecord(
                    date=trip.start_date + timedelta(days=offset),
                    day_number=offset + 1,
                )
                for offset in range((trip.end_date - trip.start_date).days + 1)
            ),
        )
