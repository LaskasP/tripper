from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tripper_api.itinerary.itinerary_stay_model import Stay


class StayRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_for_plan(self, daily_plan_id: UUID) -> Stay | None:
        result = await self._session.scalars(
            select(Stay).where(Stay.daily_plan_id == daily_plan_id)
        )
        return result.one_or_none()

    async def add(self, stay: Stay) -> None:
        self._session.add(stay)
        await self._session.flush()

    async def delete(self, stay: Stay) -> None:
        await self._session.delete(stay)
