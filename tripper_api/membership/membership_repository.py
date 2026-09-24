from typing import cast
from uuid import UUID

from sqlalchemy import case, select
from sqlalchemy.ext.asyncio import AsyncSession

from tripper_api.auth.auth_model import Account
from tripper_api.destination.destination_model import Destination
from tripper_api.membership.membership_model import TripMembership, TripRole
from tripper_api.membership.membership_read_model import (
    MembershipTripSummary,
    TripAccess,
)
from tripper_api.trip.trip_model import Trip


class MembershipRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, membership: TripMembership) -> None:
        self._session.add(membership)
        await self._session.flush()

    async def list_for_account(self, account_id: UUID) -> list[MembershipTripSummary]:
        rows = (
            (
                await self._session.execute(
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
            )
            .tuples()
            .all()
        )
        return [MembershipTripSummary(*row) for row in rows]

    async def roster(self, trip_id: UUID) -> list[tuple[str, TripRole]]:
        rows = (
            (
                await self._session.execute(
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
            )
            .tuples()
            .all()
        )
        return [(display_name, role) for display_name, role in rows]

    async def lock_trip_and_get_membership(
        self, trip_id: UUID, account_id: UUID
    ) -> TripAccess | None:
        trip = await self._session.scalar(
            select(Trip).where(Trip.id == trip_id).with_for_update()
        )
        if trip is None:
            return None
        role = await self.current_role(trip_id, account_id)
        if role is None:
            return None
        return TripAccess(trip=trip, role=role)

    async def current_role(self, trip_id: UUID, account_id: UUID) -> TripRole | None:
        return cast(
            TripRole | None,
            await self._session.scalar(
                select(TripMembership.role).where(
                    TripMembership.trip_id == trip_id,
                    TripMembership.account_id == account_id,
                )
            ),
        )
