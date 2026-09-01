"""
Обработчики поднятия объявлений (п.1.1 — Ручное поднятие и напоминания).

Колбэки:
  my_ad_boost:{id}      — экран информации о поднятии (из «Мои объявления»)
  boost_not_ready:{id}  — алерт «время ещё не пришло»
  boost_execute:{id}    — немедленное поднятие
  boost_confirm:{id}    — подтверждение поднятия из ЛС-напоминания
  boost_unpublish:{id}  — снятие с публикации из ЛС-напоминания
  boost_queue_to_my_ads   — «К объявлениям» из экрана очереди поднятия
"""

from datetime import datetime, timezone, timedelta
from loguru import logger

MSK = timezone(timedelta(hours=3))


def _format_dt_msk(utc_dt):
    """Форматирует наивный UTC datetime в строку по московскому времени (МСК)."""
    if utc_dt is None:
        return ""
    utc_dt = utc_dt.replace(tzinfo=timezone.utc)
    msk_dt = utc_dt.astimezone(MSK)
    return msk_dt.strftime('%d.%m.%Y %H:%M') + " МСК"

from aiogram import types
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

from src.bot.database.methods import (
    get_ad_by_id, get_user_by_tg_id, get_user_by_id, get_ad_photos, update_ad,
    delete_edits_for_ad,
    get_boost_settings, get_daily_boost_count,
    mark_ad_boost_confirmed,
    enqueue_channel_boost,
    is_ad_in_channel_boost_queue,
    remove_channel_boost_from_queue,
    get_user_ads,
)
from src.bot.keyboards.keyboards import boost_info_kb
from src.bot.keyboards.key_text import BACK_BTN
from src.bot.loader import bot
from src.bot.services.channel_boost_queue import process_channel_boost_queue_once


async def my_ad_boost_callback(callback: types.CallbackQuery, state: FSMContext):
    """Показать экран информации о поднятии объявления."""
    await callback.answer()

    ad_id = int(callback.data.split(':')[1])
    ad = await get_ad_by_id(ad_id)
    if not ad:
        await callback.answer("❌ Объявление не найдено.", show_alert=True)
        return

    user = await get_user_by_tg_id(callback.from_user.id)
    if not user or ad.seller_user_id != user.id:
        await callback.answer("❌ Это не ваше объявление.", show_alert=True)
        return

    settings = await get_boost_settings()
    is_trusted = getattr(user, 'is_trusted_seller', False)
    max_boosts = settings.trusted_boost_count if is_trusted else settings.regular_boost_count
    interval_days = settings.trusted_boost_interval_days if is_trusted else settings.regular_boost_interval_days

    boosts_used = getattr(ad, 'boost_count', 0) or 0
    boosts_left = max(0, max_boosts - boosts_used)
    next_boost_at = getattr(ad, 'next_boost_at', None)
    now = datetime.utcnow()

    boost_available = boosts_left > 0 and (next_boost_at is None or now >= next_boost_at)

    info_text = (
        f"🚀 <b>Поднятие объявления #{ad_id}</b>\n\n"
        f"Вам доступно <b>{max_boosts}</b> автоподнятия(-й) "
        f"с периодичностью <b>{interval_days} дней</b>\n\n"
        f"Использовано: {boosts_used}/{max_boosts}\n"
    )
    if not boost_available and next_boost_at and boosts_left > 0:
        info_text += f"Следующее поднятие доступно: {_format_dt_msk(next_boost_at)}\n"

    try:
        await callback.message.edit_text(
            info_text, parse_mode='HTML',
            reply_markup=boost_info_kb(ad_id, boost_available, boosts_left)
        )
    except Exception:
        await callback.message.answer(
            info_text, parse_mode='HTML',
            reply_markup=boost_info_kb(ad_id, boost_available, boosts_left)
        )


