import asyncio
from collections.abc import AsyncIterator
from uuid import UUID, uuid4

import pytest
from asgi_lifespan import LifespanManager
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from tripper_api.app import create_app
from tripper_api.core.config import Settings
from tripper_api.core.security import AuthenticatedUser, require_current_user

pytestmark = [
    pytest.mark.usefixtures("clean_database"),
    pytest.mark.asyncio(loop_factories=["selector"]),
]


TRIP = {
    "name": "Greek Islands 2027",
    "destination": "Cyclades",
    "short_name": "Greek Islands",
    "description": "A week through the Cyclades",
    "timezone": "Europe/Athens",
    "location": {"lat": 37.4467, "lng": 25.3289},
    "start_date": "2027-06-10",
    "end_date": "2027-06-17",
}

ALEX_ID = "a7bff584-bfcd-4d4a-86f8-ece48870e67a"
JAMIE_ID = "83c801db-7558-4f93-bb03-6025479920fc"
MORGAN_ID = "2a385a2e-8800-4e45-91ea-cbec7e264876"


async def app_client(
    settings: Settings,
    user: dict[str, str] | None = None,
) -> AsyncIterator[tuple[AsyncClient, FastAPI]]:
    if user is not None:
        engine = create_async_engine(settings.database_url)
        async with engine.begin() as connection:
            await connection.execute(
                text(
                    "INSERT INTO accounts (id, issuer, subject, email, display_name) "
                    "VALUES (:id, 'test', :subject, 'test@example.com', 'Test User') "
                    "ON CONFLICT (id) DO NOTHING"
                ),
                {"id": UUID(user["id"]), "subject": user["id"]},
            )
        await engine.dispose()
    app = create_app(settings)
    if user is not None:
        app.dependency_overrides[require_current_user] = lambda: AuthenticatedUser(
            id=UUID(user["id"]),
            session_id=UUID("00000000-0000-0000-0000-000000000001"),
            email="test@example.com",
            display_name="Test User",
        )

    async with (
        LifespanManager(app),
        AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False),
            base_url="http://test",
        ) as client,
    ):
        yield client, app


async def add_participant(
    settings: Settings,
    *,
    trip_id: str,
    account_id: str,
    display_name: str,
    role: str,
) -> None:
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as connection:
        await connection.execute(
            text(
                "INSERT INTO accounts (id, issuer, subject, email, display_name) "
                "VALUES (:account_id, 'test', :subject, :email, :display_name)"
            ),
            {
                "account_id": UUID(account_id),
                "subject": account_id,
                "email": f"{account_id}@example.com",
                "display_name": display_name,
            },
        )
        await connection.execute(
            text(
                "INSERT INTO trip_memberships (id, trip_id, account_id, role) "
                "VALUES (:id, :trip_id, :account_id, :role)"
            ),
            {
                "id": uuid4(),
                "trip_id": UUID(trip_id),
                "account_id": UUID(account_id),
                "role": role,
            },
        )
    await engine.dispose()


async def remove_participant(
    settings: Settings, *, trip_id: str, account_id: str
) -> None:
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as connection:
        await connection.execute(
            text(
                "DELETE FROM trip_memberships "
                "WHERE trip_id = :trip_id AND account_id = :account_id"
            ),
            {"trip_id": UUID(trip_id), "account_id": UUID(account_id)},
        )
    await engine.dispose()


async def add_daily_plan(
    settings: Settings,
    *,
    trip_id: str,
    destination_id: str,
    plan_date: str,
) -> UUID:
    plan_id = uuid4()
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as connection:
        await connection.execute(
            text(
                "INSERT INTO daily_plans "
                "(id, trip_id, destination_id, date, title, summary, background_image) "
                "VALUES (:id, :trip_id, :destination_id, :date, 'Planned day', '', '')"
            ),
            {
                "id": plan_id,
                "trip_id": UUID(trip_id),
                "destination_id": UUID(destination_id),
                "date": plan_date,
            },
        )
    await engine.dispose()
    return plan_id


