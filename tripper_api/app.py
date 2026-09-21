from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from tripper_api.core.config import Settings
from tripper_api.core.database import Database
from tripper_api.core.errors import register_error_handlers
from tripper_api.trip.trip_controller import router as trip_router


def create_app(settings: Settings | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        resolved_settings = settings or Settings()
        database = Database(resolved_settings)
        await database.start()
        app.state.database = database
        try:
            yield
        finally:
            await database.stop()

    app = FastAPI(title="Tripper API", lifespan=lifespan)
    app.include_router(trip_router)
    register_error_handlers(app)

    return app
