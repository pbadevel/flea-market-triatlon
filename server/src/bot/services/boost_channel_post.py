"""
Публикация поднятого объявления в канал (архив старого поста + новый пост).
Общая логика для планировщика и обработчика очереди канала.
"""

from datetime import datetime, timedelta
from loguru import logger

from src.bot.database.methods import (
    get_user_by_id,
    get_ad_photos,
    update_ad,
    execute_ad_boost,
    log_boost,
)
from src.bot.keyboards.keyboards import ad_in_channel_kb
from src.bot.loader import bot
from src.bot.settings.settings import CHANNEL_ID, CHANNEL_USERNAME, BOT_USERNAME, TEST_MODE as ENV_TEST_MODE

# Согласовано с services.scheduler (тест-режим .env)
_TEST_REGULAR_INTERVAL = timedelta(minutes=30)
_TEST_TRUSTED_INTERVAL = timedelta(minutes=15)


def boost_interval_for_seller(is_trusted: bool, settings) -> timedelta:
    if ENV_TEST_MODE:
        return _TEST_TRUSTED_INTERVAL if is_trusted else _TEST_REGULAR_INTERVAL
    days = settings.trusted_boost_interval_days if is_trusted else settings.regular_boost_interval_days
    return timedelta(days=days)


def max_boosts_for_seller(is_trusted: bool, settings) -> int:
    return settings.trusted_boost_count if is_trusted else settings.regular_boost_count


def daily_limit_for_seller(is_trusted: bool, settings) -> int:
    return settings.trusted_daily_limit if is_trusted else settings.regular_daily_limit


async def publish_boost_to_channel(ad, settings) -> bool:
    """
    Выполнить поднятие: архив + новый пост в канале, обновление БД.
    Возвращает True при успехе (включая отложенное поднятие из-за суточного лимита — как в исходном _execute_boost).
    """
    from src.bot.utils.channel_utils import format_active_caption, format_archive_caption
    from src.bot.database.methods import get_daily_boost_count

    seller = await get_user_by_id(ad.seller_user_id)
    if not seller:
        logger.warning(f"Поднятие #{ad.id}: продавец не найден")
        return False

    is_trusted = getattr(seller, "is_trusted_seller", False)
    interval = boost_interval_for_seller(is_trusted, settings)
    max_boosts = max_boosts_for_seller(is_trusted, settings)
    daily_limit = daily_limit_for_seller(is_trusted, settings)

    daily_count = await get_daily_boost_count(seller.id)
    if daily_count >= daily_limit:
        logger.info(f"Объявление #{ad.id}: суточный лимит исчерпан, откладываем поднятие")
        await update_ad(ad.id, next_boost_at=datetime.utcnow() + timedelta(hours=24))
        return False

    photos = await get_ad_photos(ad.id)
    if not photos:
        logger.warning(f"Объявление #{ad.id}: нет фото для поднятия")
        return False

    channel_target = f"@{CHANNEL_USERNAME}" if CHANNEL_USERNAME else CHANNEL_ID

    if ad.channel_message_id:
        try:
            old_caption = format_archive_caption(ad)
            await bot.edit_message_caption(
                chat_id=channel_target,
                message_id=ad.channel_message_id,
                caption=old_caption,
                parse_mode="HTML",
                reply_markup=None,
            )
        except Exception as e:
            logger.warning(f"Не удалось архивировать пост #{ad.channel_message_id}: {e}")

    cover_file_id = getattr(ad, "cover_file_id", None) or photos[0].file_id
    caption = format_active_caption(ad, is_trusted)

    try:
        new_msg = await bot.send_photo(
            chat_id=channel_target,
            photo=cover_file_id,
            caption=caption,
            parse_mode="HTML",
            reply_markup=ad_in_channel_kb(ad.id, BOT_USERNAME),
        )
    except Exception as e:
        logger.error(f"Не удалось опубликовать новый пост для #{ad.id}: {e}")
        return False

    await execute_ad_boost(ad.id, new_msg.message_id, 0, boost_interval_delta=interval)

    await log_boost(seller.id, ad.id)
    logger.info(f"Автоподнятие выполнено для объявления #{ad.id}")
    return True
