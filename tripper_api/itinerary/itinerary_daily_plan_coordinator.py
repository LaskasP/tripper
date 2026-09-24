from datetime import date
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from tripper_api.destination.destination_errors import TripDestinationMismatchError
from tripper_api.destination.destination_repository import DestinationRepository
from tripper_api.itinerary.itinerary_daily_plan_dto import (
    DailyPlanMoveRequest,
    DailyPlanResponse,
    DailyPlanRevisionRequest,
    DailyPlanWriteRequest,
)
from tripper_api.itinerary.itinerary_daily_plan_errors import (
    DailyPlanOutOfRangeError,
    DailyPlanRevisionConflictError,
)
from tripper_api.itinerary.itinerary_daily_plan_service import DailyPlanService
from tripper_api.membership.membership_model import TripRole
from tripper_api.membership.membership_read_model import TripAccess
from tripper_api.membership.membership_repository import MembershipRepository
from tripper_api.trip.trip_command_errors import TripEditForbiddenError
from tripper_api.trip.trip_errors import TripNotFoundError


class DailyPlanCommandCoordinator:
    """Coordinates cross-capability checks around autonomous Daily plan commands."""

    def __init__(
        self,
        session: AsyncSession,
        daily_plan_service: DailyPlanService,
        destination_repository: DestinationRepository,
        membership_repository: MembershipRepository,
    ) -> None:
        self._session = session
        self._daily_plan_service = daily_plan_service
        self._destination_repository = destination_repository
        self._membership_repository = membership_repository

    async def _lock_trip_for_edit(self, trip_id: UUID, account_id: UUID) -> TripAccess:
        access = await self._membership_repository.lock_trip_and_get_membership(
            trip_id, account_id
        )
        if access is None:
            raise TripNotFoundError
        if access.role not in {TripRole.CREATOR, TripRole.CONTRIBUTOR}:
            raise TripEditForbiddenError
        return access

    @staticmethod
    def _validate_date(access: TripAccess, plan_date: date) -> None:
        if not access.trip.start_date <= plan_date <= access.trip.end_date:
            raise DailyPlanOutOfRangeError

    async def write(
        self,
        *,
        trip_id: UUID,
        account_id: UUID,
        plan_date: date,
        request: DailyPlanWriteRequest,
    ) -> DailyPlanResponse:
        async with self._session.begin():
            access = await self._lock_trip_for_edit(trip_id, account_id)
            self._validate_date(access, plan_date)
            if not await self._destination_repository.belongs_to_trip(
                trip_id, request.destination_id
            ):
                raise TripDestinationMismatchError
            if (
                request.id is None
                and request.starting_revision != access.trip.content_revision
            ):
                current = await self._daily_plan_service.current(
                    trip_id=trip_id, plan_date=plan_date
                )
                raise DailyPlanRevisionConflictError(
                    current.model_dump(mode="json") if current else None
                )
            response = await self._daily_plan_service.write(
                trip_id=trip_id,
                plan_date=plan_date,
                plan_id=request.id,
                starting_revision=request.starting_revision,
                destination_id=request.destination_id,
                title=request.title,
                summary=request.summary,
                background_image=request.background_image,
            )
            access.trip.content_revision += 1
        return response

    async def clear(
        self,
        *,
        trip_id: UUID,
        account_id: UUID,
        plan_date: date,
        request: DailyPlanRevisionRequest,
    ) -> None:
        async with self._session.begin():
            access = await self._lock_trip_for_edit(trip_id, account_id)
            await self._daily_plan_service.clear(
                trip_id=trip_id,
                plan_date=plan_date,
                starting_revision=request.starting_revision,
            )
            access.trip.content_revision += 1

    async def move(
        self,
        *,
        trip_id: UUID,
        account_id: UUID,
        plan_id: UUID,
        request: DailyPlanMoveRequest,
    ) -> DailyPlanResponse:
        async with self._session.begin():
            access = await self._lock_trip_for_edit(trip_id, account_id)
            self._validate_date(access, request.target_date)
            response = await self._daily_plan_service.move(
                trip_id=trip_id,
                plan_id=plan_id,
                target_date=request.target_date,
                starting_revision=request.starting_revision,
            )
            access.trip.content_revision += 1
        return response