async def add_timeline_entry(
    settings: Settings,
    *,
    daily_plan_id: UUID,
    destination_id: str,
) -> None:
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as connection:
        await connection.execute(
            text(
                "INSERT INTO timeline_entries "
                "(id, daily_plan_id, destination_id, local_time, title, description, "
                "position) VALUES (:id, :daily_plan_id, :destination_id, "
                "'09:00', 'Athens stop', '', 0)"
            ),
            {
                "id": uuid4(),
                "daily_plan_id": daily_plan_id,
                "destination_id": UUID(destination_id),
            },
        )
    await engine.dispose()


async def test_signed_in_user_creates_trip_and_finds_it_in_my_trips(
    database_settings: Settings,
) -> None:
    user = {"id": ALEX_ID}
    async for client, _ in app_client(database_settings, user):
        created = await client.post("/api/trips", json=TRIP)
        listed = await client.get("/api/me/trips")

    assert created.status_code == 201
    assert listed.status_code == 200
    assert listed.json() == [
        {
            "id": created.json()["id"],
            "name": "Greek Islands 2027",
            "destination": "Cyclades",
            "short_name": "Greek Islands",
            "start_date": "2027-06-10",
            "end_date": "2027-06-17",
            "role": "creator",
        }
    ]


async def test_signed_in_user_can_create_multiple_independent_trips(
    database_settings: Settings,
) -> None:
    second_trip = {
        **TRIP,
        "name": "Japan 2028",
        "destination": "Tokyo",
        "short_name": "Japan",
        "start_date": "2028-04-01",
        "end_date": "2028-04-03",
    }

    async for client, _ in app_client(database_settings, {"id": ALEX_ID}):
        first = await client.post("/api/trips", json=TRIP)
        second = await client.post("/api/trips", json=second_trip)
        listed = await client.get("/api/me/trips")

    assert [first.status_code, second.status_code, listed.status_code] == [
        201,
        201,
        200,
    ]
    assert {(trip["name"], trip["role"]) for trip in listed.json()} == {
        ("Greek Islands 2027", "creator"),
        ("Japan 2028", "creator"),
    }
    assert first.json()["id"] != second.json()["id"]


async def test_trip_creation_rejects_client_supplied_creator_and_role(
    database_settings: Settings,
) -> None:
    untrusted_trip = {**TRIP, "creatorId": JAMIE_ID, "role": "creator"}

    async for client, _ in app_client(database_settings, {"id": ALEX_ID}):
        response = await client.post("/api/trips", json=untrusted_trip)
        listed = await client.get("/api/me/trips")

    assert response.status_code == 422
    assert response.json() == {
        "error": {
            "code": "validation_error",
            "message": "Request validation failed",
        }
    }
    assert listed.json() == []


async def test_trip_creation_allows_optional_details_to_be_omitted(
    database_settings: Settings,
) -> None:
    minimal_trip = {
        "name": "Athens weekend",
        "destination": "Athens",
        "timezone": "Europe/Athens",
        "start_date": "2027-09-03",
        "end_date": "2027-09-05",
    }

    async for client, _ in app_client(database_settings, {"id": ALEX_ID}):
        response = await client.post("/api/trips", json=minimal_trip)
        detail = await client.get(f"/api/trips/{response.json()['id']}")

    assert response.status_code == 201
    assert detail.status_code == 200
    assert detail.json()["short_name"] == ""
    assert detail.json()["description"] == ""
    assert detail.json()["location"] is None


@pytest.mark.parametrize(
    ("field", "value"),
    [("name", "   "), ("destination", "\t"), ("timezone", "Mars/Olympus")],
)
async def test_trip_creation_rejects_invalid_required_metadata(
    database_settings: Settings,
    field: str,
    value: str,
) -> None:
    invalid_trip = {**TRIP, field: value}

    async for client, _ in app_client(database_settings, {"id": ALEX_ID}):
        response = await client.post("/api/trips", json=invalid_trip)

    assert response.status_code == 422


async def test_trip_management_requires_authentication(
    database_settings: Settings,
) -> None:
    async for client, _ in app_client(database_settings):
        create_response = await client.post("/api/trips", json=TRIP)
        list_response = await client.get("/api/me/trips")

    assert [create_response.status_code, list_response.status_code] == [401, 401]
    assert create_response.json() == {
        "error": {
            "code": "authentication_required",
            "message": "Authentication required",
        }
    }


