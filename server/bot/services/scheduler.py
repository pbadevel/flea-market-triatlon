"""
Фоновый планировщик для системы поднятия объявлений.

Задачи (запускаются в цикле каждые 60 секунд):
1. Отправить первичные напоминания (за 24ч до next_boost_at, или за 5 мин в тест-режиме).
2. Отправить повторные напоминания (через 24ч для step=1, каждые 48ч для step≥2).
3. Поставить в очередь подтверждённые автоподнятия и обработать очередь (в канал не чаще одного поднятия за интервал).
4. Перевести в статус unpublished (7 дней без ответа с первого напоминания).
5. Перевести в unpublished (30 дней после последнего поднятия, если все поднятия исчерпаны).
"""

import asyncio
from datetime import datetime, timedelta
from loguru import logger

from src.bot.database.methods import (
    get_boost_settings,
    get_ads_for_reminder, get_ads_for_reminder_test,
    get_ads_for_boost_execution,
    get_ads_for_repeat_reminder,
    get_ads_to_pause,
    get_ads_to_deactivate_after_30_days,
    mark_ad_boost_reminded,
    enqueue_channel_boost,
    pause_ad,
    update_ad,
    get_user_by_id,
)
from src.bot.services.channel_boost_queue import process_channel_boost_queue_once
from src.bot.keyboards.keyboards import boost_reminder_dm_kb
from src.bot.loader import bot
from src.bot.settings.settings import TEST_MODE as ENV_TEST_MODE
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton


# ─── Конфигурация тест-режима (.env TEST_MODE=1) ────────────────────────────
# Все значения жёстко заданы и не зависят от boost_settings в БД.
_TEST_REGULAR_INTERVAL      = timedelta(minutes=30)   # интервал поднятия для обычных
_TEST_TRUSTED_INTERVAL      = timedelta(minutes=15)   # интервал поднятия для доверенных
_TEST_REPEAT_DELTA       = timedelta(minutes=10)    # интервал повторных напоминаний
_TEST_PAUSE_DELTA        = timedelta(minutes=35)    # авто-пауза после X мин без ответа
_TEST_DEACTIVATE_DELTA   = timedelta(minutes=30)    # авто-деактивация через X мин


def _max_boosts(is_trusted: bool, settings) -> int:
    return settings.trusted_boost_count if is_trusted else settings.regular_boost_count


async def _send_reminder(ad, step: int, is_first: bool):
    """Отправить DM-напоминание пользователю."""
    seller = await get_user_by_id(ad.seller_user_id)
    if not seller:
        return

    pub_date = (ad.published_at or ad.created_at).strftime('%d.%m.%Y') if (ad.published_at or ad.created_at) else "—"

    if is_first:
        first_reminder_time_text = "Через 24 часа" if not ENV_TEST_MODE else "Через ~5 минут"
        text = (
            f"⏰ <b>Напоминание об объявлении</b>\n"
            f"№{ad.id} · «{ad.title}»\n\n"
            f"{first_reminder_time_text} будет доступно поднятие объявления в канале.\n"
            f"Если нужно изменить статус — выберите действие:"
        )
    else:
        text = (
            f"⏰ <b>Напоминание об объявлении</b>\n"
            f"№{ad.id} · «{ad.title}»\n\n"
            f"Доступно поднятие объявления в канале.\n"
            f"Если нужно изменить статус — выберите действие:"
        )

    try:
        await bot.send_message(
            chat_id=seller.tg_user_id,
            text=text,
            parse_mode='HTML',
            reply_markup=boost_reminder_dm_kb(ad.id)
        )
        logger.info(f"Напоминание о поднятии отправлено для объявления #{ad.id}, шаг {step}")
    except Exception as e:
        logger.warning(f"Не удалось отправить напоминание для #{ad.id}: {e}")


async def _archive_channel_message(ad):
    """Перевести сообщение объявления в архивный формат."""
    from src.bot.utils.channel_utils import format_archive_caption
    from src.bot.settings.settings import CHANNEL_ID, CHANNEL_USERNAME

    if not ad.channel_message_id:
        return

    channel_target = f"@{CHANNEL_USERNAME}" if CHANNEL_USERNAME else CHANNEL_ID
    try:
        archive_caption = format_archive_caption(ad)
        await bot.edit_message_caption(
            chat_id=channel_target,
            message_id=ad.channel_message_id,
            caption=archive_caption,
            parse_mode='HTML',
            reply_markup=None
        )
    except Exception as e:
        logger.warning(f"Не удалось архивировать пост #{ad.channel_message_id}: {e}")


