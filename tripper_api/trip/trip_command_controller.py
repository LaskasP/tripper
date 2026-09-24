from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from tripper_api.core.security import AuthenticatedUser, require_current_user
from tripper_api.membership.membership_dto import TripSummaryResponse
from tripper_api.trip.trip_command_dependencies import get_trip_command_service
from tripper_api.trip.trip_command_dto import (
    TripCreateRequest,
    TripDetailsUpdateRequest,
)
from tripper_api.trip.trip_command_service import TripCommandService
from tripper_api.trip.trip_guide_dto import TripDetailResponse

router = APIRouter(prefix="/api")


@router.post(
    "/trips",
    response_model=TripSummaryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_trip(
    trip: TripCreateRequest,
    user: Annotated[AuthenticatedUser, Depends(require_current_user)],
    service: Annotated[TripCommandService, Depends(get_trip_command_service)],
) -> TripSummaryResponse:
    return await service.create(account_id=user.id, request=trip)


@router.put("/trips/{trip_id}/details", response_model=TripDetailResponse)
async def update_trip_details(
    trip_id: UUID,
    trip: TripDetailsUpdateRequest,
    user: Annotated[AuthenticatedUser, Depends(require_current_user)],
    service: Annotated[TripCommandService, Depends(get_trip_command_service)],
) -> TripDetailResponse:
    return await service.update_details(
        trip_id=trip_id,
        account_id=user.id,
        request=trip,
    )
