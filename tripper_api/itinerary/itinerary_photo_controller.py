from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from tripper_api.core.security import AuthenticatedUser, require_current_user
from tripper_api.itinerary.itinerary_photo_dependencies import get_photo_service
from tripper_api.itinerary.itinerary_photo_dto import (
    PhotoCreateRequest,
    PhotoDeleteRequest,
    PhotoReorderRequest,
)
from tripper_api.itinerary.itinerary_photo_service import PhotoService
from tripper_api.trip.trip_guide_dto import TripDetailResponse

router = APIRouter(prefix="/api")


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
    service: Annotated[PhotoService, Depends(get_photo_service)],
) -> TripDetailResponse:
    return await service.create(
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
    service: Annotated[PhotoService, Depends(get_photo_service)],
) -> TripDetailResponse:
    return await service.reorder(
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
    service: Annotated[PhotoService, Depends(get_photo_service)],
) -> TripDetailResponse:
    return await service.delete(
        trip_id=trip_id,
        account_id=user.id,
        plan_id=plan_id,
        photo_id=photo_id,
        request=request,
    )
