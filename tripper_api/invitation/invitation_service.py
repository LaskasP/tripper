from datetime import UTC, datetime
from hashlib import sha256
from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from tripper_api.core.constants import INVITATION_LIFETIME
from tripper_api.invitation.invitation_dto import InvitationResponse
from tripper_api.invitation.invitation_errors import (
    ActiveInvitationExistsError,
    InvitationForbiddenError,
    InvitationNotFoundError,
)
from tripper_api.invitation.invitation_model import (
    InvitationEmailOutbox,
    OutboxStatus,
    TripInvitation,
)
from tripper_api.invitation.invitation_read_model import NormalizedDeliveryEvent
from tripper_api.invitation.invitation_repository import InvitationRepository
from tripper_api.invitation.invitation_secret import derive_invitation_secret
from tripper_api.membership.membership_model import TripRole
from tripper_api.trip.trip_access_control import TripAccessControl


class InvitationService:
    def __init__(
        self,
        session: AsyncSession,
        access_control: TripAccessControl,
        invitation_repository: InvitationRepository,
        token_key: bytes,
    ) -> None:
        self._session = session
        self._access_control = access_control
        self._invitations = invitation_repository
        self._token_key = token_key

    async def list(self, trip_id: UUID, account_id: UUID) -> list[InvitationResponse]:
        async with self._session.begin():
            await self._require_creator(trip_id, account_id)
            invitations = await self._invitations.list_active(
                trip_id, datetime.now(UTC)
            )
            return [InvitationResponse.model_validate(item) for item in invitations]

    async def create(
        self, trip_id: UUID, account_id: UUID, email: str, role: TripRole
    ) -> InvitationResponse:
        now = datetime.now(UTC)
        async with self._session.begin():
            await self._require_creator(trip_id, account_id)
            await self._invitations.invalidate_expired_for_email(trip_id, email, now)
            try:
                invitation = await self._create_invitation(trip_id, email, role, now)
            except IntegrityError as error:
                raise ActiveInvitationExistsError from error
            return self._response(invitation)

    async def revoke(
        self, trip_id: UUID, invitation_id: UUID, account_id: UUID
    ) -> None:
        async with self._session.begin():
            await self._require_creator(trip_id, account_id)
            invitation = await self._invitations.active_for_update(
                trip_id, invitation_id
            )
            if invitation is None:
                raise InvitationNotFoundError
            invitation.revoked_at = datetime.now(UTC)
            await self._invitations.cancel_delivery(invitation.id)

    async def replace(
        self, trip_id: UUID, invitation_id: UUID, account_id: UUID
    ) -> InvitationResponse:
        now = datetime.now(UTC)
        async with self._session.begin():
            await self._require_creator(trip_id, account_id)
            invitation = await self._invitations.active_for_update(
                trip_id, invitation_id
            )
            if invitation is None:
                raise InvitationNotFoundError
            invitation.replaced_at = now
            await self._invitations.cancel_delivery(invitation.id)
            replacement = await self._create_invitation(
                trip_id, invitation.email, invitation.role, now
            )
            return self._response(replacement)

    async def _create_invitation(
        self, trip_id: UUID, email: str, role: TripRole, now: datetime
    ) -> TripInvitation:
        invitation_id = uuid4()
        secret = derive_invitation_secret(invitation_id, self._token_key)
        invitation = TripInvitation(
            id=invitation_id,
            trip_id=trip_id,
            email=email,
            role=role,
            token_hash=sha256(secret.encode()).hexdigest(),
            created_at=now,
            expires_at=now + INVITATION_LIFETIME,
        )
        await self._invitations.add_invitation(invitation)
        await self._invitations.add_outbox(
            InvitationEmailOutbox(
                invitation_id=invitation.id,
                deduplication_key=f"trip-invitation:{invitation.id}",
                recipient_email=email,
                status="pending",
                created_at=now,
                next_attempt_at=now,
            )
        )
        return invitation

    @staticmethod
    def _response(invitation: TripInvitation) -> InvitationResponse:
        return InvitationResponse(
            id=invitation.id,
            email=invitation.email,
            role=invitation.role,
            created_at=invitation.created_at,
            expires_at=invitation.expires_at,
            delivery_status=OutboxStatus.PENDING,
        )

    async def _require_creator(self, trip_id: UUID, account_id: UUID) -> None:
        access = await self._access_control.lock_for_edit(trip_id, account_id)
        if access.role is not TripRole.CREATOR:
            raise InvitationForbiddenError


class InvitationDeliveryService:
    def __init__(
        self, session: AsyncSession, invitation_repository: InvitationRepository
    ) -> None:
        self._session = session
        self._invitations = invitation_repository

    async def record(self, event: NormalizedDeliveryEvent) -> None:
        async with self._session.begin():
            await self._invitations.record_delivery_event(event, datetime.now(UTC))
