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
    PhotoCreateRequest,
    PhotoDeleteRequest,
    PhotoReorderRequest,
    TimelineEntryCreateRequest,
    TimelineEntryDeleteRequest,
    TimelineEntryMoveRequest,
    TimelineEntryUpdateRequest,
    TimelineReorderRequest,
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


@router.post(
    "/trips/{trip_id}/daily-plans/{plan_id}/timeline",
    response_model=TripDetailResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_timeline_entry(
    trip_id: UUID,
    plan_id: UUID,
    request: TimelineEntryCreateRequest,
    user: Annotated[AuthenticatedUser, Depends(require_current_user)],
    service: Annotated[TripService, Depends(get_trip_service)],
) -> TripDetailResponse:
    return await service.create_timeline_entry(
        trip_id=trip_id,
        account_id=user.id,
        plan_id=plan_id,
        request=request,
    )


@router.post(
    "/trips/{trip_id}/daily-plans/{plan_id}/timeline/reorder",
    response_model=TripDetailResponse,
)
async def reorder_timeline_entries(
    trip_id: UUID,
    plan_id: UUID,
    request: TimelineReorderRequest,
    user: Annotated[AuthenticatedUser, Depends(require_current_user)],
    service: Annotated[TripService, Depends(get_trip_service)],
) -> TripDetailResponse:
    return await service.reorder_timeline_entries(
        trip_id=trip_id,
        account_id=user.id,
        plan_id=plan_id,
        request=request,
    )


@router.post(
    "/trips/{trip_id}/daily-plans/{plan_id}/timeline/{entry_id}/move",
    response_model=TripDetailResponse,
)
async def move_timeline_entry(
    trip_id: UUID,
    plan_id: UUID,
    entry_id: UUID,
    request: TimelineEntryMoveRequest,
    user: Annotated[AuthenticatedUser, Depends(require_current_user)],
    service: Annotated[TripService, Depends(get_trip_service)],
) -> TripDetailResponse:
    return await service.move_timeline_entry(
        trip_id=trip_id,
        account_id=user.id,
        source_plan_id=plan_id,
        entry_id=entry_id,
        request=request,
    )


@router.put(
    "/trips/{trip_id}/daily-plans/{plan_id}/timeline/{entry_id}",
    response_model=TripDetailResponse,
)
async def update_timeline_entry(
    trip_id: UUID,
    plan_id: UUID,
    entry_id: UUID,
    request: TimelineEntryUpdateRequest,
    user: Annotated[AuthenticatedUser, Depends(require_current_user)],
    service: Annotated[TripService, Depends(get_trip_service)],
) -> TripDetailResponse:
    return await service.update_timeline_entry(
        trip_id=trip_id,
        account_id=user.id,
        plan_id=plan_id,
        entry_id=entry_id,
        request=request,
    )


@router.delete(
    "/trips/{trip_id}/daily-plans/{plan_id}/timeline/{entry_id}",
    response_model=TripDetailResponse,
)
async def delete_timeline_entry(
    trip_id: UUID,
    plan_id: UUID,
    entry_id: UUID,
    request: TimelineEntryDeleteRequest,
    user: Annotated[AuthenticatedUser, Depends(require_current_user)],
    service: Annotated[TripService, Depends(get_trip_service)],
) -> TripDetailResponse:
    return await service.delete_timeline_entry(
        trip_id=trip_id,
        account_id=user.id,
        plan_id=plan_id,
        entry_id=entry_id,
        request=request,
    )


@router.post(
    "/trips/{trip_id}/daily-plans/{plan_id}/photos",
    response_model=TripDetailResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_photo(
    trip_id: UUID,
    plan_id: UUID,
    request: PhotoCreateRequest,
    user: Annotated[AuthenticatedUser, Depends(require_current_user)],
    service: Annotated[TripService, Depends(get_trip_service)],
) -> TripDetailResponse:
    return await service.create_photo(
        trip_id=trip_id,
        account_id=user.id,
        plan_id=plan_id,
        request=request,
    )


@router.post(
    "/trips/{trip_id}/daily-plans/{plan_id}/photos/reorder",
    response_model=TripDetailResponse,
)
async def reorder_photos(
    trip_id: UUID,
    plan_id: UUID,
    request: PhotoReorderRequest,
    user: Annotated[AuthenticatedUser, Depends(require_current_user)],
    service: Annotated[TripService, Depends(get_trip_service)],
) -> TripDetailResponse:
    return await service.reorder_photos(
        trip_id=trip_id,
        account_id=user.id,
        plan_id=plan_id,
        request=request,
    )


@router.delete(
    "/trips/{trip_id}/daily-plans/{plan_id}/photos/{photo_id}",
    response_model=TripDetailResponse,
)
async def delete_photo(
    trip_id: UUID,
    plan_id: UUID,
    photo_id: UUID,
    request: PhotoDeleteRequest,
    user: Annotated[AuthenticatedUser, Depends(require_current_user)],
    service: Annotated[TripService, Depends(get_trip_service)],
) -> TripDetailResponse:
    return await service.delete_photo(
        trip_id=trip_id,
        account_id=user.id,
        plan_id=plan_id,
        photo_id=photo_id,
        request=request,
    )
