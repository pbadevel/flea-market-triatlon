"""
Глобальная очередь публикаций поднятий в канал: не чаще одного поста за заданный интервал.
Первичная публикация объявления модератором не использует эту очередь и не влияет на таймер.
"""

import asyncio
from datetime import datetime, timedelta

from loguru import logger

from src.bot.database.methods import (
    get_boost_settings,
    get_ad_by_id,
    pop_oldest_channel_boost_queue_ad_id,
    channel_boost_queue_size,
    update_boost_settings,
)
from src.bot.services.boost_channel_post import publish_boost_to_channel
from src.bot.settings.settings import TEST_MODE as ENV_TEST_MODE

_CHANNEL_BOOST_GAP = timedelta(minutes=10)
_TEST_CHANNEL_BOOST_GAP = timedelta(minutes=1)


def channel_boost_min_gap() -> timedelta:
    return _TEST_CHANNEL_BOOST_GAP if ENV_TEST_MODE else _CHANNEL_BOOST_GAP


_boost_queue_lock = asyncio.Lock()


async def process_channel_boost_queue_once(settings=None) -> bool:
    """
    Опубликовать одно поднятие из головы очереди, если с прошлой успешной публикации поднятия прошёл интервал.
    Невалидные записи пропускаются без расхода слота по времени.
    Возвращает True, если пост в канале реально выполнен.
    """
    if settings is None:
        settings = await get_boost_settings()

    async with _boost_queue_lock:
        while True:
            if await channel_boost_queue_size() == 0:
                return False

            settings = await get_boost_settings()
            now = datetime.utcnow()
            last = settings.last_channel_boost_post_at
            gap = channel_boost_min_gap()
            if last and (now - last) < gap:
                return False

            ad_id = await pop_oldest_channel_boost_queue_ad_id()
            if ad_id is None:
                return False

            ad = await get_ad_by_id(ad_id)
            if not ad or ad.status != "approved":
                logger.info(f"Очередь поднятий: пропуск #{ad_id} (объявление не найдено или не активно)")
                continue

            ok = await publish_boost_to_channel(ad, settings)
            if ok:
                await update_boost_settings(last_channel_boost_post_at=datetime.utcnow())
                return True

            logger.warning(f"Очередь поднятий: публикация #{ad_id} не выполнена, остальные ждут следующего слота")
            return False
