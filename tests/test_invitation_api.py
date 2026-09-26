from datetime import datetime, timedelta
from hashlib import sha256
from urllib.parse import urlparse
from uuid import UUID

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from tests.test_trips_api import ALEX_ID, JAMIE_ID, TRIP, add_participant, app_client
from tripper_api.core.config import Settings
from tripper_api.invitation.invitation_provider import EmailMessage
from tripper_api.invitation.invitation_worker import InvitationOutboxWorker

pytestmark = [
    pytest.mark.usefixtures("clean_database"),
    pytest.mark.asyncio(loop_factories=["selector"]),
]


class RecordingEmailProvider:
    def __init__(self) -> None:
        self.messages: list[EmailMessage] = []

    async def send(self, message: EmailMessage) -> None:
        self.messages.append(message)


async def _invitation_rows(settings: Settings, trip_id: str) -> list[dict[str, object]]:
    engine = create_async_engine(settings.database_url)
    async with engine.connect() as connection:
        rows = (
            (
                await connection.execute(
                    text(
                        "SELECT id, email, role, token_hash, expires_at, revoked_at, "
                        "replaced_at FROM trip_invitations WHERE trip_id = :trip_id "
                        "ORDER BY created_at, id"
                    ),
                    {"trip_id": UUID(trip_id)},
                )
            )
            .mappings()
            .all()
        )
    await engine.dispose()
    return [dict(row) for row in rows]


async def test_creator_invites_without_creating_participant_access(
    database_settings: Settings,
) -> None:
    async for creator, _ in app_client(database_settings, {"id": ALEX_ID}):
        trip_id = (await creator.post("/api/trips", json=TRIP)).json()["id"]
        created = await creator.post(
            f"/api/trips/{trip_id}/invitations",
            json={"email": "  Invitee@Example.com ", "role": "contributor"},
        )
        duplicate = await creator.post(
            f"/api/trips/{trip_id}/invitations",
            json={"email": "invitee@example.com", "role": "traveller"},
        )
        listed = await creator.get(f"/api/trips/{trip_id}/invitations")
        participant_trip = await creator.get(f"/api/trips/{trip_id}")

    assert created.status_code == 201
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "active_invitation_exists"
    assert created.json() == listed.json()[0]
    assert set(created.json()) == {
        "id",
        "email",
        "role",
        "created_at",
        "expires_at",
        "delivery_status",
    }
    assert created.json()["delivery_status"] == "pending"
    assert created.json()["email"] == "invitee@example.com"
    assert created.json()["role"] == "contributor"
    expires_at = datetime.fromisoformat(created.json()["expires_at"])
    created_at = datetime.fromisoformat(created.json()["created_at"])
    assert expires_at - created_at == timedelta(days=7)

    rows = await _invitation_rows(database_settings, trip_id)
    assert len(rows) == 1
    assert len(str(rows[0]["token_hash"])) == 64
    assert "secret" not in created.text.lower()
    assert participant_trip.json()["roster"] == [
        {"display_name": "Test User", "role": "creator"}
    ]

    async for invitee, _ in app_client(
        database_settings, {"id": JAMIE_ID, "email": "invitee@example.com"}
    ):
        private_trip = await invitee.get(f"/api/trips/{trip_id}")
        my_trips = await invitee.get("/api/me/trips")
    assert private_trip.status_code == 404
    assert my_trips.json() == []


async def test_only_creator_can_administer_invitations(
    database_settings: Settings,
) -> None:
    async for creator, _ in app_client(database_settings, {"id": ALEX_ID}):
        trip_id = (await creator.post("/api/trips", json=TRIP)).json()["id"]
        invitation_id = (
            await creator.post(
                f"/api/trips/{trip_id}/invitations",
                json={"email": "person@example.com", "role": "traveller"},
            )
        ).json()["id"]
    await add_participant(
        database_settings,
        trip_id=trip_id,
        account_id=JAMIE_ID,
        display_name="Contributor",
        role="contributor",
    )

    async for contributor, _ in app_client(database_settings, {"id": JAMIE_ID}):
        responses = [
            await contributor.get(f"/api/trips/{trip_id}/invitations"),
            await contributor.post(
                f"/api/trips/{trip_id}/invitations",
                json={"email": "other@example.com", "role": "traveller"},
            ),
            await contributor.delete(
                f"/api/trips/{trip_id}/invitations/{invitation_id}"
            ),
            await contributor.post(
                f"/api/trips/{trip_id}/invitations/{invitation_id}/replace"
            ),
        ]

    assert {response.status_code for response in responses} == {403}
    assert all(
        response.json()["error"]["code"] == "invitation_forbidden"
        for response in responses
    )


