from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from tripper_api.core.error_handler import error_response
from tripper_api.invitation.invitation_errors import (
    ActiveInvitationExistsError,
    InvalidDeliveryWebhookError,
    InvitationForbiddenError,
    InvitationNotFoundError,
)


def register_invitation_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(InvitationForbiddenError)
    async def invitation_forbidden(
        request: Request, exc: InvitationForbiddenError
    ) -> JSONResponse:
        del request, exc
        return error_response(
            status.HTTP_403_FORBIDDEN,
            "invitation_forbidden",
            "Only the Trip Creator can manage invitations",
        )

    @app.exception_handler(InvitationNotFoundError)
    async def invitation_not_found(
        request: Request, exc: InvitationNotFoundError
    ) -> JSONResponse:
        del request, exc
        return error_response(
            status.HTTP_404_NOT_FOUND,
            "invitation_not_found",
            "Invitation not found",
        )

    @app.exception_handler(ActiveInvitationExistsError)
    async def active_invitation_exists(
        request: Request, exc: ActiveInvitationExistsError
    ) -> JSONResponse:
        del request, exc
        return error_response(
            status.HTTP_409_CONFLICT,
            "active_invitation_exists",
            "An active invitation already exists for this email",
        )

    @app.exception_handler(InvalidDeliveryWebhookError)
    async def invalid_delivery_webhook(
        request: Request, exc: InvalidDeliveryWebhookError
    ) -> JSONResponse:
        del request, exc
        return error_response(
            status.HTTP_401_UNAUTHORIZED,
            "invalid_delivery_webhook",
            "Invalid delivery webhook",
        )
