"""
Админ-панель для управления ботом
"""

from aiogram import Dispatcher, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton
from loguru import logger

from datetime import datetime, timedelta
from io import BytesIO
from openpyxl import Workbook

from src.bot.database.states import AdminPanelState, PostAttachState
from src.bot.database.methods import (
    get_ad_by_id, update_ad, mark_ad_removed,
    set_moderator, get_user_by_id, is_moderator,
    count_users, count_banned, get_users_csv_rows,
    add_to_blacklist, remove_from_blacklist, is_banned, get_user_by_username, get_user_by_tg_id,
    get_details_stats_aggregated, get_contact_stats_aggregated,
    get_details_detailed_rows, get_contact_detailed_rows,
    get_total_placed_sold_removed, get_top_placed, get_top_sold, get_top_removed,
    get_top_reviews_activity,
    count_trusted_sellers, set_trusted_seller, is_trusted_seller,
)
from src.bot.settings.settings import ADMIN_IDS, CHANNEL_ID, CHANNEL_USERNAME, BOT_USERNAME
from src.bot.settings.constants import CONDITIONS, DEFAULT_CITIES
from src.bot.loader import bot
from src.bot.keyboards.keyboards import ad_in_channel_kb
from sqlalchemy import select, func
from src.bot.database.methods import async_session
from src.models import User, Ad, Review
from src.bot.middlewares.throttle_middleware import invalidate_banned_cache


# === /post_attach (пост в канал с кнопкой на бота) ===

from ._common import *

# ============================================================
# === НАСТРОЙКИ ПОДНЯТИЯ (п.2.4) ===
# ============================================================

async def admin_boost_settings_menu(callback: types.CallbackQuery, state: FSMContext):
    """Меню настроек поднятия объявлений."""
    await callback.answer()
    if not await check_admin_rights(callback.from_user.id):
        return
    await state.clear()

    from src.bot.database.methods import get_boost_settings
    settings = await get_boost_settings()

    text = (
        "🚀 <b>Настройки поднятия объявлений</b>\n\n"
        f"<b>Обычные пользователи:</b>\n"
        f"  • Кол-во поднятий: {settings.regular_boost_count}\n"
        f"  • Интервал: {settings.regular_boost_interval_days} дней\n"
        f"  • Суточный лимит: {settings.regular_daily_limit}\n\n"
        f"<b>Доверенные продавцы:</b>\n"
        f"  • Кол-во поднятий: {settings.trusted_boost_count}\n"
        f"  • Интервал: {settings.trusted_boost_interval_days} дней\n"
        f"  • Суточный лимит: {settings.trusted_daily_limit}"
    )

    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text="👤 Кол-во поднятий (обычный)", callback_data="admin:boost:set:regular_boost_count"))
    keyboard.row(InlineKeyboardButton(text="⭐ Кол-во поднятий (доверенный)", callback_data="admin:boost:set:trusted_boost_count"))
    keyboard.row(InlineKeyboardButton(text="📅 Интервал (обычный, дней)", callback_data="admin:boost:set:regular_boost_interval_days"))
    keyboard.row(InlineKeyboardButton(text="📅 Интервал (доверенный, дней)", callback_data="admin:boost:set:trusted_boost_interval_days"))
    keyboard.row(InlineKeyboardButton(text="🔢 Суточный лимит (обычный)", callback_data="admin:boost:set:regular_daily_limit"))
    keyboard.row(InlineKeyboardButton(text="🔢 Суточный лимит (доверенный)", callback_data="admin:boost:set:trusted_daily_limit"))
    keyboard.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:back"))

    try:
        await callback.message.edit_text(text, parse_mode='HTML', reply_markup=keyboard.as_markup())
    except Exception:
        await callback.message.answer(text, parse_mode='HTML', reply_markup=keyboard.as_markup())


BOOST_FIELD_NAMES = {
    "regular_boost_count": "количества поднятий за один цикл для обычных пользователей",
    "trusted_boost_count": "количества поднятий за один цикл для доверенных продавцов",
    "regular_boost_interval_days": "интервала между автоподнятиями (дни) для обычных пользователей",
    "trusted_boost_interval_days": "интервала между автоподнятиями (дни) для доверенных продавцов",
    "regular_daily_limit": "суточного лимита поднятий для обычных пользователей",
    "trusted_daily_limit": "суточного лимита поднятий для доверенных продавцов",
}


