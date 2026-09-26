from itertools import pairwise
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from tripper_api.destination.destination_errors import TripDestinationMismatchError
from tripper_api.destination.destination_repository import DestinationRepository
from tripper_api.itinerary.itinerary_daily_plan_errors import DailyPlanNotFoundError
from tripper_api.itinerary.itinerary_timeline_dto import (
    TimelineEntryCreateRequest,
    TimelineEntryDeleteRequest,
    TimelineEntryMoveRequest,
    TimelineEntryUpdateRequest,
    TimelineReorderRequest,
)
from tripper_api.itinerary.itinerary_timeline_errors import (
    TimelineCollectionRevisionConflictError,
    TimelineEntryNotFoundError,
    TimelineEntryRevisionConflictError,
    TimelineOrderInvalidError,
)
from tripper_api.itinerary.itinerary_timeline_model import TimelineEntry
from tripper_api.itinerary.itinerary_timeline_repository import TimelineRepository
from tripper_api.trip.trip_access_control import TripAccessControl
from tripper_api.trip.trip_guide_dto import TripDetailResponse
from tripper_api.trip.trip_guide_reader import TripGuideReader


class TimelineService:
    def __init__(
        self,
        session: AsyncSession,
        repository: TimelineRepository,
        destination_repository: DestinationRepository,
        access_control: TripAccessControl,
        guide_reader: TripGuideReader,
    ) -> None:
        self._session = session
        self._repository = repository
        self._destination_repository = destination_repository
        self._access_control = access_control
        self._guide_reader = guide_reader

    async def _validate_destination(
        self, trip_id: UUID, destination_id: UUID | None
    ) -> None:
        if destination_id is not None and not (
            await self._destination_repository.belongs_to_trip(trip_id, destination_id)
        ):
            raise TripDestinationMismatchError

    async def _latest_values(
        self, trip_id: UUID, account_id: UUID
    ) -> dict[str, object]:
        latest = await self._guide_reader.get_participant_guide(trip_id, account_id)
        return latest.model_dump(mode="json")

    async def create(
        self,
        *,
        trip_id: UUID,
        account_id: UUID,
        plan_id: UUID,
        request: TimelineEntryCreateRequest,
    ) -> TripDetailResponse:
        conflict = False
        async with self._session.begin():
            access = await self._access_control.lock_for_edit(trip_id, account_id)
            plans = await self._repository.lock_plans(trip_id, [plan_id])
            plan = plans.get(plan_id)
            if plan is None:
                raise DailyPlanNotFoundError
            await self._validate_destination(trip_id, request.destination_id)
            if plan.timeline_revision != request.starting_revision:
                conflict = True
            else:
                await self._repository.add(
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
                        position=await self._repository.next_position(plan.id),
                    )
                )
                plan.timeline_revision += 1
                access.trip.content_revision += 1
        if conflict:
            raise TimelineCollectionRevisionConflictError(
                await self._latest_values(trip_id, account_id)
            )
        return await self._guide_reader.get_participant_guide(trip_id, account_id)

    async def update(
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
            access = await self._access_control.lock_for_edit(trip_id, account_id)
            plans = await self._repository.lock_plans(trip_id, [plan_id])
            plan = plans.get(plan_id)
            if plan is None:
                raise DailyPlanNotFoundError
            entry = await self._repository.get(plan.id, entry_id)
            if entry is None:
                raise TimelineEntryNotFoundError
            await self._validate_destination(trip_id, request.destination_id)
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
                access.trip.content_revision += 1
        if conflict:
            raise TimelineEntryRevisionConflictError(
                await self._latest_values(trip_id, account_id)
            )
        return await self._guide_reader.get_participant_guide(trip_id, account_id)

    async def delete(
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
            access = await self._access_control.lock_for_edit(trip_id, account_id)
            plans = await self._repository.lock_plans(trip_id, [plan_id])
            plan = plans.get(plan_id)
            if plan is None:
                raise DailyPlanNotFoundError
            entry = await self._repository.get(plan.id, entry_id)
            if entry is None:
                raise TimelineEntryNotFoundError
            entry_conflict = entry.revision != request.starting_revision
            collection_conflict = (
                plan.timeline_revision != request.starting_collection_revision
            )
            if not entry_conflict and not collection_conflict:
                await self._repository.delete(entry)
                plan.timeline_revision += 1
                access.trip.content_revision += 1
        if entry_conflict or collection_conflict:
            if entry_conflict:
                raise TimelineEntryRevisionConflictError(
                    await self._latest_values(trip_id, account_id)
                )
            raise TimelineCollectionRevisionConflictError(
                await self._latest_values(trip_id, account_id)
            )
        return await self._guide_reader.get_participant_guide(trip_id, account_id)

    async def reorder(
        self,
        *,
        trip_id: UUID,
        account_id: UUID,
        plan_id: UUID,
        request: TimelineReorderRequest,
    ) -> TripDetailResponse:
        conflict = False
        async with self._session.begin():
            access = await self._access_control.lock_for_edit(trip_id, account_id)
            plans = await self._repository.lock_plans(trip_id, [plan_id])
            plan = plans.get(plan_id)
            if plan is None:
                raise DailyPlanNotFoundError
            if plan.timeline_revision != request.starting_revision:
                conflict = True
            else:
                current = await self._repository.list_entries(plan.id)
                by_id = {entry.id: entry for entry in current}
                if set(request.entry_ids) != set(by_id):
                    raise TimelineOrderInvalidError
                ordered = [by_id[entry_id] for entry_id in request.entry_ids]
                if any(
                    first.local_time > second.local_time
                    for first, second in pairwise(ordered)
                ):
                    raise TimelineOrderInvalidError
                await self._repository.reorder(current, ordered)
                plan.timeline_revision += 1
                access.trip.content_revision += 1
        if conflict:
            raise TimelineCollectionRevisionConflictError(
                await self._latest_values(trip_id, account_id)
            )
        return await self._guide_reader.get_participant_guide(trip_id, account_id)

    async def move(
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
            access = await self._access_control.lock_for_edit(trip_id, account_id)
            plans = await self._repository.lock_plans(
                trip_id, [source_plan_id, request.target_plan_id]
            )
            source = plans.get(source_plan_id)
            target = plans.get(request.target_plan_id)
            if source is None or target is None or source.id == target.id:
                raise DailyPlanNotFoundError
            entry = await self._repository.get(source.id, entry_id)
            if entry is None:
                raise TimelineEntryNotFoundError
            if (
                source.timeline_revision != request.source_starting_revision
                or target.timeline_revision != request.target_starting_revision
            ):
                conflict = True
            else:
                target_position = await self._repository.next_position(target.id)
                entry.daily_plan_id = target.id
                entry.position = target_position
                source.timeline_revision += 1
                target.timeline_revision += 1
                access.trip.content_revision += 1
        if conflict:
            raise TimelineCollectionRevisionConflictError(
                await self._latest_values(trip_id, account_id)
            )
        return await self._guide_reader.get_participant_guide(trip_id, account_id)
