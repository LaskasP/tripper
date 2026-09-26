from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from tripper_api.core.error_handler import error_response
from tripper_api.publication.publication_errors import (
    PublicationForbiddenError,
    PublicationRevisionConflictError,
    TripNotReadyToPublishError,
)


def register_publication_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(PublicationForbiddenError)
    async def publication_forbidden(
        request: Request, exc: PublicationForbiddenError
    ) -> JSONResponse:
        del request, exc
        return error_response(
            status.HTTP_403_FORBIDDEN,
            "publication_forbidden",
            "Only the Trip Creator can manage publication",
        )

    @app.exception_handler(TripNotReadyToPublishError)
    async def trip_not_ready(
        request: Request, exc: TripNotReadyToPublishError
    ) -> JSONResponse:
        del request, exc
        return error_response(
            status.HTTP_409_CONFLICT,
            "trip_not_ready_to_publish",
            "Complete valid Trip details and at least one Daily plan first",
        )

    @app.exception_handler(PublicationRevisionConflictError)
    async def publication_conflict(
        request: Request, exc: PublicationRevisionConflictError
    ) -> JSONResponse:
        del request, exc
        return error_response(
            status.HTTP_409_CONFLICT,
            "publication_revision_conflict",
            "Publication changed after this page loaded",
        )
