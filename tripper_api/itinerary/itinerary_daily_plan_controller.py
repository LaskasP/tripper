from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status

from tripper_api.core.security import AuthenticatedUser, require_current_user
from tripper_api.itinerary.itinerary_daily_plan_coordinator import (
    DailyPlanCommandCoordinator,
)
from tripper_api.itinerary.itinerary_daily_plan_dependencies import (
    get_daily_plan_command_coordinator,
)
from tripper_api.itinerary.itinerary_daily_plan_dto import (
    DailyPlanMoveRequest,
    DailyPlanResponse,
    DailyPlanRevisionRequest,
    DailyPlanWriteRequest,
)

router = APIRouter(prefix="/api")


@router.put(
    "/trips/{trip_id}/daily-plans/{plan_date}", response_model=DailyPlanResponse
)
async def write_daily_plan(
    trip_id: UUID,
    plan_date: date,
    request: DailyPlanWriteRequest,
    user: Annotated[AuthenticatedUser, Depends(require_current_user)],
    coordinator: Annotated[
        DailyPlanCommandCoordinator, Depends(get_daily_plan_command_coordinator)
    ],
) -> DailyPlanResponse:
    return await coordinator.write(
        trip_id=trip_id, account_id=user.id, plan_date=plan_date, request=request
    )


@router.delete(
    "/trips/{trip_id}/daily-plans/{plan_date}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def clear_daily_plan(
    trip_id: UUID,
    plan_date: date,
    request: DailyPlanRevisionRequest,
    user: Annotated[AuthenticatedUser, Depends(require_current_user)],
    coordinator: Annotated[
        DailyPlanCommandCoordinator, Depends(get_daily_plan_command_coordinator)
    ],
) -> Response:
    await coordinator.clear(
        trip_id=trip_id, account_id=user.id, plan_date=plan_date, request=request
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/trips/{trip_id}/daily-plans/{plan_id}/move",
    response_model=DailyPlanResponse,
)
async def move_daily_plan(
    trip_id: UUID,
    plan_id: UUID,
    request: DailyPlanMoveRequest,
    user: Annotated[AuthenticatedUser, Depends(require_current_user)],
    coordinator: Annotated[
        DailyPlanCommandCoordinator, Depends(get_daily_plan_command_coordinator)
    ],
) -> DailyPlanResponse:
    return await coordinator.move(
        trip_id=trip_id, account_id=user.id, plan_id=plan_id, request=request
    )