async def test_my_trips_is_scoped_to_the_authenticated_user(
    database_settings: Settings,
) -> None:
    user = {"id": ALEX_ID}
    async for client, _ in app_client(database_settings, user):
        await client.post("/api/trips", json=TRIP)
        user["id"] = JAMIE_ID
        listed = await client.get("/api/me/trips")

    assert listed.status_code == 200
    assert listed.json() == []


async def test_created_trip_survives_a_new_application_instance(
    database_settings: Settings,
) -> None:
    async for client, _ in app_client(database_settings, {"id": ALEX_ID}):
        created = await client.post("/api/trips", json=TRIP)
        assert created.status_code == 201

    async for client, _ in app_client(database_settings, {"id": ALEX_ID}):
        listed = await client.get("/api/me/trips")

    assert listed.status_code == 200
    assert [(trip["name"], trip["role"]) for trip in listed.json()] == [
        ("Greek Islands 2027", "creator")
    ]


async def test_created_draft_is_available_only_to_its_participants(
    database_settings: Settings,
) -> None:
    async for client, app in app_client(database_settings, {"id": ALEX_ID}):
        created = await client.post("/api/trips", json=TRIP)
        participant_trip = await client.get(f"/api/trips/{created.json()['id']}")
        app.dependency_overrides.pop(require_current_user)
        anonymous_trip = await client.get(f"/api/trips/{created.json()['id']}")

    assert participant_trip.status_code == 200
    assert participant_trip.json()["name"] == "Greek Islands 2027"
    assert participant_trip.json()["calendar"] == [
        {"date": f"2027-06-{day:02d}", "day_number": day - 9, "is_planned": False}
        for day in range(10, 18)
    ]
    assert participant_trip.json()["roster"] == [
        {"display_name": "Test User", "role": "creator"}
    ]
    assert anonymous_trip.status_code == 401


async def test_creator_updates_trip_details_and_ordered_destinations(
    database_settings: Settings,
) -> None:
    async for client, _ in app_client(database_settings, {"id": ALEX_ID}):
        created = await client.post("/api/trips", json=TRIP)
        before = await client.get(f"/api/trips/{created.json()['id']}")
        cyclades_id = before.json()["destinations"][0]["id"]

        updated = await client.put(
            f"/api/trips/{created.json()['id']}/details",
            json={
                "name": "Aegean summer",
                "short_name": "Aegean",
                "description": "Athens first, then the islands.",
                "start_date": "2027-06-08",
                "end_date": "2027-06-19",
                "destinations": [
                    {
                        "name": "Athens",
                        "timezone": "Europe/Athens",
                        "location": {"lat": 37.9838, "lng": 23.7275},
                    },
                    {
                        "id": cyclades_id,
                        "name": "Cyclades",
                        "timezone": "Europe/Athens",
                        "location": {"lat": 37.4467, "lng": 25.3289},
                    },
                ],
            },
        )
        reader_projection = await client.get(f"/api/trips/{created.json()['id']}")

    assert updated.status_code == 200
    assert updated.json()["role"] == "creator"
    assert updated.json()["name"] == "Aegean summer"
    assert updated.json()["destination"] == "Athens"
    assert updated.json()["start_date"] == "2027-06-08"
    assert updated.json()["end_date"] == "2027-06-19"
    assert [destination["name"] for destination in updated.json()["destinations"]] == [
        "Athens",
        "Cyclades",
    ]
    assert updated.json()["destinations"][1]["id"] == cyclades_id
    assert reader_projection.json() == updated.json()


