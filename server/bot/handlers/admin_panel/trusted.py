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


# === УПРАВЛЕНИЕ РОЛЯМИ (ЗАГЛУШКА) ===

async def admin_roles_stub(callback: types.CallbackQuery, state: FSMContext):
    """Управление ролями — в разработке."""
    await callback.answer()
    if not await check_admin_rights(callback.from_user.id):
        return
    await state.clear()
    text = "На данный момент этот пункт находится в разработке, возвращайтесь позже."
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:back"))
    try:
        await callback.message.edit_text(text, reply_markup=keyboard.as_markup())
    except Exception:
        await callback.message.answer(text, reply_markup=keyboard.as_markup())


# === ДОВЕРЕННЫЙ ПРОДАВЕЦ ===

async def admin_trusted_menu(callback: types.CallbackQuery, state: FSMContext):
    """Меню управления статусом «Доверенный продавец»."""
    await callback.answer()
    if not await check_admin_rights(callback.from_user.id):
        return
    await state.clear()
    
    from src.bot.database.methods import count_trusted_sellers
    trusted_count = await count_trusted_sellers()
    
    text = f"Количество пользователей со статусом «Доверенный продавец»: {trusted_count}"
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text="Назначить", callback_data="admin:trusted:assign"))
    keyboard.row(InlineKeyboardButton(text="Разжаловать", callback_data="admin:trusted:revoke"))
    keyboard.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:back"))
    
    try:
        await callback.message.edit_text(text, reply_markup=keyboard.as_markup())
    except Exception:
        await callback.message.answer(text, reply_markup=keyboard.as_markup())
        try:
            await callback.message.delete()
        except Exception:
            pass


async def admin_trusted_assign_start(callback: types.CallbackQuery, state: FSMContext):
    """Начало процесса назначения статуса доверенного продавца."""
    await callback.answer()
    if not await check_admin_rights(callback.from_user.id):
        return
    await state.set_state(AdminPanelState.trusted_seller_assign_input)
    text = "Введите @username или tg_id пользователя."
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text="Отмена", callback_data="admin:trusted"))
    try:
        msg = await callback.message.edit_text(text, reply_markup=keyboard.as_markup())
        await state.update_data(trusted_assign_msg_id=msg.message_id)
    except Exception:
        msg = await callback.message.answer(text, reply_markup=keyboard.as_markup())
        await state.update_data(trusted_assign_msg_id=msg.message_id)


async def admin_trusted_assign_input(message: types.Message, state: FSMContext):
    """Обработка ввода пользователя для назначения статуса."""
    from src.bot.database.methods import get_user_by_username, get_user_by_tg_id
    
    user_input = message.text.strip().lstrip("@")
    original_input = message.text.strip()  # Сохраняем оригинальный ввод для отображения
    
    # Пытаемся найти пользователя по username или tg_id
    user = None
    try:
        # Сначала пробуем как tg_id
        tg_id = int(user_input)
        user = await get_user_by_tg_id(tg_id)
    except ValueError:
        # Если не число, пробуем как username
        user = await get_user_by_username(user_input)
    
    # Удаляем сообщение пользователя
    try:
        await message.delete()
    except Exception:
        pass
    
    # Получаем ID сообщения для редактирования
    data = await state.get_data()
    msg_id = data.get("trusted_assign_msg_id")
    
    if not user:
        err_text = "❌ Пользователь не найден. Проверьте правильность ввода."
        keyboard = InlineKeyboardBuilder()
        keyboard.row(InlineKeyboardButton(text="Отмена", callback_data="admin:trusted"))
        if msg_id:
            try:
                await bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=msg_id,
                    text=err_text,
                    reply_markup=keyboard.as_markup()
                )
            except Exception:
                await message.answer(err_text, reply_markup=keyboard.as_markup())
        else:
            await message.answer(err_text, reply_markup=keyboard.as_markup())
        return
    
    # Проверяем, не является ли уже доверенным продавцом
    if user.is_trusted_seller:
        err_text = "❌ У пользователя уже есть статус «Доверенный продавец»."
        keyboard = InlineKeyboardBuilder()
        keyboard.row(InlineKeyboardButton(text="Отмена", callback_data="admin:trusted"))
        if msg_id:
            try:
                await bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=msg_id,
                    text=err_text,
                    reply_markup=keyboard.as_markup()
                )
            except Exception:
                await message.answer(err_text, reply_markup=keyboard.as_markup())
        else:
            await message.answer(err_text, reply_markup=keyboard.as_markup())
        return
    
    # Сохраняем данные пользователя в состоянии
    await state.update_data(
        trusted_user_id=user.id,
        trusted_tg_id=user.tg_user_id,
        trusted_username=user.username
    )
    await state.set_state(AdminPanelState.trusted_seller_assign_confirm)
    
    username_display = f"@{user.username}" if user.username else str(user.tg_user_id)
    from src.bot.database.methods import get_boost_settings
    settings = await get_boost_settings()
    text = (
        f"✅ Пользователю {username_display} будет присвоен статус \"Доверенный продавец\".\n"
        f"📅 Суточный лимит поднятий: {settings.trusted_daily_limit}"
    )
    keyboard = InlineKeyboardBuilder()
    keyboard.row(
        InlineKeyboardButton(text="Отмена", callback_data="admin:trusted"),
        InlineKeyboardButton(text="Подтвердить", callback_data="admin:trusted:assign:confirm")
    )
    
    if msg_id:
        try:
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=msg_id,
                text=text,
                reply_markup=keyboard.as_markup()
            )
        except Exception:
            await message.answer(text, reply_markup=keyboard.as_markup())
    else:
        await message.answer(text, reply_markup=keyboard.as_markup())


