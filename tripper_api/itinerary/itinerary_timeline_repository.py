from collections.abc import Iterable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tripper_api.itinerary.itinerary_daily_plan_model import DailyPlan
from tripper_api.itinerary.itinerary_timeline_model import TimelineEntry


class TimelineRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def lock_plans(
        self, trip_id: UUID, plan_ids: Iterable[UUID]
    ) -> dict[UUID, DailyPlan]:
        unique_ids = set(plan_ids)
        plans = await self._session.scalars(
            select(DailyPlan)
            .where(DailyPlan.trip_id == trip_id, DailyPlan.id.in_(unique_ids))
            .order_by(DailyPlan.id)
            .with_for_update()
        )
        return {plan.id: plan for plan in plans.all()}

    async def add(self, entry: TimelineEntry) -> None:
        self._session.add(entry)
        await self._session.flush()

    async def next_position(self, daily_plan_id: UUID) -> int:
        positions = await self._session.scalars(
            select(TimelineEntry.position).where(
                TimelineEntry.daily_plan_id == daily_plan_id
            )
        )
        return max(positions.all(), default=-1) + 1

    async def get(self, daily_plan_id: UUID, entry_id: UUID) -> TimelineEntry | None:
        result = await self._session.scalars(
            select(TimelineEntry).where(
                TimelineEntry.daily_plan_id == daily_plan_id,
                TimelineEntry.id == entry_id,
            )
        )
        return result.one_or_none()

    async def delete(self, entry: TimelineEntry) -> None:
        await self._session.delete(entry)

    async def list_entries(self, daily_plan_id: UUID) -> list[TimelineEntry]:
        result = await self._session.scalars(
            select(TimelineEntry)
            .where(TimelineEntry.daily_plan_id == daily_plan_id)
            .order_by(
                TimelineEntry.local_time, TimelineEntry.position, TimelineEntry.id
            )
        )
        return list(result.all())

    async def reorder(
        self, current: list[TimelineEntry], ordered: list[TimelineEntry]
    ) -> None:
        offset = len(current) + 1
        for entry in current:
            entry.position += offset
        await self._session.flush()
        for position, entry in enumerate(ordered):
            entry.position = position
        await self._session.flush()
