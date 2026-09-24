from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from tripper_api.core.database import get_database_session
from tripper_api.membership.membership_repository import MembershipRepository
from tripper_api.membership.membership_service import MembershipService


def get_membership_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> MembershipService:
    return MembershipService(session, MembershipRepository(session))