async def admin_boost_set_field_start(callback: types.CallbackQuery, state: FSMContext):
    """Начать редактирование числового параметра настроек поднятия."""
    await callback.answer()
    if not await check_admin_rights(callback.from_user.id):
        return

    field = callback.data.split("admin:boost:set:")[1]
    field_name = BOOST_FIELD_NAMES.get(field, field)

    from src.bot.database.methods import get_boost_settings
    settings = await get_boost_settings()
    current_val = getattr(settings, field, "—")

    await state.update_data(boost_field=field)
    await state.update_data(boost_prompt_msg_id=callback.message.message_id)
    await state.set_state(AdminPanelState.boost_settings_input)

    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text="⬅️ Отмена", callback_data="admin:boost"))
    await callback.message.edit_text(
        f"Введите новое значение для <b>{field_name}</b> (целое число).\n\nТекущее значение: <b>{current_val}</b>",
        parse_mode='HTML',
        reply_markup=keyboard.as_markup()
    )


async def admin_boost_set_field_input(message: types.Message, state: FSMContext):
    """Сохранить введённое значение настройки поднятия."""
    if not await check_admin_rights(message.from_user.id):
        return

    data = await state.get_data()
    field = data.get('boost_field')
    if not field:
        await state.clear()
        return

    try:
        value = int(message.text.strip())
        if value <= 0:
            raise ValueError
    except (ValueError, AttributeError):
        await message.answer("❌ Введите положительное целое число.")
        return

    from src.bot.database.methods import update_boost_settings
    await update_boost_settings(**{field: value})
    await state.clear()

    field_name = BOOST_FIELD_NAMES.get(field, field)
    # Удаляем сообщение пользователя и редактируем одно и то же сообщение с вводом
    try:
        await message.delete()
    except Exception:
        pass

    # Для возврата в меню используем callback_data "admin:boost"
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:boost"))

    # Берём message_id из состояния (сообщение с "Введите новое значение ...")
    prompt_msg_id = data.get("boost_prompt_msg_id")
    try:
        await bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=prompt_msg_id,
            text=f"✅ Настройка «{field_name}» обновлена: <b>{value}</b>",
            parse_mode='HTML',
            reply_markup=keyboard.as_markup(),
        )
    except Exception:
        # Если редактирование не получилось (например, сообщение пропало) — хотя бы отправим успех 1 сообщением
        await message.answer(
            f"✅ Настройка «{field_name}» обновлена: <b>{value}</b>",
            parse_mode='HTML',
            reply_markup=keyboard.as_markup(),
        )
    logger.info(f"Админ {message.from_user.id} изменил настройку поднятия {field} = {value}")


async def admin_boost_toggle_test(callback: types.CallbackQuery, state: FSMContext):
    """Переключить тест-режим напоминаний."""
    await callback.answer()
    if not await check_admin_rights(callback.from_user.id):
        return

    from src.bot.database.methods import get_boost_settings, update_boost_settings
    settings = await get_boost_settings()
    new_val = not settings.test_mode
    await update_boost_settings(test_mode=new_val)
    status = "включён" if new_val else "выключен"
    await callback.answer(f"🧪 Тест-режим {status}", show_alert=True)

    # Обновляем меню
    await admin_boost_settings_menu(callback, state)


# ============================================================
# === АВТОПОДНЯТИЕ — новый UI (п.2.4 доработка) ===
# ============================================================

def _autoboost_root_kb():
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="Интервалы автоподнятия", callback_data="admin:autoboost:intervals"))
    kb.row(InlineKeyboardButton(text="Кол-во автоподнятий", callback_data="admin:autoboost:counts"))
    kb.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:back"))
    return kb.as_markup()


async def admin_autoboost_menu(callback: types.CallbackQuery, state: FSMContext):
    """Главное меню [Автоподнятие]."""
    await callback.answer()
    if not await check_admin_rights(callback.from_user.id):
        return
    await state.clear()
    try:
        await callback.message.edit_text("Выберите нужный пункт", reply_markup=_autoboost_root_kb())
    except Exception:
        await callback.message.answer("Выберите нужный пункт", reply_markup=_autoboost_root_kb())


# --- А) Интервалы ---

def _intervals_who_kb():
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="Обычные продавцы", callback_data="admin:autoboost:intervals:regular"))
    kb.row(InlineKeyboardButton(text="Доверенные продавцы", callback_data="admin:autoboost:intervals:trusted"))
    kb.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:autoboost"))
    return kb.as_markup()


