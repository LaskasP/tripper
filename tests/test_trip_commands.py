from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from tripper_api.auth.auth_model import Account
from tripper_api.core.config import Settings
from tripper_api.destination.destination_model import Destination
from tripper_api.membership.membership_model import TripMembership
from tripper_api.membership.membership_repository import MembershipRepository
from tripper_api.trip.trip_command_dependencies import get_trip_command_service
from tripper_api.trip.trip_command_dto import (
    TripCreateRequest,
    TripDetailsUpdateRequest,
)
from tripper_api.trip.trip_guide_reader import TripGuideReader
from tripper_api.trip.trip_model import Trip

pytestmark = [
    pytest.mark.usefixtures("clean_database"),
    pytest.mark.asyncio(loop_factories=["selector"]),
]


async def test_trip_creation_rolls_back_every_capability_write_on_failure(
    database_settings: Settings,
) -> None:
    engine = create_async_engine(database_settings.database_url)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    missing_account_id = uuid4()

    async with sessions() as session:
        service = get_trip_command_service(session)
        with pytest.raises(IntegrityError):
            await service.create(
                account_id=missing_account_id,
                request=TripCreateRequest(
                    name="Atomic Trip",
                    destination="Athens",
                    timezone="Europe/Athens",
                    start_date=date(2027, 6, 10),
                    end_date=date(2027, 6, 17),
                ),
            )

    async with sessions() as session:
        counts = [
            await session.scalar(select(func.count()).select_from(model))
            for model in (Trip, Destination, TripMembership)
        ]

    await engine.dispose()
    assert counts == [0, 0, 0]


async def test_trip_details_command_returns_the_focused_reader_response(
    database_settings: Settings,
) -> None:
    engine = create_async_engine(database_settings.database_url)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
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
        service = get_trip_command_service(session)
        created = await service.create(
            account_id=account_id,
            request=TripCreateRequest(
                name="Greek Islands",
                destination="Cyclades",
                timezone="Europe/Athens",
                start_date=date(2027, 6, 10),
                end_date=date(2027, 6, 17),
            ),
        )
        before = await TripGuideReader(
            session, MembershipRepository(session)
        ).get_participant_guide(created.id, account_id)
        updated = await service.update_details(
            trip_id=created.id,
            account_id=account_id,
            request=TripDetailsUpdateRequest(
                starting_revision=before.revision,
                name="Aegean summer",
                short_name="Aegean",
                description="Athens first, then the islands.",
                start_date=date(2027, 6, 8),
                end_date=date(2027, 6, 19),
                destinations=[
                    {"name": "Athens", "timezone": "Europe/Athens"},
                    {
                        "id": before.destinations[0].id,
                        "name": "Cyclades",
                        "timezone": "Europe/Athens",
                    },
                ],
            ),
        )

    await engine.dispose()
    assert updated.name == "Aegean summer"
    assert updated.destination == "Athens"
    assert [destination.name for destination in updated.destinations] == [
        "Athens",
        "Cyclades",
    ]
    assert updated.revision == before.revision + 1
    assert updated.content_revision == before.content_revision + 1
