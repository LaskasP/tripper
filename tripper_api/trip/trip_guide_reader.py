from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import load_only, selectinload

from tripper_api.destination.destination_model import Destination
from tripper_api.itinerary.itinerary_daily_plan_model import DailyPlan
from tripper_api.itinerary.itinerary_photo_model import Photo
from tripper_api.itinerary.itinerary_stay_model import Stay
from tripper_api.itinerary.itinerary_timeline_model import TimelineEntry
from tripper_api.membership.membership_dto import TripRosterMemberResponse
from tripper_api.membership.membership_model import TripRole
from tripper_api.membership.membership_repository import MembershipRepository
from tripper_api.trip.trip_errors import TripNotFoundError
from tripper_api.trip.trip_guide_dto import (
    DailyPlanResponse,
    DestinationDetailsResponse,
    GuideLocationResponse,
    PhotoResponse,
    StayResponse,
    TimelineEntryResponse,
    TripCalendarDateResponse,
    TripDetailResponse,
)
from tripper_api.trip.trip_model import Trip


def _location(
    latitude: float | None, longitude: float | None
) -> GuideLocationResponse | None:
    if latitude is None or longitude is None:
        return None
    return GuideLocationResponse(lat=latitude, lng=longitude)


@dataclass(frozen=True)
class _DailyPlanEditRevisions:
    revision: int
    timeline_revision: int
    photo_revision: int


@dataclass(frozen=True)
class _ParticipantEditRevisions:
    trip: int
    content: int
    destinations: dict[UUID, int]
    daily_plans: dict[UUID, _DailyPlanEditRevisions]
    timeline_entries: dict[UUID, int]
    stays: dict[UUID, int]


