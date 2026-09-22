from collections.abc import AsyncIterator
from uuid import UUID

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
    assert anonymous_trip.status_code == 401


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
