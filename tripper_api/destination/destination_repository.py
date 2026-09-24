from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tripper_api.destination.destination_model import Destination


class DestinationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, destination: Destination) -> None:
        self._session.add(destination)
        await self._session.flush()

    async def list_for_update(self, trip_id: UUID) -> tuple[Destination, ...]:
        destinations = await self._session.scalars(
            select(Destination)
            .where(Destination.trip_id == trip_id)
            .order_by(Destination.position, Destination.id)
            .with_for_update()
        )
        return tuple(destinations.all())

    async def belongs_to_trip(self, trip_id: UUID, destination_id: UUID) -> bool:
        stored_id = await self._session.scalar(
            select(Destination.id).where(
                Destination.trip_id == trip_id,
                Destination.id == destination_id,
            )
        )
        return stored_id is not None

    async def replace(
        self,
        *,
        previous: tuple[Destination, ...],
        current: list[Destination],
        removed: list[Destination],
    ) -> None:
        offset = len(previous) + len(current) + 1
        for destination in previous:
            destination.position += offset
        await self._session.flush()
        for destination in removed:
            await self._session.delete(destination)
        await self._session.flush()
        for position, destination in enumerate(current):
            destination.position = position
            self._session.add(destination)
        await self._session.flush()
