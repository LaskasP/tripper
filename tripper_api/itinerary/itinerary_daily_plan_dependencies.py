from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from tripper_api.core.database import get_database_session
from tripper_api.destination.destination_repository import DestinationRepository
from tripper_api.itinerary.itinerary_daily_plan_coordinator import (
    DailyPlanCommandCoordinator,
)
from tripper_api.itinerary.itinerary_daily_plan_service import DailyPlanService
from tripper_api.itinerary.itinerary_repository import ItineraryRepository
from tripper_api.membership.membership_repository import MembershipRepository
from tripper_api.trip.trip_access_control import TripAccessControl


def get_daily_plan_command_coordinator(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> DailyPlanCommandCoordinator:
    membership_repository = MembershipRepository(session)
    itinerary_repository = ItineraryRepository(session)
    return DailyPlanCommandCoordinator(
        session,
        DailyPlanService(itinerary_repository),
        DestinationRepository(session),
        TripAccessControl(membership_repository),
    )