async def admin_trusted_assign_confirm(callback: types.CallbackQuery, state: FSMContext):
    """Подтверждение назначения статуса доверенного продавца. Редактируем текущее сообщение, кнопка «Назад» возвращает в меню доверенных продавцов."""
    await callback.answer()
    if not await check_admin_rights(callback.from_user.id):
        return
    
    data = await state.get_data()
    tg_id = data.get("trusted_tg_id")
    username = data.get("trusted_username")
    
    if not tg_id:
        await callback.message.answer("❌ Ошибка: данные пользователя не найдены.")
        await admin_trusted_menu(callback, state)
        return
    
    from src.bot.database.methods import set_trusted_seller
    success = await set_trusted_seller(tg_id, True)
    
    if success:
        username_display = f"@{username}" if username else str(tg_id)
        text = f"✅ Пользователю {username_display} присвоен статус \"Доверенный продавец\"."
        keyboard = InlineKeyboardBuilder()
        keyboard.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:trusted"))
        try:
            await callback.message.edit_text(text, reply_markup=keyboard.as_markup())
        except Exception:
            await callback.message.answer(text, reply_markup=keyboard.as_markup())
        
        # Отправляем сообщение пользователю
        try:
            from src.bot.database.methods import get_boost_settings
            settings = await get_boost_settings()
            # На практике админ может менять суточный лимит либо для обычных,
            # либо для доверенных продавцов; чтобы сообщение не показывало дефолт (например, 6),
            # отображаем лимит как максимум из двух настроек.
            daily_limit_to_display = max(settings.trusted_daily_limit, settings.regular_daily_limit)
            user_message = (
                "Вам присвоен статус \"Доверенный продавец\".\n"
                f"📅 Суточный лимит поднятий: {daily_limit_to_display}"
            )
            notify_kb = InlineKeyboardBuilder()
            notify_kb.row(InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu"))
            await bot.send_message(chat_id=tg_id, text=user_message, reply_markup=notify_kb.as_markup())
        except Exception as e:
            logger.error(f"Не удалось отправить сообщение пользователю {tg_id}: {e}")
    else:
        await callback.message.answer("❌ Ошибка при назначении статуса.")
    
    await state.clear()


async def admin_trusted_revoke_start(callback: types.CallbackQuery, state: FSMContext):
    """Начало процесса разжалования статуса доверенного продавца."""
    await callback.answer()
    if not await check_admin_rights(callback.from_user.id):
        return
    await state.set_state(AdminPanelState.trusted_seller_revoke_input)
    text = "Введите @username или tg_id пользователя."
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text="Отмена", callback_data="admin:trusted"))
    try:
        msg = await callback.message.edit_text(text, reply_markup=keyboard.as_markup())
        await state.update_data(trusted_revoke_msg_id=msg.message_id)
    except Exception:
        msg = await callback.message.answer(text, reply_markup=keyboard.as_markup())
        await state.update_data(trusted_revoke_msg_id=msg.message_id)


