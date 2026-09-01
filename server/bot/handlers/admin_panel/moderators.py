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


async def admin_moderators_menu(callback: types.CallbackQuery, state: FSMContext):
    """Меню модераторов"""
    await callback.answer()
    
    if not await check_admin_rights(callback.from_user.id):
        await callback.answer("❌ У вас нет прав доступа.", show_alert=True)
        return
    
    await state.set_state(AdminPanelState.moderators_menu)
    
    text = "👮 <b>МОДЕРАТОРЫ</b>\n\nВы находитесь в пункте 'МОДЕРАТОРЫ', выберите действие:"
    
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text="📋 Список модераторов", callback_data="admin:mods:list"))
    keyboard.row(InlineKeyboardButton(text="➕ Добавить модератора", callback_data="admin:mods:add"))
    keyboard.row(InlineKeyboardButton(text="➖ Удалить модератора", callback_data="admin:mods:remove"))
    keyboard.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:back"))
    
    try:
        await callback.message.edit_text(text, parse_mode='HTML', reply_markup=keyboard.as_markup())
    except:
        await callback.message.answer(text, parse_mode='HTML', reply_markup=keyboard.as_markup())


async def admin_moderators_list(callback: types.CallbackQuery, state: FSMContext):
    """Список модераторов"""
    await callback.answer()
    
    # Получаем список модераторов
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.is_moderator == True)
        )
        moderators = result.scalars().all()
    
    text = "📋 <b>СПИСОК МОДЕРАТОРОВ</b>\n\n"
    
    if moderators:
        for mod in moderators:
            text += f"👤 <b>{mod.first_name or 'Без имени'}</b>\n"
            text += f"   ID: <code>{mod.tg_user_id}</code>\n"
            text += f"   Username: @{mod.username}" if mod.username else "   Username: не указан"
            text += "\n\n"
    else:
        text += "Модераторов нет."
    
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:moderators"))
    
    try:
        await callback.message.edit_text(text, parse_mode='HTML', reply_markup=keyboard.as_markup())
    except:
        await callback.message.answer(text, parse_mode='HTML', reply_markup=keyboard.as_markup())


async def admin_moderators_add_start(callback: types.CallbackQuery, state: FSMContext):
    """Начало добавления модератора"""
    await callback.answer()
    
    await state.set_state(AdminPanelState.add_moderator_input)
    
    text = "➕ <b>Добавление модератора</b>\n\nУкажите Telegram ID пользователя:"
    
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:moderators"))
    
    try:
        msg = await callback.message.edit_text(text, parse_mode='HTML', reply_markup=keyboard.as_markup())
        await state.update_data(add_mod_msg_id=msg.message_id)
    except:
        msg = await callback.message.answer(text, parse_mode='HTML', reply_markup=keyboard.as_markup())
        await state.update_data(add_mod_msg_id=msg.message_id)


async def admin_moderators_add_input(message: types.Message, state: FSMContext):
    """Обработка ввода ID для добавления модератора"""
    # Деактивируем кнопки в предыдущем сообщении
    data = await state.get_data()
    prev_msg_id = data.get('add_mod_msg_id')
    if prev_msg_id:
        try:
            await bot.edit_message_reply_markup(
                chat_id=message.chat.id,
                message_id=prev_msg_id,
                reply_markup=None
            )
        except:
            pass
    
    try:
        user_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Неверный формат. Укажите числовой ID.")
        return
    
    # Добавляем модератора
    await set_moderator(user_id, True)
    
    await message.answer(f"✅ Пользователь {user_id} назначен модератором.")
    logger.info(f"Админ {message.from_user.id} назначил модератором пользователя {user_id}")
    
    await state.clear()


async def admin_moderators_remove_start(callback: types.CallbackQuery, state: FSMContext):
    """Начало удаления модератора"""
    await callback.answer()
    
    await state.set_state(AdminPanelState.remove_moderator_input)
    
    text = "➖ <b>Удаление модератора</b>\n\nУкажите Telegram ID модератора для удаления:"
    
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:moderators"))
    
    try:
        msg = await callback.message.edit_text(text, parse_mode='HTML', reply_markup=keyboard.as_markup())
        await state.update_data(remove_mod_msg_id=msg.message_id)
    except:
        msg = await callback.message.answer(text, parse_mode='HTML', reply_markup=keyboard.as_markup())
        await state.update_data(remove_mod_msg_id=msg.message_id)


async def admin_moderators_remove_input(message: types.Message, state: FSMContext):
    """Обработка ввода ID для удаления модератора"""
    # Деактивируем кнопки в предыдущем сообщении
    data = await state.get_data()
    prev_msg_id = data.get('remove_mod_msg_id')
    if prev_msg_id:
        try:
            await bot.edit_message_reply_markup(
                chat_id=message.chat.id,
                message_id=prev_msg_id,
                reply_markup=None
            )
        except:
            pass
    
    try:
        user_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Неверный формат. Укажите числовой ID.")
        return
    
    # Удаляем модератора
    await set_moderator(user_id, False)
    
    await message.answer(f"✅ Пользователь {user_id} снят с должности модератора.")
    logger.info(f"Админ {message.from_user.id} снял с должности модератора пользователя {user_id}")
    
    await state.clear()


# === РАЗДЕЛ "ЛОГИ" ===
