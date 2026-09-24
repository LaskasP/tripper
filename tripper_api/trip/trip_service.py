from datetime import date, timedelta
from itertools import pairwise
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from tripper_api.destination.destination_model import Destination
from tripper_api.itinerary.itinerary_daily_plan_model import DailyPlan
from tripper_api.itinerary.itinerary_photo_model import Photo
from tripper_api.itinerary.itinerary_stay_model import Stay
from tripper_api.itinerary.itinerary_timeline_model import TimelineEntry
from tripper_api.membership.membership_dto import (
    TripRosterMemberResponse,
    TripSummaryResponse,
)
from tripper_api.membership.membership_model import TripMembership, TripRole
from tripper_api.membership.membership_repository import MembershipRepository
from tripper_api.trip.trip_dto import (
    DailyPlanMoveRequest,
    DailyPlanResponse,
    DailyPlanRevisionRequest,
    DailyPlanWriteRequest,
    DestinationDetailsResponse,
    LocationInput,
    PhotoCreateRequest,
    PhotoDeleteRequest,
    PhotoReorderRequest,
    PhotoResponse,
    StayDeleteRequest,
    StayResponse,
    StayWriteRequest,
    TimelineEntryCreateRequest,
    TimelineEntryDeleteRequest,
    TimelineEntryMoveRequest,
    TimelineEntryResponse,
    TimelineEntryUpdateRequest,
    TimelineReorderRequest,
    TripCalendarDateResponse,
    TripCreateRequest,
    TripDetailResponse,
    TripDetailsUpdateRequest,
)
from tripper_api.trip.trip_errors import (
    DailyPlanNotFoundError,
    DailyPlanOccupiedError,
    DailyPlanOutOfRangeError,
    DailyPlanRevisionConflictError,
    PhotoCollectionRevisionConflictError,
    PhotoNotFoundError,
    PhotoOrderInvalidError,
    StayNotFoundError,
    StayRevisionConflictError,
    TimelineCollectionRevisionConflictError,
    TimelineEntryNotFoundError,
    TimelineEntryRevisionConflictError,
    TimelineOrderInvalidError,
    TripDateRangeExcludesPlansError,
    TripDestinationInUseError,
    TripDestinationMismatchError,
    TripEditForbiddenError,
    TripNotFoundError,
    TripRevisionConflictError,
)
from tripper_api.trip.trip_model import Trip
from tripper_api.trip.trip_repository import TripForUpdate, TripRepository


def _location(latitude: float | None, longitude: float | None) -> LocationInput | None:
    if latitude is None or longitude is None:
        return None
    return LocationInput(lat=latitude, lng=longitude)


