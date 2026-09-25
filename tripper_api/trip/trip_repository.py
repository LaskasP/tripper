from sqlalchemy.ext.asyncio import AsyncSession

from tripper_api.trip.trip_model import Trip


class TripRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add_trip(self, trip: Trip) -> None:
        self._session.add(trip)
        await self._session.flush()
