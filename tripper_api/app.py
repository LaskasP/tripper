from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from tripper_api.auth.auth_controller import router as auth_router
from tripper_api.auth.auth_identity import GoogleIdentity
from tripper_api.auth.google_identity import GoogleIdentityVerifier
from tripper_api.core.config import Settings
from tripper_api.core.database import Database
from tripper_api.core.error_handler import register_error_handlers
from tripper_api.itinerary.itinerary_daily_plan_controller import (
    router as daily_plan_router,
)
from tripper_api.itinerary.itinerary_photo_controller import router as photo_router
from tripper_api.itinerary.itinerary_stay_controller import router as stay_router
from tripper_api.itinerary.itinerary_timeline_controller import (
    router as timeline_router,
)
from tripper_api.membership.membership_controller import router as membership_router
from tripper_api.trip.trip_command_controller import router as trip_command_router
from tripper_api.trip.trip_controller import router as trip_router


def create_app(
    settings: Settings | None = None,
    verify_google_identity: Callable[[str], Awaitable[GoogleIdentity]] | None = None,
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        resolved_settings = settings or Settings()
        database = Database(resolved_settings)
        google_client = httpx.AsyncClient(timeout=10)
        await database.start()
        app.state.database = database
        app.state.settings = resolved_settings
        google_verifier = GoogleIdentityVerifier(
            resolved_settings.google_client_id, google_client
        )
        app.state.verify_google_identity = (
            verify_google_identity or google_verifier.verify
        )
        try:
            yield
        finally:
            await google_client.aclose()
            await database.stop()

    app = FastAPI(title="Tripper API", lifespan=lifespan)
    app.include_router(auth_router)
    app.include_router(membership_router)
    app.include_router(trip_command_router)
    app.include_router(daily_plan_router)
    app.include_router(stay_router)
    app.include_router(timeline_router)
    app.include_router(photo_router)
    app.include_router(trip_router)
    register_error_handlers(app)

    return app
