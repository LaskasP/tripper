from datetime import timedelta
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from tripper_api.trip.trip_dto import (
    DailyPlanResponse,
    DestinationDetailsResponse,
    LocationInput,
    PhotoResponse,
    StayResponse,
    TimelineEntryResponse,
    TripCalendarDateResponse,
    TripCreateRequest,
    TripDetailResponse,
    TripDetailsUpdateRequest,
    TripRosterMemberResponse,
    TripSummaryResponse,
)
from tripper_api.trip.trip_errors import (
    TripDateRangeExcludesPlansError,
    TripDestinationInUseError,
    TripDestinationMismatchError,
    TripEditForbiddenError,
    TripNotFoundError,
)
from tripper_api.trip.trip_model import Destination, Trip, TripMembership, TripRole
from tripper_api.trip.trip_repository import TripRepository


def _location(latitude: float | None, longitude: float | None) -> LocationInput | None:
    if latitude is None or longitude is None:
        return None
    return LocationInput(lat=latitude, lng=longitude)


class TripService:
    def __init__(self, session: AsyncSession, repository: TripRepository) -> None:
        self._session = session
        self._repository = repository

    async def create(
        self,
        *,
        account_id: UUID,
        request: TripCreateRequest,
    ) -> TripSummaryResponse:
        trip = Trip(
            id=uuid4(),
            name=request.name,
            short_name=request.short_name,
            description=request.description,
            start_date=request.start_date,
            end_date=request.end_date,
        )
        destination = Destination(
            id=uuid4(),
            trip_id=trip.id,
            name=request.destination,
            timezone=request.timezone,
            latitude=request.location.lat if request.location is not None else None,
            longitude=request.location.lng if request.location is not None else None,
            position=0,
        )
        membership = TripMembership(
            id=uuid4(),
            trip_id=trip.id,
            account_id=account_id,
            role=TripRole.CREATOR,
        )
        async with self._session.begin():
            await self._repository.add(trip, destination, membership)
        return TripSummaryResponse(
            id=trip.id,
            name=trip.name,
            destination=destination.name,
            short_name=trip.short_name,
            start_date=trip.start_date,
            end_date=trip.end_date,
            role=membership.role,
        )

    async def list_for_account(self, account_id: UUID) -> list[TripSummaryResponse]:
        async with self._session.begin():
            return await self._repository.list_for_account(account_id)

    async def get_participant_guide(
        self, trip_id: UUID, account_id: UUID
    ) -> TripDetailResponse:
        async with self._session.begin():
            trip = await self._repository.load_participant_guide(trip_id, account_id)
        if trip is None:
            raise TripNotFoundError
        location = _location(trip.latitude, trip.longitude)
        return TripDetailResponse(
            id=trip.id,
            revision=trip.revision,
            role=trip.role,
            name=trip.name,
            destination=trip.destination,
            short_name=trip.short_name,
            description=trip.description,
            timezone=trip.timezone,
            location=location,
            start_date=trip.start_date,
            end_date=trip.end_date,
            destinations=[
                DestinationDetailsResponse(
                    id=destination.id,
                    name=destination.name,
                    timezone=destination.timezone,
                    location=_location(destination.latitude, destination.longitude),
                    position=destination.position,
                    revision=destination.revision,
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
                    date=plan.date,
                    day_number=(plan.date - trip.start_date).days + 1,
                    title=plan.title,
                    summary=plan.summary,
                    background_image=plan.background_image,
                    stay=(
                        StayResponse(
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
                            time=entry.local_time,
                            title=entry.title,
                            description=entry.description,
                            location=_location(entry.latitude, entry.longitude),
                            location_name=entry.location_name,
                        )
                        for entry in plan.timeline
                    ],
                    photos=[
                        PhotoResponse(url=photo.url, caption=photo.caption)
                        for photo in plan.photos
                    ],
                )
                for plan in trip.daily_plans
            ],
            roster=[
                TripRosterMemberResponse(display_name=display_name, role=role)
                for display_name, role in trip.roster
            ],
        )

    async def update_details(
        self,
        *,
        trip_id: UUID,
        account_id: UUID,
        request: TripDetailsUpdateRequest,
    ) -> TripDetailResponse:
        async with self._session.begin():
            stored = await self._repository.load_for_update(trip_id, account_id)
            if stored is None:
                raise TripNotFoundError
            if stored.role not in {TripRole.CREATOR, TripRole.CONTRIBUTOR}:
                raise TripEditForbiddenError
            if any(
                plan_date < request.start_date or plan_date > request.end_date
                for plan_date in stored.plan_dates
            ):
                raise TripDateRangeExcludesPlansError

            existing_by_id = {
                destination.id: destination for destination in stored.destinations
            }
            requested_ids = {
                destination.id
                for destination in request.destinations
                if destination.id is not None
            }
            if not requested_ids.issubset(existing_by_id):
                raise TripDestinationMismatchError
            removed = [
                destination
                for destination in stored.destinations
                if destination.id not in requested_ids
            ]
            if any(
                destination.id in stored.referenced_destination_ids
                for destination in removed
            ):
                raise TripDestinationInUseError

            stored.trip.name = request.name
            stored.trip.short_name = request.short_name
            stored.trip.description = request.description
            stored.trip.start_date = request.start_date
            stored.trip.end_date = request.end_date
            stored.trip.revision += 1
            stored.trip.content_revision += 1

            destinations: list[Destination] = []
            for position, item in enumerate(request.destinations):
                if item.id is None:
                    destination = Destination(
                        id=uuid4(),
                        trip_id=trip_id,
                        name=item.name,
                        timezone=item.timezone,
                        latitude=item.location.lat if item.location else None,
                        longitude=item.location.lng if item.location else None,
                        position=position,
                    )
                else:
                    destination = existing_by_id[item.id]
                    destination.name = item.name
                    destination.timezone = item.timezone
                    destination.latitude = item.location.lat if item.location else None
                    destination.longitude = item.location.lng if item.location else None
                    destination.revision += 1
                destinations.append(destination)
            await self._repository.replace_destinations(
                previous=stored.destinations,
                current=destinations,
                removed=removed,
            )
        return await self.get_participant_guide(trip_id, account_id)
