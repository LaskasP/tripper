from datetime import UTC, datetime, timedelta
from hashlib import sha256
from hmac import new as hmac_new
from urllib.parse import parse_qs
from uuid import UUID

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from tests.test_trips_api import ALEX_ID, TRIP, app_client
from tripper_api.core.config import Settings
from tripper_api.invitation.invitation_model import DeliveryEventType
from tripper_api.invitation.invitation_provider import (
    EmailDeliveryAmbiguousError,
    EmailDeliveryRejectedError,
    EmailDeliveryRetryableError,
    EmailMessage,
    MailgunEmailProvider,
    normalize_mailgun_event,
)
from tripper_api.invitation.invitation_worker import InvitationOutboxWorker

pytestmark = [
    pytest.mark.usefixtures("clean_database"),
    pytest.mark.asyncio(loop_factories=["selector"]),
]


class AmbiguousProvider:
    def __init__(self) -> None:
        self.calls = 0

    async def send(self, message: EmailMessage) -> None:
        self.calls += 1
        raise RuntimeError(f"timeout while sending {message.invitation_url}")


class SuccessfulProvider:
    async def send(self, message: EmailMessage) -> None:
        pass


def mailgun_payload(
    *,
    event_id: str,
    event: str,
    deduplication_key: str,
    severity: str | None = None,
    signature_valid: bool = True,
    occurred_at: datetime | None = None,
    additional_event_data: dict[str, object] | None = None,
) -> dict[str, object]:
    timestamp = str(int(datetime.now(UTC).timestamp()))
    token = "mailgun-test-token"
    signature = hmac_new(
        b"test-webhook-key", f"{timestamp}{token}".encode(), sha256
    ).hexdigest()
    if not signature_valid:
        signature = "invalid"
    event_data: dict[str, object] = {
        "id": event_id,
        "event": event,
        "severity": severity,
        "timestamp": (occurred_at or datetime.now(UTC)).timestamp(),
        "user-variables": {"deduplication_key": deduplication_key},
    }
    event_data.update(additional_event_data or {})
    return {
        "signature": {
            "timestamp": timestamp,
            "token": token,
            "signature": signature,
        },
        "event-data": event_data,
    }


async def test_ambiguous_outcome_is_sanitized_and_never_automatically_retried(
    database_settings: Settings,
    caplog: pytest.LogCaptureFixture,
) -> None:
    async for creator, app in app_client(database_settings, {"id": ALEX_ID}):
        trip_id = (await creator.post("/api/trips", json=TRIP)).json()["id"]
        await creator.post(
            f"/api/trips/{trip_id}/invitations",
            json={"email": "ambiguous@example.com", "role": "traveller"},
        )
        provider = AmbiguousProvider()
        worker = InvitationOutboxWorker.from_app(app, provider.send)
        with caplog.at_level("WARNING"):
            assert await worker.deliver_next() is True
            assert await worker.deliver_next() is False

    engine = create_async_engine(database_settings.database_url)
    async with engine.connect() as connection:
        status, error_code = (
            await connection.execute(
                text("SELECT status, last_error_code FROM invitation_email_outbox")
            )
        ).one()
    await engine.dispose()
    assert provider.calls == 1
    assert (status, error_code) == ("ambiguous", "provider_outcome_ambiguous")
    assert "timeout while sending" not in caplog.text
    assert "tripper/invitations" not in caplog.text


async def test_abandoned_claim_becomes_visible_and_is_not_retried(
    database_settings: Settings,
) -> None:
    async for creator, app in app_client(database_settings, {"id": ALEX_ID}):
        trip_id = (await creator.post("/api/trips", json=TRIP)).json()["id"]
        created = await creator.post(
            f"/api/trips/{trip_id}/invitations",
            json={"email": "abandoned@example.com", "role": "contributor"},
        )
        engine = create_async_engine(database_settings.database_url)
        async with engine.begin() as connection:
            await connection.execute(
                text(
                    "UPDATE invitation_email_outbox SET status = 'delivering', "
                    "claimed_at = now() - interval '11 minutes' "
                    "WHERE invitation_id = :invitation_id"
                ),
                {"invitation_id": UUID(created.json()["id"])},
            )
        await engine.dispose()
        provider = AmbiguousProvider()
        worker = InvitationOutboxWorker.from_app(app, provider.send)
        assert await worker.deliver_next() is False
        listed = await creator.get(f"/api/trips/{trip_id}/invitations")

    assert provider.calls == 0
    assert listed.json()[0]["delivery_status"] == "ambiguous"


async def test_mailgun_webhook_authenticates_deduplicates_and_updates_delivery(
    database_settings: Settings,
) -> None:
    async for creator, app in app_client(database_settings, {"id": ALEX_ID}):
        trip_id = (await creator.post("/api/trips", json=TRIP)).json()["id"]
        created = await creator.post(
            f"/api/trips/{trip_id}/invitations",
            json={"email": "delivered@example.com", "role": "traveller"},
        )
        invitation_id = created.json()["id"]
        assert await InvitationOutboxWorker.from_app(
            app, SuccessfulProvider().send
        ).deliver_next()
        payload = mailgun_payload(
            event_id="mailgun-event-1",
            event="delivered",
            deduplication_key=f"trip-invitation:{invitation_id}",
        )

        first = await creator.post("/api/email/mailgun/events", json=payload)
        duplicate = await creator.post("/api/email/mailgun/events", json=payload)
        listed = await creator.get(f"/api/trips/{trip_id}/invitations")
        invalid = await creator.post(
            "/api/email/mailgun/events",
            json=mailgun_payload(
                event_id="mailgun-event-2",
                event="delivered",
                deduplication_key=f"trip-invitation:{invitation_id}",
                signature_valid=False,
            ),
        )

    engine = create_async_engine(database_settings.database_url)
    async with engine.connect() as connection:
        event_count = await connection.scalar(
            text("SELECT count(*) FROM invitation_email_events")
        )
    await engine.dispose()
    assert first.status_code == 204
    assert duplicate.status_code == 204
    assert invalid.status_code == 401
    assert listed.json()[0]["delivery_status"] == "delivered"
    assert event_count == 1


