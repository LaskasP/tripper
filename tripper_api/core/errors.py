import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from tripper_api.auth.google_identity import InvalidGoogleCredentialError
from tripper_api.core.security import AuthenticationRequiredError, CsrfValidationError
from tripper_api.trip.trip_errors import (
    TripDateRangeExcludesPlansError,
    TripDestinationInUseError,
    TripDestinationMismatchError,
    TripEditForbiddenError,
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


def error_response(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message}},
    )
