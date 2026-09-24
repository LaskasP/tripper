from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from tripper_api.auth.auth_model import Account
from tripper_api.core.config import Settings
from tripper_api.destination.destination_model import Destination
from tripper_api.membership.membership_model import TripMembership, TripRole
from tripper_api.membership.membership_repository import MembershipRepository
from tripper_api.trip.trip_model import Trip
from tripper_api.trip.trip_repository import TripRepository

pytestmark = [
    pytest.mark.usefixtures("clean_database"),
    pytest.mark.asyncio(loop_factories=["selector"]),
]


def trip_records() -> tuple[Trip, Destination, TripMembership]:
    trip = Trip(
        id=uuid4(),
        name="Constraint test",
        short_name="Constraint",
        description="",
        start_date=date(2027, 6, 10),
        end_date=date(2027, 6, 17),
    )
    destination = Destination(
        id=uuid4(),
        trip_id=trip.id,
        name="Cyclades",
        timezone="Europe/Athens",
        latitude=None,
        longitude=None,
        position=0,
    )
    membership = TripMembership(
        id=uuid4(),
        trip_id=trip.id,
        account_id=uuid4(),
        role=TripRole.CREATOR,
    )
    return trip, destination, membership


async def test_postgresql_rejects_a_second_creator_from_another_session(
    database_settings: Settings,
) -> None:
    engine = create_async_engine(database_settings.database_url)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    trip, destination, creator = trip_records()
    second_account_id = uuid4()

    async with sessions() as account_session, account_session.begin():
        account_session.add_all(
            [
                Account(
                    id=creator.account_id,
                    issuer="test",
                    subject=str(creator.account_id),
                    email="creator@example.com",
                    display_name="Creator",
                ),
                Account(
                    id=second_account_id,
                    issuer="test",
                    subject=str(second_account_id),
                    email="second@example.com",
                    display_name="Second Creator",
                ),
            ]
        )

    async with sessions() as first_session, first_session.begin():
        await TripRepository(first_session).add(trip, destination)
        await MembershipRepository(first_session).add(creator)

    second_creator = TripMembership(
        id=uuid4(),
        trip_id=trip.id,
        account_id=second_account_id,
        role=TripRole.CREATOR,
    )
    with pytest.raises(IntegrityError):
        async with sessions() as second_session, second_session.begin():
            second_session.add(second_creator)
            await second_session.flush()

    await engine.dispose()


async def test_failed_multi_record_write_rolls_back_the_whole_trip(
    database_settings: Settings,
) -> None:
    engine = create_async_engine(database_settings.database_url)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    trip, destination, creator = trip_records()
    destination.position = -1

    with pytest.raises(IntegrityError):
        async with sessions() as write_session, write_session.begin():
            await TripRepository(write_session).add(trip, destination)
            await MembershipRepository(write_session).add(creator)

    async with sessions() as read_session:
        persisted_trip = await read_session.scalar(
            select(Trip).where(Trip.id == trip.id)
        )

    await engine.dispose()
    assert persisted_trip is None


async def test_postgresql_rejects_a_partial_destination_location(
    database_settings: Settings,
) -> None:
    engine = create_async_engine(database_settings.database_url)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    trip, destination, creator = trip_records()
    destination.latitude = 37.9838

    async with sessions() as account_session, account_session.begin():
        account_session.add(
            Account(
                id=creator.account_id,
                issuer="test",
                subject=str(creator.account_id),
                email="creator@example.com",
                display_name="Creator",
            )
        )

    with pytest.raises(IntegrityError):
        async with sessions() as write_session, write_session.begin():
            await TripRepository(write_session).add(trip, destination)
            await MembershipRepository(write_session).add(creator)

    await engine.dispose()