async def test_contributor_can_edit_but_traveller_cannot(
    database_settings: Settings,
) -> None:
    user = {"id": ALEX_ID}
    async for client, _ in app_client(database_settings, user):
        created = await client.post("/api/trips", json=TRIP)
        trip_id = created.json()["id"]
        original = await client.get(f"/api/trips/{trip_id}")
        destination = original.json()["destinations"][0]
        await add_participant(
            database_settings,
            trip_id=trip_id,
            account_id=JAMIE_ID,
            display_name="Jamie Contributor",
            role="contributor",
        )
        await add_participant(
            database_settings,
            trip_id=trip_id,
            account_id=MORGAN_ID,
            display_name="Morgan Traveller",
            role="traveller",
        )
        request = {
            "name": "Contributor update",
            "short_name": "Greek Islands",
            "description": "Updated together.",
            "start_date": "2027-06-10",
            "end_date": "2027-06-17",
            "destinations": [
                {
                    "id": destination["id"],
                    "name": destination["name"],
                    "timezone": destination["timezone"],
                    "location": destination["location"],
                }
            ],
        }

        user["id"] = JAMIE_ID
        contributor_update = await client.put(
            f"/api/trips/{trip_id}/details", json=request
        )
        user["id"] = MORGAN_ID
        traveller_update = await client.put(
            f"/api/trips/{trip_id}/details",
            json={**request, "name": "Traveller overwrite"},
        )
        traveller_view = await client.get(f"/api/trips/{trip_id}")

    assert contributor_update.status_code == 200
    assert contributor_update.json()["role"] == "contributor"
    assert traveller_update.status_code == 403
    assert traveller_update.json() == {
        "error": {
            "code": "trip_edit_forbidden",
            "message": "Trip editing is not permitted",
        }
    }
    assert traveller_view.json()["name"] == "Contributor update"
    assert traveller_view.json()["role"] == "traveller"


@pytest.mark.parametrize(
    "changes",
    [
        {"name": "   "},
        {"destinations": []},
        {"destinations": [{"name": "Athens", "timezone": "Mars/Olympus"}]},
        {"start_date": "2027-06-18", "end_date": "2027-06-17"},
    ],
)
async def test_trip_details_reject_invalid_metadata(
    database_settings: Settings,
    changes: dict[str, object],
) -> None:
    async for client, _ in app_client(database_settings, {"id": ALEX_ID}):
        created = await client.post("/api/trips", json=TRIP)
        detail = await client.get(f"/api/trips/{created.json()['id']}")
        request: dict[str, object] = {
            "name": detail.json()["name"],
            "short_name": detail.json()["short_name"],
            "description": detail.json()["description"],
            "start_date": detail.json()["start_date"],
            "end_date": detail.json()["end_date"],
            "destinations": [
                {
                    "id": destination["id"],
                    "name": destination["name"],
                    "timezone": destination["timezone"],
                    "location": destination["location"],
                }
                for destination in detail.json()["destinations"]
            ],
        }
        response = await client.put(
            f"/api/trips/{created.json()['id']}/details",
            json={**request, **changes},
        )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


async def test_date_range_cannot_exclude_a_populated_daily_plan(
    database_settings: Settings,
) -> None:
    async for client, _ in app_client(database_settings, {"id": ALEX_ID}):
        created = await client.post("/api/trips", json=TRIP)
        trip_id = created.json()["id"]
        detail = await client.get(f"/api/trips/{trip_id}")
        destination = detail.json()["destinations"][0]
        await add_daily_plan(
            database_settings,
            trip_id=trip_id,
            destination_id=destination["id"],
            plan_date="2027-06-10",
        )
        rejected = await client.put(
            f"/api/trips/{trip_id}/details",
            json={
                "name": detail.json()["name"],
                "short_name": detail.json()["short_name"],
                "description": detail.json()["description"],
                "start_date": "2027-06-11",
                "end_date": detail.json()["end_date"],
                "destinations": [
                    {
                        "id": destination["id"],
                        "name": destination["name"],
                        "timezone": destination["timezone"],
                        "location": destination["location"],
                    }
                ],
            },
        )
        unchanged = await client.get(f"/api/trips/{trip_id}")

    assert rejected.status_code == 409
    assert rejected.json() == {
        "error": {
            "code": "trip_date_range_excludes_plans",
            "message": "Move or clear plans outside the new date range first",
        }
    }
    assert unchanged.json()["start_date"] == "2027-06-10"


