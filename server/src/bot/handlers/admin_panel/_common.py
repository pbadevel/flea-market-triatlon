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

# === ПРОВЕРКА ПРАВ АДМИНА ===

async def check_admin_rights(user_id: int) -> bool:
    """Проверить права администратора (ADMIN_IDS или модератор из БД)"""
    return await is_moderator(user_id)


async def _get_admin_main_menu_text_and_kb():
    """Текст и клавиатура главного меню админ-панели (одно меню для админов и модераторов)."""
    async with async_session() as session:
        result = await session.execute(select(func.count(User.id)))
        users_count = result.scalar()
        result = await session.execute(select(func.count(Ad.id)).where(Ad.status == 'approved'))
        active_ads = result.scalar()
        result = await session.execute(select(func.count(User.id)).where(User.is_moderator == True))
        moderators_count = result.scalar()
    text = (
        f"🎛 <b>АДМИН-ПАНЕЛЬ</b>\n\n"
        f"👥 <b>Пользователей:</b> {users_count}\n"
        f"📦 <b>Активных объявлений:</b> {active_ads}\n"
        f"👮 <b>Модераторов:</b> {moderators_count}\n\n"
        "Выберите раздел:"
    )
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text="👥 Управление пользователями", callback_data="admin:users"))
    keyboard.row(InlineKeyboardButton(text="👮 Управление ролями", callback_data="admin:roles"))
    keyboard.row(InlineKeyboardButton(text="📊 Статистика", callback_data="admin:stats"))
    keyboard.row(InlineKeyboardButton(text="⭐ Доверенный продавец", callback_data="admin:trusted"))
    keyboard.row(InlineKeyboardButton(text="📦 Объявления", callback_data="admin:ads"))
    keyboard.row(InlineKeyboardButton(text="👮 Модераторы", callback_data="admin:moderators"))
    keyboard.row(InlineKeyboardButton(text="📋 Логи", callback_data="admin:logs"))
    keyboard.row(InlineKeyboardButton(text="🚀 Настройки поднятия", callback_data="admin:boost"))
    keyboard.row(InlineKeyboardButton(text="🚪 Выход", callback_data="admin:exit"))
    return text, keyboard


# === ГЛАВНОЕ МЕНЮ АДМИН-ПАНЕЛИ ===

async def admin_command(message: types.Message, state: FSMContext):
    """Команда /admin: одна админ-панель для всех (ADMIN_IDS и модераторы из БД). Чат чистится (последние 30 сообщений)."""
    if not await check_admin_rights(message.from_user.id):
        return  # бот не реагирует
    await state.clear()
    admin_msg_id = message.message_id
    text, keyboard = await _get_admin_main_menu_text_and_kb()
    await message.answer(text, parse_mode='HTML', reply_markup=keyboard.as_markup())
    # Чистим чат: удаляем сообщение с /admin и предыдущие 30 сообщений
    try:
        await message.delete()
    except Exception:
        pass
    try:
        for i in range(1, 31):
            try:
                msg_id_to_delete = admin_msg_id - i
                if msg_id_to_delete > 0:
                    await bot.delete_message(chat_id=message.chat.id, message_id=msg_id_to_delete)
            except Exception:
                pass
    except Exception:
        pass


# === ВОЗВРАТ В ГЛАВНОЕ МЕНЮ АДМИН-ПАНЕЛИ ===

async def admin_exit(callback: types.CallbackQuery, state: FSMContext):
    """Выход из админ-панели: редактируем сообщение админ-панели на главное меню."""
    await callback.answer()
    if not await check_admin_rights(callback.from_user.id):
        return
    await state.clear()
    from src.bot.handlers.start import get_main_menu_text
    from src.bot.keyboards.keyboards import main_menu_kb
    menu_text = await get_main_menu_text()
    user_id = callback.from_user.id
    try:
        await callback.message.edit_text(
            menu_text,
            parse_mode='HTML',
            reply_markup=await main_menu_kb(user_id)
        )
        await state.update_data(main_menu_msg_id=callback.message.message_id)
    except Exception as e:
        logger.warning(f"Не удалось отредактировать сообщение админ-панели на главное меню: {e}")
        from src.bot.handlers.start import send_main_menu
        await send_main_menu(callback, state=state)


async def admin_back(callback: types.CallbackQuery, state: FSMContext):
    """Возврат в главное меню админ-панели (одно меню для всех)."""
    await callback.answer()
    if not await check_admin_rights(callback.from_user.id):
        return
    await state.clear()
    text, keyboard = await _get_admin_main_menu_text_and_kb()
    try:
        await callback.message.edit_text(text, parse_mode='HTML', reply_markup=keyboard.as_markup())
    except Exception:
        await callback.message.answer(text, parse_mode='HTML', reply_markup=keyboard.as_markup())
