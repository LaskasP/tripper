from dataclasses import dataclass
from datetime import date, time
from uuid import UUID

from sqlalchemy import case, select
from sqlalchemy.ext.asyncio import AsyncSession

from tripper_api.auth.auth_model import Account
from tripper_api.trip.trip_dto import TripSummaryResponse
from tripper_api.trip.trip_model import (
    DailyPlan,
    Destination,
    Photo,
    Stay,
    TimelineEntry,
    Trip,
    TripMembership,
    TripRole,
)


@dataclass(frozen=True)
class _StoredTimelineEntry:
    id: UUID
    destination_id: UUID | None
    local_time: time
    title: str
    description: str
    location_name: str | None
    latitude: float | None
    longitude: float | None
    position: int
    revision: int


@dataclass(frozen=True)
class _StoredStay:
    name: str
    address: str
    latitude: float | None
    longitude: float | None
    check_in: time | None
    check_out: time | None
    public_listing_url: str | None
    booking_platform: str | None


@dataclass(frozen=True)
class _StoredPhoto:
    url: str
    caption: str


@dataclass(frozen=True)
class _StoredDailyPlan:
    id: UUID
    destination_id: UUID
    revision: int
    timeline_revision: int
    date: date
    title: str
    summary: str
    background_image: str
    stay: _StoredStay | None
    timeline: tuple[_StoredTimelineEntry, ...]
    photos: tuple[_StoredPhoto, ...]


@dataclass(frozen=True)
class _StoredDestination:
    id: UUID
    name: str
    timezone: str
    latitude: float | None
    longitude: float | None
    position: int
    revision: int


@dataclass(frozen=True)
class _StoredParticipantGuide:
    id: UUID
    revision: int
    content_revision: int
    role: TripRole
    name: str
    destination: str
    short_name: str
    description: str
    timezone: str
    latitude: float | None
    longitude: float | None
    start_date: date
    end_date: date
    destinations: tuple[_StoredDestination, ...]
    daily_plans: tuple[_StoredDailyPlan, ...]
    roster: tuple[tuple[str, TripRole], ...]


@dataclass(frozen=True)
class _StoredTripForUpdate:
    trip: Trip
    role: TripRole
    destinations: tuple[Destination, ...]
    plan_dates: frozenset[date]
    referenced_destination_ids: frozenset[UUID]


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
                Trip.revision,
                Trip.content_revision,
                TripMembership.role,
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
        destination_rows = (
            (
                await self._session.execute(
                    select(
                        Destination.id,
                        Destination.name,
                        Destination.timezone,
                        Destination.latitude,
                        Destination.longitude,
                        Destination.position,
                        Destination.revision,
                    )
                    .where(Destination.trip_id == trip_id)
                    .order_by(Destination.position, Destination.id)
                )
            )
            .tuples()
            .all()
        )
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
        plan_rows = (
            (
                await self._session.execute(
                    select(
                        DailyPlan.id,
                        DailyPlan.destination_id,
                        DailyPlan.revision,
                        DailyPlan.timeline_revision,
                        DailyPlan.date,
                        DailyPlan.title,
                        DailyPlan.summary,
                        DailyPlan.background_image,
                    )
                    .where(DailyPlan.trip_id == trip_id)
                    .order_by(DailyPlan.date, DailyPlan.id)
                )
            )
            .tuples()
            .all()
        )
        daily_plans: list[_StoredDailyPlan] = []
        for (
            plan_id,
            destination_id,
            revision,
            timeline_revision,
            plan_date,
            title,
            summary,
            background_image,
        ) in plan_rows:
            timeline_rows = (
                (
                    await self._session.execute(
                        select(
                            TimelineEntry.local_time,
                            TimelineEntry.id,
                            TimelineEntry.destination_id,
                            TimelineEntry.title,
                            TimelineEntry.description,
                            TimelineEntry.location_name,
                            TimelineEntry.latitude,
                            TimelineEntry.longitude,
                            TimelineEntry.position,
                            TimelineEntry.revision,
                        )
                        .where(TimelineEntry.daily_plan_id == plan_id)
                        .order_by(
                            TimelineEntry.local_time,
                            TimelineEntry.position,
                            TimelineEntry.id,
                        )
                    )
                )
                .tuples()
                .all()
            )
            stay_row = (
                (
                    await self._session.execute(
                        select(
                            Stay.name,
                            Stay.address,
                            Stay.latitude,
                            Stay.longitude,
                            Stay.check_in,
                            Stay.check_out,
                            Stay.public_listing_url,
                            Stay.booking_platform,
                        ).where(Stay.daily_plan_id == plan_id)
                    )
                )
                .tuples()
                .one_or_none()
            )
            photo_rows = (
                (
                    await self._session.execute(
                        select(Photo.url, Photo.caption)
                        .where(Photo.daily_plan_id == plan_id)
                        .order_by(Photo.position, Photo.id)
                    )
                )
                .tuples()
                .all()
            )
            daily_plans.append(
                _StoredDailyPlan(
                    id=plan_id,
                    destination_id=destination_id,
                    revision=revision,
                    timeline_revision=timeline_revision,
                    date=plan_date,
                    title=title,
                    summary=summary,
                    background_image=background_image,
                    stay=_StoredStay(*stay_row) if stay_row is not None else None,
                    timeline=tuple(
                        _StoredTimelineEntry(
                            id=entry[1],
                            destination_id=entry[2],
                            local_time=entry[0],
                            title=entry[3],
                            description=entry[4],
                            location_name=entry[5],
                            latitude=entry[6],
                            longitude=entry[7],
                            position=entry[8],
                            revision=entry[9],
                        )
                        for entry in timeline_rows
                    ),
                    photos=tuple(_StoredPhoto(*photo) for photo in photo_rows),
                )
            )
        return _StoredParticipantGuide(
            id=row[0],
            revision=row[1],
            content_revision=row[2],
            role=row[3],
            name=row[4],
            destination=row[5],
            short_name=row[6],
            description=row[7],
            timezone=row[8],
            latitude=row[9],
            longitude=row[10],
            start_date=row[11],
            end_date=row[12],
            destinations=tuple(_StoredDestination(*row) for row in destination_rows),
            daily_plans=tuple(daily_plans),
            roster=tuple((display_name, role) for display_name, role in roster_rows),
        )

    async def load_for_update(
        self, trip_id: UUID, account_id: UUID
    ) -> _StoredTripForUpdate | None:
        row = (
            await self._session.execute(
                select(Trip, TripMembership.role)
                .join(TripMembership, TripMembership.trip_id == Trip.id)
                .where(
                    Trip.id == trip_id,
                    TripMembership.account_id == account_id,
                )
                .with_for_update(of=Trip)
            )
        ).one_or_none()
        if row is None:
            return None
        trip, role = row
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
        return _StoredTripForUpdate(
            trip=trip,
            role=role,
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

    async def replace_destinations(
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