@pytest.mark.parametrize(
    ("event", "severity", "expected_type"),
    [
        ("delivered", None, DeliveryEventType.DELIVERED),
        ("failed", "temporary", DeliveryEventType.TEMPORARY_FAILURE),
        ("failed", "permanent", DeliveryEventType.PERMANENT_FAILURE),
        ("complained", None, DeliveryEventType.COMPLAINED),
    ],
)
async def test_mailgun_webhook_normalizes_delivery_events(
    event: str,
    severity: str | None,
    expected_type: DeliveryEventType,
) -> None:
    payload = mailgun_payload(
        event_id=f"mailgun-{expected_type}",
        event=event,
        severity=severity,
        deduplication_key="trip-invitation:id",
    )

    normalized = normalize_mailgun_event(payload, "test-webhook-key", datetime.now(UTC))

    assert normalized is not None
    assert normalized.event_type is expected_type


async def test_mailgun_webhooks_do_not_regress_terminal_delivery_state(
    database_settings: Settings,
) -> None:
    async for creator, app in app_client(database_settings, {"id": ALEX_ID}):
        trip_id = (await creator.post("/api/trips", json=TRIP)).json()["id"]
        created = await creator.post(
            f"/api/trips/{trip_id}/invitations",
            json={"email": "ordered@example.com", "role": "traveller"},
        )
        invitation_id = created.json()["id"]
        assert await InvitationOutboxWorker.from_app(
            app, SuccessfulProvider().send
        ).deliver_next()
        deduplication_key = f"trip-invitation:{invitation_id}"
        now = datetime.now(UTC)
        for payload in [
            mailgun_payload(
                event_id="delivered-first",
                event="delivered",
                deduplication_key=deduplication_key,
                occurred_at=now,
            ),
            mailgun_payload(
                event_id="complaint-second",
                event="complained",
                deduplication_key=deduplication_key,
                occurred_at=now,
            ),
            mailgun_payload(
                event_id="delivered-delayed",
                event="delivered",
                deduplication_key=deduplication_key,
                occurred_at=now - timedelta(minutes=5),
            ),
            mailgun_payload(
                event_id="failure-delayed",
                event="failed",
                severity="permanent",
                deduplication_key=deduplication_key,
                occurred_at=now - timedelta(minutes=4),
            ),
        ]:
            assert (
                await creator.post("/api/email/mailgun/events", json=payload)
            ).status_code == 204
        listed = await creator.get(f"/api/trips/{trip_id}/invitations")

    assert listed.json()[0]["delivery_status"] == "complained"


async def test_mailgun_webhook_accepts_unconsumed_provider_event_fields() -> None:
    payload = mailgun_payload(
        event_id="mailgun-extra",
        event="delivered",
        deduplication_key="trip-invitation:id",
        additional_event_data={
            "recipient": "invitee@example.com",
            "message": {"headers": {"message-id": "provider-message"}},
            "envelope": {"sender": "invitations@mg.example.com"},
            "flags": {"is-authenticated": True},
            "delivery-status": {"code": 250, "description": "OK"},
        },
    )

    normalized = normalize_mailgun_event(payload, "test-webhook-key", datetime.now(UTC))

    assert normalized is not None
    assert normalized.event_type is DeliveryEventType.DELIVERED


async def test_mailgun_adapter_keeps_secret_out_of_provider_metadata() -> None:
    captured: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, json={"id": "provider-id"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        provider = MailgunEmailProvider(
            client,
            api_key="private-api-key",
            domain="mg.example.com",
            from_email="Tripper <invitations@mg.example.com>",
        )
        await provider.send(
            EmailMessage(
                to_email="invitee@example.com",
                invitation_url="https://tripper.example/invitations/id/raw-secret",
                deduplication_key="trip-invitation:id",
            )
        )

    fields = parse_qs(captured[0].content.decode())
    assert fields["v:deduplication_key"] == ["trip-invitation:id"]
    assert "raw-secret" not in fields["v:deduplication_key"][0]
    assert fields["o:tracking"] == ["no"]
    assert fields["o:tracking-clicks"] == ["no"]
    assert fields["o:tracking-opens"] == ["no"]


@pytest.mark.parametrize(
    ("status_code", "error_type"),
    [
        (400, EmailDeliveryRejectedError),
        (429, EmailDeliveryRetryableError),
        (500, EmailDeliveryAmbiguousError),
    ],
)
async def test_mailgun_adapter_classifies_safe_and_ambiguous_failures(
    status_code: int,
    error_type: type[Exception],
) -> None:
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(status_code, request=request)
        )
    ) as client:
        provider = MailgunEmailProvider(
            client,
            api_key="private-api-key",
            domain="mg.example.com",
            from_email="invitations@mg.example.com",
        )
        with pytest.raises(error_type):
            await provider.send(
                EmailMessage(
                    to_email="invitee@example.com",
                    invitation_url="https://tripper.example/invitations/id/secret",
                    deduplication_key="trip-invitation:id",
                )
            )
