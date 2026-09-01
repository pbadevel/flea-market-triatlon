# database.py
from collections.abc import AsyncGenerator
from typing import Literal
from contextlib import asynccontextmanager

from src.config import settings
from src.kit.database.postgres import (
    AsyncEngine,
    AsyncSession,
    AsyncSessionMaker,
    create_async_engine as _create_async_engine,
    create_async_sessionmaker,
)

class DatabaseService:
    def __init__(self):
        self._engines: dict[str, AsyncEngine] = {}
        self._sessionmakers: dict[str, AsyncSessionMaker] = {}

    def get_engine(self, process_name: Literal["app", "scheduler", "bot"] = "app") -> AsyncEngine:
        if process_name not in self._engines:
            self._engines[process_name] = _create_async_engine(
                dsn=str(settings.get_postgres_dsn("asyncpg")),
                application_name=f"{settings.ENV}.{process_name}",
                pool_size=settings.DATABASE_POOL_SIZE,
                pool_recycle=settings.DATABASE_POOL_RECYCLE_SECONDS,
                command_timeout=settings.DATABASE_COMMAND_TIMEOUT_SECONDS,
            )
        return self._engines[process_name]

    def get_sessionmaker(self, process_name: Literal["app", "scheduler", "bot"] = "app") -> AsyncSessionMaker:
        if process_name not in self._sessionmakers:
            engine = self.get_engine(process_name)
            self._sessionmakers[process_name] = create_async_sessionmaker(engine)
        return self._sessionmakers[process_name]

    @asynccontextmanager
    async def get_session(self, process_name: Literal["app", "scheduler", "bot"] = "app") -> AsyncGenerator[AsyncSession, None]:
        sessionmaker = self.get_sessionmaker(process_name)
        async with sessionmaker() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            else:
                await session.commit()


database_service = DatabaseService()