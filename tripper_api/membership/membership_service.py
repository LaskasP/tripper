from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from tripper_api.membership.membership_dto import TripSummaryResponse
from tripper_api.membership.membership_repository import MembershipRepository


class MembershipService:
    def __init__(self, session: AsyncSession, repository: MembershipRepository) -> None:
        self._session = session
        self._repository = repository

    async def list_for_account(self, account_id: UUID) -> list[TripSummaryResponse]:
        async with self._session.begin():
            trips = await self._repository.list_for_account(account_id)
        return [TripSummaryResponse.model_validate(trip) for trip in trips]
