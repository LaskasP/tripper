import asyncio
import os
from pathlib import Path
from uuid import UUID

import uvicorn
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from tripper_api.app import create_app
from tripper_api.core.config import Settings
from tripper_api.core.security import AuthenticatedUser, require_current_user

UI_ROOT = Path(__file__).resolve().parents[1]
DIST_DIR = UI_ROOT / "dist"

settings = Settings(
    database_url=os.getenv(
        "TRIPPER_TEST_DATABASE_URL",
        "postgresql+psycopg_async://tripper:tripper@127.0.0.1:55432/tripper_test",
    )
)
app = create_app(settings)
app.dependency_overrides[require_current_user] = lambda: AuthenticatedUser(
    id=UUID("aa158969-c991-4d90-b615-6b5bcea4f5f0")
)


@app.get("/tripper/my-trips", include_in_schema=False)
def my_trips_page() -> FileResponse:
    return FileResponse(DIST_DIR / "index.html")


app.mount("/tripper", StaticFiles(directory=DIST_DIR, html=True), name="frontend")


if __name__ == "__main__":
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=18014,
        loop=asyncio.SelectorEventLoop,
    )
