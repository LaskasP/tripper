from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from tripper_api.core.database import get_database_session
from tripper_api.membership.membership_repository import MembershipRepository
from tripper_api.trip.trip_guide_reader import TripGuideReader


def get_trip_guide_reader(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> TripGuideReader:
    return TripGuideReader(session, MembershipRepository(session))