async def test_revoke_and_replace_invalidate_prior_invitations(
    database_settings: Settings,
) -> None:
    async for creator, _ in app_client(database_settings, {"id": ALEX_ID}):
        trip_id = (await creator.post("/api/trips", json=TRIP)).json()["id"]
        first = await creator.post(
            f"/api/trips/{trip_id}/invitations",
            json={"email": "one@example.com", "role": "traveller"},
        )
        revoked = await creator.delete(
            f"/api/trips/{trip_id}/invitations/{first.json()['id']}"
        )
        second = await creator.post(
            f"/api/trips/{trip_id}/invitations",
            json={"email": "two@example.com", "role": "contributor"},
        )
        replacement = await creator.post(
            f"/api/trips/{trip_id}/invitations/{second.json()['id']}/replace"
        )
        active = await creator.get(f"/api/trips/{trip_id}/invitations")

    assert revoked.status_code == 204
    assert replacement.status_code == 201
    assert replacement.json()["id"] != second.json()["id"]
    assert replacement.json()["email"] == second.json()["email"]
    assert replacement.json()["role"] == second.json()["role"]
    assert active.json() == [replacement.json()]
    rows = await _invitation_rows(database_settings, trip_id)
    assert rows[0]["revoked_at"] is not None
    assert rows[1]["replaced_at"] is not None
    assert rows[2]["revoked_at"] is None and rows[2]["replaced_at"] is None
    assert len({row["token_hash"] for row in rows}) == 3


async def test_expired_invitation_can_be_reissued(
    database_settings: Settings,
) -> None:
    async for creator, _ in app_client(database_settings, {"id": ALEX_ID}):
        trip_id = (await creator.post("/api/trips", json=TRIP)).json()["id"]
        first = await creator.post(
            f"/api/trips/{trip_id}/invitations",
            json={"email": "expired@example.com", "role": "traveller"},
        )
    engine = create_async_engine(database_settings.database_url)
    async with engine.begin() as connection:
        await connection.execute(
            text(
                "UPDATE trip_invitations SET "
                "created_at = now() - interval '8 days', "
                "expires_at = now() - interval '1 day' "
                "WHERE id = :invitation_id"
            ),
            {"invitation_id": UUID(first.json()["id"])},
        )
    await engine.dispose()

    async for creator, _ in app_client(database_settings, {"id": ALEX_ID}):
        replacement = await creator.post(
            f"/api/trips/{trip_id}/invitations",
            json={"email": "expired@example.com", "role": "contributor"},
        )

    assert replacement.status_code == 201
    assert replacement.json()["id"] != first.json()["id"]
    assert replacement.json()["role"] == "contributor"


async def test_outbox_delivers_once_and_secret_matches_only_the_hash(
    database_settings: Settings,
) -> None:
    async for creator, app in app_client(database_settings, {"id": ALEX_ID}):
        trip_id = (await creator.post("/api/trips", json=TRIP)).json()["id"]
        created = await creator.post(
            f"/api/trips/{trip_id}/invitations",
            json={"email": "delivery@example.com", "role": "traveller"},
        )
        provider = RecordingEmailProvider()
        worker = InvitationOutboxWorker.from_app(app, provider.send)
        assert await worker.deliver_next() is True
        assert await worker.deliver_next() is False

    assert len(provider.messages) == 1
    message = provider.messages[0]
    assert message.to_email == "delivery@example.com"
    assert message.deduplication_key == f"trip-invitation:{created.json()['id']}"
    secret = urlparse(message.invitation_url).path.rsplit("/", 1)[-1]
    assert len(secret) >= 43
    rows = await _invitation_rows(database_settings, trip_id)
    assert sha256(secret.encode()).hexdigest() == rows[0]["token_hash"]
    assert secret not in created.text
