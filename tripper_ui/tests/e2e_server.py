import asyncio
import os
from dataclasses import dataclass
from pathlib import Path

import uvicorn
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from tripper_api.app import create_app
from tripper_api.auth.auth_identity import GoogleIdentity
from tripper_api.core.config import Settings

UI_ROOT = Path(__file__).resolve().parents[1]
DIST_DIR = UI_ROOT / "dist"

settings = Settings(
    database_url=os.getenv(
        "TRIPPER_TEST_DATABASE_URL",
        "postgresql+psycopg_async://tripper:tripper@127.0.0.1:55432/tripper_test",
    ),
    google_client_id="test-client-id",
)


@dataclass
class E2EGoogleIdentityVerifier:
    async def verify(self, credential: str) -> GoogleIdentity:
        if credential != "e2e-google-credential":
            raise ValueError("unexpected E2E credential")
        return GoogleIdentity(
            issuer="https://accounts.google.com",
            subject="e2e-google-subject",
            email="traveller@example.com",
            display_name="E2E Traveller",
        )


app = create_app(
    settings,
    verify_google_identity=E2EGoogleIdentityVerifier().verify,
)


@app.get("/tripper/my-trips", include_in_schema=False)
def my_trips_page() -> FileResponse:
    return FileResponse(DIST_DIR / "index.html")


@app.get("/tripper/trips/{trip_id}/edit", include_in_schema=False)
def trip_planner_page(trip_id: str) -> FileResponse:
    del trip_id
    return FileResponse(DIST_DIR / "index.html")


@app.get("/tripper/trips/{trip_id}", include_in_schema=False)
def participant_guide_page(trip_id: str) -> FileResponse:
    del trip_id
    return FileResponse(DIST_DIR / "index.html")


app.mount("/tripper", StaticFiles(directory=DIST_DIR, html=True), name="frontend")


if __name__ == "__main__":
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=18014,
        loop=asyncio.SelectorEventLoop,
    )
