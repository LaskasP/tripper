from typing import Annotated

from fastapi import APIRouter, Depends

from tripper_api.core.security import AuthenticatedUser, require_current_user
from tripper_api.membership.membership_dependencies import get_membership_service
from tripper_api.membership.membership_dto import TripSummaryResponse
from tripper_api.membership.membership_service import MembershipService

router = APIRouter(prefix="/api")


@router.get("/me/trips", response_model=list[TripSummaryResponse])
async def list_my_trips(
    user: Annotated[AuthenticatedUser, Depends(require_current_user)],
    service: Annotated[MembershipService, Depends(get_membership_service)],
) -> list[TripSummaryResponse]:
    return await service.list_for_account(user.id)
