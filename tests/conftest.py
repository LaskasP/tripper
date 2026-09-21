import asyncio
import os
import sys
from collections.abc import AsyncIterator, Callable, Iterator

import pytest
import pytest_asyncio
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine

from tripper_api.core.config import Settings


def pytest_asyncio_loop_factories(
    config: pytest.Config,
    item: pytest.Item,
) -> dict[str, Callable[[], asyncio.AbstractEventLoop]]:
    del config, item
    factory = (
        asyncio.SelectorEventLoop if sys.platform == "win32" else asyncio.new_event_loop
    )
    return {"selector": factory}


DEFAULT_TEST_DATABASE_URL = (
    "postgresql+psycopg_async://tripper:tripper@127.0.0.1:55432/tripper_test"
)


def _test_database_url() -> str:
    database_url = os.getenv("TRIPPER_TEST_DATABASE_URL", DEFAULT_TEST_DATABASE_URL)
    parsed = make_url(database_url)
    if parsed.host not in {"127.0.0.1", "localhost", "postgres"}:
        raise RuntimeError("test database must use an explicitly allowed host")
    if parsed.database is None or not parsed.database.endswith("_test"):
        raise RuntimeError("test database name must end with '_test'")
    return database_url


@pytest.fixture(scope="session")
def database_settings() -> Iterator[Settings]:
    database_url = _test_database_url()
    config = Config("alembic.ini")
    config.attributes["database_url"] = database_url
    command.upgrade(config, "head")
    yield Settings(database_url=database_url)


@pytest_asyncio.fixture
async def clean_database(
    database_settings: Settings,
) -> AsyncIterator[None]:
    engine = create_async_engine(database_settings.database_url)
    async with engine.begin() as connection:
        await connection.execute(
            text("TRUNCATE TABLE trip_memberships, destinations, trips CASCADE")
        )
    await engine.dispose()
    yield
