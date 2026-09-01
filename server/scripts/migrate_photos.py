"""

RUN THIS SCRIPT ONCE IF DON'T HAVE PHOTO!

"""

import asyncio
import os
from pathlib import Path
import aiohttp
from aiohttp import ClientSession
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import AdPhoto, AdEditPhoto
from src.kit.database.service import database_service 
from src.services.storage import LocalFileStorage
from src.logging import get_logger

log = get_logger()

# Конфигурация
BOT_TOKEN = "8192224436:AAGeom4u2DmXbqWO-iNGBVqzbHJzGpcXf9M"
MAX_CONCURRENT_TASKS = 5  # Количество параллельных "потоков" (оптимально для Telegram 5-10)
MAX_RETRIES = 3           # Количество попыток при ошибках сети или лимитах

storage = LocalFileStorage()

async def download_from_telegram_with_retry(file_id: str, http_session: ClientSession) -> bytes | None:
    """Скачивает файл из Telegram с обработкой ошибок сети, лимитов 429 и 3 ретраями."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            # 1. Получаем путь к файлу
            async with http_session.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}") as resp:
                if resp.status == 429:
                    retry_after = int(resp.headers.get("Retry-After", 5))
                    log.warning(f"⚠️ [429] Лимит Telegram. Спим {retry_after} сек. Попытка {attempt}/{MAX_RETRIES}")
                    await asyncio.sleep(retry_after)
                    continue
                
                if resp.status != 200:
                    log.error(f"❌ getFile status {resp.status} для {file_id}")
                    await asyncio.sleep(1 * attempt)
                    continue

                data = await resp.json()
                if not data.get("ok"):
                    log.error(f"❌ getFile failed для {file_id}: {data.get('description')}")
                    return None
                file_path = data["result"]["file_path"]

            # 2. Скачиваем бинарные данные
            url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
            async with http_session.get(url) as resp:
                if resp.status == 429:
                    retry_after = int(resp.headers.get("Retry-After", 5))
                    await asyncio.sleep(retry_after)
                    continue
                
                resp.raise_for_status()
                return await resp.read()

        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            log.warning(f"⏳ Ошибка сети на попытке {attempt}/{MAX_RETRIES} для {file_id}: {e}")
            if attempt < MAX_RETRIES:
                await asyncio.sleep(2 * attempt) # Экспоненциальная задержка между ретраями
            else:
                log.error(f"💥 Все {MAX_RETRIES} попыток исчерпаны для file_id {file_id}")
    return None

async def process_single_record(record, model_name: str, http_session: ClientSession, semaphore: asyncio.Semaphore):
    """Обрабатывает одну запись внутри семафора безопасности."""
    async with semaphore:
        file_bytes = await download_from_telegram_with_retry(record.file_id, http_session)
        if not file_bytes:
            return

        try:
            # Сохраняем на диск сервера
            storage_path = await storage.save(file_bytes, ".jpg")
            record.storage_path = storage_path
            log.info(f"✅ Успешно: {model_name} id={record.id} -> {storage_path}")
        except Exception as e:
            log.error(f"❌ Ошибка сохранения файла на диск для {model_name} id={record.id}: {e}")

async def migrate_model(model_cls, db_session: AsyncSession, http_session: ClientSession):
    stmt = select(model_cls).where(model_cls.file_id.isnot(None), model_cls.storage_path.is_(None))
    result = await db_session.execute(stmt)
    records = result.scalars().all()
    
    if not records:
        log.info(f"🔹 Нет записей {model_cls.__name__} для миграции.")
        return

    log.info(f"🚀 Найдено {len(records)} записей {model_cls.__name__}. Запуск в {MAX_CONCURRENT_TASKS} потоков...")
    
    # Семафор ограничивает количество одновременно работающих задач в сети
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_TASKS)
    
    # Создаем пул асинхронных задач
    tasks = [
        process_single_record(record, model_cls.__name__, http_session, semaphore)
        for record in records
    ]
    
    # Запускаем всё параллельно
    await asyncio.gather(*tasks)
    
    # Делаем ОДИН общий коммит на всю модель в конце — это ускорит скрипт в десятки раз
    await db_session.commit()
    log.info(f"💾 Все изменения для {model_cls.__name__} успешно сохранены в БД.")

async def main():
    # Настраиваем увеличенные таймауты для скачивания больших медиафайлов
    timeout = aiohttp.ClientTimeout(total=30, connect=10, sock_read=15)
    async with ClientSession(timeout=timeout) as http:
        async with database_service.get_session() as db:
            await migrate_model(AdPhoto, db, http)
            await migrate_model(AdEditPhoto, db, http)

if __name__ == "__main__":
    # Запускаем скрипт
    asyncio.run(main())