async def test_destination_used_by_a_timeline_entry_cannot_be_removed(
    database_settings: Settings,
) -> None:
    async for client, _ in app_client(database_settings, {"id": ALEX_ID}):
        created = await client.post("/api/trips", json=TRIP)
        trip_id = created.json()["id"]
        detail = await client.get(f"/api/trips/{trip_id}")
        cyclades = detail.json()["destinations"][0]
        with_athens = await client.put(
            f"/api/trips/{trip_id}/details",
            json={
                "name": detail.json()["name"],
                "short_name": detail.json()["short_name"],
                "description": detail.json()["description"],
                "start_date": detail.json()["start_date"],
                "end_date": detail.json()["end_date"],
                "destinations": [
                    {
                        "id": cyclades["id"],
                        "name": cyclades["name"],
                        "timezone": cyclades["timezone"],
                        "location": cyclades["location"],
                    },
                    {"name": "Athens", "timezone": "Europe/Athens"},
                ],
            },
        )
        athens = with_athens.json()["destinations"][1]
        plan_id = await add_daily_plan(
            database_settings,
            trip_id=trip_id,
            destination_id=cyclades["id"],
            plan_date="2027-06-10",
        )
        await add_timeline_entry(
            database_settings,
            daily_plan_id=plan_id,
            destination_id=athens["id"],
        )
        rejected = await client.put(
            f"/api/trips/{trip_id}/details",
            json={
                "name": detail.json()["name"],
                "short_name": detail.json()["short_name"],
                "description": detail.json()["description"],
                "start_date": detail.json()["start_date"],
                "end_date": detail.json()["end_date"],
                "destinations": [
                    {
                        "id": cyclades["id"],
                        "name": cyclades["name"],
                        "timezone": cyclades["timezone"],
                        "location": cyclades["location"],
                    }
                ],
            },
        )

    assert rejected.status_code == 409
    assert rejected.json()["error"]["code"] == "trip_destination_in_use"


async def test_concurrent_destination_reorders_remain_atomic(
    database_settings: Settings,
) -> None:
    async for setup_client, _ in app_client(database_settings, {"id": ALEX_ID}):
        created = await setup_client.post("/api/trips", json=TRIP)
        trip_id = created.json()["id"]
        detail = await setup_client.get(f"/api/trips/{trip_id}")
        cyclades = detail.json()["destinations"][0]
        with_athens = await setup_client.put(
            f"/api/trips/{trip_id}/details",
            json={
                "name": detail.json()["name"],
                "short_name": detail.json()["short_name"],
                "description": detail.json()["description"],
                "start_date": detail.json()["start_date"],
                "end_date": detail.json()["end_date"],
                "destinations": [
                    {
                        "id": cyclades["id"],
                        "name": cyclades["name"],
                        "timezone": cyclades["timezone"],
                        "location": cyclades["location"],
                    },
                    {"name": "Athens", "timezone": "Europe/Athens"},
                ],
            },
        )
    destinations = [
        {
            "id": destination["id"],
            "name": destination["name"],
            "timezone": destination["timezone"],
            "location": destination["location"],
        }
        for destination in with_athens.json()["destinations"]
    ]
    base_request = {
        "name": detail.json()["name"],
        "short_name": detail.json()["short_name"],
        "description": detail.json()["description"],
        "start_date": detail.json()["start_date"],
        "end_date": detail.json()["end_date"],
    }
    app = create_app(database_settings)
    app.dependency_overrides[require_current_user] = lambda: AuthenticatedUser(
        id=UUID(ALEX_ID),
        session_id=UUID("00000000-0000-0000-0000-000000000001"),
        email="test@example.com",
        display_name="Test User",
    )
    async with (
        LifespanManager(app),
        AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as first,
        AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as second,
    ):
        responses = await asyncio.gather(
            first.put(
                f"/api/trips/{trip_id}/details",
                json={**base_request, "destinations": destinations},
            ),
            second.put(
                f"/api/trips/{trip_id}/details",
                json={**base_request, "destinations": list(reversed(destinations))},
            ),
        )
        final = await first.get(f"/api/trips/{trip_id}")

    assert [response.status_code for response in responses] == [200, 200]
    final_names = [item["name"] for item in final.json()["destinations"]]
    assert final_names in [["Cyclades", "Athens"], ["Athens", "Cyclades"]]