class TripGuideReader:
    def __init__(
        self,
        session: AsyncSession,
        membership_repository: MembershipRepository,
    ) -> None:
        self._session = session
        self._membership_repository = membership_repository

    async def get_participant_guide(
        self, trip_id: UUID, account_id: UUID
    ) -> TripDetailResponse:
        async with self._session.begin():
            locked_trip_id = await self._session.scalar(
                select(Trip.id).where(Trip.id == trip_id).with_for_update(read=True)
            )
            if locked_trip_id is None:
                raise TripNotFoundError
            role = await self._membership_repository.current_role(trip_id, account_id)
            if role is None:
                raise TripNotFoundError
            trip = await self._load_content(trip_id)
            roster = await self._membership_repository.roster(trip_id)
            revisions = await self._load_edit_revisions(trip_id)
            return self._to_participant_response(trip, role, roster, revisions)

    async def _load_content(self, trip_id: UUID) -> Trip:
        trip = await self._session.scalar(
            select(Trip)
            .options(
                load_only(
                    Trip.id,
                    Trip.name,
                    Trip.short_name,
                    Trip.description,
                    Trip.start_date,
                    Trip.end_date,
                ),
                selectinload(Trip.destinations).load_only(
                    Destination.id,
                    Destination.name,
                    Destination.timezone,
                    Destination.latitude,
                    Destination.longitude,
                    Destination.position,
                ),
                selectinload(Trip.daily_plans)
                .selectinload(DailyPlan.timeline_entries)
                .load_only(
                    TimelineEntry.id,
                    TimelineEntry.destination_id,
                    TimelineEntry.local_time,
                    TimelineEntry.title,
                    TimelineEntry.description,
                    TimelineEntry.location_name,
                    TimelineEntry.latitude,
                    TimelineEntry.longitude,
                    TimelineEntry.position,
                ),
                selectinload(Trip.daily_plans)
                .selectinload(DailyPlan.stay)
                .load_only(
                    Stay.id,
                    Stay.name,
                    Stay.address,
                    Stay.latitude,
                    Stay.longitude,
                    Stay.check_in,
                    Stay.check_out,
                    Stay.public_listing_url,
                    Stay.booking_platform,
                ),
                selectinload(Trip.daily_plans)
                .selectinload(DailyPlan.photos)
                .load_only(Photo.id, Photo.position, Photo.url, Photo.caption),
                selectinload(Trip.daily_plans).load_only(
                    DailyPlan.id,
                    DailyPlan.destination_id,
                    DailyPlan.date,
                    DailyPlan.title,
                    DailyPlan.summary,
                    DailyPlan.background_image,
                ),
            )
            .where(Trip.id == trip_id)
        )
        if trip is None:
            raise TripNotFoundError
        return trip

    async def _load_edit_revisions(self, trip_id: UUID) -> _ParticipantEditRevisions:
        trip_revisions = (
            await self._session.execute(
                select(Trip.revision, Trip.content_revision).where(Trip.id == trip_id)
            )
        ).one()
        destination_revisions = (
            (
                await self._session.execute(
                    select(Destination.id, Destination.revision).where(
                        Destination.trip_id == trip_id
                    )
                )
            )
            .tuples()
            .all()
        )
        plan_revisions = (
            (
                await self._session.execute(
                    select(
                        DailyPlan.id,
                        DailyPlan.revision,
                        DailyPlan.timeline_revision,
                        DailyPlan.photo_revision,
                    ).where(DailyPlan.trip_id == trip_id)
                )
            )
            .tuples()
            .all()
        )
        timeline_revisions = (
            (
                await self._session.execute(
                    select(TimelineEntry.id, TimelineEntry.revision)
                    .join(DailyPlan, DailyPlan.id == TimelineEntry.daily_plan_id)
                    .where(DailyPlan.trip_id == trip_id)
                )
            )
            .tuples()
            .all()
        )
        stay_revisions = (
            (
                await self._session.execute(
                    select(Stay.id, Stay.revision)
                    .join(DailyPlan, DailyPlan.id == Stay.daily_plan_id)
                    .where(DailyPlan.trip_id == trip_id)
                )
            )
            .tuples()
            .all()
        )
        return _ParticipantEditRevisions(
            trip=trip_revisions.revision,
            content=trip_revisions.content_revision,
            destinations=dict(destination_revisions),
            daily_plans={
                plan_id: _DailyPlanEditRevisions(
                    revision=revision,
                    timeline_revision=timeline_revision,
                    photo_revision=photo_revision,
                )
                for plan_id, revision, timeline_revision, photo_revision in plan_revisions
            },
            timeline_entries=dict(timeline_revisions),
            stays=dict(stay_revisions),
        )

    @staticmethod
    def _to_participant_response(
        trip: Trip,
        role: TripRole,
        roster: list[tuple[str, TripRole]],
        revisions: _ParticipantEditRevisions,
    ) -> TripDetailResponse:
        primary_destination = trip.destinations[0]
        destination_timezones = {
            destination.id: destination.timezone for destination in trip.destinations
        }
        return TripDetailResponse(
            id=trip.id,
            revision=revisions.trip,
            content_revision=revisions.content,
            role=role,
            name=trip.name,
            destination=primary_destination.name,
            short_name=trip.short_name,
            description=trip.description,
            timezone=primary_destination.timezone,
            location=_location(
                primary_destination.latitude, primary_destination.longitude
            ),
            start_date=trip.start_date,
            end_date=trip.end_date,
            destinations=[
                DestinationDetailsResponse(
                    id=destination.id,
                    name=destination.name,
                    timezone=destination.timezone,
                    location=_location(destination.latitude, destination.longitude),
                    position=destination.position,
                    revision=revisions.destinations[destination.id],
                )
                for destination in trip.destinations
            ],
            calendar=[
                TripCalendarDateResponse(
                    date=trip.start_date + timedelta(days=offset),
                    day_number=offset + 1,
                    is_planned=any(
                        plan.date == trip.start_date + timedelta(days=offset)
                        for plan in trip.daily_plans
                    ),
                )
                for offset in range((trip.end_date - trip.start_date).days + 1)
            ],
            daily_plans=[
                DailyPlanResponse(
                    id=plan.id,
                    destination_id=plan.destination_id,
                    revision=revisions.daily_plans[plan.id].revision,
                    timeline_revision=revisions.daily_plans[plan.id].timeline_revision,
                    photo_revision=revisions.daily_plans[plan.id].photo_revision,
                    date=plan.date,
                    day_number=(plan.date - trip.start_date).days + 1,
                    title=plan.title,
                    summary=plan.summary,
                    background_image=plan.background_image,
                    stay=(
                        StayResponse(
                            id=plan.stay.id,
                            revision=revisions.stays[plan.stay.id],
                            name=plan.stay.name,
                            address=plan.stay.address,
                            location=_location(plan.stay.latitude, plan.stay.longitude),
                            check_in=plan.stay.check_in,
                            check_out=plan.stay.check_out,
                            public_listing_url=plan.stay.public_listing_url,
                            booking_platform=plan.stay.booking_platform,
                        )
                        if plan.stay is not None
                        else None
                    ),
                    timeline=[
                        TimelineEntryResponse(
                            id=entry.id,
                            destination_id=entry.destination_id,
                            revision=revisions.timeline_entries[entry.id],
                            position=entry.position,
                            time=entry.local_time,
                            timezone=destination_timezones[
                                entry.destination_id or plan.destination_id
                            ],
                            title=entry.title,
                            description=entry.description,
                            location=_location(entry.latitude, entry.longitude),
                            location_name=entry.location_name,
                        )
                        for entry in plan.timeline_entries
                    ],
                    photos=[
                        PhotoResponse(
                            id=photo.id,
                            position=photo.position,
                            url=photo.url,
                            caption=photo.caption,
                        )
                        for photo in plan.photos
                    ],
                )
                for plan in trip.daily_plans
            ],
            roster=[
                TripRosterMemberResponse(display_name=display_name, role=member_role)
                for display_name, member_role in roster
            ],
        )
