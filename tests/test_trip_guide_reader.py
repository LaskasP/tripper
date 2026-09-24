import threading
import time as wall_time
from datetime import date, time
from uuid import UUID, uuid4

import psycopg
import pytest
from sqlalchemy import event
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from tripper_api.auth.auth_model import Account
from tripper_api.core.config import Settings
from tripper_api.destination.destination_model import Destination
from tripper_api.itinerary.itinerary_daily_plan_model import DailyPlan
from tripper_api.itinerary.itinerary_photo_model import Photo
from tripper_api.itinerary.itinerary_stay_model import Stay
from tripper_api.itinerary.itinerary_timeline_model import TimelineEntry
from tripper_api.membership.membership_model import TripMembership, TripRole
from tripper_api.membership.membership_repository import MembershipRepository
from tripper_api.trip.trip_guide_reader import TripGuideReader
from tripper_api.trip.trip_model import Trip

pytestmark = [
    pytest.mark.usefixtures("clean_database"),
    pytest.mark.asyncio(loop_factories=["selector"]),
]


async def seed_guide(database_settings: Settings) -> tuple[UUID, UUID]:
    trip_id = uuid4()
    account_id = uuid4()
    destination_id = uuid4()
    engine = create_async_engine(database_settings.database_url)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with sessions() as session, session.begin():
        session.add_all(
            [
                Account(
                    id=account_id,
                    issuer="test",
                    subject=str(account_id),
                    email="reader@example.com",
                    display_name="Guide Reader",
                ),
                Trip(
                    id=trip_id,
                    name="Coherent trip",
                    short_name="Coherent",
                    description="Before",
                    start_date=date(2027, 6, 10),
                    end_date=date(2027, 6, 11),
                ),
            ]
        )
        await session.flush()
        session.add_all(
            [
                Destination(
                    id=destination_id,
                    trip_id=trip_id,
                    name="Athens",
                    timezone="Europe/Athens",
                    latitude=37.9838,
                    longitude=23.7275,
                    position=0,
                ),
                TripMembership(
                    id=uuid4(),
                    trip_id=trip_id,
                    account_id=account_id,
                    role=TripRole.TRAVELLER,
                ),
            ]
        )
        await session.flush()
        for offset in range(2):
            plan_id = uuid4()
            session.add(
                DailyPlan(
                    id=plan_id,
                    trip_id=trip_id,
                    destination_id=destination_id,
                    date=date(2027, 6, 10 + offset),
                    title=f"Day {offset + 1}",
                    summary="",
                    background_image="",
                )
            )
            await session.flush()
            session.add_all(
                [
                    TimelineEntry(
                        id=uuid4(),
                        daily_plan_id=plan_id,
                        destination_id=None,
                        local_time=time(9),
                        title="Breakfast",
                        description="",
                        location_name=None,
                        latitude=None,
                        longitude=None,
                        position=0,
                    ),
                    Stay(
                        id=uuid4(),
                        daily_plan_id=plan_id,
                        name="Hotel",
                        address="Athens",
                        latitude=None,
                        longitude=None,
                        check_in=time(15),
                        check_out=None,
                        public_listing_url=None,
                        booking_platform=None,
                    ),
                    Photo(
                        id=uuid4(),
                        daily_plan_id=plan_id,
                        url="https://example.com/photo.jpg",
                        caption="Athens",
                        position=0,
                    ),
                ]
            )
    await engine.dispose()
    return trip_id, account_id


async def test_participant_guide_has_bounded_queries_and_serializes_after_session(
    database_settings: Settings,
) -> None:
    trip_id, account_id = await seed_guide(database_settings)
    engine = create_async_engine(database_settings.database_url)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    statements: list[str] = []

    def count_selects(
        _connection: object,
        _cursor: object,
        statement: str,
        _parameters: object,
        _context: object,
        _executemany: bool,
    ) -> None:
        if statement.lstrip().upper().startswith("SELECT"):
            statements.append(statement)

    event.listen(engine.sync_engine, "before_cursor_execute", count_selects)
    async with sessions() as session:
        response = await TripGuideReader(
            session, MembershipRepository(session)
        ).get_participant_guide(trip_id, account_id)
    query_count = len(statements)
    serialized = response.model_dump(mode="json")
    event.remove(engine.sync_engine, "before_cursor_execute", count_selects)
    await engine.dispose()

    content_sql = " ".join(statements[2:8]).lower()
    assert query_count == 14
    assert "for share" in statements[0].lower()
    assert "trip_memberships" in statements[1].lower()
    assert "revision" not in content_sql
    assert "trip_memberships" not in content_sql
    assert "accounts" not in content_sql
    assert "sessions" not in content_sql
    assert serialized["role"] == "traveller"
    assert serialized["roster"] == [
        {"display_name": "Guide Reader", "role": "traveller"}
    ]
    assert [plan["title"] for plan in serialized["daily_plans"]] == [
        "Day 1",
        "Day 2",
    ]
    assert all(
        plan["timeline"][0]["timezone"] == "Europe/Athens"
        for plan in serialized["daily_plans"]
    )


async def test_participant_guide_is_coherent_during_a_concurrent_content_change(
    database_settings: Settings,
) -> None:
    trip_id, account_id = await seed_guide(database_settings)
    engine = create_async_engine(database_settings.database_url)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    root_selected = threading.Event()
    writer_ready = threading.Event()
    writer_attempted = threading.Event()
    writer_done = threading.Event()
    writer_errors: list[BaseException] = []
    root_query_seen = False
    sync_url = (
        make_url(database_settings.database_url)
        .set(drivername="postgresql")
        .render_as_string(hide_password=False)
    )

    def update_content() -> None:
        try:
            with psycopg.connect(sync_url) as connection:
                writer_ready.set()
                if not root_selected.wait(timeout=2):
                    raise TimeoutError("reader did not load the Trip")
                writer_attempted.set()
                connection.execute(
                    "UPDATE trips SET description = 'After' WHERE id = %s",
                    (trip_id,),
                )
                connection.execute(
                    "UPDATE daily_plans SET title = 'Changed' WHERE trip_id = %s",
                    (trip_id,),
                )
                connection.commit()
        except (psycopg.Error, TimeoutError) as error:
            writer_errors.append(error)
        finally:
            writer_done.set()

    def pause_after_root_query(
        _connection: object,
        _cursor: object,
        statement: str,
        _parameters: object,
        _context: object,
        _executemany: bool,
    ) -> None:
        nonlocal root_query_seen
        if root_query_seen or "FROM trips" not in statement:
            return
        root_query_seen = True
        root_selected.set()
        if not writer_attempted.wait(timeout=2):
            raise TimeoutError("writer did not attempt the concurrent change")
        wall_time.sleep(0.2)

    writer = threading.Thread(target=update_content)
    writer.start()
    assert writer_ready.wait(timeout=2)
    event.listen(engine.sync_engine, "after_cursor_execute", pause_after_root_query)
    async with sessions() as session:
        response = await TripGuideReader(
            session, MembershipRepository(session)
        ).get_participant_guide(trip_id, account_id)
    event.remove(engine.sync_engine, "after_cursor_execute", pause_after_root_query)
    writer.join(timeout=2)
    await engine.dispose()

    assert writer_done.is_set()
    assert writer_errors == []
    assert response.description == "Before"
    assert [plan.title for plan in response.daily_plans] == ["Day 1", "Day 2"]
