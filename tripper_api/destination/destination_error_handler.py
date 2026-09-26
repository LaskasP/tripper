from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from tripper_api.core.error_handler import error_response
from tripper_api.destination.destination_errors import (
    TripDestinationInUseError,
    TripDestinationMismatchError,
)


def register_destination_error_handlers(app: FastAPI) -> None:
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
