from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from tripper_api.core.database import get_database_session
from tripper_api.core.security import AuthenticatedUser, require_current_user
from tripper_api.trip.trip_domain import CreateTrip
from tripper_api.trip.trip_dto import PublicTrip, TripInput, TripSummary
from tripper_api.trip.trip_repository import (
    StoredParticipantTrip,
    StoredTrip,
    TripRepository,
)
from tripper_api.trip.trip_service import TripService

router = APIRouter(prefix="/api")


def get_trip_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> TripService:
    return TripService(session, TripRepository(session))


@router.post(
    "/trips",
    response_model=TripSummary,
    status_code=status.HTTP_201_CREATED,
)
async def create_trip(
    trip: TripInput,
    user: Annotated[AuthenticatedUser, Depends(require_current_user)],
    service: Annotated[TripService, Depends(get_trip_service)],
) -> TripSummary:
    stored_trip = await service.create(
        CreateTrip(
            name=trip.name,
            destination=trip.destination,
            short_name=trip.short_name,
            description=trip.description,
            timezone=trip.timezone,
            latitude=trip.location.lat,
            longitude=trip.location.lng,
            start_date=trip.start_date,
            end_date=trip.end_date,
        ),
        user.id,
    )
    return summary_response(stored_trip)


@router.get("/me/trips", response_model=list[TripSummary])
async def list_my_trips(
    user: Annotated[AuthenticatedUser, Depends(require_current_user)],
    service: Annotated[TripService, Depends(get_trip_service)],
) -> list[TripSummary]:
    stored_trips = await service.list_for_account(user.id)
    return [summary_response(stored_trip) for stored_trip in stored_trips]


@router.get("/trips/{trip_id}", response_model=PublicTrip)
async def get_public_trip(
    trip_id: UUID,
    service: Annotated[TripService, Depends(get_trip_service)],
) -> PublicTrip:
    return public_response(await service.get_public(trip_id))


def summary_response(stored_trip: StoredParticipantTrip) -> TripSummary:
    trip = stored_trip.trip
    return TripSummary(
        id=trip.id,
        name=trip.name,
        destination=stored_trip.destination.name,
        short_name=trip.short_name,
        start_date=trip.start_date,
        end_date=trip.end_date,
        role=stored_trip.role,
    )


def public_response(stored_trip: StoredTrip) -> PublicTrip:
    trip = stored_trip.trip
    destination = stored_trip.destination
    return PublicTrip(
        id=trip.id,
        name=trip.name,
        destination=destination.name,
        short_name=trip.short_name,
        description=trip.description,
        timezone=destination.timezone,
        location={"lat": destination.latitude, "lng": destination.longitude},
        start_date=trip.start_date,
        end_date=trip.end_date,
    )
