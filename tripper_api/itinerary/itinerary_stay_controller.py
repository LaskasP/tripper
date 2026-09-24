from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status

from tripper_api.core.security import AuthenticatedUser, require_current_user
from tripper_api.itinerary.itinerary_stay_dependencies import get_stay_service
from tripper_api.itinerary.itinerary_stay_dto import (
    StayRevisionRequest,
    StayWriteRequest,
)
from tripper_api.itinerary.itinerary_stay_service import StayService
from tripper_api.trip.trip_guide_dto import StayResponse

router = APIRouter(prefix="/api")


@router.put(
    "/trips/{trip_id}/daily-plans/{plan_id}/stay",
    response_model=StayResponse,
)
async def write_stay(
    trip_id: UUID,
    plan_id: UUID,
    request: StayWriteRequest,
    user: Annotated[AuthenticatedUser, Depends(require_current_user)],
    service: Annotated[StayService, Depends(get_stay_service)],
) -> StayResponse:
    return await service.write(
        trip_id=trip_id,
        account_id=user.id,
        plan_id=plan_id,
        request=request,
    )


@router.delete(
    "/trips/{trip_id}/daily-plans/{plan_id}/stay",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def clear_stay(
    trip_id: UUID,
    plan_id: UUID,
    request: StayRevisionRequest,
    user: Annotated[AuthenticatedUser, Depends(require_current_user)],
    service: Annotated[StayService, Depends(get_stay_service)],
) -> Response:
    await service.clear(
        trip_id=trip_id,
        account_id=user.id,
        plan_id=plan_id,
        request=request,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
