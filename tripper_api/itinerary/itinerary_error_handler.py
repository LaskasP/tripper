from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from tripper_api.core.error_handler import error_response
from tripper_api.itinerary.itinerary_daily_plan_errors import (
    DailyPlanNotFoundError,
    DailyPlanOccupiedError,
    DailyPlanOutOfRangeError,
    DailyPlanRevisionConflictError,
)
from tripper_api.itinerary.itinerary_photo_errors import (
    PhotoCollectionRevisionConflictError,
    PhotoNotFoundError,
    PhotoOrderInvalidError,
)
from tripper_api.itinerary.itinerary_stay_errors import (
    StayNotFoundError,
    StayRevisionConflictError,
)
from tripper_api.itinerary.itinerary_timeline_errors import (
    TimelineCollectionRevisionConflictError,
    TimelineEntryNotFoundError,
    TimelineEntryRevisionConflictError,
    TimelineOrderInvalidError,
)


def register_itinerary_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(DailyPlanNotFoundError)
    async def daily_plan_not_found(
        request: Request, exc: DailyPlanNotFoundError
    ) -> JSONResponse:
        del request, exc
        return error_response(
            status.HTTP_404_NOT_FOUND,
            "daily_plan_not_found",
            "Daily plan not found",
        )

    @app.exception_handler(DailyPlanOccupiedError)
    async def daily_plan_occupied(
        request: Request, exc: DailyPlanOccupiedError
    ) -> JSONResponse:
        del request, exc
        return error_response(
            status.HTTP_409_CONFLICT,
            "daily_plan_occupied",
            "Target date already has a plan",
        )

    @app.exception_handler(DailyPlanOutOfRangeError)
    async def daily_plan_out_of_range(
        request: Request, exc: DailyPlanOutOfRangeError
    ) -> JSONResponse:
        del request, exc
        return error_response(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "daily_plan_out_of_range",
            "Date is outside the Trip",
        )

    @app.exception_handler(DailyPlanRevisionConflictError)
    async def daily_plan_revision_conflict(
        request: Request, exc: DailyPlanRevisionConflictError
    ) -> JSONResponse:
        del request
        return error_response(
            status.HTTP_409_CONFLICT,
            "daily_plan_revision_conflict",
            "This Daily plan changed after editing started",
            current_plan=exc.current_plan,
        )

    @app.exception_handler(StayNotFoundError)
    async def stay_not_found(request: Request, exc: StayNotFoundError) -> JSONResponse:
        del request, exc
        return error_response(
            status.HTTP_404_NOT_FOUND, "stay_not_found", "Stay not found"
        )

    @app.exception_handler(StayRevisionConflictError)
    async def stay_revision_conflict(
        request: Request, exc: StayRevisionConflictError
    ) -> JSONResponse:
        del request
        return error_response(
            status.HTTP_409_CONFLICT,
            "stay_revision_conflict",
            "This Stay changed after editing started",
            current_stay=exc.current_stay,
        )

    @app.exception_handler(TimelineEntryNotFoundError)
    async def timeline_entry_not_found(
        request: Request, exc: TimelineEntryNotFoundError
    ) -> JSONResponse:
        del request, exc
        return error_response(
            status.HTTP_404_NOT_FOUND,
            "timeline_entry_not_found",
            "Timeline entry not found",
        )

    @app.exception_handler(TimelineEntryRevisionConflictError)
    async def timeline_entry_revision_conflict(
        request: Request, exc: TimelineEntryRevisionConflictError
    ) -> JSONResponse:
        del request
        return error_response(
            status.HTTP_409_CONFLICT,
            "timeline_entry_revision_conflict",
            "This Timeline entry changed after editing started",
            latest_values=exc.latest_values,
        )

    @app.exception_handler(TimelineCollectionRevisionConflictError)
    async def timeline_collection_revision_conflict(
        request: Request, exc: TimelineCollectionRevisionConflictError
    ) -> JSONResponse:
        del request
        return error_response(
            status.HTTP_409_CONFLICT,
            "timeline_collection_revision_conflict",
            "This Timeline changed after editing started",
            latest_values=exc.latest_values,
        )

    @app.exception_handler(TimelineOrderInvalidError)
    async def timeline_order_invalid(
        request: Request, exc: TimelineOrderInvalidError
    ) -> JSONResponse:
        del request, exc
        return error_response(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "timeline_order_invalid",
            "Timeline order must contain every entry in chronological order",
        )

    @app.exception_handler(PhotoNotFoundError)
    async def photo_not_found(
        request: Request, exc: PhotoNotFoundError
    ) -> JSONResponse:
        del request, exc
        return error_response(
            status.HTTP_404_NOT_FOUND, "photo_not_found", "Photo not found"
        )

    @app.exception_handler(PhotoCollectionRevisionConflictError)
    async def photo_collection_revision_conflict(
        request: Request, exc: PhotoCollectionRevisionConflictError
    ) -> JSONResponse:
        del request
        return error_response(
            status.HTTP_409_CONFLICT,
            "photo_collection_revision_conflict",
            "These photos changed after editing started",
            latest_values=exc.latest_values,
        )

    @app.exception_handler(PhotoOrderInvalidError)
    async def photo_order_invalid(
        request: Request, exc: PhotoOrderInvalidError
    ) -> JSONResponse:
        del request, exc
        return error_response(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "photo_order_invalid",
            "Photo order must contain every photo exactly once",
        )
