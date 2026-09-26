from datetime import UTC, datetime
from typing import Annotated, cast
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Request, Response, status

from tripper_api.core.config import Settings
from tripper_api.core.security import AuthenticatedUser, require_current_user
from tripper_api.invitation.invitation_dependencies import (
    get_invitation_delivery_service,
    get_invitation_service,
)
from tripper_api.invitation.invitation_dto import (
    InvitationCreateRequest,
    InvitationResponse,
)
from tripper_api.invitation.invitation_errors import InvalidDeliveryWebhookError
from tripper_api.invitation.invitation_provider import normalize_mailgun_event
from tripper_api.invitation.invitation_service import (
    InvitationDeliveryService,
    InvitationService,
)

router = APIRouter(prefix="/api/trips/{trip_id}/invitations", tags=["invitations"])
delivery_router = APIRouter(prefix="/api/email/mailgun", tags=["email-delivery"])


@router.get("", response_model=list[InvitationResponse])
async def list_invitations(
    trip_id: UUID,
    user: Annotated[AuthenticatedUser, Depends(require_current_user)],
    service: Annotated[InvitationService, Depends(get_invitation_service)],
) -> list[InvitationResponse]:
    return await service.list(trip_id, user.id)


@router.post("", response_model=InvitationResponse, status_code=status.HTTP_201_CREATED)
async def create_invitation(
    trip_id: UUID,
    request: InvitationCreateRequest,
    user: Annotated[AuthenticatedUser, Depends(require_current_user)],
    service: Annotated[InvitationService, Depends(get_invitation_service)],
) -> InvitationResponse:
    return await service.create(trip_id, user.id, request.email, request.role)


@router.delete("/{invitation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_invitation(
    trip_id: UUID,
    invitation_id: UUID,
    user: Annotated[AuthenticatedUser, Depends(require_current_user)],
    service: Annotated[InvitationService, Depends(get_invitation_service)],
) -> Response:
    await service.revoke(trip_id, invitation_id, user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{invitation_id}/replace",
    response_model=InvitationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def replace_invitation(
    trip_id: UUID,
    invitation_id: UUID,
    user: Annotated[AuthenticatedUser, Depends(require_current_user)],
    service: Annotated[InvitationService, Depends(get_invitation_service)],
) -> InvitationResponse:
    return await service.replace(trip_id, invitation_id, user.id)


@delivery_router.post("/events", status_code=status.HTTP_204_NO_CONTENT)
async def record_mailgun_event(
    payload: Annotated[object, Body()],
    request: Request,
    service: Annotated[
        InvitationDeliveryService, Depends(get_invitation_delivery_service)
    ],
) -> Response:
    settings = cast(Settings, request.app.state.settings)
    if settings.mailgun_webhook_signing_key is None:
        raise InvalidDeliveryWebhookError
    event = normalize_mailgun_event(
        payload,
        settings.mailgun_webhook_signing_key.get_secret_value(),
        datetime.now(UTC),
    )
    if event is not None:
        await service.record(event)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
