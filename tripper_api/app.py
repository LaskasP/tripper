from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from tripper_api.api_error_handlers import register_api_error_handlers
from tripper_api.api_routes import register_api_routes
from tripper_api.auth.auth_identity import GoogleIdentity
from tripper_api.auth.google_identity import GoogleIdentityVerifier
from tripper_api.core.config import Settings
from tripper_api.core.database import Database


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
    register_api_routes(app)
    register_api_error_handlers(app)

    return app