async def test_every_participant_role_reads_the_draft_and_current_roster(
    database_settings: Settings,
) -> None:
    user = {"id": ALEX_ID}
    async for client, _ in app_client(database_settings, user):
        created = await client.post("/api/trips", json=TRIP)
        trip_id = created.json()["id"]
        await add_participant(
            database_settings,
            trip_id=trip_id,
            account_id=JAMIE_ID,
            display_name="Jamie Contributor",
            role="contributor",
        )
        await add_participant(
            database_settings,
            trip_id=trip_id,
            account_id=MORGAN_ID,
            display_name="Morgan Traveller",
            role="traveller",
        )

        responses = []
        for account_id in (ALEX_ID, JAMIE_ID, MORGAN_ID):
            user["id"] = account_id
            responses.append(await client.get(f"/api/trips/{trip_id}"))

    assert [response.status_code for response in responses] == [200, 200, 200]
    expected_roster = [
        {"display_name": "Test User", "role": "creator"},
        {"display_name": "Jamie Contributor", "role": "contributor"},
        {"display_name": "Morgan Traveller", "role": "traveller"},
    ]
    assert all(response.json()["roster"] == expected_roster for response in responses)


async def test_created_draft_is_hidden_from_a_different_signed_in_user(
    database_settings: Settings,
) -> None:
    user = {"id": ALEX_ID}
    async for client, _ in app_client(database_settings, user):
        created = await client.post("/api/trips", json=TRIP)
        user["id"] = JAMIE_ID
        hidden_trip = await client.get(f"/api/trips/{created.json()['id']}")

    assert hidden_trip.status_code == 404
    assert hidden_trip.json() == {
        "error": {"code": "trip_not_found", "message": "Trip not found"}
    }


async def test_participation_in_another_trip_does_not_reveal_a_draft(
    database_settings: Settings,
) -> None:
    async for client, _ in app_client(database_settings, {"id": ALEX_ID}):
        private_trip = await client.post("/api/trips", json=TRIP)

    async for client, _ in app_client(database_settings, {"id": JAMIE_ID}):
        other_trip = await client.post(
            "/api/trips",
            json={**TRIP, "name": "Jamie's Trip"},
        )
        hidden_trip = await client.get(f"/api/trips/{private_trip.json()['id']}")

    assert other_trip.status_code == 201
    assert hidden_trip.status_code == 404


async def test_membership_changes_apply_to_the_next_protected_request(
    database_settings: Settings,
) -> None:
    user = {"id": ALEX_ID}
    async for client, _ in app_client(database_settings, user):
        created = await client.post("/api/trips", json=TRIP)
        trip_id = created.json()["id"]
        await add_participant(
            database_settings,
            trip_id=trip_id,
            account_id=JAMIE_ID,
            display_name="Jamie Former Participant",
            role="traveller",
        )

        user["id"] = JAMIE_ID
        accepted_participant = await client.get(f"/api/trips/{trip_id}")
        await remove_participant(
            database_settings,
            trip_id=trip_id,
            account_id=JAMIE_ID,
        )
        former_participant = await client.get(f"/api/trips/{trip_id}")

        user["id"] = ALEX_ID
        current_roster = await client.get(f"/api/trips/{trip_id}")

    assert accepted_participant.status_code == 200
    assert former_participant.status_code == 404
    assert current_roster.json()["roster"] == [
        {"display_name": "Test User", "role": "creator"}
    ]


async def test_unexpected_errors_are_logged_without_exposing_details(
    database_settings: Settings,
    caplog: pytest.LogCaptureFixture,
) -> None:
    app = create_app(database_settings)

    @app.get("/api/test/unexpected")
    async def unexpected() -> None:
        raise RuntimeError("private failure detail")

    with caplog.at_level("ERROR"):
        async with (
            LifespanManager(app),
            AsyncClient(
                transport=ASGITransport(app=app, raise_app_exceptions=False),
                base_url="http://test",
            ) as client,
        ):
            response = await client.get("/api/test/unexpected")

    assert response.status_code == 500
    assert response.json() == {
        "error": {
            "code": "internal_server_error",
            "message": "An unexpected error occurred",
        }
    }
    assert "Unhandled request error" in caplog.text
    assert "private failure detail" not in response.text
