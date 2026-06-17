"""

RUN THIS SCRIPT ONCE IF DON'T HAVE PHOTO!

"""


# scripts/migrate_files_to_server.py
import asyncio
import os
from pathlib import Path
from aiohttp import ClientSession
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import AdPhoto, AdEditPhoto
from src.kit.database.service import database_service  # твой engine/creator
from src.services.storage import LocalFileStorage

BOT_TOKEN = "8192224436:AAGeom4u2DmXbqWO-iNGBVqzbHJzGpcXf9M"

storage = LocalFileStorage()

async def download_from_telegram(file_id: str, session: ClientSession) -> bytes | None:
    # 1. Получаем путь к файлу
    async with session.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}") as resp:
        data = await resp.json()
        if not data.get("ok"):
            print(f"❌ getFile failed for {file_id}: {data.get('description')}")
            return None
        file_path = data["result"]["file_path"]

    # 2. Скачиваем бинарник
    url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
    async with session.get(url) as resp:
        resp.raise_for_status()
        return await resp.read()

async def migrate_model(model_cls, session: AsyncSession, http_session: ClientSession):
    stmt = select(model_cls).where(model_cls.file_id.isnot(None), model_cls.storage_path.is_(None))
    result = await session.execute(stmt)
    records = result.scalars().all()
    
    print(f"🔄 Найдено {len(records)} записей {model_cls.__name__} для миграции...")
    
    for record in records:
        file_bytes = await download_from_telegram(record.file_id, http_session)
        if not file_bytes:
            continue
            
        # Определяем расширение (Telegram не отдаёт его в API, подставляем .jpg по умолчанию или парсишь content-type)
        storage_path = await storage.save(file_bytes, ".jpg")
        record.storage_path = storage_path
        await session.commit()
        print(f"✅ {model_cls.__name__} id={record.id} -> {storage_path}")

async def main():
    async with ClientSession() as http:
        async with database_service.get_session() as db:
            await migrate_model(AdPhoto, db, http)
            await migrate_model(AdEditPhoto, db, http)

if __name__ == "__main__":
    asyncio.run(main())