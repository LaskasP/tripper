from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from tripper_api.core.error_handler import error_response
from tripper_api.trip.trip_command_errors import (
    TripDateRangeExcludesPlansError,
    TripEditForbiddenError,
    TripRevisionConflictError,
)
from tripper_api.trip.trip_errors import TripNotFoundError


def register_trip_error_handlers(app: FastAPI) -> None:
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
