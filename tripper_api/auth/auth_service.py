from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from secrets import token_urlsafe
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from tripper_api.auth.auth_identity import GoogleIdentity
from tripper_api.auth.auth_model import Account, TripperSession
from tripper_api.auth.auth_repository import AuthRepository

SESSION_LIFETIME = timedelta(days=7)


@dataclass(frozen=True)
class CreatedSession:
    account: Account
    session_token: str
    csrf_token: str


def hash_token(token: str) -> str:
    return sha256(token.encode()).hexdigest()


class AuthService:
    def __init__(self, session: AsyncSession, repository: AuthRepository) -> None:
        self._session = session
        self._repository = repository

    async def sign_in(
        self,
        verify_google_identity: Callable[[str], Awaitable[GoogleIdentity]],
        credential: str,
    ) -> CreatedSession:
        identity = await verify_google_identity(credential)
        now = datetime.now(UTC)
        session_token = token_urlsafe(32)
        csrf_token = token_urlsafe(32)
        async with self._session.begin():
            account = await self._repository.upsert_account(identity)
            await self._repository.add_session(
                TripperSession(
                    account_id=account.id,
                    token_hash=hash_token(session_token),
                    csrf_token_hash=hash_token(csrf_token),
                    created_at=now,
                    expires_at=now + SESSION_LIFETIME,
                )
            )
        return CreatedSession(account, session_token, csrf_token)

    async def sign_out(self, session_id: UUID) -> None:
        async with self._session.begin():
            await self._repository.delete_session(session_id)
