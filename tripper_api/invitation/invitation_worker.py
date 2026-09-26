import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from typing import cast

from fastapi import FastAPI

from tripper_api.core.config import Settings
from tripper_api.core.database import Database
from tripper_api.invitation.invitation_model import OutboxStatus
from tripper_api.invitation.invitation_provider import (
    EmailDeliveryAmbiguousError,
    EmailDeliveryRejectedError,
    EmailDeliveryRetryableError,
    EmailMessage,
)
from tripper_api.invitation.invitation_repository import InvitationRepository
from tripper_api.invitation.invitation_secret import derive_invitation_secret

logger = logging.getLogger(__name__)


class InvitationOutboxWorker:
    def __init__(
        self,
        database: Database,
        send_email: Callable[[EmailMessage], Awaitable[None]],
        token_key: bytes,
        invitation_base_url: str,
    ) -> None:
        self._database = database
        self._send_email = send_email
        self._token_key = token_key
        self._invitation_base_url = invitation_base_url.rstrip("/")

    @classmethod
    def from_app(
        cls,
        app: FastAPI,
        send_email: Callable[[EmailMessage], Awaitable[None]],
    ) -> "InvitationOutboxWorker":
        settings = cast(Settings, app.state.settings)
        return cls(
            cast(Database, app.state.database),
            send_email,
            settings.invitation_key_bytes(),
            settings.invitation_base_url,
        )

    async def deliver_next(self) -> bool:
        if self._database.sessions is None:
            raise RuntimeError("database lifespan has not started")
        async with self._database.sessions() as session, session.begin():
            claimed = await InvitationRepository(session).claim_next(datetime.now(UTC))
        if claimed is None:
            return False

        secret = derive_invitation_secret(claimed.invitation_id, self._token_key)
        message = EmailMessage(
            to_email=claimed.recipient_email,
            invitation_url=(
                f"{self._invitation_base_url}/{claimed.invitation_id}/{secret}"
            ),
            deduplication_key=claimed.deduplication_key,
        )
        status = OutboxStatus.SENT
        error_code: str | None = None
        next_attempt_at: datetime | None = None
        try:
            await self._send_email(message)
        except EmailDeliveryRejectedError as error:
            status = OutboxStatus.FAILED
            error_code = error.code
        except EmailDeliveryRetryableError as error:
            error_code = error.code
            if claimed.attempt_count >= 5:
                status = OutboxStatus.FAILED
            else:
                status = OutboxStatus.PENDING
                delay_seconds = 30 * (2 ** (claimed.attempt_count - 1))
                next_attempt_at = datetime.now(UTC) + timedelta(seconds=delay_seconds)
        except EmailDeliveryAmbiguousError:
            status = OutboxStatus.AMBIGUOUS
            error_code = "provider_outcome_ambiguous"
        except Exception:  # noqa: BLE001 - unknown send outcomes must never auto-retry
            status = OutboxStatus.AMBIGUOUS
            error_code = "provider_outcome_ambiguous"
        finally:
            secret = ""
            message = EmailMessage("", "", "")

        async with self._database.sessions() as session, session.begin():
            await InvitationRepository(session).finish_delivery(
                claimed.outbox_id,
                status,
                datetime.now(UTC),
                error_code,
                next_attempt_at,
            )
        if status not in {OutboxStatus.SENT, OutboxStatus.PENDING}:
            logger.warning(
                "Invitation email delivery did not complete",
                extra={"outbox_id": str(claimed.outbox_id), "error_code": error_code},
            )
        return True
