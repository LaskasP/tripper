from collections.abc import Awaitable, Callable
from typing import Annotated, cast

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from tripper_api.auth.auth_identity import GoogleIdentity
from tripper_api.auth.auth_repository import AuthRepository
from tripper_api.auth.auth_service import AuthService
from tripper_api.core.database import get_database_session


def get_auth_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> AuthService:
    return AuthService(session, AuthRepository(session))


def get_identity_verifier(
    request: Request,
) -> Callable[[str], Awaitable[GoogleIdentity]]:
    return cast(
        Callable[[str], Awaitable[GoogleIdentity]],
        request.app.state.verify_google_identity,
    )
