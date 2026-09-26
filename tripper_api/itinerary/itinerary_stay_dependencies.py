from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from tripper_api.core.database import get_database_session
from tripper_api.itinerary.itinerary_repository import ItineraryRepository
from tripper_api.itinerary.itinerary_stay_repository import StayRepository
from tripper_api.itinerary.itinerary_stay_service import StayService
from tripper_api.membership.membership_repository import MembershipRepository
from tripper_api.trip.trip_access_control import TripAccessControl
from tripper_api.trip.trip_guide_reader import TripGuideReader


def get_stay_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> StayService:
    membership_repository = MembershipRepository(session)
    return StayService(
        session,
        ItineraryRepository(session),
        StayRepository(session),
        TripAccessControl(membership_repository),
        TripGuideReader(session, membership_repository),
    )