async def admin_autoboost_intervals_menu(callback: types.CallbackQuery, state: FSMContext):
    """А) Выберите для кого изменить интервал между автоподнятиями."""
    await callback.answer()
    if not await check_admin_rights(callback.from_user.id):
        return
    await state.clear()
    try:
        await callback.message.edit_text(
            "Выберите, для кого изменить интервал между автоподнятиями:",
            reply_markup=_intervals_who_kb()
        )
    except Exception:
        await callback.message.answer(
            "Выберите, для кого изменить интервал между автоподнятиями:",
            reply_markup=_intervals_who_kb()
        )


def _interval_seller_kb(seller_type: str):
    seller_label = "обычных" if seller_type == "regular" else "доверенных"
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="Свое", callback_data=f"admin:autoboost:intervals:{seller_type}:custom"))
    kb.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:autoboost:intervals"))
    return kb.as_markup(), seller_label


async def _show_interval_seller_menu(callback: types.CallbackQuery, state: FSMContext, seller_type: str):
    """А1) Выберите интервал между автоподнятиями для конкретного типа продавца."""
    await callback.answer()
    if not await check_admin_rights(callback.from_user.id):
        return
    await state.clear()
    kb, seller_label = _interval_seller_kb(seller_type)
    text = f"Выберите интервал между автоподнятиями для {seller_label} продавцов:"
    try:
        await callback.message.edit_text(text, reply_markup=kb)
    except Exception:
        await callback.message.answer(text, reply_markup=kb)


async def admin_autoboost_intervals_regular(callback: types.CallbackQuery, state: FSMContext):
    await _show_interval_seller_menu(callback, state, "regular")


async def admin_autoboost_intervals_trusted(callback: types.CallbackQuery, state: FSMContext):
    await _show_interval_seller_menu(callback, state, "trusted")


async def _start_interval_input(callback: types.CallbackQuery, state: FSMContext, seller_type: str):
    """Показать запрос интервала между автоподнятиями с текущим значением."""
    await callback.answer()
    if not await check_admin_rights(callback.from_user.id):
        return
    from src.bot.database.methods import get_boost_settings
    settings = await get_boost_settings()
    current = settings.regular_boost_interval_days if seller_type == "regular" else settings.trusted_boost_interval_days
    seller_label = "обычных" if seller_type == "regular" else "доверенных"
    text = (
        f"Введите новое значение для интервала между автоподнятиями для {seller_label} продавцов (1–30 дней).\n\n"
        f"Текущее значение: <b>{current}</b> дней"
    )
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"admin:autoboost:intervals:{seller_type}"))
    try:
        await callback.message.edit_text(text, parse_mode='HTML', reply_markup=kb.as_markup())
    except Exception:
        await callback.message.answer(text, parse_mode='HTML', reply_markup=kb.as_markup())
    await state.update_data(
        autoboost_bot_msg_id=callback.message.message_id,
        autoboost_seller_type=seller_type,
        autoboost_mode="interval",
    )
    await state.set_state(AdminPanelState.auto_boost_interval_input)


async def admin_autoboost_intervals_regular_custom(callback: types.CallbackQuery, state: FSMContext):
    await _start_interval_input(callback, state, "regular")


async def admin_autoboost_intervals_trusted_custom(callback: types.CallbackQuery, state: FSMContext):
    await _start_interval_input(callback, state, "trusted")


async def admin_autoboost_interval_input(message: types.Message, state: FSMContext):
    """Обработка текстового ввода интервала (1–30 дней)."""
    if not await check_admin_rights(message.from_user.id):
        return

    data = await state.get_data()
    seller_type = data.get("autoboost_seller_type", "regular")
    bot_msg_id = data.get("autoboost_bot_msg_id")
    seller_label = "обычных" if seller_type == "regular" else "доверенных"
    user_input = (message.text or "").strip()

    try:
        await message.delete()
    except Exception:
        pass

    value = None
    try:
        value = int(user_input)
        valid = 1 <= value <= 30
    except (ValueError, TypeError):
        valid = False

    kb = InlineKeyboardBuilder()
    if valid:
        field = "regular_boost_interval_days" if seller_type == "regular" else "trusted_boost_interval_days"
        from src.bot.database.methods import update_boost_settings
        await update_boost_settings(**{field: value})
        await state.clear()
        text = (
            f"Для {seller_label} продавцов установлен интервал между автоподнятиями: <b>{value}</b> дней.\n\n"
            f"⚠️ Текущий цикл у каждого пользователя доработает по старому расписанию. "
            f"Новый интервал вступит в силу со следующего автоподнятия."
        )
        kb.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:autoboost:intervals"))
    else:
        text = f"Неверное значение. Введите число от 1 до 30 (дней между автоподнятиями). Вы ввели: {user_input}"
        kb.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"admin:autoboost:intervals:{seller_type}"))

    if bot_msg_id:
        try:
            await bot.edit_message_text(
                text=text,
                chat_id=message.chat.id,
                message_id=bot_msg_id,
                reply_markup=kb.as_markup(),
                parse_mode='HTML',
            )
            return
        except Exception:
            pass
    await message.answer(text, reply_markup=kb.as_markup(), parse_mode='HTML' if '<b>' in text else None)


