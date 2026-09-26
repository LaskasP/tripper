from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from hmac import compare_digest
from hmac import new as hmac_new

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from tripper_api.invitation.invitation_errors import InvalidDeliveryWebhookError
from tripper_api.invitation.invitation_model import DeliveryEventType
from tripper_api.invitation.invitation_read_model import NormalizedDeliveryEvent


@dataclass(frozen=True)
class EmailMessage:
    to_email: str
    invitation_url: str
    deduplication_key: str


class EmailDeliveryRejectedError(Exception):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class EmailDeliveryAmbiguousError(Exception):
    pass


class EmailDeliveryRetryableError(Exception):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class _MailgunSignature(BaseModel):
    model_config = ConfigDict(extra="forbid")

    timestamp: str
    token: str
    signature: str


class _MailgunEventData(BaseModel):
    # Mailgun adds provider-owned event fields that Tripper does not consume.
    model_config = ConfigDict(extra="ignore")

    provider_event_id: str = Field(alias="id")
    event: str
    severity: str | None = None
    timestamp: float
    user_variables: dict[str, str] = Field(alias="user-variables")


class _MailgunWebhookPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    signature: _MailgunSignature
    event_data: _MailgunEventData = Field(alias="event-data")


def normalize_mailgun_event(
    raw_payload: object,
    signing_key: str,
    now: datetime,
) -> NormalizedDeliveryEvent | None:
    try:
        payload = _MailgunWebhookPayload.model_validate(raw_payload)
    except ValidationError as error:
        raise InvalidDeliveryWebhookError from error
    signed = f"{payload.signature.timestamp}{payload.signature.token}".encode()
    expected = hmac_new(signing_key.encode(), signed, sha256).hexdigest()
    try:
        signed_at = datetime.fromtimestamp(int(payload.signature.timestamp), tz=UTC)
    except (ValueError, OverflowError) as error:
        raise InvalidDeliveryWebhookError from error
    if abs(now - signed_at) > timedelta(minutes=15) or not compare_digest(
        expected, payload.signature.signature
    ):
        raise InvalidDeliveryWebhookError

    event_type: DeliveryEventType | None
    if payload.event_data.event == "delivered":
        event_type = DeliveryEventType.DELIVERED
    elif payload.event_data.event == "complained":
        event_type = DeliveryEventType.COMPLAINED
    elif payload.event_data.event == "failed":
        event_type = (
            DeliveryEventType.TEMPORARY_FAILURE
            if payload.event_data.severity == "temporary"
            else DeliveryEventType.PERMANENT_FAILURE
        )
    else:
        event_type = None
    deduplication_key = payload.event_data.user_variables.get("deduplication_key")
    if event_type is None or deduplication_key is None:
        return None
    try:
        occurred_at = datetime.fromtimestamp(payload.event_data.timestamp, tz=UTC)
    except (ValueError, OverflowError) as error:
        raise InvalidDeliveryWebhookError from error
    return NormalizedDeliveryEvent(
        provider_event_id=payload.event_data.provider_event_id,
        deduplication_key=deduplication_key,
        event_type=event_type,
        occurred_at=occurred_at,
    )


class MailgunEmailProvider:
    def __init__(
        self,
        client: httpx.AsyncClient,
        *,
        api_key: str,
        domain: str,
        from_email: str,
        api_base_url: str = "https://api.eu.mailgun.net",
    ) -> None:
        self._client = client
        self._api_key = api_key
        self._domain = domain
        self._from_email = from_email
        self._api_base_url = api_base_url.rstrip("/")

    async def send(self, message: EmailMessage) -> None:
        try:
            response = await self._client.post(
                f"{self._api_base_url}/v3/{self._domain}/messages",
                auth=("api", self._api_key),
                data={
                    "from": self._from_email,
                    "to": message.to_email,
                    "subject": "You are invited to a Trip",
                    "text": f"Open this invitation: {message.invitation_url}",
                    "o:tracking": "no",
                    "o:tracking-clicks": "no",
                    "o:tracking-opens": "no",
                    "v:deduplication_key": message.deduplication_key,
                },
            )
        except httpx.RequestError as error:
            raise EmailDeliveryAmbiguousError from error
        if 200 <= response.status_code < 300:
            return
        if response.status_code == 429:
            raise EmailDeliveryRetryableError("provider_http_429")
        if 400 <= response.status_code < 500:
            raise EmailDeliveryRejectedError(f"provider_http_{response.status_code}")
        raise EmailDeliveryAmbiguousError
