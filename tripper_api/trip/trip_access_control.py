from uuid import UUID

from tripper_api.membership.membership_model import TripRole
from tripper_api.membership.membership_read_model import TripAccess
from tripper_api.membership.membership_repository import MembershipRepository
from tripper_api.trip.trip_command_errors import TripEditForbiddenError
from tripper_api.trip.trip_errors import TripNotFoundError


class TripAccessControl:
    def __init__(self, membership_repository: MembershipRepository) -> None:
        self._membership_repository = membership_repository

    async def lock_for_edit(self, trip_id: UUID, account_id: UUID) -> TripAccess:
        access = await self._membership_repository.lock_trip_and_get_membership(
            trip_id, account_id
        )
        if access is None:
            raise TripNotFoundError
        if access.role not in {TripRole.CREATOR, TripRole.CONTRIBUTOR}:
            raise TripEditForbiddenError
        return access
