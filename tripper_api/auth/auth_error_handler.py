from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from tripper_api.auth.auth_errors import (
    AuthenticationRequiredError,
    CsrfValidationError,
    InvalidGoogleCredentialError,
)
from tripper_api.core.error_handler import error_response


def register_auth_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AuthenticationRequiredError)
    async def authentication_required(
        request: Request, exc: AuthenticationRequiredError
    ) -> JSONResponse:
        del request, exc
        return error_response(
            status.HTTP_401_UNAUTHORIZED,
            "authentication_required",
            "Authentication required",
        )

    @app.exception_handler(CsrfValidationError)
    async def csrf_validation_failed(
        request: Request, exc: CsrfValidationError
    ) -> JSONResponse:
        del request, exc
        return error_response(
            status.HTTP_403_FORBIDDEN,
            "csrf_validation_failed",
            "CSRF validation failed",
        )

    @app.exception_handler(InvalidGoogleCredentialError)
    async def invalid_google_credential(
        request: Request, exc: InvalidGoogleCredentialError
    ) -> JSONResponse:
        del request, exc
        return error_response(
            status.HTTP_401_UNAUTHORIZED,
            "invalid_google_credential",
            "Google sign-in failed",
        )
