from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from tripper_api.itinerary.itinerary_daily_plan_errors import DailyPlanNotFoundError
from tripper_api.itinerary.itinerary_repository import ItineraryRepository
from tripper_api.itinerary.itinerary_stay_dto import (
    StayRevisionRequest,
    StayWriteRequest,
)
from tripper_api.itinerary.itinerary_stay_errors import (
    StayNotFoundError,
    StayRevisionConflictError,
)
from tripper_api.itinerary.itinerary_stay_model import Stay
from tripper_api.itinerary.itinerary_stay_repository import StayRepository
from tripper_api.trip.trip_access_control import TripAccessControl
from tripper_api.trip.trip_guide_dto import StayResponse
from tripper_api.trip.trip_guide_reader import TripGuideReader


class StayService:
    def __init__(
        self,
        session: AsyncSession,
        itinerary_repository: ItineraryRepository,
        stay_repository: StayRepository,
        access_control: TripAccessControl,
        guide_reader: TripGuideReader,
    ) -> None:
        self._session = session
        self._itinerary_repository = itinerary_repository
        self._stay_repository = stay_repository
        self._access_control = access_control
        self._guide_reader = guide_reader

    async def write(
        self,
        *,
        trip_id: UUID,
        account_id: UUID,
        plan_id: UUID,
        request: StayWriteRequest,
    ) -> StayResponse:
        conflict = False
        async with self._session.begin():
            access = await self._access_control.lock_for_edit(trip_id, account_id)
            plan = await self._itinerary_repository.plan_by_id(trip_id, plan_id)
            if plan is None:
                raise DailyPlanNotFoundError
            stay = await self._stay_repository.get_for_plan(plan.id)
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
                    await self._stay_repository.add(stay)
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
                access.trip.content_revision += 1
        current = await self._guide_reader.get_stay(trip_id, plan_id)
        if conflict:
            latest = current.model_dump(mode="json") if current is not None else None
            raise StayRevisionConflictError(latest)
        if current is None:
            raise StayNotFoundError
        return current

    async def clear(
        self,
        *,
        trip_id: UUID,
        account_id: UUID,
        plan_id: UUID,
        request: StayRevisionRequest,
    ) -> None:
        conflict = False
        async with self._session.begin():
            access = await self._access_control.lock_for_edit(trip_id, account_id)
            plan = await self._itinerary_repository.plan_by_id(trip_id, plan_id)
            if plan is None:
                raise DailyPlanNotFoundError
            stay = await self._stay_repository.get_for_plan(plan.id)
            if stay is None:
                raise StayNotFoundError
            if stay.revision != request.starting_revision:
                conflict = True
            else:
                await self._stay_repository.delete(stay)
                access.trip.content_revision += 1
        if conflict:
            current = await self._guide_reader.get_stay(trip_id, plan_id)
            latest = current.model_dump(mode="json") if current is not None else None
            raise StayRevisionConflictError(latest)
