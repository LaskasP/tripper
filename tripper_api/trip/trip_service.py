from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from tripper_api.itinerary.itinerary_daily_plan_errors import DailyPlanNotFoundError
from tripper_api.itinerary.itinerary_photo_model import Photo
from tripper_api.itinerary.itinerary_repository import ItineraryRepository
from tripper_api.membership.membership_model import TripRole
from tripper_api.membership.membership_read_model import TripAccess
from tripper_api.membership.membership_repository import MembershipRepository
from tripper_api.trip.trip_command_errors import TripEditForbiddenError
from tripper_api.trip.trip_dto import (
    PhotoCreateRequest,
    PhotoDeleteRequest,
    PhotoReorderRequest,
)
from tripper_api.trip.trip_errors import (
    PhotoCollectionRevisionConflictError,
    PhotoNotFoundError,
    PhotoOrderInvalidError,
    TripNotFoundError,
)
from tripper_api.trip.trip_guide_dto import TripDetailResponse
from tripper_api.trip.trip_guide_reader import TripGuideReader
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

    async def _lock_trip_for_edit(self, trip_id: UUID, account_id: UUID) -> TripAccess:
        access = await self._membership_repository.lock_trip_and_get_membership(
            trip_id, account_id
        )
        if access is None:
            raise TripNotFoundError
        if access.role not in {TripRole.CREATOR, TripRole.CONTRIBUTOR}:
            raise TripEditForbiddenError
        return access

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
            access = await self._lock_trip_for_edit(trip_id, account_id)
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
                access.trip.content_revision += 1
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
            access = await self._lock_trip_for_edit(trip_id, account_id)
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
                access.trip.content_revision += 1
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
            access = await self._lock_trip_for_edit(trip_id, account_id)
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
                access.trip.content_revision += 1
        if conflict:
            latest = await self._guide_reader.get_participant_guide(trip_id, account_id)
            raise PhotoCollectionRevisionConflictError(latest.model_dump(mode="json"))
        return await self._guide_reader.get_participant_guide(trip_id, account_id)
