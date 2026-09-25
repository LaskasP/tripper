from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from tripper_api.core.security import AuthenticatedUser, require_current_user
from tripper_api.trip.trip_dependencies import get_trip_guide_reader
from tripper_api.trip.trip_guide_dto import TripDetailResponse
from tripper_api.trip.trip_guide_reader import TripGuideReader

router = APIRouter(prefix="/api")


@router.get("/trips/{trip_id}", response_model=TripDetailResponse)
async def get_participant_trip(
    trip_id: UUID,
    user: Annotated[AuthenticatedUser, Depends(require_current_user)],
    reader: Annotated[TripGuideReader, Depends(get_trip_guide_reader)],
) -> TripDetailResponse:
    return await reader.get_participant_guide(trip_id, user.id)
