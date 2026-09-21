from datetime import datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from tripper_api.auth.auth_identity import GoogleIdentity
from tripper_api.auth.auth_model import Account, TripperSession


class AuthRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert_account(self, identity: GoogleIdentity) -> Account:
        statement = (
            insert(Account)
            .values(
                issuer=identity.issuer,
                subject=identity.subject,
                email=identity.email,
                display_name=identity.display_name,
            )
            .on_conflict_do_update(
                constraint="uq_account_google_identity",
                set_={
                    "email": identity.email,
                    "display_name": identity.display_name,
                },
            )
            .returning(Account)
        )
        return (await self._session.execute(statement)).scalar_one()

    async def add_session(self, tripper_session: TripperSession) -> None:
        self._session.add(tripper_session)
        await self._session.flush()

    async def delete_session(self, session_id: object) -> None:
        tripper_session = await self._session.get(TripperSession, session_id)
        if tripper_session is not None:
            await self._session.delete(tripper_session)

    async def find_active_session(
        self, token_hash: str, now: datetime
    ) -> tuple[TripperSession, Account] | None:
        statement = (
            select(TripperSession, Account)
            .join(Account, Account.id == TripperSession.account_id)
            .where(
                TripperSession.token_hash == token_hash,
                TripperSession.expires_at > now,
            )
        )
        row = (await self._session.execute(statement)).one_or_none()
        if row is None:
            return None
        return row._tuple()
