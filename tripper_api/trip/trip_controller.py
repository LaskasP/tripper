from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from tripper_api.core.database import get_database_session
from tripper_api.core.security import AuthenticatedUser, require_current_user
from tripper_api.trip.trip_domain import PublicTripView
from tripper_api.trip.trip_dto import (
    PublicTripResponse,
    TripCreateRequest,
    TripSummaryResponse,
)
from tripper_api.trip.trip_repository import TripRepository
from tripper_api.trip.trip_service import TripService

router = APIRouter(prefix="/api")


def get_trip_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> TripService:
    return TripService(session, TripRepository(session))


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
        name=trip.name,
        destination_name=trip.destination,
        short_name=trip.short_name,
        description=trip.description,
        timezone=trip.timezone,
        latitude=trip.location.lat,
        longitude=trip.location.lng,
        start_date=trip.start_date,
        end_date=trip.end_date,
    )
    return TripSummaryResponse.model_validate(created_trip)


@router.get("/me/trips", response_model=list[TripSummaryResponse])
async def list_my_trips(
    user: Annotated[AuthenticatedUser, Depends(require_current_user)],
    service: Annotated[TripService, Depends(get_trip_service)],
) -> list[TripSummaryResponse]:
    trips = await service.list_for_account(user.id)
    return [TripSummaryResponse.model_validate(trip) for trip in trips]


@router.get("/trips/{trip_id}", response_model=PublicTripResponse)
async def get_public_trip(
    trip_id: UUID,
    service: Annotated[TripService, Depends(get_trip_service)],
) -> PublicTripResponse:
    return public_response(await service.get_public(trip_id))


def public_response(trip: PublicTripView) -> PublicTripResponse:
    return PublicTripResponse(
        id=trip.id,
        name=trip.name,
        destination=trip.destination,
        short_name=trip.short_name,
        description=trip.description,
        timezone=trip.timezone,
        location={"lat": trip.latitude, "lng": trip.longitude},
        start_date=trip.start_date,
        end_date=trip.end_date,
    )
