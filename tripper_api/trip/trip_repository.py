from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tripper_api.trip.trip_dto import (
    LocationInput,
    PublicTripResponse,
    TripSummaryResponse,
)
from tripper_api.trip.trip_model import Destination, Trip, TripMembership


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

    async def list_for_account(self, account_id: UUID) -> list[TripSummaryResponse]:
        statement = (
            select(
                Trip.id,
                Trip.name,
                Destination.name,
                Trip.short_name,
                Trip.start_date,
                Trip.end_date,
                TripMembership.role,
            )
            .join(TripMembership, TripMembership.trip_id == Trip.id)
            .join(
                Destination,
                (Destination.trip_id == Trip.id) & (Destination.position == 0),
            )
            .where(TripMembership.account_id == account_id)
            .order_by(Trip.created_at, Trip.id)
        )
        rows = (await self._session.execute(statement)).tuples().all()
        return [
            TripSummaryResponse(
                id=row[0],
                name=row[1],
                destination=row[2],
                short_name=row[3],
                start_date=row[4],
                end_date=row[5],
                role=row[6],
            )
            for row in rows
        ]

    async def get_public(self, trip_id: UUID) -> PublicTripResponse | None:
        statement = (
            select(
                Trip.id,
                Trip.name,
                Destination.name,
                Trip.short_name,
                Trip.description,
                Destination.timezone,
                Destination.latitude,
                Destination.longitude,
                Trip.start_date,
                Trip.end_date,
            )
            .join(
                Destination,
                (Destination.trip_id == Trip.id) & (Destination.position == 0),
            )
            .where(Trip.id == trip_id)
        )
        row = (await self._session.execute(statement)).tuples().one_or_none()
        if row is None:
            return None
        return PublicTripResponse(
            id=row[0],
            name=row[1],
            destination=row[2],
            short_name=row[3],
            description=row[4],
            timezone=row[5],
            location=LocationInput(lat=row[6], lng=row[7]),
            start_date=row[8],
            end_date=row[9],
        )
