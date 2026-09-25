from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from tripper_api.core.database import get_database_session
from tripper_api.destination.destination_repository import DestinationRepository
from tripper_api.itinerary.itinerary_timeline_repository import TimelineRepository
from tripper_api.itinerary.itinerary_timeline_service import TimelineService
from tripper_api.membership.membership_repository import MembershipRepository
from tripper_api.trip.trip_guide_reader import TripGuideReader


def get_timeline_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> TimelineService:
    membership_repository = MembershipRepository(session)
    return TimelineService(
        session,
        TimelineRepository(session),
        DestinationRepository(session),
        membership_repository,
        TripGuideReader(session, membership_repository),
    )
