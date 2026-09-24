from collections.abc import AsyncIterator
from datetime import date
from uuid import uuid4

import pytest
import pytest_asyncio
from asgi_lifespan import LifespanManager
from sqlalchemy import select
from sqlalchemy.exc import DataError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from tripper_api.app import create_app
from tripper_api.auth.auth_model import Account
from tripper_api.core.config import Settings
from tripper_api.core.database import Database
from tripper_api.itinerary.itinerary_daily_plan_dependencies import (
    get_daily_plan_command_coordinator,
)
from tripper_api.itinerary.itinerary_daily_plan_dto import DailyPlanWriteRequest
from tripper_api.itinerary.itinerary_stay_dependencies import get_stay_service
from tripper_api.itinerary.itinerary_stay_dto import StayWriteRequest
from tripper_api.membership.membership_repository import MembershipRepository
from tripper_api.trip.trip_command_dependencies import get_trip_command_service
from tripper_api.trip.trip_command_dto import TripCreateRequest
from tripper_api.trip.trip_guide_reader import TripGuideReader
from tripper_api.trip.trip_model import Trip

pytestmark = [
    pytest.mark.usefixtures("clean_database"),
    pytest.mark.asyncio(loop_factories=["selector"]),
]


@pytest_asyncio.fixture
async def sessions(
    database_settings: Settings,
) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    app = create_app(database_settings)
    async with LifespanManager(app):
        database: Database = app.state.database
        assert database.sessions is not None
        yield database.sessions


async def test_failed_stay_write_rolls_back_stay_and_trip_revision(
    sessions: async_sessionmaker[AsyncSession],
) -> None:
    account_id = uuid4()
    async with sessions() as setup_session, setup_session.begin():
        setup_session.add(
            Account(
                id=account_id,
                issuer="test",
                subject=str(account_id),
                email="creator@example.com",
                display_name="Creator",
            )
        )

    async with sessions() as trip_session:
        trip = await get_trip_command_service(trip_session).create(
            account_id=account_id,
            request=TripCreateRequest(
                name="Revision boundary",
                destination="Athens",
                timezone="Europe/Athens",
                start_date=date(2027, 6, 10),
                end_date=date(2027, 6, 17),
            ),
        )
        guide = await TripGuideReader(
            trip_session, MembershipRepository(trip_session)
        ).get_participant_guide(trip.id, account_id)
        plan = await get_daily_plan_command_coordinator(trip_session).write(
            trip_id=trip.id,
            account_id=account_id,
            plan_date=date(2027, 6, 10),
            request=DailyPlanWriteRequest(
                starting_revision=guide.content_revision,
                destination_id=guide.destinations[0].id,
                title="Arrival",
            ),
        )

    maximum_postgresql_integer = 2_147_483_647
    async with sessions() as boundary_session, boundary_session.begin():
        stored_trip = await boundary_session.scalar(
            select(Trip).where(Trip.id == trip.id)
        )
        assert stored_trip is not None
        stored_trip.content_revision = maximum_postgresql_integer

    async with sessions() as failing_session:
        with pytest.raises(DataError):
            await get_stay_service(failing_session).write(
                trip_id=trip.id,
                account_id=account_id,
                plan_id=plan.id,
                request=StayWriteRequest(
                    starting_revision=plan.revision,
                    name="Must roll back",
                ),
            )

    async with sessions() as reader_session:
        unchanged = await TripGuideReader(
            reader_session, MembershipRepository(reader_session)
        ).get_participant_guide(trip.id, account_id)

    assert unchanged.content_revision == maximum_postgresql_integer
    assert unchanged.daily_plans[0].stay is None
