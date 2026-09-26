import asyncio
from uuid import UUID

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from tests.test_trips_api import (
    ALEX_ID,
    JAMIE_ID,
    TRIP,
    add_daily_plan,
    add_participant,
    app_client,
)
from tripper_api.core.config import Settings

pytestmark = [
    pytest.mark.usefixtures("clean_database"),
    pytest.mark.asyncio(loop_factories=["selector"]),
]


async def _publication_ready_trip(
    database_settings: Settings,
) -> tuple[str, str]:
    async for client, _ in app_client(database_settings, {"id": ALEX_ID}):
        created = await client.post("/api/trips", json=TRIP)
        trip_id = created.json()["id"]
        detail = (await client.get(f"/api/trips/{trip_id}")).json()
        await add_daily_plan(
            database_settings,
            trip_id=trip_id,
            destination_id=detail["destinations"][0]["id"],
            plan_date=detail["start_date"],
        )
    return trip_id, detail["destinations"][0]["id"]


async def _membership_count(database_settings: Settings, trip_id: str) -> int:
    engine = create_async_engine(database_settings.database_url)
    async with engine.connect() as connection:
        count = await connection.scalar(
            text("SELECT count(*) FROM trip_memberships WHERE trip_id = :trip_id"),
            {"trip_id": UUID(trip_id)},
        )
    await engine.dispose()
    assert count is not None
    return count


async def test_creator_publishes_an_anonymous_data_minimized_guide(
    database_settings: Settings,
) -> None:
    trip_id, _ = await _publication_ready_trip(database_settings)
    await add_participant(
        database_settings,
        trip_id=trip_id,
        account_id=JAMIE_ID,
        display_name="Private Participant",
        role="traveller",
    )

    async for creator, _ in app_client(database_settings, {"id": ALEX_ID}):
        before = await creator.get(f"/api/trips/{trip_id}/publication")
        published = await creator.post(
            f"/api/trips/{trip_id}/publication",
            json={"starting_revision": before.json()["revision"]},
        )
        async for anonymous, _ in app_client(database_settings):
            public = await anonymous.get(
                f"/api/public-guides/{published.json()['public_token']}"
            )

    assert before.json() == {
        "is_published": False,
        "public_token": None,
        "revision": 1,
    }
    assert published.status_code == 200
    assert published.json()["is_published"] is True
    assert published.json()["revision"] == 2
    assert public.status_code == 200
    body = public.json()
    assert body["name"] == TRIP["name"]
    assert body["daily_plans"][0]["title"] == "Planned day"
    serialized = public.text.lower()
    for private_name in (
        "roster",
        "role",
        "revision",
        "account",
        "session",
        "invitation",
        "ownership",
        "membership",
        "private participant",
    ):
        assert private_name not in serialized
    assert await _membership_count(database_settings, trip_id) == 2


async def test_publish_requires_a_populated_plan_and_creator_role(
    database_settings: Settings,
) -> None:
    async for creator, _ in app_client(database_settings, {"id": ALEX_ID}):
        trip_id = (await creator.post("/api/trips", json=TRIP)).json()["id"]
        detail = (await creator.get(f"/api/trips/{trip_id}")).json()
        rejected = await creator.post(
            f"/api/trips/{trip_id}/publication",
            json={"starting_revision": 1},
        )
    blank_plan_id = await add_daily_plan(
        database_settings,
        trip_id=trip_id,
        destination_id=detail["destinations"][0]["id"],
        plan_date=detail["start_date"],
    )
    engine = create_async_engine(database_settings.database_url)
    async with engine.begin() as connection:
        await connection.execute(
            text("UPDATE daily_plans SET title = '   ' WHERE id = :plan_id"),
            {"plan_id": blank_plan_id},
        )
    await engine.dispose()
    async for creator, _ in app_client(database_settings, {"id": ALEX_ID}):
        blank_rejected = await creator.post(
            f"/api/trips/{trip_id}/publication",
            json={"starting_revision": 1},
        )
    engine = create_async_engine(database_settings.database_url)
    async with engine.begin() as connection:
        await connection.execute(
            text("UPDATE daily_plans SET title = 'Day' WHERE id = :plan_id"),
            {"plan_id": blank_plan_id},
        )
        await connection.execute(
            text(
                "UPDATE destinations SET timezone = 'Mars/Olympus' "
                "WHERE trip_id = :trip_id"
            ),
            {"trip_id": UUID(trip_id)},
        )
    await engine.dispose()
    async for creator, _ in app_client(database_settings, {"id": ALEX_ID}):
        invalid_metadata = await creator.post(
            f"/api/trips/{trip_id}/publication",
            json={"starting_revision": 1},
        )
    await add_participant(
        database_settings,
        trip_id=trip_id,
        account_id=JAMIE_ID,
        display_name="Contributor",
        role="contributor",
    )
    async for contributor, _ in app_client(database_settings, {"id": JAMIE_ID}):
        hidden = await contributor.get(f"/api/trips/{trip_id}/publication")
        forbidden = await contributor.post(
            f"/api/trips/{trip_id}/publication",
            json={"starting_revision": 1},
        )

    assert rejected.status_code == 409
    assert rejected.json()["error"]["code"] == "trip_not_ready_to_publish"
    assert blank_rejected.status_code == 409
    assert blank_rejected.json()["error"]["code"] == "trip_not_ready_to_publish"
    assert invalid_metadata.status_code == 409
    assert invalid_metadata.json()["error"]["code"] == "trip_not_ready_to_publish"
    assert hidden.status_code == 403
    assert forbidden.status_code == 403


