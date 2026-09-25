from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tripper_api.itinerary.itinerary_photo_model import Photo
from tripper_api.trip.trip_model import Trip


class TripRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add_trip(self, trip: Trip) -> None:
        self._session.add(trip)
        await self._session.flush()

    def add_photo(self, photo: Photo) -> None:
        self._session.add(photo)

    async def next_photo_position(self, daily_plan_id: UUID) -> int:
        positions = await self._session.scalars(
            select(Photo.position).where(Photo.daily_plan_id == daily_plan_id)
        )
        return max(positions.all(), default=-1) + 1

    async def photo_by_id(self, daily_plan_id: UUID, photo_id: UUID) -> Photo | None:
        result = await self._session.scalars(
            select(Photo).where(
                Photo.daily_plan_id == daily_plan_id,
                Photo.id == photo_id,
            )
        )
        return result.one_or_none()

    async def delete_photo(self, photo: Photo) -> None:
        await self._session.delete(photo)
        await self._session.flush()

    async def photos(self, daily_plan_id: UUID) -> list[Photo]:
        result = await self._session.scalars(
            select(Photo)
            .where(Photo.daily_plan_id == daily_plan_id)
            .order_by(Photo.position, Photo.id)
        )
        return list(result.all())

    async def reorder_photos(self, current: list[Photo], ordered: list[Photo]) -> None:
        offset = len(current) + 1
        for photo in current:
            photo.position += offset
        await self._session.flush()
        for position, photo in enumerate(ordered):
            photo.position = position
        await self._session.flush()
