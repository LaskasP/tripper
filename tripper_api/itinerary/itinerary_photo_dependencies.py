from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from tripper_api.core.database import get_database_session
from tripper_api.itinerary.itinerary_photo_repository import PhotoRepository
from tripper_api.itinerary.itinerary_photo_service import PhotoService
from tripper_api.membership.membership_repository import MembershipRepository
from tripper_api.trip.trip_guide_reader import TripGuideReader


def get_photo_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> PhotoService:
    membership_repository = MembershipRepository(session)
    return PhotoService(
        session,
        PhotoRepository(session),
        membership_repository,
        TripGuideReader(session, membership_repository),
    )