async def run_scheduler():
    """Основной цикл планировщика (запускается как asyncio task)."""
    logger.info("Планировщик поднятий запущен")

    if ENV_TEST_MODE:
        logger.warning("⚠️  SCHEDULER запущен в TEST_MODE (.env): все интервалы урезаны!")

    while True:
        try:
            settings = await get_boost_settings()

            # === 1. Первичные напоминания ===
            # В ENV TEST_MODE всегда используем тест-окно (4-6 мин), иначе — по DB-флагу
            if ENV_TEST_MODE or settings.test_mode:
                ads_for_reminder = await get_ads_for_reminder_test()
            else:
                ads_for_reminder = await get_ads_for_reminder()

            for ad in ads_for_reminder:
                seller = await get_user_by_id(ad.seller_user_id)
                if not seller:
                    continue
                is_trusted = getattr(seller, 'is_trusted_seller', False)
                if (getattr(ad, 'boost_count', 0) or 0) >= _max_boosts(is_trusted, settings):
                    continue
                await _send_reminder(ad, step=1, is_first=True)
                await mark_ad_boost_reminded(ad.id, step=1, first_reminder=True)

            # === 2. Повторные напоминания ===
            repeat_delta = _TEST_REPEAT_DELTA if ENV_TEST_MODE else None
            ads_for_repeat = await get_ads_for_repeat_reminder(
                step1_delta=repeat_delta,
                stepN_delta=repeat_delta,
            )
            for ad in ads_for_repeat:
                seller = await get_user_by_id(ad.seller_user_id)
                if not seller:
                    continue
                is_trusted = getattr(seller, 'is_trusted_seller', False)
                if (getattr(ad, 'boost_count', 0) or 0) >= _max_boosts(is_trusted, settings):
                    continue

                new_step = (ad.boost_reminder_step or 1) + 1
                # Переносим next_boost_at вперёд на тот же интервал повторного напоминания
                if ENV_TEST_MODE:
                    fwd = _TEST_REPEAT_DELTA
                else:
                    fwd = timedelta(hours=24) if ad.boost_reminder_step == 1 else timedelta(hours=48)
                new_next_boost = (ad.next_boost_at or datetime.utcnow()) + fwd
                await update_ad(ad.id, next_boost_at=new_next_boost)
                await _send_reminder(ad, step=new_step, is_first=False)
                await mark_ad_boost_reminded(ad.id, step=new_step, first_reminder=False)

            # === 3. Выполнение подтверждённых автоподнятий (очередь в канал: 1 пост / интервал) ===
            ads_for_boost = await get_ads_for_boost_execution()
            for ad in ads_for_boost:
                await enqueue_channel_boost(ad.id)
            await process_channel_boost_queue_once(settings)

            # === 4. Авто-пауза ===
            pause_delta = _TEST_PAUSE_DELTA if ENV_TEST_MODE else None
            ads_to_pause = await get_ads_to_pause(threshold_delta=pause_delta)
            for ad in ads_to_pause:
                seller = await get_user_by_id(ad.seller_user_id)
                await _archive_channel_message(ad)
                await pause_ad(ad.id)
                if seller:
                    try:
                        kb = InlineKeyboardBuilder()
                        kb.row(
                            InlineKeyboardButton(
                                text="ОК",
                                callback_data=f"boost_pause_auto_ok:{ad.id}",
                            )
                        )
                        pause_no_answer_text = (
                            "нет ответа на напоминания 7 дней"
                            if not ENV_TEST_MODE
                            else f"нет ответа на напоминания {int(_TEST_PAUSE_DELTA.total_seconds() // 60)} мин"
                        )
                        await bot.send_message(
                            chat_id=seller.tg_user_id,
                            text=(
                                f"⏸️ Объявление №{ad.id} «{ad.title}» было автоматически снято с публикации "
                                f"({pause_no_answer_text}).\n"
                                f"Вы можете вернуть его через «Мои объявления»."
                            ),
                            parse_mode='HTML',
                            reply_markup=kb.as_markup(),
                        )
                    except Exception as e:
                        logger.warning(f"Не удалось уведомить о паузе #{ad.id}: {e}")
                logger.info(f"Объявление #{ad.id} автоматически снято с публикации (нет ответа на напоминания)")

            # === 5. Авто-деактивация (30 дней / TEST: 30 мин) ===
            deact_delta = _TEST_DEACTIVATE_DELTA if ENV_TEST_MODE else None
            ads_to_deactivate = await get_ads_to_deactivate_after_30_days(threshold_delta=deact_delta)
            for ad in ads_to_deactivate:
                seller = await get_user_by_id(ad.seller_user_id)
                if not seller:
                    continue
                is_trusted = getattr(seller, 'is_trusted_seller', False)
                max_boosts = _max_boosts(is_trusted, settings)
                boosts_used = getattr(ad, 'boost_count', 0) or 0
                if boosts_used < max_boosts:
                    continue  # поднятия ещё есть, пропускаем

                from datetime import datetime as _dt
                now = _dt.utcnow()
                last_boost = getattr(ad, 'last_boost_at', None)
                if ENV_TEST_MODE:
                    if last_boost and (now - last_boost) < _TEST_DEACTIVATE_DELTA:
                        continue
                else:
                    if last_boost and (now - last_boost).days < 30:
                        continue

                await _archive_channel_message(ad)
                # Сбрасываем счётчик автоподнятий и поля напоминаний — после возврата объявления будет новый цикл
                await update_ad(
                    ad.id,
                    status='unpublished',
                    inactive_since=now,
                    boost_count=0,
                    next_boost_at=None,
                    boost_reminder_step=0,
                    boost_confirmed=False,
                    boost_reminder_sent_at=None,
                    boost_first_reminder_at=None,
                )
                try:
                    await bot.send_message(
                        chat_id=seller.tg_user_id,
                        text=(
                            f"📴 Объявление №{ad.id} «{ad.title}» автоматически снято с публикации "
                                f"(все поднятия использованы, прошло {('30 дней' if not ENV_TEST_MODE else '30 мин')}).\n"
                            f"Вы можете вернуть его через «Мои объявления» — счётчик поднятий сбросится."
                        ),
                        parse_mode='HTML'
                    )
                except Exception as e:
                    logger.warning(f"Не удалось уведомить о деактивации #{ad.id}: {e}")
                logger.info(f"Объявление #{ad.id} деактивировано (30 дней после последнего поднятия)")

        except Exception as e:
            logger.error(f"Ошибка в планировщике: {e}", exc_info=True)

        await asyncio.sleep(60)  # проверяем каждую минуту
