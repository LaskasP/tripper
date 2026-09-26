from datetime import datetime, timedelta
from typing import cast
from uuid import UUID

from sqlalchemy import ColumnElement, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from tripper_api.invitation.invitation_model import (
    DeliveryEventType,
    InvitationEmailEvent,
    InvitationEmailOutbox,
    OutboxStatus,
    TripInvitation,
)
from tripper_api.invitation.invitation_read_model import (
    ClaimedInvitationEmail,
    InvitationSummary,
    NormalizedDeliveryEvent,
)


def _active_invitation_conditions() -> tuple[ColumnElement[bool], ...]:
    return (
        TripInvitation.revoked_at.is_(None),
        TripInvitation.replaced_at.is_(None),
        TripInvitation.accepted_at.is_(None),
    )


class InvitationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add_invitation(self, invitation: TripInvitation) -> None:
        self._session.add(invitation)
        await self._session.flush()

    async def add_outbox(self, outbox: InvitationEmailOutbox) -> None:
        self._session.add(outbox)
        await self._session.flush()

    async def list_active(
        self, trip_id: UUID, now: datetime
    ) -> list[InvitationSummary]:
        rows = (
            (
                await self._session.execute(
                    select(TripInvitation, InvitationEmailOutbox.status)
                    .join(
                        InvitationEmailOutbox,
                        InvitationEmailOutbox.invitation_id == TripInvitation.id,
                    )
                    .where(
                        TripInvitation.trip_id == trip_id,
                        *_active_invitation_conditions(),
                        TripInvitation.expires_at > now,
                    )
                    .order_by(TripInvitation.created_at, TripInvitation.id)
                )
            )
            .tuples()
            .all()
        )
        return [
            InvitationSummary(
                id=invitation.id,
                email=invitation.email,
                role=invitation.role,
                created_at=invitation.created_at,
                expires_at=invitation.expires_at,
                delivery_status=status,
            )
            for invitation, status in rows
        ]

    async def active_for_update(
        self, trip_id: UUID, invitation_id: UUID
    ) -> TripInvitation | None:
        return cast(
            TripInvitation | None,
            await self._session.scalar(
                select(TripInvitation)
                .where(
                    TripInvitation.id == invitation_id,
                    TripInvitation.trip_id == trip_id,
                    *_active_invitation_conditions(),
                )
                .with_for_update()
            ),
        )

    async def invalidate_expired_for_email(
        self, trip_id: UUID, email: str, now: datetime
    ) -> None:
        expired = (
            await self._session.scalars(
                select(TripInvitation)
                .where(
                    TripInvitation.trip_id == trip_id,
                    TripInvitation.email == email,
                    *_active_invitation_conditions(),
                    TripInvitation.expires_at <= now,
                )
                .with_for_update()
            )
        ).all()
        for invitation in expired:
            invitation.replaced_at = now
            await self.cancel_delivery(invitation.id)

    async def cancel_delivery(self, invitation_id: UUID) -> None:
        await self._session.execute(
            update(InvitationEmailOutbox)
            .where(
                InvitationEmailOutbox.invitation_id == invitation_id,
                InvitationEmailOutbox.status.in_(
                    [OutboxStatus.PENDING, OutboxStatus.DELIVERING]
                ),
            )
            .values(status=OutboxStatus.CANCELLED)
        )

    async def claim_next(self, now: datetime) -> ClaimedInvitationEmail | None:
        await self._session.execute(
            update(InvitationEmailOutbox)
            .where(
                InvitationEmailOutbox.status == OutboxStatus.DELIVERING,
                InvitationEmailOutbox.claimed_at <= now - timedelta(minutes=10),
            )
            .values(
                status=OutboxStatus.AMBIGUOUS,
                last_error_code="worker_claim_abandoned",
            )
        )
        await self._session.execute(
            update(InvitationEmailOutbox)
            .where(
                InvitationEmailOutbox.status.in_(
                    [OutboxStatus.PENDING, OutboxStatus.DELIVERING]
                ),
                InvitationEmailOutbox.invitation_id.in_(
                    select(TripInvitation.id).where(
                        TripInvitation.expires_at <= now,
                        TripInvitation.accepted_at.is_(None),
                    )
                ),
            )
            .values(status=OutboxStatus.CANCELLED)
        )
        outbox = await self._session.scalar(
            select(InvitationEmailOutbox)
            .join(
                TripInvitation,
                TripInvitation.id == InvitationEmailOutbox.invitation_id,
            )
            .where(
                InvitationEmailOutbox.status == OutboxStatus.PENDING,
                InvitationEmailOutbox.next_attempt_at <= now,
                *_active_invitation_conditions(),
                TripInvitation.expires_at > now,
            )
            .order_by(InvitationEmailOutbox.created_at, InvitationEmailOutbox.id)
            .with_for_update(skip_locked=True)
        )
        if outbox is None:
            return None
        outbox.status = OutboxStatus.DELIVERING
        outbox.claimed_at = now
        outbox.attempt_count += 1
        await self._session.flush()
        return ClaimedInvitationEmail(
            outbox_id=outbox.id,
            invitation_id=outbox.invitation_id,
            recipient_email=outbox.recipient_email,
            deduplication_key=outbox.deduplication_key,
            attempt_count=outbox.attempt_count,
        )

    async def finish_delivery(
        self,
        outbox_id: UUID,
        status: OutboxStatus,
        now: datetime,
        error_code: str | None = None,
        next_attempt_at: datetime | None = None,
    ) -> None:
        values: dict[str, object] = {
            "status": status,
            "last_error_code": error_code,
        }
        if status is OutboxStatus.SENT:
            values["sent_at"] = now
        if next_attempt_at is not None:
            values["next_attempt_at"] = next_attempt_at
        await self._session.execute(
            update(InvitationEmailOutbox)
            .where(
                InvitationEmailOutbox.id == outbox_id,
                InvitationEmailOutbox.status == OutboxStatus.DELIVERING,
            )
            .values(**values)
        )

    async def record_delivery_event(
        self, event: NormalizedDeliveryEvent, now: datetime
    ) -> None:
        outbox = await self._session.scalar(
            select(InvitationEmailOutbox)
            .where(InvitationEmailOutbox.deduplication_key == event.deduplication_key)
            .with_for_update()
        )
        if outbox is None:
            return
        inserted_event_id = await self._session.scalar(
            insert(InvitationEmailEvent)
            .values(
                outbox_id=outbox.id,
                provider_event_id=event.provider_event_id,
                event_type=event.event_type,
                occurred_at=event.occurred_at,
                created_at=now,
            )
            .on_conflict_do_nothing(index_elements=["provider_event_id"])
            .returning(InvitationEmailEvent.id)
        )
        if inserted_event_id is None:
            return
        if outbox.status is OutboxStatus.COMPLAINED:
            return
        if event.event_type is DeliveryEventType.COMPLAINED:
            outbox.status = OutboxStatus.COMPLAINED
            outbox.last_error_code = "provider_complaint"
        elif outbox.status is OutboxStatus.DELIVERED:
            return
        elif event.event_type is DeliveryEventType.DELIVERED:
            outbox.status = OutboxStatus.DELIVERED
            outbox.last_error_code = None
        elif event.event_type is DeliveryEventType.PERMANENT_FAILURE:
            outbox.status = OutboxStatus.FAILED
            outbox.last_error_code = "provider_permanent_failure"
        elif outbox.status is not OutboxStatus.FAILED:
            outbox.last_error_code = "provider_temporary_failure"