class TripService:
    def __init__(
        self,
        session: AsyncSession,
        repository: TripRepository,
        membership_repository: MembershipRepository,
    ) -> None:
        self._session = session
        self._repository = repository
        self._membership_repository = membership_repository

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
            await self._repository.add(trip, destination)
            await self._membership_repository.add(membership)
        return TripSummaryResponse(
            id=trip.id,
            name=trip.name,
            destination=destination.name,
            short_name=trip.short_name,
            start_date=trip.start_date,
            end_date=trip.end_date,
            role=membership.role,
        )

    async def get_participant_guide(
        self, trip_id: UUID, account_id: UUID
    ) -> TripDetailResponse:
        async with self._session.begin():
            role = await self._membership_repository.current_role(trip_id, account_id)
            if role is None:
                raise TripNotFoundError
            trip = await self._repository.load_participant_guide(trip_id)
            roster = await self._membership_repository.roster(trip_id)
        if trip is None:
            raise TripNotFoundError
        location = _location(trip.latitude, trip.longitude)
        return TripDetailResponse(
            id=trip.id,
            revision=trip.revision,
            content_revision=trip.content_revision,
            role=role,
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
                    id=plan.id,
                    destination_id=plan.destination_id,
                    revision=plan.revision,
                    timeline_revision=plan.timeline_revision,
                    photo_revision=plan.photo_revision,
                    date=plan.date,
                    day_number=(plan.date - trip.start_date).days + 1,
                    title=plan.title,
                    summary=plan.summary,
                    background_image=plan.background_image,
                    stay=(
                        StayResponse(
                            id=plan.stay.id,
                            revision=plan.stay.revision,
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
                            revision=entry.revision,
                            position=entry.position,
                            time=entry.local_time,
                            timezone=(
                                next(
                                    destination.timezone
                                    for destination in trip.destinations
                                    if destination.id
                                    == (entry.destination_id or plan.destination_id)
                                )
                            ),
                            title=entry.title,
                            description=entry.description,
                            location=_location(entry.latitude, entry.longitude),
                            location_name=entry.location_name,
                        )
                        for entry in plan.timeline
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
                TripRosterMemberResponse(display_name=display_name, role=role)
                for display_name, role in roster
            ],
        )

    async def _load_for_edit(self, trip_id: UUID, account_id: UUID) -> TripForUpdate:
        access = await self._membership_repository.lock_trip_and_get_membership(
            trip_id, account_id
        )
        if access is None:
            raise TripNotFoundError
        if access.role not in {TripRole.CREATOR, TripRole.CONTRIBUTOR}:
            raise TripEditForbiddenError
        return await self._repository.load_for_update(access.trip)

    async def update_details(
        self,
        *,
        trip_id: UUID,
        account_id: UUID,
        request: TripDetailsUpdateRequest,
    ) -> TripDetailResponse:
        revision_conflict = False
        async with self._session.begin():
            stored = await self._load_for_edit(trip_id, account_id)
            if stored.trip.revision != request.starting_revision:
                revision_conflict = True
            else:
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
                            latitude=(item.location.lat if item.location else None),
                            longitude=(item.location.lng if item.location else None),
                            position=position,
                        )
                    else:
                        destination = existing_by_id[item.id]
                        destination.name = item.name
                        destination.timezone = item.timezone
                        destination.latitude = (
                            item.location.lat if item.location else None
                        )
                        destination.longitude = (
                            item.location.lng if item.location else None
                        )
                        destination.revision += 1
                    destinations.append(destination)
                await self._repository.replace_destinations(
                    previous=stored.destinations,
                    current=destinations,
                    removed=removed,
                )
        if revision_conflict:
            latest_values = await self.get_participant_guide(trip_id, account_id)
            raise TripRevisionConflictError(latest_values.model_dump(mode="json"))
        return await self.get_participant_guide(trip_id, account_id)

    async def write_daily_plan(
        self,
        *,
        trip_id: UUID,
        account_id: UUID,
        plan_date: date,
        request: DailyPlanWriteRequest,
    ) -> TripDetailResponse:
        conflict = False
        async with self._session.begin():
            stored = await self._load_for_edit(trip_id, account_id)
            if not stored.trip.start_date <= plan_date <= stored.trip.end_date:
                raise DailyPlanOutOfRangeError
            if request.destination_id not in {item.id for item in stored.destinations}:
                raise TripDestinationMismatchError
            plan = await self._repository.plan_on_date(trip_id, plan_date)
            if (plan is None) != (request.id is None) or (
                plan is not None and plan.id != request.id
            ):
                conflict = True
            observed_revision = plan.revision if plan else stored.trip.content_revision
            if observed_revision != request.starting_revision:
                conflict = True
            if not conflict:
                if plan is None:
                    plan = DailyPlan(
                        id=uuid4(),
                        trip_id=trip_id,
                        date=plan_date,
                        destination_id=request.destination_id,
                        title=request.title,
                        summary=request.summary,
                        background_image=request.background_image,
                    )
                    self._repository.add_plan(plan)
                else:
                    plan.destination_id = request.destination_id
                    plan.title = request.title
                    plan.summary = request.summary
                    plan.background_image = request.background_image
                    plan.revision += 1
                stored.trip.content_revision += 1
        if conflict:
            latest = await self.get_participant_guide(trip_id, account_id)
            raise DailyPlanRevisionConflictError(latest.model_dump(mode="json"))
        return await self.get_participant_guide(trip_id, account_id)

    async def clear_daily_plan(
        self,
        *,
        trip_id: UUID,
        account_id: UUID,
        plan_date: date,
        request: DailyPlanRevisionRequest,
    ) -> TripDetailResponse:
        conflict = False
        async with self._session.begin():
            stored = await self._load_for_edit(trip_id, account_id)
            plan = await self._repository.plan_on_date(trip_id, plan_date)
            if plan is None:
                raise DailyPlanNotFoundError
            if plan.revision != request.starting_revision:
                conflict = True
            else:
                await self._repository.delete_plan(plan)
                stored.trip.content_revision += 1
        if conflict:
            latest = await self.get_participant_guide(trip_id, account_id)
            raise DailyPlanRevisionConflictError(latest.model_dump(mode="json"))
        return await self.get_participant_guide(trip_id, account_id)

    async def write_stay(
        self,
        *,
        trip_id: UUID,
        account_id: UUID,
        plan_id: UUID,
        request: StayWriteRequest,
    ) -> TripDetailResponse:
        conflict = False
        async with self._session.begin():
            stored = await self._load_for_edit(trip_id, account_id)
            plan = await self._repository.plan_by_id(trip_id, plan_id)
            if plan is None:
                raise DailyPlanNotFoundError
            stay = await self._repository.stay(plan.id)
            if (stay is None) != (request.id is None) or (
                stay is not None and stay.id != request.id
            ):
                conflict = True
            observed_revision = stay.revision if stay else plan.revision
            if observed_revision != request.starting_revision:
                conflict = True
            if not conflict:
                if stay is None:
                    stay = Stay(
                        id=uuid4(),
                        daily_plan_id=plan.id,
                        name=request.name,
                        address=request.address,
                        latitude=request.location.lat if request.location else None,
                        longitude=request.location.lng if request.location else None,
                        check_in=request.check_in,
                        check_out=request.check_out,
                        public_listing_url=request.public_listing_url,
                        booking_platform=request.booking_platform,
                    )
                    self._repository.add_stay(stay)
                else:
                    stay.name = request.name
                    stay.address = request.address
                    stay.latitude = request.location.lat if request.location else None
                    stay.longitude = request.location.lng if request.location else None
                    stay.check_in = request.check_in
                    stay.check_out = request.check_out
                    stay.public_listing_url = request.public_listing_url
                    stay.booking_platform = request.booking_platform
                    stay.revision += 1
                stored.trip.content_revision += 1
        if conflict:
            latest = await self.get_participant_guide(trip_id, account_id)
            raise StayRevisionConflictError(latest.model_dump(mode="json"))
        return await self.get_participant_guide(trip_id, account_id)

    async def clear_stay(
        self,
        *,
        trip_id: UUID,
        account_id: UUID,
        plan_id: UUID,
        request: StayDeleteRequest,
    ) -> TripDetailResponse:
        conflict = False
        async with self._session.begin():
            stored = await self._load_for_edit(trip_id, account_id)
            plan = await self._repository.plan_by_id(trip_id, plan_id)
            if plan is None:
                raise DailyPlanNotFoundError
            stay = await self._repository.stay(plan.id)
            if stay is None:
                raise StayNotFoundError
            if stay.revision != request.starting_revision:
                conflict = True
            else:
                await self._repository.delete_stay(stay)
                stored.trip.content_revision += 1
        if conflict:
            latest = await self.get_participant_guide(trip_id, account_id)
            raise StayRevisionConflictError(latest.model_dump(mode="json"))
        return await self.get_participant_guide(trip_id, account_id)

    async def create_timeline_entry(
        self,
        *,
        trip_id: UUID,
        account_id: UUID,
        plan_id: UUID,
        request: TimelineEntryCreateRequest,
    ) -> TripDetailResponse:
        conflict = False
        async with self._session.begin():
            stored = await self._load_for_edit(trip_id, account_id)
            plan = await self._repository.plan_by_id(trip_id, plan_id)
            if plan is None:
                raise DailyPlanNotFoundError
            if request.destination_id is not None and request.destination_id not in {
                destination.id for destination in stored.destinations
            }:
                raise TripDestinationMismatchError
            if plan.timeline_revision != request.starting_revision:
                conflict = True
            else:
                self._repository.add_timeline_entry(
                    TimelineEntry(
                        id=uuid4(),
                        daily_plan_id=plan.id,
                        destination_id=request.destination_id,
                        local_time=request.time,
                        title=request.title,
                        description=request.description,
                        location_name=request.location_name,
                        latitude=request.location.lat if request.location else None,
                        longitude=request.location.lng if request.location else None,
                        position=await self._repository.next_timeline_position(plan.id),
                    )
                )
                plan.timeline_revision += 1
                stored.trip.content_revision += 1
        if conflict:
            latest = await self.get_participant_guide(trip_id, account_id)
            raise TimelineCollectionRevisionConflictError(
                latest.model_dump(mode="json")
            )
        return await self.get_participant_guide(trip_id, account_id)

    async def update_timeline_entry(
        self,
        *,
        trip_id: UUID,
        account_id: UUID,
        plan_id: UUID,
        entry_id: UUID,
        request: TimelineEntryUpdateRequest,
    ) -> TripDetailResponse:
        conflict = False
        async with self._session.begin():
            stored = await self._load_for_edit(trip_id, account_id)
            plan = await self._repository.plan_by_id(trip_id, plan_id)
            if plan is None:
                raise DailyPlanNotFoundError
            entry = await self._repository.timeline_entry_by_id(plan.id, entry_id)
            if entry is None:
                raise TimelineEntryNotFoundError
            if request.destination_id is not None and request.destination_id not in {
                destination.id for destination in stored.destinations
            }:
                raise TripDestinationMismatchError
            if entry.revision != request.starting_revision:
                conflict = True
            else:
                entry.destination_id = request.destination_id
                entry.local_time = request.time
                entry.title = request.title
                entry.description = request.description
                entry.location_name = request.location_name
                entry.latitude = request.location.lat if request.location else None
                entry.longitude = request.location.lng if request.location else None
                entry.revision += 1
                plan.timeline_revision += 1
                stored.trip.content_revision += 1
        if conflict:
            latest = await self.get_participant_guide(trip_id, account_id)
            raise TimelineEntryRevisionConflictError(latest.model_dump(mode="json"))
        return await self.get_participant_guide(trip_id, account_id)

    async def delete_timeline_entry(
        self,
        *,
        trip_id: UUID,
        account_id: UUID,
        plan_id: UUID,
        entry_id: UUID,
        request: TimelineEntryDeleteRequest,
    ) -> TripDetailResponse:
        entry_conflict = False
        collection_conflict = False
        async with self._session.begin():
            stored = await self._load_for_edit(trip_id, account_id)
            plan = await self._repository.plan_by_id(trip_id, plan_id)
            if plan is None:
                raise DailyPlanNotFoundError
            entry = await self._repository.timeline_entry_by_id(plan.id, entry_id)
            if entry is None:
                raise TimelineEntryNotFoundError
            entry_conflict = entry.revision != request.starting_revision
            collection_conflict = (
                plan.timeline_revision != request.starting_collection_revision
            )
            if not entry_conflict and not collection_conflict:
                await self._repository.delete_timeline_entry(entry)
                plan.timeline_revision += 1
                stored.trip.content_revision += 1
        if entry_conflict or collection_conflict:
            latest = await self.get_participant_guide(trip_id, account_id)
            if entry_conflict:
                raise TimelineEntryRevisionConflictError(latest.model_dump(mode="json"))
            raise TimelineCollectionRevisionConflictError(
                latest.model_dump(mode="json")
            )
        return await self.get_participant_guide(trip_id, account_id)

    async def reorder_timeline_entries(
        self,
        *,
        trip_id: UUID,
        account_id: UUID,
        plan_id: UUID,
        request: TimelineReorderRequest,
    ) -> TripDetailResponse:
        conflict = False
        async with self._session.begin():
            stored = await self._load_for_edit(trip_id, account_id)
            plan = await self._repository.plan_by_id(trip_id, plan_id)
            if plan is None:
                raise DailyPlanNotFoundError
            if plan.timeline_revision != request.starting_revision:
                conflict = True
            else:
                current = await self._repository.timeline_entries(plan.id)
                by_id = {entry.id: entry for entry in current}
                if set(request.entry_ids) != set(by_id):
                    raise TimelineOrderInvalidError
                ordered = [by_id[entry_id] for entry_id in request.entry_ids]
                if any(
                    first.local_time > second.local_time
                    for first, second in pairwise(ordered)
                ):
                    raise TimelineOrderInvalidError
                await self._repository.reorder_timeline_entries(current, ordered)
                plan.timeline_revision += 1
                stored.trip.content_revision += 1
        if conflict:
            latest = await self.get_participant_guide(trip_id, account_id)
            raise TimelineCollectionRevisionConflictError(
                latest.model_dump(mode="json")
            )
        return await self.get_participant_guide(trip_id, account_id)

    async def move_timeline_entry(
        self,
        *,
        trip_id: UUID,
        account_id: UUID,
        source_plan_id: UUID,
        entry_id: UUID,
        request: TimelineEntryMoveRequest,
    ) -> TripDetailResponse:
        conflict = False
        async with self._session.begin():
            stored = await self._load_for_edit(trip_id, account_id)
            source = await self._repository.plan_by_id(trip_id, source_plan_id)
            target = await self._repository.plan_by_id(trip_id, request.target_plan_id)
            if source is None or target is None or source.id == target.id:
                raise DailyPlanNotFoundError
            entry = await self._repository.timeline_entry_by_id(source.id, entry_id)
            if entry is None:
                raise TimelineEntryNotFoundError
            if (
                source.timeline_revision != request.source_starting_revision
                or target.timeline_revision != request.target_starting_revision
            ):
                conflict = True
            else:
                target_position = await self._repository.next_timeline_position(
                    target.id
                )
                entry.daily_plan_id = target.id
                entry.position = target_position
                source.timeline_revision += 1
                target.timeline_revision += 1
                stored.trip.content_revision += 1
        if conflict:
            latest = await self.get_participant_guide(trip_id, account_id)
            raise TimelineCollectionRevisionConflictError(
                latest.model_dump(mode="json")
            )
        return await self.get_participant_guide(trip_id, account_id)

    async def create_photo(
        self,
        *,
        trip_id: UUID,
        account_id: UUID,
        plan_id: UUID,
        request: PhotoCreateRequest,
    ) -> TripDetailResponse:
        conflict = False
        async with self._session.begin():
            stored = await self._load_for_edit(trip_id, account_id)
            plan = await self._repository.plan_by_id(trip_id, plan_id)
            if plan is None:
                raise DailyPlanNotFoundError
            if plan.photo_revision != request.starting_revision:
                conflict = True
            else:
                self._repository.add_photo(
                    Photo(
                        id=uuid4(),
                        daily_plan_id=plan.id,
                        url=request.url,
                        caption=request.caption,
                        position=await self._repository.next_photo_position(plan.id),
                    )
                )
                plan.photo_revision += 1
                stored.trip.content_revision += 1
        if conflict:
            latest = await self.get_participant_guide(trip_id, account_id)
            raise PhotoCollectionRevisionConflictError(latest.model_dump(mode="json"))
        return await self.get_participant_guide(trip_id, account_id)

    async def delete_photo(
        self,
        *,
        trip_id: UUID,
        account_id: UUID,
        plan_id: UUID,
        photo_id: UUID,
        request: PhotoDeleteRequest,
    ) -> TripDetailResponse:
        collection_conflict = False
        async with self._session.begin():
            stored = await self._load_for_edit(trip_id, account_id)
            plan = await self._repository.plan_by_id(trip_id, plan_id)
            if plan is None:
                raise DailyPlanNotFoundError
            collection_conflict = plan.photo_revision != request.starting_revision
            if not collection_conflict:
                photo = await self._repository.photo_by_id(plan.id, photo_id)
                if photo is None:
                    raise PhotoNotFoundError
                await self._repository.delete_photo(photo)
                remaining = await self._repository.photos(plan.id)
                await self._repository.reorder_photos(remaining, remaining)
                plan.photo_revision += 1
                stored.trip.content_revision += 1
        if collection_conflict:
            latest = await self.get_participant_guide(trip_id, account_id)
            raise PhotoCollectionRevisionConflictError(latest.model_dump(mode="json"))
        return await self.get_participant_guide(trip_id, account_id)

    async def reorder_photos(
        self,
        *,
        trip_id: UUID,
        account_id: UUID,
        plan_id: UUID,
        request: PhotoReorderRequest,
    ) -> TripDetailResponse:
        conflict = False
        async with self._session.begin():
            stored = await self._load_for_edit(trip_id, account_id)
            plan = await self._repository.plan_by_id(trip_id, plan_id)
            if plan is None:
                raise DailyPlanNotFoundError
            if plan.photo_revision != request.starting_revision:
                conflict = True
            else:
                current = await self._repository.photos(plan.id)
                by_id = {photo.id: photo for photo in current}
                if set(request.photo_ids) != set(by_id):
                    raise PhotoOrderInvalidError
                ordered = [by_id[photo_id] for photo_id in request.photo_ids]
                await self._repository.reorder_photos(current, ordered)
                plan.photo_revision += 1
                stored.trip.content_revision += 1
        if conflict:
            latest = await self.get_participant_guide(trip_id, account_id)
            raise PhotoCollectionRevisionConflictError(latest.model_dump(mode="json"))
        return await self.get_participant_guide(trip_id, account_id)

    async def move_daily_plan(
        self,
        *,
        trip_id: UUID,
        account_id: UUID,
        plan_id: UUID,
        request: DailyPlanMoveRequest,
    ) -> TripDetailResponse:
        conflict = False
        async with self._session.begin():
            stored = await self._load_for_edit(trip_id, account_id)
            plan = await self._repository.plan_by_id(trip_id, plan_id)
            if plan is None:
                raise DailyPlanNotFoundError
            if plan.revision != request.starting_revision:
                conflict = True
            else:
                if (
                    not stored.trip.start_date
                    <= request.target_date
                    <= stored.trip.end_date
                ):
                    raise DailyPlanOutOfRangeError
                if await self._repository.plan_on_date(trip_id, request.target_date):
                    raise DailyPlanOccupiedError
                plan.date = request.target_date
                plan.revision += 1
                stored.trip.content_revision += 1
        if conflict:
            latest = await self.get_participant_guide(trip_id, account_id)
            raise DailyPlanRevisionConflictError(latest.model_dump(mode="json"))
        return await self.get_participant_guide(trip_id, account_id)
