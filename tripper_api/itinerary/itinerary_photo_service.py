from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from tripper_api.itinerary.itinerary_daily_plan_errors import DailyPlanNotFoundError
from tripper_api.itinerary.itinerary_photo_dto import (
    PhotoCreateRequest,
    PhotoDeleteRequest,
    PhotoReorderRequest,
)
from tripper_api.itinerary.itinerary_photo_errors import (
    PhotoCollectionRevisionConflictError,
    PhotoNotFoundError,
    PhotoOrderInvalidError,
)
from tripper_api.itinerary.itinerary_photo_model import Photo
from tripper_api.itinerary.itinerary_photo_repository import PhotoRepository
from tripper_api.membership.membership_model import TripRole
from tripper_api.membership.membership_read_model import TripAccess
from tripper_api.membership.membership_repository import MembershipRepository
from tripper_api.trip.trip_command_errors import TripEditForbiddenError
from tripper_api.trip.trip_errors import TripNotFoundError
from tripper_api.trip.trip_guide_dto import TripDetailResponse
from tripper_api.trip.trip_guide_reader import TripGuideReader


class PhotoService:
    def __init__(
        self,
        session: AsyncSession,
        repository: PhotoRepository,
        membership_repository: MembershipRepository,
        guide_reader: TripGuideReader,
    ) -> None:
        self._session = session
        self._repository = repository
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
        request: PhotoCreateRequest,
    ) -> TripDetailResponse:
        conflict = False
        async with self._session.begin():
            access = await self._lock_trip_for_edit(trip_id, account_id)
            plan = await self._repository.lock_plan(trip_id, plan_id)
            if plan is None:
                raise DailyPlanNotFoundError
            if plan.photo_revision != request.starting_revision:
                conflict = True
            else:
                await self._repository.add(
                    Photo(
                        id=uuid4(),
                        daily_plan_id=plan.id,
                        url=request.url,
                        caption=request.caption,
                        position=await self._repository.next_position(plan.id),
                    )
                )
                plan.photo_revision += 1
                access.trip.content_revision += 1
        if conflict:
            raise PhotoCollectionRevisionConflictError(
                await self._latest_values(trip_id, account_id)
            )
        return await self._guide_reader.get_participant_guide(trip_id, account_id)

    async def delete(
        self,
        *,
        trip_id: UUID,
        account_id: UUID,
        plan_id: UUID,
        photo_id: UUID,
        request: PhotoDeleteRequest,
    ) -> TripDetailResponse:
        conflict = False
        async with self._session.begin():
            access = await self._lock_trip_for_edit(trip_id, account_id)
            plan = await self._repository.lock_plan(trip_id, plan_id)
            if plan is None:
                raise DailyPlanNotFoundError
            if plan.photo_revision != request.starting_revision:
                conflict = True
            else:
                photo = await self._repository.get(plan.id, photo_id)
                if photo is None:
                    raise PhotoNotFoundError
                await self._repository.delete(photo)
                remaining = await self._repository.list_photos(plan.id)
                await self._repository.reorder(remaining, remaining)
                plan.photo_revision += 1
                access.trip.content_revision += 1
        if conflict:
            raise PhotoCollectionRevisionConflictError(
                await self._latest_values(trip_id, account_id)
            )
        return await self._guide_reader.get_participant_guide(trip_id, account_id)

    async def reorder(
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
            plan = await self._repository.lock_plan(trip_id, plan_id)
            if plan is None:
                raise DailyPlanNotFoundError
            if plan.photo_revision != request.starting_revision:
                conflict = True
            else:
                current = await self._repository.list_photos(plan.id)
                by_id = {photo.id: photo for photo in current}
                if set(request.photo_ids) != set(by_id):
                    raise PhotoOrderInvalidError
                ordered = [by_id[photo_id] for photo_id in request.photo_ids]
                await self._repository.reorder(current, ordered)
                plan.photo_revision += 1
                access.trip.content_revision += 1
        if conflict:
            raise PhotoCollectionRevisionConflictError(
                await self._latest_values(trip_id, account_id)
            )
        return await self._guide_reader.get_participant_guide(trip_id, account_id)
