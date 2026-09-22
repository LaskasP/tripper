from dataclasses import dataclass
from datetime import date
from uuid import UUID

from sqlalchemy import case, select
from sqlalchemy.ext.asyncio import AsyncSession

from tripper_api.auth.auth_model import Account
from tripper_api.trip.trip_dto import TripSummaryResponse
from tripper_api.trip.trip_model import Destination, Trip, TripMembership, TripRole


@dataclass(frozen=True)
class _StoredParticipantGuide:
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
    roster: tuple[tuple[str, TripRole], ...]


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

    async def load_participant_guide(
        self, trip_id: UUID, account_id: UUID
    ) -> _StoredParticipantGuide | None:
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
            .join(TripMembership, TripMembership.trip_id == Trip.id)
            .where(
                Trip.id == trip_id,
                TripMembership.account_id == account_id,
            )
        )
        row = (await self._session.execute(statement)).tuples().one_or_none()
        if row is None:
            return None
        roster_statement = (
            select(Account.display_name, TripMembership.role)
            .join(TripMembership, TripMembership.account_id == Account.id)
            .where(TripMembership.trip_id == trip_id)
            .order_by(
                case(
                    (TripMembership.role == TripRole.CREATOR, 0),
                    (TripMembership.role == TripRole.CONTRIBUTOR, 1),
                    else_=2,
                ),
                Account.display_name,
                TripMembership.account_id,
            )
        )
        roster_rows = (await self._session.execute(roster_statement)).tuples().all()
        return _StoredParticipantGuide(
            id=row[0],
            name=row[1],
            destination=row[2],
            short_name=row[3],
            description=row[4],
            timezone=row[5],
            latitude=row[6],
            longitude=row[7],
            start_date=row[8],
            end_date=row[9],
            roster=tuple((display_name, role) for display_name, role in roster_rows),
        )
