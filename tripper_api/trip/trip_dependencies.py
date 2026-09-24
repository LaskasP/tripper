from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from tripper_api.core.database import get_database_session
from tripper_api.membership.membership_repository import MembershipRepository
from tripper_api.trip.trip_guide_reader import TripGuideReader
from tripper_api.trip.trip_repository import TripRepository
from tripper_api.trip.trip_service import TripService


def get_trip_guide_reader(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> TripGuideReader:
    return TripGuideReader(session, MembershipRepository(session))


def get_trip_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> TripService:
    membership_repository = MembershipRepository(session)
    return TripService(
        session,
        TripRepository(session),
        membership_repository,
        TripGuideReader(session, membership_repository),
    )
