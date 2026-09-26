from uuid import UUID

from sqlalchemy import exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from tripper_api.destination.destination_model import Destination
from tripper_api.itinerary.itinerary_daily_plan_model import DailyPlan
from tripper_api.itinerary.itinerary_photo_model import Photo
from tripper_api.itinerary.itinerary_stay_model import Stay
from tripper_api.itinerary.itinerary_timeline_model import TimelineEntry


class PublicationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def destination_metadata(self, trip_id: UUID) -> list[tuple[str, str]]:
        return list(
            (
                await self._session.execute(
                    select(Destination.name, Destination.timezone).where(
                        Destination.trip_id == trip_id
                    )
                )
            )
            .tuples()
            .all()
        )

    async def has_populated_plan(self, trip_id: UUID) -> bool:
        return bool(
            await self._session.scalar(
                select(
                    or_(
                        exists().where(
                            DailyPlan.trip_id == trip_id,
                            or_(
                                func.btrim(DailyPlan.title) != "",
                                func.btrim(DailyPlan.summary) != "",
                                func.btrim(DailyPlan.background_image) != "",
                            ),
                        ),
                        exists().where(
                            TimelineEntry.daily_plan_id == DailyPlan.id,
                            DailyPlan.trip_id == trip_id,
                        ),
                        exists().where(
                            Stay.daily_plan_id == DailyPlan.id,
                            DailyPlan.trip_id == trip_id,
                        ),
                        exists().where(
                            Photo.daily_plan_id == DailyPlan.id,
                            DailyPlan.trip_id == trip_id,
                        ),
                    )
                )
            )
        )
