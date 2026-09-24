from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tripper_api.itinerary.itinerary_daily_plan_model import DailyPlan
from tripper_api.itinerary.itinerary_read_model import ItineraryTripReferences
from tripper_api.itinerary.itinerary_timeline_model import TimelineEntry


class ItineraryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def plan_on_date(self, trip_id: UUID, plan_date: date) -> DailyPlan | None:
        result = await self._session.scalars(
            select(DailyPlan).where(
                DailyPlan.trip_id == trip_id,
                DailyPlan.date == plan_date,
            )
        )
        return result.one_or_none()

    async def plan_by_id(self, trip_id: UUID, plan_id: UUID) -> DailyPlan | None:
        result = await self._session.scalars(
            select(DailyPlan).where(
                DailyPlan.trip_id == trip_id,
                DailyPlan.id == plan_id,
            )
        )
        return result.one_or_none()

    async def add_plan(self, plan: DailyPlan) -> None:
        self._session.add(plan)
        await self._session.flush()

    async def delete_plan(self, plan: DailyPlan) -> None:
        await self._session.delete(plan)

    async def trip_references(self, trip_id: UUID) -> ItineraryTripReferences:
        plans = (
            await self._session.execute(
                select(DailyPlan.date, DailyPlan.destination_id).where(
                    DailyPlan.trip_id == trip_id
                )
            )
        ).tuples()
        plan_rows = tuple(plans)
        timeline_destination_ids = (
            await self._session.scalars(
                select(TimelineEntry.destination_id)
                .join(DailyPlan, DailyPlan.id == TimelineEntry.daily_plan_id)
                .where(
                    DailyPlan.trip_id == trip_id,
                    TimelineEntry.destination_id.is_not(None),
                )
            )
        ).all()
        return ItineraryTripReferences(
            plan_dates=frozenset(plan_date for plan_date, _ in plan_rows),
            destination_ids=(
                frozenset(destination_id for _, destination_id in plan_rows)
                | frozenset(
                    destination_id
                    for destination_id in timeline_destination_ids
                    if destination_id is not None
                )
            ),
        )
