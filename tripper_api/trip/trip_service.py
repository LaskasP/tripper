from itertools import pairwise
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from tripper_api.destination.destination_errors import TripDestinationMismatchError
from tripper_api.itinerary.itinerary_daily_plan_errors import DailyPlanNotFoundError
from tripper_api.itinerary.itinerary_photo_model import Photo
from tripper_api.itinerary.itinerary_repository import ItineraryRepository
from tripper_api.itinerary.itinerary_stay_model import Stay
from tripper_api.itinerary.itinerary_timeline_model import TimelineEntry
from tripper_api.membership.membership_model import TripRole
from tripper_api.membership.membership_repository import MembershipRepository
from tripper_api.trip.trip_command_errors import TripEditForbiddenError
from tripper_api.trip.trip_dto import (
    PhotoCreateRequest,
    PhotoDeleteRequest,
    PhotoReorderRequest,
    StayDeleteRequest,
    StayWriteRequest,
    TimelineEntryCreateRequest,
    TimelineEntryDeleteRequest,
    TimelineEntryMoveRequest,
    TimelineEntryUpdateRequest,
    TimelineReorderRequest,
)
from tripper_api.trip.trip_errors import (
    PhotoCollectionRevisionConflictError,
    PhotoNotFoundError,
    PhotoOrderInvalidError,
    StayNotFoundError,
    StayRevisionConflictError,
    TimelineCollectionRevisionConflictError,
    TimelineEntryNotFoundError,
    TimelineEntryRevisionConflictError,
    TimelineOrderInvalidError,
    TripNotFoundError,
)
from tripper_api.trip.trip_guide_dto import TripDetailResponse
from tripper_api.trip.trip_guide_reader import TripGuideReader
from tripper_api.trip.trip_read_model import TripForUpdate
from tripper_api.trip.trip_repository import TripRepository


class TripService:
    def __init__(
        self,
        session: AsyncSession,
        repository: TripRepository,
        itinerary_repository: ItineraryRepository,
        membership_repository: MembershipRepository,
        guide_reader: TripGuideReader,
    ) -> None:
        self._session = session
        self._repository = repository
        self._itinerary_repository = itinerary_repository
        self._membership_repository = membership_repository
        self._guide_reader = guide_reader

    async def _load_for_edit(self, trip_id: UUID, account_id: UUID) -> TripForUpdate:
        access = await self._membership_repository.lock_trip_and_get_membership(
            trip_id, account_id
        )
        if access is None:
            raise TripNotFoundError
        if access.role not in {TripRole.CREATOR, TripRole.CONTRIBUTOR}:
            raise TripEditForbiddenError
        return await self._repository.load_for_update(access.trip)

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
            plan = await self._itinerary_repository.plan_by_id(trip_id, plan_id)
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
            latest = await self._guide_reader.get_participant_guide(trip_id, account_id)
            raise StayRevisionConflictError(latest.model_dump(mode="json"))
        return await self._guide_reader.get_participant_guide(trip_id, account_id)

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
            plan = await self._itinerary_repository.plan_by_id(trip_id, plan_id)
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
            latest = await self._guide_reader.get_participant_guide(trip_id, account_id)
            raise StayRevisionConflictError(latest.model_dump(mode="json"))
        return await self._guide_reader.get_participant_guide(trip_id, account_id)

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
            plan = await self._itinerary_repository.plan_by_id(trip_id, plan_id)
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
            latest = await self._guide_reader.get_participant_guide(trip_id, account_id)
            raise TimelineCollectionRevisionConflictError(
                latest.model_dump(mode="json")
            )
        return await self._guide_reader.get_participant_guide(trip_id, account_id)

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
            plan = await self._itinerary_repository.plan_by_id(trip_id, plan_id)
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
            latest = await self._guide_reader.get_participant_guide(trip_id, account_id)
            raise TimelineEntryRevisionConflictError(latest.model_dump(mode="json"))
        return await self._guide_reader.get_participant_guide(trip_id, account_id)

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
            plan = await self._itinerary_repository.plan_by_id(trip_id, plan_id)
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
            latest = await self._guide_reader.get_participant_guide(trip_id, account_id)
            if entry_conflict:
                raise TimelineEntryRevisionConflictError(latest.model_dump(mode="json"))
            raise TimelineCollectionRevisionConflictError(
                latest.model_dump(mode="json")
            )
        return await self._guide_reader.get_participant_guide(trip_id, account_id)

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
            plan = await self._itinerary_repository.plan_by_id(trip_id, plan_id)
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
            latest = await self._guide_reader.get_participant_guide(trip_id, account_id)
            raise TimelineCollectionRevisionConflictError(
                latest.model_dump(mode="json")
            )
        return await self._guide_reader.get_participant_guide(trip_id, account_id)

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
            source = await self._itinerary_repository.plan_by_id(
                trip_id, source_plan_id
            )
            target = await self._itinerary_repository.plan_by_id(
                trip_id, request.target_plan_id
            )
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
            latest = await self._guide_reader.get_participant_guide(trip_id, account_id)
            raise TimelineCollectionRevisionConflictError(
                latest.model_dump(mode="json")
            )
        return await self._guide_reader.get_participant_guide(trip_id, account_id)

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
            plan = await self._itinerary_repository.plan_by_id(trip_id, plan_id)
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
            latest = await self._guide_reader.get_participant_guide(trip_id, account_id)
            raise PhotoCollectionRevisionConflictError(latest.model_dump(mode="json"))
        return await self._guide_reader.get_participant_guide(trip_id, account_id)

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
            plan = await self._itinerary_repository.plan_by_id(trip_id, plan_id)
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
            latest = await self._guide_reader.get_participant_guide(trip_id, account_id)
            raise PhotoCollectionRevisionConflictError(latest.model_dump(mode="json"))
        return await self._guide_reader.get_participant_guide(trip_id, account_id)

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
            plan = await self._itinerary_repository.plan_by_id(trip_id, plan_id)
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
            latest = await self._guide_reader.get_participant_guide(trip_id, account_id)
            raise PhotoCollectionRevisionConflictError(latest.model_dump(mode="json"))
        return await self._guide_reader.get_participant_guide(trip_id, account_id)
