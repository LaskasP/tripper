from datetime import date
from uuid import UUID, uuid4

from tripper_api.itinerary.itinerary_daily_plan_dto import DailyPlanResponse
from tripper_api.itinerary.itinerary_daily_plan_errors import (
    DailyPlanNotFoundError,
    DailyPlanOccupiedError,
    DailyPlanRevisionConflictError,
)
from tripper_api.itinerary.itinerary_daily_plan_model import DailyPlan
from tripper_api.itinerary.itinerary_repository import ItineraryRepository


class DailyPlanService:
    """Owns Daily plan state transitions without depending on other capabilities."""

    def __init__(self, itinerary_repository: ItineraryRepository) -> None:
        self._itinerary_repository = itinerary_repository

    @staticmethod
    def response(plan: DailyPlan) -> DailyPlanResponse:
        return DailyPlanResponse.model_validate(plan, from_attributes=True)

    def _conflict(self, plan: DailyPlan | None) -> DailyPlanRevisionConflictError:
        current = self.response(plan).model_dump(mode="json") if plan else None
        return DailyPlanRevisionConflictError(current)

    async def write(
        self,
        *,
        trip_id: UUID,
        plan_date: date,
        plan_id: UUID | None,
        starting_revision: int,
        destination_id: UUID,
        title: str,
        summary: str,
        background_image: str,
    ) -> DailyPlanResponse:
        plan = await self._itinerary_repository.plan_on_date(trip_id, plan_date)
        if (plan is None) != (plan_id is None) or (
            plan is not None and plan.id != plan_id
        ):
            raise self._conflict(plan)
        if plan is not None and plan.revision != starting_revision:
            raise self._conflict(plan)

        if plan is None:
            plan = DailyPlan(
                id=uuid4(),
                trip_id=trip_id,
                date=plan_date,
                destination_id=destination_id,
                title=title,
                summary=summary,
                background_image=background_image,
            )
            await self._itinerary_repository.add_plan(plan)
        else:
            plan.destination_id = destination_id
            plan.title = title
            plan.summary = summary
            plan.background_image = background_image
            plan.revision += 1
        return self.response(plan)

    async def current(
        self, *, trip_id: UUID, plan_date: date
    ) -> DailyPlanResponse | None:
        plan = await self._itinerary_repository.plan_on_date(trip_id, plan_date)
        return self.response(plan) if plan else None

    async def clear(
        self, *, trip_id: UUID, plan_date: date, starting_revision: int
    ) -> None:
        plan = await self._itinerary_repository.plan_on_date(trip_id, plan_date)
        if plan is None:
            raise DailyPlanNotFoundError
        if plan.revision != starting_revision:
            raise self._conflict(plan)
        await self._itinerary_repository.delete_plan(plan)

    async def move(
        self,
        *,
        trip_id: UUID,
        plan_id: UUID,
        target_date: date,
        starting_revision: int,
    ) -> DailyPlanResponse:
        plan = await self._itinerary_repository.plan_by_id(trip_id, plan_id)
        if plan is None:
            raise DailyPlanNotFoundError
        if plan.revision != starting_revision:
            raise self._conflict(plan)
        occupied = await self._itinerary_repository.plan_on_date(trip_id, target_date)
        if occupied is not None:
            raise DailyPlanOccupiedError
        plan.date = target_date
        plan.revision += 1
        return self.response(plan)