# --- Б) Кол-во автоподнятий ---

def _counts_who_kb():
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="Обычные продавцы", callback_data="admin:autoboost:counts:regular"))
    kb.row(InlineKeyboardButton(text="Доверенные продавцы", callback_data="admin:autoboost:counts:trusted"))
    kb.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:autoboost"))
    return kb.as_markup()


async def admin_autoboost_counts_menu(callback: types.CallbackQuery, state: FSMContext):
    """Б) Выберите для кого изменить количество автоподнятий за один цикл."""
    await callback.answer()
    if not await check_admin_rights(callback.from_user.id):
        return
    await state.clear()
    try:
        await callback.message.edit_text(
            "Выберите, для кого изменить количество автоподнятий за один цикл:",
            reply_markup=_counts_who_kb()
        )
    except Exception:
        await callback.message.answer(
            "Выберите, для кого изменить количество автоподнятий за один цикл:",
            reply_markup=_counts_who_kb()
        )


async def _start_count_input(callback: types.CallbackQuery, state: FSMContext, seller_type: str):
    """Б1) Показать запрос количества автоподнятий с текущим значением."""
    await callback.answer()
    if not await check_admin_rights(callback.from_user.id):
        return
    from src.bot.database.methods import get_boost_settings
    settings = await get_boost_settings()
    current = settings.regular_boost_count if seller_type == "regular" else settings.trusted_boost_count
    seller_label = "обычного" if seller_type == "regular" else "доверенного"
    text = (
        f"Введите новое значение для количества автоподнятий за один цикл для {seller_label} продавца (1–5).\n\n"
        f"Текущее значение: <b>{current}</b>"
    )
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:autoboost:counts"))
    try:
        await callback.message.edit_text(text, parse_mode='HTML', reply_markup=kb.as_markup())
    except Exception:
        await callback.message.answer(text, parse_mode='HTML', reply_markup=kb.as_markup())
    await state.update_data(
        autoboost_bot_msg_id=callback.message.message_id,
        autoboost_seller_type=seller_type,
        autoboost_mode="count",
    )
    await state.set_state(AdminPanelState.auto_boost_count_input)


async def admin_autoboost_counts_regular(callback: types.CallbackQuery, state: FSMContext):
    await _start_count_input(callback, state, "regular")


async def admin_autoboost_counts_trusted(callback: types.CallbackQuery, state: FSMContext):
    await _start_count_input(callback, state, "trusted")


async def admin_autoboost_count_input(message: types.Message, state: FSMContext):
    """Обработка текстового ввода кол-ва поднятий (1–5)."""
    if not await check_admin_rights(message.from_user.id):
        return

    data = await state.get_data()
    seller_type = data.get("autoboost_seller_type", "regular")
    bot_msg_id = data.get("autoboost_bot_msg_id")
    seller_label = "обычных" if seller_type == "regular" else "доверенных"
    user_input = (message.text or "").strip()

    try:
        await message.delete()
    except Exception:
        pass

    value = None
    try:
        value = int(user_input)
        valid = 1 <= value <= 5
    except (ValueError, TypeError):
        valid = False

    kb = InlineKeyboardBuilder()
    if valid:
        field = "regular_boost_count" if seller_type == "regular" else "trusted_boost_count"
        from src.bot.database.methods import update_boost_settings
        await update_boost_settings(**{field: value})
        await state.clear()
        text = f"Для {seller_label} продавцов установлено количество автоподнятий за один цикл: <b>{value}</b>"
        kb.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:autoboost:counts"))
    else:
        text = f"Неверное значение. Введите число от 1 до 5 (количество автоподнятий за цикл). Вы ввели: {user_input}"
        kb.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"admin:autoboost:counts:{seller_type}"))

    if bot_msg_id:
        try:
            await bot.edit_message_text(
                text=text,
                chat_id=message.chat.id,
                message_id=bot_msg_id,
                reply_markup=kb.as_markup(),
                parse_mode='HTML',
            )
            return
        except Exception:
            pass
    await message.answer(text, reply_markup=kb.as_markup(), parse_mode='HTML' if '<b>' in text else None)