async def admin_trusted_revoke_input(message: types.Message, state: FSMContext):
    """Обработка ввода пользователя для разжалования статуса."""
    from src.bot.database.methods import get_user_by_username, get_user_by_tg_id
    
    user_input = message.text.strip().lstrip("@")
    original_input = message.text.strip()  # Сохраняем оригинальный ввод для отображения
    
    # Пытаемся найти пользователя по username или tg_id
    user = None
    try:
        # Сначала пробуем как tg_id
        tg_id = int(user_input)
        user = await get_user_by_tg_id(tg_id)
    except ValueError:
        # Если не число, пробуем как username
        user = await get_user_by_username(user_input)
    
    # Удаляем сообщение пользователя
    try:
        await message.delete()
    except Exception:
        pass
    
    # Получаем ID сообщения для редактирования
    data = await state.get_data()
    msg_id = data.get("trusted_revoke_msg_id")
    
    if not user:
        # Формируем отображаемое имя пользователя
        display_input = original_input if original_input.startswith("@") else f"@{original_input.lstrip('@')}"
        err_text = f"❌ У аккаунта {display_input} нет статуса \"Доверенного продавца\", введите ниже @username или tg_id другого пользователя."
        keyboard = InlineKeyboardBuilder()
        keyboard.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:trusted:revoke:back"))
        if msg_id:
            try:
                await bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=msg_id,
                    text=err_text,
                    reply_markup=keyboard.as_markup()
                )
            except Exception:
                await message.answer(err_text, reply_markup=keyboard.as_markup())
        else:
            await message.answer(err_text, reply_markup=keyboard.as_markup())
        return
    
    # Проверяем, является ли доверенным продавцом
    if not user.is_trusted_seller:
        # Формируем отображаемое имя пользователя
        display_input = original_input if original_input.startswith("@") else f"@{original_input.lstrip('@')}"
        err_text = f"❌ У аккаунта {display_input} нет статуса \"Доверенного продавца\", введите ниже @username или tg_id другого пользователя."
        keyboard = InlineKeyboardBuilder()
        keyboard.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:trusted:revoke:back"))
        if msg_id:
            try:
                await bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=msg_id,
                    text=err_text,
                    reply_markup=keyboard.as_markup()
                )
            except Exception:
                await message.answer(err_text, reply_markup=keyboard.as_markup())
        else:
            await message.answer(err_text, reply_markup=keyboard.as_markup())
        return
    
    # Сохраняем данные пользователя в состоянии
    await state.update_data(
        trusted_user_id=user.id,
        trusted_tg_id=user.tg_user_id,
        trusted_username=user.username
    )
    await state.set_state(AdminPanelState.trusted_seller_revoke_confirm)
    
    username_display = f"@{user.username}" if user.username else str(user.tg_user_id)
    text = f"⚠️ У пользователя {username_display} будет отозван статус \"Доверенный продавец\". 📊 Лимит поднятий станет 3 в день."
    keyboard = InlineKeyboardBuilder()
    keyboard.row(
        InlineKeyboardButton(text="Отмена", callback_data="admin:trusted"),
        InlineKeyboardButton(text="Подтвердить", callback_data="admin:trusted:revoke:confirm")
    )
    
    if msg_id:
        try:
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=msg_id,
                text=text,
                reply_markup=keyboard.as_markup()
            )
        except Exception:
            await message.answer(text, reply_markup=keyboard.as_markup())
    else:
        await message.answer(text, reply_markup=keyboard.as_markup())


async def admin_trusted_revoke_confirm(callback: types.CallbackQuery, state: FSMContext):
    """Подтверждение разжалования статуса доверенного продавца. Редактируем текущее сообщение, кнопка «Назад» возвращает в меню доверенных продавцов."""
    await callback.answer()
    if not await check_admin_rights(callback.from_user.id):
        return
    
    data = await state.get_data()
    tg_id = data.get("trusted_tg_id")
    username = data.get("trusted_username")
    
    if not tg_id:
        await callback.message.answer("❌ Ошибка: данные пользователя не найдены.")
        await admin_trusted_menu(callback, state)
        return
    
    from src.bot.database.methods import set_trusted_seller
    success = await set_trusted_seller(tg_id, False)
    
    if success:
        username_display = f"@{username}" if username else str(tg_id)
        text = f"✅ У пользователя {username_display} отозван статус \"Доверенный продавец\"."
        keyboard = InlineKeyboardBuilder()
        keyboard.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:trusted"))
        try:
            await callback.message.edit_text(text, reply_markup=keyboard.as_markup())
        except Exception:
            await callback.message.answer(text, reply_markup=keyboard.as_markup())
        
        # Отправляем сообщение пользователю
        try:
            from src.bot.database.methods import get_boost_settings
            settings = await get_boost_settings()
            user_message = (
                "Статус \"Доверенный продавец\" отозван.\n"
                f"📅 Суточный лимит поднятий: {settings.regular_daily_limit}"
            )
            notify_kb = InlineKeyboardBuilder()
            notify_kb.row(InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu"))
            await bot.send_message(chat_id=tg_id, text=user_message, reply_markup=notify_kb.as_markup())
        except Exception as e:
            logger.error(f"Не удалось отправить сообщение пользователю {tg_id}: {e}")
    else:
        await callback.message.answer("❌ Ошибка при разжаловании статуса.")
        
    await state.clear()


async def admin_trusted_revoke_back(callback: types.CallbackQuery, state: FSMContext):
    """Возврат к началу процесса разжалования статуса (кнопка Назад при ошибке)."""
    await callback.answer()
    if not await check_admin_rights(callback.from_user.id):
        return
    await state.set_state(AdminPanelState.trusted_seller_revoke_input)
    text = "Введите @username или tg_id пользователя."
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text="Отмена", callback_data="admin:trusted"))
    try:
        msg = await callback.message.edit_text(text, reply_markup=keyboard.as_markup())
        await state.update_data(trusted_revoke_msg_id=msg.message_id)
    except Exception:
        msg = await callback.message.answer(text, reply_markup=keyboard.as_markup())
        await state.update_data(trusted_revoke_msg_id=msg.message_id)


