from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tripper_api.destination.destination_model import Destination
from tripper_api.itinerary.itinerary_daily_plan_model import DailyPlan
from tripper_api.itinerary.itinerary_photo_model import Photo
from tripper_api.itinerary.itinerary_stay_model import Stay
from tripper_api.itinerary.itinerary_timeline_model import TimelineEntry
from tripper_api.trip.trip_model import Trip
from tripper_api.trip.trip_read_model import TripForUpdate


class TripRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add_trip(self, trip: Trip) -> None:
        self._session.add(trip)
        await self._session.flush()

    async def load_for_update(self, trip: Trip) -> TripForUpdate:
        trip_id = trip.id
        destinations = tuple(
            (
                await self._session.scalars(
                    select(Destination)
                    .where(Destination.trip_id == trip_id)
                    .order_by(Destination.position, Destination.id)
                    .with_for_update()
                )
            ).all()
        )
        plan_rows = (
            await self._session.execute(
                select(DailyPlan.date, DailyPlan.destination_id).where(
                    DailyPlan.trip_id == trip_id
                )
            )
        ).tuples()
        plans = tuple(plan_rows)
        timeline_destination_rows = (
            await self._session.scalars(
                select(TimelineEntry.destination_id)
                .join(DailyPlan, DailyPlan.id == TimelineEntry.daily_plan_id)
                .where(
                    DailyPlan.trip_id == trip_id,
                    TimelineEntry.destination_id.is_not(None),
                )
            )
        ).all()
        timeline_destination_ids = frozenset(
            destination_id
            for destination_id in timeline_destination_rows
            if destination_id is not None
        )
        return TripForUpdate(
            trip=trip,
            destinations=destinations,
            plan_dates=frozenset(plan_date for plan_date, _ in plans),
            referenced_destination_ids=(
                frozenset(destination_id for _, destination_id in plans)
                | timeline_destination_ids
            ),
        )

    async def plan_on_date(self, trip_id: UUID, plan_date: date) -> DailyPlan | None:
        result = await self._session.scalars(
            select(DailyPlan).where(
                DailyPlan.trip_id == trip_id, DailyPlan.date == plan_date
            )
        )
        return result.one_or_none()

    async def plan_by_id(self, trip_id: UUID, plan_id: UUID) -> DailyPlan | None:
        result = await self._session.scalars(
            select(DailyPlan).where(
                DailyPlan.trip_id == trip_id, DailyPlan.id == plan_id
            )
        )
        return result.one_or_none()

    def add_plan(self, plan: DailyPlan) -> None:
        self._session.add(plan)

    def add_timeline_entry(self, entry: TimelineEntry) -> None:
        self._session.add(entry)

    async def stay(self, daily_plan_id: UUID) -> Stay | None:
        result = await self._session.scalars(
            select(Stay).where(Stay.daily_plan_id == daily_plan_id)
        )
        return result.one_or_none()

    def add_stay(self, stay: Stay) -> None:
        self._session.add(stay)

    async def delete_stay(self, stay: Stay) -> None:
        await self._session.delete(stay)

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

    async def next_timeline_position(self, daily_plan_id: UUID) -> int:
        positions = await self._session.scalars(
            select(TimelineEntry.position).where(
                TimelineEntry.daily_plan_id == daily_plan_id
            )
        )
        return max(positions.all(), default=-1) + 1

    async def timeline_entry_by_id(
        self, daily_plan_id: UUID, entry_id: UUID
    ) -> TimelineEntry | None:
        result = await self._session.scalars(
            select(TimelineEntry).where(
                TimelineEntry.daily_plan_id == daily_plan_id,
                TimelineEntry.id == entry_id,
            )
        )
        return result.one_or_none()

    async def delete_timeline_entry(self, entry: TimelineEntry) -> None:
        await self._session.delete(entry)

    async def timeline_entries(self, daily_plan_id: UUID) -> list[TimelineEntry]:
        result = await self._session.scalars(
            select(TimelineEntry)
            .where(TimelineEntry.daily_plan_id == daily_plan_id)
            .order_by(
                TimelineEntry.local_time, TimelineEntry.position, TimelineEntry.id
            )
        )
        return list(result.all())

    async def reorder_timeline_entries(
        self, current: list[TimelineEntry], ordered: list[TimelineEntry]
    ) -> None:
        offset = len(current) + 1
        for entry in current:
            entry.position += offset
        await self._session.flush()
        for position, entry in enumerate(ordered):
            entry.position = position
        await self._session.flush()

    async def delete_plan(self, plan: DailyPlan) -> None:
        await self._session.delete(plan)
