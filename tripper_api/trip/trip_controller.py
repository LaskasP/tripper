from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from tripper_api.core.security import AuthenticatedUser, require_current_user
from tripper_api.trip.trip_dependencies import get_trip_service
from tripper_api.trip.trip_dto import (
    DailyPlanMoveRequest,
    DailyPlanRevisionRequest,
    DailyPlanWriteRequest,
    TripCreateRequest,
    TripDetailResponse,
    TripDetailsUpdateRequest,
    TripSummaryResponse,
)
from tripper_api.trip.trip_service import TripService

router = APIRouter(prefix="/api")


@router.post(
    "/trips",
    response_model=TripSummaryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_trip(
    trip: TripCreateRequest,
    user: Annotated[AuthenticatedUser, Depends(require_current_user)],
    service: Annotated[TripService, Depends(get_trip_service)],
) -> TripSummaryResponse:
    created_trip = await service.create(
        account_id=user.id,
        request=trip,
    )
    return TripSummaryResponse.model_validate(created_trip)


@router.get("/me/trips", response_model=list[TripSummaryResponse])
async def list_my_trips(
    user: Annotated[AuthenticatedUser, Depends(require_current_user)],
    service: Annotated[TripService, Depends(get_trip_service)],
) -> list[TripSummaryResponse]:
    trips = await service.trip_list_for_account(user.id)
    return [TripSummaryResponse.model_validate(trip) for trip in trips]


@router.get("/trips/{trip_id}", response_model=TripDetailResponse)
async def get_participant_trip(
    trip_id: UUID,
    user: Annotated[AuthenticatedUser, Depends(require_current_user)],
    service: Annotated[TripService, Depends(get_trip_service)],
) -> TripDetailResponse:
    return await service.get_participant_guide(trip_id, user.id)


@router.put("/trips/{trip_id}/details", response_model=TripDetailResponse)
async def update_trip_details(
    trip_id: UUID,
    trip: TripDetailsUpdateRequest,
    user: Annotated[AuthenticatedUser, Depends(require_current_user)],
    service: Annotated[TripService, Depends(get_trip_service)],
) -> TripDetailResponse:
    return await service.update_details(
        trip_id=trip_id,
        account_id=user.id,
        request=trip,
    )


@router.put(
    "/trips/{trip_id}/daily-plans/{plan_date}", response_model=TripDetailResponse
)
async def write_daily_plan(
    trip_id: UUID,
    plan_date: date,
    request: DailyPlanWriteRequest,
    user: Annotated[AuthenticatedUser, Depends(require_current_user)],
    service: Annotated[TripService, Depends(get_trip_service)],
) -> TripDetailResponse:
    return await service.write_daily_plan(
        trip_id=trip_id, account_id=user.id, plan_date=plan_date, request=request
    )


@router.delete(
    "/trips/{trip_id}/daily-plans/{plan_date}", response_model=TripDetailResponse
)
async def clear_daily_plan(
    trip_id: UUID,
    plan_date: date,
    request: DailyPlanRevisionRequest,
    user: Annotated[AuthenticatedUser, Depends(require_current_user)],
    service: Annotated[TripService, Depends(get_trip_service)],
) -> TripDetailResponse:
    return await service.clear_daily_plan(
        trip_id=trip_id, account_id=user.id, plan_date=plan_date, request=request
    )


@router.post(
    "/trips/{trip_id}/daily-plans/{plan_id}/move", response_model=TripDetailResponse
)
async def move_daily_plan(
    trip_id: UUID,
    plan_id: UUID,
    request: DailyPlanMoveRequest,
    user: Annotated[AuthenticatedUser, Depends(require_current_user)],
    service: Annotated[TripService, Depends(get_trip_service)],
) -> TripDetailResponse:
    return await service.move_daily_plan(
        trip_id=trip_id, account_id=user.id, plan_id=plan_id, request=request
    )
