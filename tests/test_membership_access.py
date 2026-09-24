import asyncio
from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from tripper_api.auth.auth_model import Account
from tripper_api.core.config import Settings
from tripper_api.destination.destination_model import Destination
from tripper_api.membership.membership_model import TripMembership, TripRole
from tripper_api.membership.membership_repository import MembershipRepository
from tripper_api.trip.trip_command_dependencies import get_trip_command_service
from tripper_api.trip.trip_command_dto import TripDetailsUpdateRequest
from tripper_api.trip.trip_command_errors import TripEditForbiddenError
from tripper_api.trip.trip_model import Trip

pytestmark = [
    pytest.mark.usefixtures("clean_database"),
    pytest.mark.asyncio(loop_factories=["selector"]),
]


async def add_trip_with_participants(
    session: AsyncSession,
) -> tuple[Trip, Destination, TripMembership, TripMembership]:
    creator_id = uuid4()
    participant_id = uuid4()
    trip = Trip(
        id=uuid4(),
        name="Lock ordering",
        short_name="Locking",
        description="",
        start_date=date(2027, 6, 10),
        end_date=date(2027, 6, 17),
    )
    destination = Destination(
        id=uuid4(),
        trip_id=trip.id,
        name="Athens",
        timezone="Europe/Athens",
        position=0,
    )
    creator = TripMembership(
        id=uuid4(),
        trip_id=trip.id,
        account_id=creator_id,
        role=TripRole.CREATOR,
    )
    participant = TripMembership(
        id=uuid4(),
        trip_id=trip.id,
        account_id=participant_id,
        role=TripRole.CONTRIBUTOR,
    )
    session.add_all(
        [
            Account(
                id=creator_id,
                issuer="test",
                subject=str(creator_id),
                email="creator@example.com",
                display_name="Creator",
            ),
            Account(
                id=participant_id,
                issuer="test",
                subject=str(participant_id),
                email="participant@example.com",
                display_name="Participant",
            ),
            trip,
        ]
    )
    await session.flush()
    session.add_all([destination, creator, participant])
    await session.flush()
    return trip, destination, creator, participant


async def test_trip_lock_serializes_current_role_evaluation(
    database_settings: Settings,
) -> None:
    engine = create_async_engine(database_settings.database_url)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with sessions() as setup_session, setup_session.begin():
        trip, _, _, participant = await add_trip_with_participants(setup_session)

    started = asyncio.Event()

    async def read_after_trip_lock() -> TripRole:
        async with sessions() as reader, reader.begin():
            started.set()
            access = await MembershipRepository(reader).lock_trip_and_get_membership(
                trip.id, participant.account_id
            )
            assert access is not None
            return access.role

    async with sessions() as writer, writer.begin():
        writer_access = await MembershipRepository(writer).lock_trip_and_get_membership(
            trip.id, participant.account_id
        )
        assert writer_access is not None
        assert writer_access.role == TripRole.CONTRIBUTOR
        stored_participant = await writer.scalar(
            select(TripMembership).where(TripMembership.id == participant.id)
        )
        assert stored_participant is not None
        stored_participant.role = TripRole.TRAVELLER
        await writer.flush()

        reader_task = asyncio.create_task(read_after_trip_lock())
        await started.wait()
        await asyncio.sleep(0.1)
        assert not reader_task.done()

    assert await asyncio.wait_for(reader_task, timeout=2) == TripRole.TRAVELLER
    await engine.dispose()


async def test_membership_change_rolls_back_with_the_trip_locked_transaction(
    database_settings: Settings,
) -> None:
    engine = create_async_engine(database_settings.database_url)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with sessions() as setup_session, setup_session.begin():
        trip, _, _, participant = await add_trip_with_participants(setup_session)

    with pytest.raises(RuntimeError, match="abort membership change"):
        async with sessions() as writer, writer.begin():
            access = await MembershipRepository(writer).lock_trip_and_get_membership(
                trip.id, participant.account_id
            )
            assert access is not None
            stored_participant = await writer.scalar(
                select(TripMembership).where(TripMembership.id == participant.id)
            )
            assert stored_participant is not None
            stored_participant.role = TripRole.TRAVELLER
            await writer.flush()
            raise RuntimeError("abort membership change")

    async with sessions() as reader:
        role = await MembershipRepository(reader).current_role(
            trip.id, participant.account_id
        )

    await engine.dispose()
    assert role == TripRole.CONTRIBUTOR


async def test_role_change_racing_content_write_uses_the_new_role(
    database_settings: Settings,
) -> None:
    engine = create_async_engine(database_settings.database_url)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with sessions() as setup_session, setup_session.begin():
        trip, destination, creator, participant = await add_trip_with_participants(
            setup_session
        )

    command_started = asyncio.Event()

    async def edit_trip() -> None:
        async with sessions() as command_session:
            command_started.set()
            await get_trip_command_service(command_session).update_details(
                trip_id=trip.id,
                account_id=participant.account_id,
                request=TripDetailsUpdateRequest(
                    starting_revision=1,
                    name="Stale contributor edit",
                    short_name=trip.short_name,
                    description=trip.description,
                    start_date=trip.start_date,
                    end_date=trip.end_date,
                    destinations=[
                        {
                            "id": destination.id,
                            "name": destination.name,
                            "timezone": destination.timezone,
                        }
                    ],
                ),
            )

    async with sessions() as governance_session, governance_session.begin():
        creator_access = await MembershipRepository(
            governance_session
        ).lock_trip_and_get_membership(trip.id, creator.account_id)
        assert creator_access is not None
        stored_participant = await governance_session.scalar(
            select(TripMembership).where(TripMembership.id == participant.id)
        )
        assert stored_participant is not None
        stored_participant.role = TripRole.TRAVELLER
        await governance_session.flush()

        command_task = asyncio.create_task(edit_trip())
        await command_started.wait()
        await asyncio.sleep(0.1)
        assert not command_task.done()

    with pytest.raises(TripEditForbiddenError):
        await asyncio.wait_for(command_task, timeout=2)

    async with sessions() as reader:
        saved_name = await reader.scalar(select(Trip.name).where(Trip.id == trip.id))
        saved_role = await MembershipRepository(reader).current_role(
            trip.id, participant.account_id
        )

    await engine.dispose()
    assert saved_name == "Lock ordering"
    assert saved_role == TripRole.TRAVELLER
