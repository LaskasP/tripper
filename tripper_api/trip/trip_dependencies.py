from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from tripper_api.core.database import get_database_session
from tripper_api.trip.trip_repository import TripRepository
from tripper_api.trip.trip_service import TripService


def get_trip_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> TripService:
    return TripService(session, TripRepository(session))