async def test_unpublish_and_rotation_invalidate_public_access(
    database_settings: Settings,
) -> None:
    trip_id, _ = await _publication_ready_trip(database_settings)

    async for creator, _ in app_client(database_settings, {"id": ALEX_ID}):
        published = await creator.post(
            f"/api/trips/{trip_id}/publication",
            json={"starting_revision": 1},
        )
        old_token = published.json()["public_token"]
        rotated = await creator.post(
            f"/api/trips/{trip_id}/publication/rotate",
            json={"starting_revision": published.json()["revision"]},
        )
        new_token = rotated.json()["public_token"]
        async for anonymous, _ in app_client(database_settings):
            old_link = await anonymous.get(f"/api/public-guides/{old_token}")
            new_link = await anonymous.get(f"/api/public-guides/{new_token}")
        unpublished = await creator.request(
            "DELETE",
            f"/api/trips/{trip_id}/publication",
            json={"starting_revision": rotated.json()["revision"]},
        )
        async for anonymous, _ in app_client(database_settings):
            disabled = await anonymous.get(f"/api/public-guides/{new_token}")

    assert new_token != old_token
    assert old_link.status_code == 404
    assert new_link.status_code == 200
    assert unpublished.json() == {
        "is_published": False,
        "public_token": new_token,
        "revision": 4,
    }
    assert disabled.status_code == 404
    assert (
        old_link.json()
        == disabled.json()
        == {"error": {"code": "trip_not_found", "message": "Trip not found"}}
    )


async def test_stale_publication_change_is_rejected_atomically(
    database_settings: Settings,
) -> None:
    trip_id, _ = await _publication_ready_trip(database_settings)

    async for creator, _ in app_client(database_settings, {"id": ALEX_ID}):
        published = await creator.post(
            f"/api/trips/{trip_id}/publication",
            json={"starting_revision": 1},
        )
        rejected = await creator.post(
            f"/api/trips/{trip_id}/publication/rotate",
            json={"starting_revision": 1},
        )
        current = await creator.get(f"/api/trips/{trip_id}/publication")

    assert rejected.status_code == 409
    assert rejected.json()["error"]["code"] == "publication_revision_conflict"
    assert current.json() == published.json()


async def test_concurrent_public_link_changes_allow_exactly_one_winner(
    database_settings: Settings,
) -> None:
    trip_id, _ = await _publication_ready_trip(database_settings)
    async for setup, _ in app_client(database_settings, {"id": ALEX_ID}):
        published = await setup.post(
            f"/api/trips/{trip_id}/publication",
            json={"starting_revision": 1},
        )

    async for first, _ in app_client(database_settings, {"id": ALEX_ID}):
        async for second, _ in app_client(database_settings, {"id": ALEX_ID}):
            responses = await asyncio.gather(
                first.post(
                    f"/api/trips/{trip_id}/publication/rotate",
                    json={"starting_revision": published.json()["revision"]},
                ),
                second.request(
                    "DELETE",
                    f"/api/trips/{trip_id}/publication",
                    json={"starting_revision": published.json()["revision"]},
                ),
            )

    assert sorted(response.status_code for response in responses) == [200, 409]
