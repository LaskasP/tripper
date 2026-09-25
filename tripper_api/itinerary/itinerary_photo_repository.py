from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tripper_api.itinerary.itinerary_daily_plan_model import DailyPlan
from tripper_api.itinerary.itinerary_photo_model import Photo


class PhotoRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def lock_plan(self, trip_id: UUID, plan_id: UUID) -> DailyPlan | None:
        result = await self._session.scalars(
            select(DailyPlan)
            .where(DailyPlan.trip_id == trip_id, DailyPlan.id == plan_id)
            .with_for_update()
        )
        return result.one_or_none()

    async def add(self, photo: Photo) -> None:
        self._session.add(photo)
        await self._session.flush()

    async def next_position(self, daily_plan_id: UUID) -> int:
        positions = await self._session.scalars(
            select(Photo.position).where(Photo.daily_plan_id == daily_plan_id)
        )
        return max(positions.all(), default=-1) + 1

    async def get(self, daily_plan_id: UUID, photo_id: UUID) -> Photo | None:
        result = await self._session.scalars(
            select(Photo).where(
                Photo.daily_plan_id == daily_plan_id,
                Photo.id == photo_id,
            )
        )
        return result.one_or_none()

    async def delete(self, photo: Photo) -> None:
        await self._session.delete(photo)
        await self._session.flush()

    async def list_photos(self, daily_plan_id: UUID) -> list[Photo]:
        result = await self._session.scalars(
            select(Photo)
            .where(Photo.daily_plan_id == daily_plan_id)
            .order_by(Photo.position, Photo.id)
        )
        return list(result.all())

    async def reorder(self, current: list[Photo], ordered: list[Photo]) -> None:
        offset = len(current) + 1
        for photo in current:
            photo.position += offset
        await self._session.flush()
        for position, photo in enumerate(ordered):
            photo.position = position
        await self._session.flush()
