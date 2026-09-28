from typing import Annotated, cast

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from tripper_api.core.config import Settings
from tripper_api.core.database import get_database_session
from tripper_api.invitation.invitation_repository import InvitationRepository
from tripper_api.invitation.invitation_service import (
    InvitationDeliveryService,
    InvitationService,
)
from tripper_api.membership.membership_repository import MembershipRepository
from tripper_api.trip.trip_access_control import TripAccessControl


def get_invitation_service(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> InvitationService:
    settings = cast(Settings, request.app.state.settings)
    membership_repository = MembershipRepository(session)
    return InvitationService(
        session,
        TripAccessControl(membership_repository),
        InvitationRepository(session),
        settings.invitation_key_bytes(),
    )


def get_invitation_delivery_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> InvitationDeliveryService:
    return InvitationDeliveryService(session, InvitationRepository(session))
