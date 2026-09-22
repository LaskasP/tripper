from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from tripper_api.core.security import AuthenticatedUser, require_current_user
from tripper_api.trip.trip_dependencies import get_trip_service
from tripper_api.trip.trip_dto import (
    LocationInput,
    TripCreateRequest,
    TripDetailResponse,
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
    trips = await service.list_for_account(user.id)
    return [TripSummaryResponse.model_validate(trip) for trip in trips]


@router.get("/trips/{trip_id}", response_model=TripDetailResponse)
async def get_participant_trip(
    trip_id: UUID,
    user: Annotated[AuthenticatedUser, Depends(require_current_user)],
    service: Annotated[TripService, Depends(get_trip_service)],
) -> TripDetailResponse:
    trip = await service.get_for_account(trip_id, user.id)
    location = (
        LocationInput(lat=trip.latitude, lng=trip.longitude)
        if trip.latitude is not None and trip.longitude is not None
        else None
    )
    return TripDetailResponse(
        id=trip.id,
        name=trip.name,
        destination=trip.destination,
        short_name=trip.short_name,
        description=trip.description,
        timezone=trip.timezone,
        location=location,
        start_date=trip.start_date,
        end_date=trip.end_date,
    )
