from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from tripper_api.core.security import AuthenticatedUser, require_current_user
from tripper_api.itinerary.itinerary_timeline_dependencies import (
    get_timeline_service,
)
from tripper_api.itinerary.itinerary_timeline_dto import (
    TimelineEntryCreateRequest,
    TimelineEntryDeleteRequest,
    TimelineEntryMoveRequest,
    TimelineEntryUpdateRequest,
    TimelineReorderRequest,
)
from tripper_api.itinerary.itinerary_timeline_service import TimelineService
from tripper_api.trip.trip_guide_dto import TripDetailResponse

router = APIRouter(prefix="/api")


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
    service: Annotated[TimelineService, Depends(get_timeline_service)],
) -> TripDetailResponse:
    return await service.create(
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
    service: Annotated[TimelineService, Depends(get_timeline_service)],
) -> TripDetailResponse:
    return await service.reorder(
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
    service: Annotated[TimelineService, Depends(get_timeline_service)],
) -> TripDetailResponse:
    return await service.move(
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
    service: Annotated[TimelineService, Depends(get_timeline_service)],
) -> TripDetailResponse:
    return await service.update(
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
    service: Annotated[TimelineService, Depends(get_timeline_service)],
) -> TripDetailResponse:
    return await service.delete(
        trip_id=trip_id,
        account_id=user.id,
        plan_id=plan_id,
        entry_id=entry_id,
        request=request,
    )
