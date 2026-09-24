from collections.abc import AsyncIterator
from dataclasses import dataclass
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
from tripper_api.itinerary.itinerary_daily_plan_dto import (
    DailyPlanResponse,
    DailyPlanRevisionRequest,
    DailyPlanWriteRequest,
)
from tripper_api.itinerary.itinerary_daily_plan_errors import (
    DailyPlanRevisionConflictError,
)
from tripper_api.membership.membership_repository import MembershipRepository
from tripper_api.trip.trip_command_dependencies import get_trip_command_service
from tripper_api.trip.trip_command_dto import TripCreateRequest
from tripper_api.trip.trip_dependencies import get_trip_service
from tripper_api.trip.trip_dto import StayWriteRequest
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


@dataclass(frozen=True)
class _TripScenario:
    account_id: UUID
    trip_id: UUID
    guide: TripDetailResponse


async def create_trip_scenario(
    sessions: async_sessionmaker[AsyncSession],
    *,
    name: str = "Aegean summer",
) -> _TripScenario:
    account_id = uuid4()
    async with sessions() as session, session.begin():
        session.add(
            Account(
                id=account_id,
                issuer="test",
                subject=str(account_id),
                email="creator@example.com",
                display_name="Creator",
            )
        )

    async with sessions() as session:
        trip = await get_trip_command_service(session).create(
            account_id=account_id,
            request=TripCreateRequest(
                name=name,
                destination="Athens",
                timezone="Europe/Athens",
                start_date=date(2027, 6, 10),
                end_date=date(2027, 6, 17),
            ),
        )
        guide = await TripGuideReader(
            session, MembershipRepository(session)
        ).get_participant_guide(trip.id, account_id)
    return _TripScenario(account_id=account_id, trip_id=trip.id, guide=guide)


async def create_daily_plan(
    sessions: async_sessionmaker[AsyncSession], scenario: _TripScenario
) -> DailyPlanResponse:
    async with sessions() as session:
        return await get_daily_plan_command_coordinator(session).write(
            trip_id=scenario.trip_id,
            account_id=scenario.account_id,
            plan_date=date(2027, 6, 10),
            request=DailyPlanWriteRequest(
                starting_revision=scenario.guide.content_revision,
                destination_id=scenario.guide.destinations[0].id,
                title="Arrival",
            ),
        )


async def test_stale_daily_plan_update_returns_only_current_daily_plan(
    sessions: async_sessionmaker[AsyncSession],
) -> None:
    scenario = await create_trip_scenario(sessions)
    created = await create_daily_plan(sessions, scenario)
    original_plan = created

    async with sessions() as first_editor:
        saved = await get_daily_plan_command_coordinator(first_editor).write(
            trip_id=scenario.trip_id,
            account_id=scenario.account_id,
            plan_date=original_plan.date,
            request=DailyPlanWriteRequest(
                id=original_plan.id,
                starting_revision=original_plan.revision,
                destination_id=original_plan.destination_id,
                title="Current title",
            ),
        )

    async with sessions() as stale_editor:
        with pytest.raises(DailyPlanRevisionConflictError) as caught:
            await get_daily_plan_command_coordinator(stale_editor).write(
                trip_id=scenario.trip_id,
                account_id=scenario.account_id,
                plan_date=original_plan.date,
                request=DailyPlanWriteRequest(
                    id=original_plan.id,
                    starting_revision=original_plan.revision,
                    destination_id=original_plan.destination_id,
                    title="Stale title",
                ),
            )

    assert caught.value.current_plan == saved.model_dump(mode="json")
    assert "destinations" not in caught.value.current_plan


async def test_whole_plan_delete_accepts_its_direct_revision_after_child_edit(
    sessions: async_sessionmaker[AsyncSession],
) -> None:
    scenario = await create_trip_scenario(sessions)
    with_plan = await create_daily_plan(sessions, scenario)
    plan = with_plan

    async with sessions() as child_editor:
        with_child = await get_trip_service(child_editor).write_stay(
            trip_id=scenario.trip_id,
            account_id=scenario.account_id,
            plan_id=plan.id,
            request=StayWriteRequest(
                starting_revision=plan.revision,
                name="Harbour Hotel",
            ),
        )

    async with sessions() as plan_editor:
        await get_daily_plan_command_coordinator(plan_editor).clear(
            trip_id=scenario.trip_id,
            account_id=scenario.account_id,
            plan_date=plan.date,
            request=DailyPlanRevisionRequest(starting_revision=plan.revision),
        )

    async with sessions() as reader_session:
        cleared = await TripGuideReader(
            reader_session, MembershipRepository(reader_session)
        ).get_participant_guide(scenario.trip_id, scenario.account_id)

    assert with_child.daily_plans[0].stay is not None
    assert cleared.daily_plans == []
    assert cleared.content_revision == with_child.content_revision + 1


async def test_failed_daily_plan_write_rolls_back_plan_and_trip_revision(
    sessions: async_sessionmaker[AsyncSession],
) -> None:
    scenario = await create_trip_scenario(sessions, name="Revision boundary")
    maximum_postgresql_integer = 2_147_483_647
    async with sessions() as boundary_session, boundary_session.begin():
        stored_trip = await boundary_session.scalar(
            select(Trip).where(Trip.id == scenario.trip_id)
        )
        assert stored_trip is not None
        stored_trip.content_revision = maximum_postgresql_integer

    async with sessions() as failing_session:
        with pytest.raises(DataError):
            await get_daily_plan_command_coordinator(failing_session).write(
                trip_id=scenario.trip_id,
                account_id=scenario.account_id,
                plan_date=date(2027, 6, 10),
                request=DailyPlanWriteRequest(
                    starting_revision=maximum_postgresql_integer,
                    destination_id=scenario.guide.destinations[0].id,
                    title="Must roll back",
                ),
            )

    async with sessions() as reader_session:
        unchanged = await TripGuideReader(
            reader_session, MembershipRepository(reader_session)
        ).get_participant_guide(scenario.trip_id, scenario.account_id)

    assert unchanged.content_revision == maximum_postgresql_integer
    assert unchanged.daily_plans == []
