from dataclasses import dataclass
from datetime import UTC, datetime
from hmac import compare_digest
from typing import cast
from uuid import UUID

from fastapi import Request

from tripper_api.auth.auth_errors import (
    AuthenticationRequiredError,
    CsrfValidationError,
)
from tripper_api.auth.auth_repository import AuthRepository
from tripper_api.auth.auth_service import hash_token
from tripper_api.core.database import Database

SESSION_COOKIE_NAME = "tripper_session"
CSRF_COOKIE_NAME = "tripper_csrf"


@dataclass(frozen=True)
class AuthenticatedUser:
    id: UUID
    session_id: UUID
    email: str
    display_name: str


async def require_current_user(request: Request) -> AuthenticatedUser:
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if token is None:
        raise AuthenticationRequiredError
    database = cast(Database, request.app.state.database)
    if database.sessions is None:
        raise RuntimeError("database lifespan has not started")
    async with database.sessions() as session:
        active = await AuthRepository(session).find_active_session(
            hash_token(token), datetime.now(UTC)
        )
    if active is None:
        raise AuthenticationRequiredError
    tripper_session, account = active
    if request.method not in {"GET", "HEAD", "OPTIONS", "TRACE"}:
        submitted_csrf = request.headers.get("X-CSRF-Token")
        csrf_cookie = request.cookies.get(CSRF_COOKIE_NAME)
        if (
            submitted_csrf is None
            or csrf_cookie is None
            or not compare_digest(submitted_csrf, csrf_cookie)
            or not compare_digest(
                hash_token(submitted_csrf), tripper_session.csrf_token_hash
            )
        ):
            raise CsrfValidationError
    return AuthenticatedUser(
        id=account.id,
        session_id=tripper_session.id,
        email=account.email,
        display_name=account.display_name,
    )
