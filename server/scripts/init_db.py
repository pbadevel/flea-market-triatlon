from src.kit.database.service import database_service

from src.models import Model
from src.config import settings

import asyncio

async def init_db() -> None:
    """
    Инициализация БД
    Создание всех таблиц (только для development)
    """
    async with database_service.get_engine().begin() as conn:
        # В production используем Alembic миграции
        if not settings.is_production():
            print('init db running...')
            await conn.run_sync(Model.metadata.create_all)
            print('db initialized')


if __name__ == "__main__":
    asyncio.run(init_db())