async def my_ad_boost_not_ready_callback(callback: types.CallbackQuery, state: FSMContext):
    """Алерт: время для поднятия ещё не пришло."""
    ad_id = int(callback.data.split(':')[1])
    ad = await get_ad_by_id(ad_id)
    next_boost_at = getattr(ad, 'next_boost_at', None) if ad else None
    msg = (
        f"⏳ Поднятие будет доступно {_format_dt_msk(next_boost_at).replace(' ', ' в ', 1)}."
        if next_boost_at else "⏳ Поднятие пока недоступно."
    )
    await callback.answer(msg, show_alert=True)


async def my_ad_boost_execute_callback(callback: types.CallbackQuery, state: FSMContext):
    """Выполнить немедленное поднятие объявления."""
    await callback.answer()

    ad_id = int(callback.data.split(':')[1])
    ad = await get_ad_by_id(ad_id)
    if not ad:
        await callback.answer("❌ Объявление не найдено.", show_alert=True)
        return

    user = await get_user_by_tg_id(callback.from_user.id)
    if not user or ad.seller_user_id != user.id:
        await callback.answer("❌ Это не ваше объявление.", show_alert=True)
        return

    if ad.status != 'approved':
        await callback.answer("❌ Можно поднять только активное объявление.", show_alert=True)
        return

    from src.bot.settings.settings import TEST_MODE
    settings = await get_boost_settings()
    is_trusted = getattr(user, 'is_trusted_seller', False)
    max_boosts = settings.trusted_boost_count if is_trusted else settings.regular_boost_count
    interval_days = settings.trusted_boost_interval_days if is_trusted else settings.regular_boost_interval_days
    daily_limit = settings.trusted_daily_limit if is_trusted else settings.regular_daily_limit
    # В тест-режиме используем короткие интервалы (минуты), иначе — дни из настроек
    if TEST_MODE:
        from src.bot.services.scheduler import _TEST_REGULAR_INTERVAL, _TEST_TRUSTED_INTERVAL
        boost_interval_delta = _TEST_TRUSTED_INTERVAL if is_trusted else _TEST_REGULAR_INTERVAL
    else:
        boost_interval_delta = None

    boosts_used = getattr(ad, 'boost_count', 0) or 0
    if boosts_used >= max_boosts:
        await callback.answer("❌ Лимит поднятий исчерпан для этого объявления.", show_alert=True)
        return

    now = datetime.utcnow()
    next_boost_at = getattr(ad, 'next_boost_at', None)
    if next_boost_at and now < next_boost_at:
        await callback.answer(
            f"⏳ Поднятие будет доступно {_format_dt_msk(next_boost_at).replace(' ', ' в ', 1)}.",
            show_alert=True
        )
        return

    daily_count = await get_daily_boost_count(user.id)
    if daily_count >= daily_limit:
        await callback.answer(
            f"❌ Достигнут суточный лимит поднятий ({daily_limit}). Попробуйте завтра.",
            show_alert=True
        )
        return

    photos = await get_ad_photos(ad_id)
    if not photos:
        await callback.answer("❌ У объявления нет фото.", show_alert=True)
        return

    if not await enqueue_channel_boost(ad_id):
        wait_again_kb = InlineKeyboardBuilder()
        wait_again_kb.row(
            InlineKeyboardButton(text="К объявлениям", callback_data="boost_queue_to_my_ads")
        )
        wait_again_text = f"Ваше объявление #{ad_id} в очереди на автоподнятие!"
        try:
            await callback.message.edit_text(
                wait_again_text,
                parse_mode="HTML",
                reply_markup=wait_again_kb.as_markup(),
            )
        except Exception:
            await callback.message.answer(
                wait_again_text,
                parse_mode="HTML",
                reply_markup=wait_again_kb.as_markup(),
            )
        return

    await process_channel_boost_queue_once(settings)

    still_waiting = await is_ad_in_channel_boost_queue(ad_id)
    ad_refreshed = await get_ad_by_id(ad_id)
    boosts_left_new = max(0, max_boosts - (getattr(ad_refreshed, 'boost_count', 0) or 0))
    if TEST_MODE:
        interval_min = int(boost_interval_delta.total_seconds() // 60)
        interval_display = f"{interval_min} мин"
    else:
        interval_display = f"{interval_days} дн."
    if still_waiting:
        result_text = f"Ваше объявление #{ad_id} в очереди на автоподнятие!"
        result_kb = InlineKeyboardBuilder()
        result_kb.row(
            InlineKeyboardButton(text="К объявлениям", callback_data="boost_queue_to_my_ads")
        )
    else:
        result_text = (
            f"✅ <b>Объявление #{ad_id} поднято!</b>\n\n"
            f"Новый пост опубликован в канале.\n"
            f"Следующее поднятие через {interval_display}.\n"
            f"Осталось поднятий: {boosts_left_new}/{max_boosts}"
        )
        result_kb = InlineKeyboardBuilder()
        result_kb.row(
            InlineKeyboardButton(text="🏠 Главное меню", callback_data="boost_execute_main_menu")
        )

    try:
        await callback.message.edit_text(
            result_text, parse_mode='HTML',
            reply_markup=result_kb.as_markup()
        )
    except Exception:
        await callback.message.answer(
            result_text,
            parse_mode='HTML',
            reply_markup=result_kb.as_markup()
        )

    logger.info(f"Объявление #{ad_id} поднято пользователем {user.tg_user_id}")


async def boost_execute_main_menu_callback(callback: types.CallbackQuery, state: FSMContext):
    """Переход в главное меню после ручного поднятия с очисткой предыдущих сообщений."""
    await callback.answer()

    current_msg_id = callback.message.message_id

    from src.bot.handlers.start import get_main_menu_text
    from src.bot.keyboards.keyboards import main_menu_kb
    from src.bot.handlers.catalog.reviews import delete_previous_messages

    menu_text = await get_main_menu_text()
    try:
        await callback.message.edit_text(
            menu_text,
            parse_mode='HTML',
            reply_markup=await main_menu_kb(callback.from_user.id)
        )
        await state.update_data(main_menu_msg_id=callback.message.message_id)
    except Exception:
        from src.bot.handlers.start import send_main_menu
        await send_main_menu(callback, state=state)

    await delete_previous_messages(callback.message.chat.id, current_msg_id, 20)


async def boost_queue_to_my_ads_callback(callback: types.CallbackQuery, state: FSMContext):
    """Редактировать текущее сообщение в список «Мои объявления», удалить предыдущий «хвост» в чате."""
    await callback.answer()

    current_msg_id = callback.message.message_id
    chat_id = callback.message.chat.id

    from src.bot.handlers.my_ads._common import delete_my_ad_info_message, _show_my_ads_page
    from src.bot.handlers.catalog.reviews import delete_previous_messages

    data = await state.get_data()
    await delete_my_ad_info_message(state, data.get('my_ad_chat_id', chat_id))
    await state.clear()

    user = await get_user_by_tg_id(callback.from_user.id)
    if not user:
        await callback.answer("❌ Пользователь не найден.", show_alert=True)
        return

    ads = await get_user_ads(user.id)
    if not ads:
        text = (
            "📭 У вас пока нет объявлений.\n\n"
            "Создайте первое объявление через 'Создать объявление' "
        )
        kb = InlineKeyboardBuilder()
        kb.row(InlineKeyboardButton(text=BACK_BTN, callback_data="back_to_menu"))
        try:
            await callback.message.edit_text(text, reply_markup=kb.as_markup())
        except Exception:
            await callback.message.answer(text, reply_markup=kb.as_markup())
    else:
        await _show_my_ads_page(callback, ads, page=0, edit=True, state=state)

    await delete_previous_messages(chat_id, current_msg_id, 20)


async def boost_confirm_from_dm_callback(callback: types.CallbackQuery, state: FSMContext):
    """
    Пользователь нажал [🆙 Поднять] в ЛС-напоминании.
    Подтверждает поднятие — scheduler выполнит его при наступлении next_boost_at.
    """
    ad_id = int(callback.data.split(':')[1])
    ad = await get_ad_by_id(ad_id)
    if not ad:
        await callback.answer("❌ Объявление не найдено.", show_alert=True)
        return

    user = await get_user_by_tg_id(callback.from_user.id)
    if not user or ad.seller_user_id != user.id:
        await callback.answer("❌ Это не ваше объявление.", show_alert=True)
        return

    if ad.status != 'approved':
        await callback.answer("❌ Объявление неактивно.", show_alert=True)
        return

    await mark_ad_boost_confirmed(ad_id)

    ok_kb = InlineKeyboardBuilder()
    ok_kb.row(InlineKeyboardButton(text="ОК", callback_data="boost_reminder_ok"))

    try:
        await callback.message.edit_text(
            f"✅ Поднятие объявления №{ad_id} «{ad.title}» подтверждено.",
            parse_mode='HTML',
            reply_markup=ok_kb.as_markup()
        )
    except Exception:
        await callback.answer("✅ Поднятие подтверждено!", show_alert=True)


async def boost_reminder_ok_callback(callback: types.CallbackQuery, state: FSMContext):
    """По нажатию [ОК] в напоминании об автоподнятии — удаляем сообщение-напоминание."""
    await callback.answer()
    try:
        await callback.message.delete()
    except Exception as e:
        logger.debug(f"Не удалось удалить сообщение напоминания: {e}")


async def boost_pause_auto_ok_callback(callback: types.CallbackQuery, state: FSMContext):
    """По нажатию [ОК] в уведомлении об авто-паузе — удаляем сообщение."""
    await callback.answer()
    try:
        await callback.message.delete()
    except Exception as e:
        logger.debug(f"Не удалось удалить сообщение авто-паузы: {e}")


async def boost_unpublish_from_dm_callback(callback: types.CallbackQuery, state: FSMContext):
    """Пользователь нажал [⏸️ Снять с публикации] в ЛС-напоминании."""
    ad_id = int(callback.data.split(':')[1])
    ad = await get_ad_by_id(ad_id)
    if not ad:
        await callback.answer("❌ Объявление не найдено.", show_alert=True)
        return

    user = await get_user_by_tg_id(callback.from_user.id)
    if not user or ad.seller_user_id != user.id:
        await callback.answer("❌ Это не ваше объявление.", show_alert=True)
        return

    if ad.status != 'approved':
        await callback.answer("❌ Объявление уже неактивно.", show_alert=True)
        return

    from src.bot.utils.channel_utils import format_archive_caption
    from src.bot.settings.settings import CHANNEL_ID, CHANNEL_USERNAME

    await delete_edits_for_ad(ad_id)
    await remove_channel_boost_from_queue(ad_id)
    await update_ad(
        ad_id, status='unpublished', inactive_since=datetime.utcnow(),
        boost_confirmed=False, boost_reminder_step=0,
        boost_reminder_sent_at=None, boost_first_reminder_at=None
    )

    if ad.channel_message_id:
        channel_target = f"@{CHANNEL_USERNAME}" if CHANNEL_USERNAME else CHANNEL_ID
        try:
            await bot.edit_message_caption(
                chat_id=channel_target,
                message_id=ad.channel_message_id,
                caption=format_archive_caption(ad),
                parse_mode='HTML',
                reply_markup=None
            )
        except Exception as e:
            logger.warning(f"Не удалось архивировать пост #{ad_id} из ЛС: {e}")

    ok_kb = InlineKeyboardBuilder()
    ok_kb.row(InlineKeyboardButton(text="ОК", callback_data=f"boost_unpublish_ok:{ad_id}"))

    try:
        await callback.message.edit_text(
            f"⏸️ Объявление №{ad_id} «{ad.title}» снято с публикации.",
            parse_mode='HTML',
            reply_markup=ok_kb.as_markup()
        )
    except Exception:
        await callback.answer("⏸️ Объявление снято с публикации.", show_alert=True)


async def boost_unpublish_ok_callback(callback: types.CallbackQuery, state: FSMContext):
    """По нажатию [ОК] под сообщением о снятии с публикации — удаляем сообщение."""
    await callback.answer()
    try:
        await callback.message.delete()
    except Exception as e:
        logger.debug(f"Не удалось удалить сообщение о снятии с публикации: {e}")