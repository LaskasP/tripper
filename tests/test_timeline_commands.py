import asyncio
from collections.abc import AsyncIterator
from datetime import date, time
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
from tripper_api.itinerary.itinerary_timeline_dependencies import get_timeline_service
from tripper_api.itinerary.itinerary_timeline_dto import (
    TimelineEntryCreateRequest,
    TimelineEntryMoveRequest,
    TimelineEntryUpdateRequest,
)
from tripper_api.itinerary.itinerary_timeline_errors import (
    TimelineCollectionRevisionConflictError,
    TimelineEntryRevisionConflictError,
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


async def create_second_plan(
    sessions: async_sessionmaker[AsyncSession],
    account_id: UUID,
    trip_id: UUID,
    guide: TripDetailResponse,
) -> TripDetailResponse:
    async with sessions() as command_session:
        await get_daily_plan_command_coordinator(command_session).write(
            trip_id=trip_id,
            account_id=account_id,
            plan_date=date(2027, 6, 11),
            request=DailyPlanWriteRequest(
                starting_revision=guide.content_revision,
                destination_id=guide.destinations[0].id,
                title="Athens",
            ),
        )
        return await TripGuideReader(
            command_session, MembershipRepository(command_session)
        ).get_participant_guide(trip_id, account_id)


async def create_entry(
    sessions: async_sessionmaker[AsyncSession],
    *,
    account_id: UUID,
    trip_id: UUID,
    plan_id: UUID,
    starting_revision: int,
    destination_id: UUID,
    title: str,
) -> TripDetailResponse:
    async with sessions() as command_session:
        return await get_timeline_service(command_session).create(
            trip_id=trip_id,
            account_id=account_id,
            plan_id=plan_id,
            request=TimelineEntryCreateRequest(
                starting_revision=starting_revision,
                destination_id=destination_id,
                time=time(9),
                title=title,
            ),
        )


async def test_stale_timeline_entry_update_returns_latest_guide_from_other_session(
    sessions: async_sessionmaker[AsyncSession],
) -> None:
    account_id, trip_id, guide = await create_trip_with_plan(sessions)
    plan = guide.daily_plans[0]
    destination_id = guide.destinations[0].id

    async with sessions() as create_session:
        created = await get_timeline_service(create_session).create(
            trip_id=trip_id,
            account_id=account_id,
            plan_id=plan.id,
            request=TimelineEntryCreateRequest(
                starting_revision=plan.timeline_revision,
                destination_id=destination_id,
                time=time(9),
                title="Coffee",
            ),
        )
    entry = created.daily_plans[0].timeline[0]

    async with sessions() as first_editor:
        saved = await get_timeline_service(first_editor).update(
            trip_id=trip_id,
            account_id=account_id,
            plan_id=plan.id,
            entry_id=entry.id,
            request=TimelineEntryUpdateRequest(
                starting_revision=entry.revision,
                destination_id=destination_id,
                time=time(9),
                title="Current coffee",
            ),
        )

    async with sessions() as stale_editor:
        with pytest.raises(TimelineEntryRevisionConflictError) as caught:
            await get_timeline_service(stale_editor).update(
                trip_id=trip_id,
                account_id=account_id,
                plan_id=plan.id,
                entry_id=entry.id,
                request=TimelineEntryUpdateRequest(
                    starting_revision=entry.revision,
                    destination_id=destination_id,
                    time=time(9),
                    title="Stale coffee",
                ),
            )

    assert caught.value.latest_values == saved.model_dump(mode="json")


async def test_stale_timeline_collection_create_returns_latest_guide_from_other_session(
    sessions: async_sessionmaker[AsyncSession],
) -> None:
    account_id, trip_id, guide = await create_trip_with_plan(sessions)
    plan = guide.daily_plans[0]
    destination_id = guide.destinations[0].id
    saved = await create_entry(
        sessions,
        account_id=account_id,
        trip_id=trip_id,
        plan_id=plan.id,
        starting_revision=plan.timeline_revision,
        destination_id=destination_id,
        title="Current entry",
    )

    async with sessions() as stale_editor:
        with pytest.raises(TimelineCollectionRevisionConflictError) as caught:
            await get_timeline_service(stale_editor).create(
                trip_id=trip_id,
                account_id=account_id,
                plan_id=plan.id,
                request=TimelineEntryCreateRequest(
                    starting_revision=plan.timeline_revision,
                    destination_id=destination_id,
                    time=time(10),
                    title="Stale entry",
                ),
            )

    assert caught.value.latest_values == saved.model_dump(mode="json")


async def test_move_preserves_identity_and_advances_each_affected_revision_once(
    sessions: async_sessionmaker[AsyncSession],
) -> None:
    account_id, trip_id, guide = await create_trip_with_plan(sessions)
    guide = await create_second_plan(sessions, account_id, trip_id, guide)
    source, target = guide.daily_plans
    guide = await create_entry(
        sessions,
        account_id=account_id,
        trip_id=trip_id,
        plan_id=source.id,
        starting_revision=source.timeline_revision,
        destination_id=guide.destinations[0].id,
        title="Museum",
    )
    source, target = guide.daily_plans
    entry = source.timeline[0]
    content_revision = guide.content_revision

    async with sessions() as move_session:
        moved = await get_timeline_service(move_session).move(
            trip_id=trip_id,
            account_id=account_id,
            source_plan_id=source.id,
            entry_id=entry.id,
            request=TimelineEntryMoveRequest(
                source_starting_revision=source.timeline_revision,
                target_plan_id=target.id,
                target_starting_revision=target.timeline_revision,
            ),
        )

    moved_source = next(plan for plan in moved.daily_plans if plan.id == source.id)
    moved_target = next(plan for plan in moved.daily_plans if plan.id == target.id)
    assert moved_source.timeline == []
    assert [(item.id, item.revision) for item in moved_target.timeline] == [
        (entry.id, entry.revision)
    ]
    assert moved_source.timeline_revision == source.timeline_revision + 1
    assert moved_target.timeline_revision == target.timeline_revision + 1
    assert moved.content_revision == content_revision + 1


async def test_opposite_direction_moves_use_stable_lock_order_without_deadlock(
    sessions: async_sessionmaker[AsyncSession],
) -> None:
    account_id, trip_id, guide = await create_trip_with_plan(sessions)
    guide = await create_second_plan(sessions, account_id, trip_id, guide)
    first, second = guide.daily_plans
    guide = await create_entry(
        sessions,
        account_id=account_id,
        trip_id=trip_id,
        plan_id=first.id,
        starting_revision=first.timeline_revision,
        destination_id=guide.destinations[0].id,
        title="First",
    )
    first, second = guide.daily_plans
    guide = await create_entry(
        sessions,
        account_id=account_id,
        trip_id=trip_id,
        plan_id=second.id,
        starting_revision=second.timeline_revision,
        destination_id=guide.destinations[0].id,
        title="Second",
    )
    first, second = guide.daily_plans

    async def move(
        source_id: UUID,
        target_id: UUID,
        entry_id: UUID,
        source_revision: int,
        target_revision: int,
    ) -> TripDetailResponse:
        async with sessions() as move_session:
            return await get_timeline_service(move_session).move(
                trip_id=trip_id,
                account_id=account_id,
                source_plan_id=source_id,
                entry_id=entry_id,
                request=TimelineEntryMoveRequest(
                    source_starting_revision=source_revision,
                    target_plan_id=target_id,
                    target_starting_revision=target_revision,
                ),
            )

    results = await asyncio.wait_for(
        asyncio.gather(
            move(
                first.id,
                second.id,
                first.timeline[0].id,
                first.timeline_revision,
                second.timeline_revision,
            ),
            move(
                second.id,
                first.id,
                second.timeline[0].id,
                second.timeline_revision,
                first.timeline_revision,
            ),
            return_exceptions=True,
        ),
        timeout=5,
    )

    assert sum(isinstance(result, TripDetailResponse) for result in results) == 1
    assert (
        sum(
            isinstance(result, TimelineCollectionRevisionConflictError)
            for result in results
        )
        == 1
    )


async def test_failed_move_rolls_back_entry_and_all_revisions(
    sessions: async_sessionmaker[AsyncSession],
) -> None:
    account_id, trip_id, guide = await create_trip_with_plan(sessions)
    guide = await create_second_plan(sessions, account_id, trip_id, guide)
    source, target = guide.daily_plans
    guide = await create_entry(
        sessions,
        account_id=account_id,
        trip_id=trip_id,
        plan_id=source.id,
        starting_revision=source.timeline_revision,
        destination_id=guide.destinations[0].id,
        title="Must stay put",
    )
    source, target = guide.daily_plans
    entry = source.timeline[0]
    maximum_postgresql_integer = 2_147_483_647
    async with sessions() as boundary_session, boundary_session.begin():
        stored_trip = await boundary_session.scalar(
            select(Trip).where(Trip.id == trip_id)
        )
        assert stored_trip is not None
        stored_trip.content_revision = maximum_postgresql_integer

    async with sessions() as failing_session:
        with pytest.raises(DataError):
            await get_timeline_service(failing_session).move(
                trip_id=trip_id,
                account_id=account_id,
                source_plan_id=source.id,
                entry_id=entry.id,
                request=TimelineEntryMoveRequest(
                    source_starting_revision=source.timeline_revision,
                    target_plan_id=target.id,
                    target_starting_revision=target.timeline_revision,
                ),
            )

    async with sessions() as reader_session:
        unchanged = await TripGuideReader(
            reader_session, MembershipRepository(reader_session)
        ).get_participant_guide(trip_id, account_id)

    unchanged_source = next(
        plan for plan in unchanged.daily_plans if plan.id == source.id
    )
    unchanged_target = next(
        plan for plan in unchanged.daily_plans if plan.id == target.id
    )
    assert [item.id for item in unchanged_source.timeline] == [entry.id]
    assert unchanged_target.timeline == []
    assert unchanged_source.timeline_revision == source.timeline_revision
    assert unchanged_target.timeline_revision == target.timeline_revision
    assert unchanged.content_revision == maximum_postgresql_integer
