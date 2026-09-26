from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from tripper_api.core.database import get_database_session
from tripper_api.membership.membership_repository import MembershipRepository
from tripper_api.publication.publication_repository import PublicationRepository
from tripper_api.publication.publication_service import PublicationService


def get_publication_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> PublicationService:
    return PublicationService(
        session,
        MembershipRepository(session),
        PublicationRepository(session),
    )
