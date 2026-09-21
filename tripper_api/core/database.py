from collections.abc import AsyncIterator
from typing import cast

from fastapi import Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from tripper_api.core.config import Settings


class Database:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self.engine: AsyncEngine | None = None
        self.sessions: async_sessionmaker[AsyncSession] | None = None

    async def start(self) -> None:
        engine = create_async_engine(
            self._settings.database_url,
            echo=self._settings.database_echo,
            pool_pre_ping=True,
        )
        try:
            async with engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
        except BaseException:
            await engine.dispose()
            raise
        self.engine = engine
        self.sessions = async_sessionmaker(engine, expire_on_commit=False)

    async def stop(self) -> None:
        if self.engine is not None:
            await self.engine.dispose()
        self.engine = None
        self.sessions = None


async def get_database_session(request: Request) -> AsyncIterator[AsyncSession]:
    database = cast(Database, request.app.state.database)
    if database.sessions is None:
        raise RuntimeError("database lifespan has not started")
    async with database.sessions() as session:
        yield session
