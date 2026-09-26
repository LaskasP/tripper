from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from tripper_api.core.database import get_database_session
from tripper_api.destination.destination_repository import DestinationRepository
from tripper_api.itinerary.itinerary_repository import ItineraryRepository
from tripper_api.membership.membership_repository import MembershipRepository
from tripper_api.trip.trip_access_control import TripAccessControl
from tripper_api.trip.trip_command_service import TripCommandService
from tripper_api.trip.trip_guide_reader import TripGuideReader
from tripper_api.trip.trip_repository import TripRepository


def get_trip_command_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> TripCommandService:
    membership_repository = MembershipRepository(session)
    return TripCommandService(
        session,
        TripRepository(session),
        DestinationRepository(session),
        membership_repository,
        TripAccessControl(membership_repository),
        ItineraryRepository(session),
        TripGuideReader(session, membership_repository),
    )
