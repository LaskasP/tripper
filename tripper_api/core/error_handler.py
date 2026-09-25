import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from tripper_api.auth.auth_errors import (
    AuthenticationRequiredError,
    CsrfValidationError,
    InvalidGoogleCredentialError,
)
from tripper_api.destination.destination_errors import (
    TripDestinationInUseError,
    TripDestinationMismatchError,
)
from tripper_api.itinerary.itinerary_daily_plan_errors import (
    DailyPlanNotFoundError,
    DailyPlanOccupiedError,
    DailyPlanOutOfRangeError,
    DailyPlanRevisionConflictError,
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
from tripper_api.trip.trip_command_errors import (
    TripDateRangeExcludesPlansError,
    TripEditForbiddenError,
    TripRevisionConflictError,
)
from tripper_api.trip.trip_errors import (
    PhotoCollectionRevisionConflictError,
    PhotoNotFoundError,
    PhotoOrderInvalidError,
    TripNotFoundError,
)

logger = logging.getLogger(__name__)


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AuthenticationRequiredError)
    async def authentication_required(
        request: Request, exc: AuthenticationRequiredError
    ) -> JSONResponse:
        del request, exc
        return error_response(401, "authentication_required", "Authentication required")

    @app.exception_handler(CsrfValidationError)
    async def csrf_validation_failed(
        request: Request, exc: CsrfValidationError
    ) -> JSONResponse:
        del request, exc
        return error_response(403, "csrf_validation_failed", "CSRF validation failed")

    @app.exception_handler(InvalidGoogleCredentialError)
    async def invalid_google_credential(
        request: Request, exc: InvalidGoogleCredentialError
    ) -> JSONResponse:
        del request, exc
        return error_response(401, "invalid_google_credential", "Google sign-in failed")

    @app.exception_handler(RequestValidationError)
    async def validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        del request, exc
        return error_response(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "validation_error",
            "Request validation failed",
        )

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException) -> JSONResponse:
        del request
        code = (
            "authentication_required"
            if exc.status_code == status.HTTP_401_UNAUTHORIZED
            else f"http_{exc.status_code}"
        )
        message = exc.detail if isinstance(exc.detail, str) else "Request failed"
        return error_response(exc.status_code, code, message)

    @app.exception_handler(TripNotFoundError)
    async def trip_not_found(request: Request, exc: TripNotFoundError) -> JSONResponse:
        del request, exc
        return error_response(
            status.HTTP_404_NOT_FOUND, "trip_not_found", "Trip not found"
        )

    @app.exception_handler(TripEditForbiddenError)
    async def trip_edit_forbidden(
        request: Request, exc: TripEditForbiddenError
    ) -> JSONResponse:
        del request, exc
        return error_response(
            status.HTTP_403_FORBIDDEN,
            "trip_edit_forbidden",
            "Trip editing is not permitted",
        )

    @app.exception_handler(TripDateRangeExcludesPlansError)
    async def trip_date_range_excludes_plans(
        request: Request, exc: TripDateRangeExcludesPlansError
    ) -> JSONResponse:
        del request, exc
        return error_response(
            status.HTTP_409_CONFLICT,
            "trip_date_range_excludes_plans",
            "Move or clear plans outside the new date range first",
        )

    @app.exception_handler(TripDestinationMismatchError)
    async def trip_destination_mismatch(
        request: Request, exc: TripDestinationMismatchError
    ) -> JSONResponse:
        del request, exc
        return error_response(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "trip_destination_mismatch",
            "A destination does not belong to this Trip",
        )

    @app.exception_handler(TripDestinationInUseError)
    async def trip_destination_in_use(
        request: Request, exc: TripDestinationInUseError
    ) -> JSONResponse:
        del request, exc
        return error_response(
            status.HTTP_409_CONFLICT,
            "trip_destination_in_use",
            "Move or clear plans using this destination first",
        )

    @app.exception_handler(TripRevisionConflictError)
    async def trip_revision_conflict(
        request: Request, exc: TripRevisionConflictError
    ) -> JSONResponse:
        del request
        return error_response(
            status.HTTP_409_CONFLICT,
            "trip_revision_conflict",
            "This Trip changed after editing started",
            latest_values=exc.latest_values,
        )

    @app.exception_handler(DailyPlanNotFoundError)
    async def daily_plan_not_found(
        request: Request, exc: DailyPlanNotFoundError
    ) -> JSONResponse:
        del request, exc
        return error_response(404, "daily_plan_not_found", "Daily plan not found")

    @app.exception_handler(DailyPlanOccupiedError)
    async def daily_plan_occupied(
        request: Request, exc: DailyPlanOccupiedError
    ) -> JSONResponse:
        del request, exc
        return error_response(
            409, "daily_plan_occupied", "Target date already has a plan"
        )

    @app.exception_handler(DailyPlanOutOfRangeError)
    async def daily_plan_out_of_range(
        request: Request, exc: DailyPlanOutOfRangeError
    ) -> JSONResponse:
        del request, exc
        return error_response(
            422, "daily_plan_out_of_range", "Date is outside the Trip"
        )

    @app.exception_handler(DailyPlanRevisionConflictError)
    async def daily_plan_revision_conflict(
        request: Request, exc: DailyPlanRevisionConflictError
    ) -> JSONResponse:
        del request
        return error_response(
            409,
            "daily_plan_revision_conflict",
            "This Daily plan changed after editing started",
            current_plan=exc.current_plan,
        )

    @app.exception_handler(StayNotFoundError)
    async def stay_not_found(request: Request, exc: StayNotFoundError) -> JSONResponse:
        del request, exc
        return error_response(404, "stay_not_found", "Stay not found")

    @app.exception_handler(StayRevisionConflictError)
    async def stay_revision_conflict(
        request: Request, exc: StayRevisionConflictError
    ) -> JSONResponse:
        del request
        return error_response(
            409,
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
            404, "timeline_entry_not_found", "Timeline entry not found"
        )

    @app.exception_handler(TimelineEntryRevisionConflictError)
    async def timeline_entry_revision_conflict(
        request: Request, exc: TimelineEntryRevisionConflictError
    ) -> JSONResponse:
        del request
        return error_response(
            409,
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
            409,
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
            422,
            "timeline_order_invalid",
            "Timeline order must contain every entry in chronological order",
        )

    @app.exception_handler(PhotoNotFoundError)
    async def photo_not_found(
        request: Request, exc: PhotoNotFoundError
    ) -> JSONResponse:
        del request, exc
        return error_response(404, "photo_not_found", "Photo not found")

    @app.exception_handler(PhotoCollectionRevisionConflictError)
    async def photo_collection_revision_conflict(
        request: Request, exc: PhotoCollectionRevisionConflictError
    ) -> JSONResponse:
        del request
        return error_response(
            409,
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
            422,
            "photo_order_invalid",
            "Photo order must contain every photo exactly once",
        )

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        del request
        logger.error(
            "Unhandled request error",
            exc_info=(type(exc), exc, exc.__traceback__),
        )
        return error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "internal_server_error",
            "An unexpected error occurred",
        )


def error_response(
    status_code: int,
    code: str,
    message: str,
    **details: object,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message, **details}},
    )
