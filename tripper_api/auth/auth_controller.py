from collections.abc import Awaitable, Callable
from hmac import compare_digest
from typing import Annotated, cast

from fastapi import APIRouter, Cookie, Depends, Form, Request, Response, status

from tripper_api.auth.auth_dependencies import get_auth_service, get_identity_verifier
from tripper_api.auth.auth_dto import (
    AccountResponse,
    GoogleConfigResponse,
    SessionResponse,
)
from tripper_api.auth.auth_errors import CsrfValidationError
from tripper_api.auth.auth_identity import GoogleIdentity
from tripper_api.auth.auth_service import AuthService
from tripper_api.core.config import Settings
from tripper_api.core.security import (
    CSRF_COOKIE_NAME,
    SESSION_COOKIE_NAME,
    AuthenticatedUser,
    require_current_user,
)

router = APIRouter(prefix="/api/auth", tags=["authentication"])
COOKIE_MAX_AGE = 7 * 24 * 60 * 60


@router.get("/google/config", response_model=GoogleConfigResponse)
async def google_config(request: Request) -> GoogleConfigResponse:
    settings = cast(Settings, request.app.state.settings)
    return GoogleConfigResponse(client_id=settings.google_client_id)


@router.post("/google", response_model=SessionResponse)
async def google_sign_in(
    response: Response,
    credential: Annotated[str, Form()],
    submitted_csrf: Annotated[str, Form(alias="g_csrf_token")],
    service: Annotated[AuthService, Depends(get_auth_service)],
    verifier: Annotated[
        Callable[[str], Awaitable[GoogleIdentity]], Depends(get_identity_verifier)
    ],
    csrf_cookie: Annotated[str | None, Cookie(alias="g_csrf_token")] = None,
) -> SessionResponse:
    if csrf_cookie is None or not compare_digest(csrf_cookie, submitted_csrf):
        raise CsrfValidationError
    created = await service.sign_in(verifier, credential)
    response.set_cookie(
        SESSION_COOKIE_NAME,
        created.session_token,
        max_age=COOKIE_MAX_AGE,
        secure=True,
        httponly=True,
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        CSRF_COOKIE_NAME,
        created.csrf_token,
        max_age=COOKIE_MAX_AGE,
        secure=True,
        httponly=False,
        samesite="lax",
        path="/",
    )
    return SessionResponse(
        account=AccountResponse(
            id=created.account.id,
            email=created.account.email,
            display_name=created.account.display_name,
        )
    )


@router.get("/session", response_model=SessionResponse)
async def current_session(
    user: Annotated[AuthenticatedUser, Depends(require_current_user)],
) -> SessionResponse:
    return SessionResponse(
        account=AccountResponse(
            id=user.id,
            email=user.email,
            display_name=user.display_name,
        )
    )


@router.post("/sign-out", status_code=status.HTTP_204_NO_CONTENT)
async def sign_out(
    response: Response,
    user: Annotated[AuthenticatedUser, Depends(require_current_user)],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> None:
    await service.sign_out(user.session_id)
    response.delete_cookie(SESSION_COOKIE_NAME, path="/", secure=True, httponly=True)
    response.delete_cookie(CSRF_COOKIE_NAME, path="/", secure=True, httponly=False)
