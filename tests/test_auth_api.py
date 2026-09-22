from collections.abc import AsyncIterator
from dataclasses import dataclass

import pytest
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from tripper_api.app import create_app
from tripper_api.auth.auth_identity import GoogleIdentity
from tripper_api.core.config import Settings

pytestmark = [
    pytest.mark.usefixtures("clean_database"),
    pytest.mark.asyncio(loop_factories=["selector"]),
]


@dataclass
class StubGoogleIdentityVerifier:
    identities: dict[str, GoogleIdentity]

    async def verify(self, credential: str) -> GoogleIdentity:
        return self.identities[credential]


IDENTITY = GoogleIdentity(
    issuer="https://accounts.google.com",
    subject="google-subject-123",
    email="alex@example.com",
    display_name="Alex Example",
)


async def auth_client(
    settings: Settings,
) -> AsyncIterator[AsyncClient]:
    app = create_app(
        settings,
        verify_google_identity=StubGoogleIdentityVerifier(
            {"valid-google-credential": IDENTITY}
        ).verify,
    )
    async with (
        LifespanManager(app),
        AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False),
            base_url="https://test",
        ) as client,
    ):
        yield client


async def sign_in(client: AsyncClient) -> None:
    client.cookies.set("g_csrf_token", "google-csrf")
    response = await client.post(
        "/api/auth/google",
        data={
            "credential": "valid-google-credential",
            "g_csrf_token": "google-csrf",
        },
    )
    assert response.status_code == 200


async def test_google_sign_in_establishes_secure_server_side_session(
    database_settings: Settings,
) -> None:
    async for client in auth_client(database_settings):
        client.cookies.set("g_csrf_token", "google-csrf")
        response = await client.post(
            "/api/auth/google",
            data={
                "credential": "valid-google-credential",
                "g_csrf_token": "google-csrf",
            },
        )
        current = await client.get("/api/auth/session")

    assert response.status_code == 200
    assert response.json() == {
        "account": {
            "display_name": "Alex Example",
            "email": "alex@example.com",
        }
    }
    assert current.status_code == 200
    assert current.json() == response.json()
    session_cookie = next(
        header
        for header in response.headers.get_list("set-cookie")
        if header.startswith("tripper_session=")
    )
    assert "HttpOnly" in session_cookie
    assert "Secure" in session_cookie
    assert "SameSite=lax" in session_cookie
    assert "Max-Age=604800" in session_cookie


async def test_google_sign_in_configuration_exposes_only_the_public_client_id(
    database_settings: Settings,
) -> None:
    async for client in auth_client(database_settings):
        response = await client.get("/api/auth/google/config")

    assert response.status_code == 200
    assert response.json() == {"client_id": "test-client-id"}


async def test_google_sign_in_rejects_mismatched_double_submit_csrf(
    database_settings: Settings,
) -> None:
    async for client in auth_client(database_settings):
        client.cookies.set("g_csrf_token", "cookie-value")
        response = await client.post(
            "/api/auth/google",
            data={
                "credential": "valid-google-credential",
                "g_csrf_token": "body-value",
            },
        )

    assert response.status_code == 403
    assert response.json() == {
        "error": {
            "code": "csrf_validation_failed",
            "message": "CSRF validation failed",
        }
    }


async def test_cookie_authenticated_write_requires_session_csrf_token(
    database_settings: Settings,
) -> None:
    trip = {
        "name": "Greek Islands 2027",
        "destination": "Cyclades",
        "short_name": "Greek Islands",
        "description": "A week through the Cyclades",
        "timezone": "Europe/Athens",
        "location": {"lat": 37.4467, "lng": 25.3289},
        "start_date": "2027-06-10",
        "end_date": "2027-06-17",
    }
    async for client in auth_client(database_settings):
        await sign_in(client)
        rejected = await client.post("/api/trips", json=trip)
        csrf_token = client.cookies["tripper_csrf"]
        accepted = await client.post(
            "/api/trips", json=trip, headers={"X-CSRF-Token": csrf_token}
        )

    assert rejected.status_code == 403
    assert rejected.json()["error"]["code"] == "csrf_validation_failed"
    assert accepted.status_code == 201


async def test_sign_out_invalidates_only_the_current_tripper_session(
    database_settings: Settings,
) -> None:
    async for first_client in auth_client(database_settings):
        await sign_in(first_client)
        first_session = first_client.cookies["tripper_session"]
        first_csrf = first_client.cookies["tripper_csrf"]

        async for second_client in auth_client(database_settings):
            await sign_in(second_client)
            signed_out = await first_client.post(
                "/api/auth/sign-out", headers={"X-CSRF-Token": first_csrf}
            )
            first_client.cookies.set("tripper_session", first_session)
            first_current = await first_client.get("/api/auth/session")
            second_current = await second_client.get("/api/auth/session")

    assert signed_out.status_code == 204
    assert first_current.status_code == 401
    assert second_current.status_code == 200


async def test_expired_session_is_rejected(
    database_settings: Settings,
) -> None:
    async for client in auth_client(database_settings):
        await sign_in(client)
        engine = create_async_engine(database_settings.database_url)
        async with engine.begin() as connection:
            await connection.execute(
                text(
                    "UPDATE sessions SET expires_at = CURRENT_TIMESTAMP - "
                    "INTERVAL '1 second'"
                )
            )
        await engine.dispose()
        response = await client.get("/api/auth/session")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "authentication_required"
