from collections.abc import AsyncIterator
from datetime import date
from uuid import UUID, uuid4

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
from tripper_api.itinerary.itinerary_photo_dependencies import get_photo_service
from tripper_api.itinerary.itinerary_photo_dto import PhotoCreateRequest
from tripper_api.itinerary.itinerary_photo_errors import (
    PhotoCollectionRevisionConflictError,
)
from tripper_api.membership.membership_repository import MembershipRepository
from tripper_api.trip.trip_command_dependencies import get_trip_command_service
from tripper_api.trip.trip_command_dto import TripCreateRequest
from tripper_api.trip.trip_guide_dto import TripDetailResponse
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


async def create_trip_with_plan(
    sessions: async_sessionmaker[AsyncSession],
) -> tuple[UUID, UUID, TripDetailResponse]:
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

    async with sessions() as command_session:
        trip = await get_trip_command_service(command_session).create(
            account_id=account_id,
            request=TripCreateRequest(
                name="Aegean summer",
                destination="Athens",
                timezone="Europe/Athens",
                start_date=date(2027, 6, 10),
                end_date=date(2027, 6, 17),
            ),
        )
        guide_reader = TripGuideReader(
            command_session, MembershipRepository(command_session)
        )
        guide = await guide_reader.get_participant_guide(trip.id, account_id)
        await get_daily_plan_command_coordinator(command_session).write(
            trip_id=trip.id,
            account_id=account_id,
            plan_date=date(2027, 6, 10),
            request=DailyPlanWriteRequest(
                starting_revision=guide.content_revision,
                destination_id=guide.destinations[0].id,
                title="Arrival",
            ),
        )
        guide = await guide_reader.get_participant_guide(trip.id, account_id)
    return account_id, trip.id, guide


async def test_stale_photo_collection_create_returns_latest_guide_from_other_session(
    sessions: async_sessionmaker[AsyncSession],
) -> None:
    account_id, trip_id, guide = await create_trip_with_plan(sessions)
    plan = guide.daily_plans[0]

    async with sessions() as first_editor:
        saved = await get_photo_service(first_editor).create(
            trip_id=trip_id,
            account_id=account_id,
            plan_id=plan.id,
            request=PhotoCreateRequest(
                starting_revision=plan.photo_revision,
                url="https://images.example/current.jpg",
                caption="Current photo",
            ),
        )

    async with sessions() as stale_editor:
        with pytest.raises(PhotoCollectionRevisionConflictError) as caught:
            await get_photo_service(stale_editor).create(
                trip_id=trip_id,
                account_id=account_id,
                plan_id=plan.id,
                request=PhotoCreateRequest(
                    starting_revision=plan.photo_revision,
                    url="https://images.example/stale.jpg",
                    caption="Stale photo",
                ),
            )

    assert caught.value.latest_values == saved.model_dump(mode="json")


async def test_failed_photo_create_rolls_back_photo_and_all_revisions(
    sessions: async_sessionmaker[AsyncSession],
) -> None:
    account_id, trip_id, guide = await create_trip_with_plan(sessions)
    plan = guide.daily_plans[0]
    maximum_postgresql_integer = 2_147_483_647
    async with sessions() as boundary_session, boundary_session.begin():
        stored_trip = await boundary_session.scalar(
            select(Trip).where(Trip.id == trip_id)
        )
        assert stored_trip is not None
        stored_trip.content_revision = maximum_postgresql_integer

    async with sessions() as failing_session:
        with pytest.raises(DataError):
            await get_photo_service(failing_session).create(
                trip_id=trip_id,
                account_id=account_id,
                plan_id=plan.id,
                request=PhotoCreateRequest(
                    starting_revision=plan.photo_revision,
                    url="https://images.example/must-roll-back.jpg",
                    caption="Must roll back",
                ),
            )

    async with sessions() as reader_session:
        unchanged = await TripGuideReader(
            reader_session, MembershipRepository(reader_session)
        ).get_participant_guide(trip_id, account_id)

    unchanged_plan = unchanged.daily_plans[0]
    assert unchanged_plan.photos == []
    assert unchanged_plan.photo_revision == plan.photo_revision
    assert unchanged.content_revision == maximum_postgresql_integer
