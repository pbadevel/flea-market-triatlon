"""
Миграции БД. Запуск:
  python -m src.migrations
"""
import asyncio
from sqlalchemy import text
from src.kit.database.service import database_service
from src.logging import get_logger

log = get_logger()

MIGRATIONS = [
    # v1 — email_confirm_token для подтверждения регистрации
    "ALTER TABLE user_credentials ADD COLUMN IF NOT EXISTS email_confirm_token VARCHAR(128)",
]


async def run_migrations():
    async with database_service.get_session() as session:
        for sql in MIGRATIONS:
            try:
                await session.execute(text(sql))
                log.info("Migration OK: %s", sql[:60])
            except Exception as e:
                log.error("Migration FAIL: %s — %s", sql[:60], e)
        await session.commit()
    log.info("All migrations applied ✅")


if __name__ == "__main__":
    asyncio.run(run_migrations())
