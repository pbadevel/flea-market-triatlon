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

# === УПРАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯМИ ===

async def admin_users_menu(callback: types.CallbackQuery, state: FSMContext):
    """Раздел «Управление пользователями»: счётчики и кнопки."""
    await callback.answer()
    if not await check_admin_rights(callback.from_user.id):
        return
    await state.clear()
    users_total = await count_users()
    banned_total = await count_banned()
    text = (
        f"Общее количество пользователей зарегистрированных в боте: {users_total}\n"
        f"Пользователи в бане: {banned_total}"
    )
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text="📥 Выгрузить csv", callback_data="admin:users:csv"))
    keyboard.row(
        InlineKeyboardButton(text="🚫 Забанить", callback_data="admin:users:ban"),
        InlineKeyboardButton(text="✅ Разбанить", callback_data="admin:users:unban"),
    )
    keyboard.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:back"))
    try:
        await callback.message.edit_text(text, reply_markup=keyboard.as_markup())
    except Exception:
        await callback.message.answer(text, reply_markup=keyboard.as_markup())
        try:
            await callback.message.delete()
        except Exception:
            pass


async def admin_users_csv(callback: types.CallbackQuery, state: FSMContext):
    """Выгрузка Excel таблицы пользователей с полями: ид, tg_id, логин, дата_регистрации, статус, доверенный_продавец, магазин, тренер, команды."""
    await callback.answer()
    if not await check_admin_rights(callback.from_user.id):
        return
    await state.clear()
    rows = await get_users_csv_rows()
    wb = Workbook()
    ws = wb.active
    ws.title = "Пользователи"
    ws.append([
        "ид", "tg_id_пользователя", "логин", "дата_регистрации",
        "статус", "доверенный_продавец", "магазин", "тренер", "команды",
    ])
    for r in rows:
        # r = (id, tg_id, username, created_at, is_banned, is_trusted_seller)
        status = "забанен" if r[4] else "активен"
        trusted = "да" if r[5] else "нет"
        ws.append([
            r[0], r[1], r[2] or "", r[3].strftime("%Y-%m-%d %H:%M:%S") if r[3] else "",
            status, trusted, 0, 0, 0,
        ])
    col_widths = [8, 22, 25, 24, 12, 22, 12, 12, 12]
    for i, width in enumerate(col_widths, 1):
        ws.column_dimensions[ws.cell(row=1, column=i).column_letter].width = width
    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    filename = f"users_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    from aiogram.types import BufferedInputFile
    file = BufferedInputFile(buf.getvalue(), filename=filename)
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:users"))
    await callback.message.answer_document(
        document=file,
        caption="Файл подписан текущей датой и временем.",
        reply_markup=keyboard.as_markup(),
    )
    try:
        await callback.message.delete()
    except Exception:
        pass


async def admin_users_ban_start(callback: types.CallbackQuery, state: FSMContext):
    """Запрос @username или tg_id для бана."""
    await callback.answer()
    if not await check_admin_rights(callback.from_user.id):
        return
    await state.set_state(AdminPanelState.ban_unban_input)
    await state.update_data(ban_action="ban")
    text = "Введите @username или tg_id пользователя"
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text="❌ Отмена", callback_data="admin:users"))
    try:
        msg = await callback.message.edit_text(text, reply_markup=keyboard.as_markup())
        await state.update_data(ban_msg_id=msg.message_id)
    except Exception:
        msg = await callback.message.answer(text, reply_markup=keyboard.as_markup())
        await state.update_data(ban_msg_id=msg.message_id)


async def admin_users_unban_start(callback: types.CallbackQuery, state: FSMContext):
    """Запрос @username или tg_id для разбана."""
    await callback.answer()
    if not await check_admin_rights(callback.from_user.id):
        return
    await state.set_state(AdminPanelState.ban_unban_input)
    await state.update_data(ban_action="unban")
    text = "Введите @username или tg_id пользователя"
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text="❌ Отмена", callback_data="admin:users"))
    try:
        msg = await callback.message.edit_text(text, reply_markup=keyboard.as_markup())
        await state.update_data(ban_msg_id=msg.message_id)
    except Exception:
        msg = await callback.message.answer(text, reply_markup=keyboard.as_markup())
        await state.update_data(ban_msg_id=msg.message_id)


async def admin_users_ban_unban_input(message: types.Message, state: FSMContext):
    """Обработка ввода @username или tg_id для бана/разбана."""
    data = await state.get_data()
    action = data.get("ban_action")
    if action not in ("ban", "unban"):
        await state.clear()
        return
    raw = (message.text or "").strip()
    if not raw:
        await message.answer("Введите @username или tg_id пользователя.")
        return
    if raw.lower() in ("отмена", "cancel"):
        try:
            await message.delete()
        except Exception:
            pass
        await state.clear()
        users_total = await count_users()
        banned_total = await count_banned()
        text = f"Общее количество пользователей зарегистрированных в боте: {users_total}\nПользователи в бане: {banned_total}"
        keyboard = InlineKeyboardBuilder()
        keyboard.row(InlineKeyboardButton(text="📥 Выгрузить csv", callback_data="admin:users:csv"))
        keyboard.row(
            InlineKeyboardButton(text="🚫 Забанить", callback_data="admin:users:ban"),
            InlineKeyboardButton(text="✅ Разбанить", callback_data="admin:users:unban"),
        )
        keyboard.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:back"))
        ban_msg_id = data.get("ban_msg_id")
        if ban_msg_id:
            try:
                await bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=ban_msg_id,
                    text=text,
                    reply_markup=keyboard.as_markup(),
                )
            except Exception:
                await message.answer(text, reply_markup=keyboard.as_markup())
        else:
            await message.answer(text, reply_markup=keyboard.as_markup())
        return
    # Определяем tg_id: число или по username
    tg_id = None
    username_display = raw
    if raw.lstrip("-").isdigit():
        tg_id = int(raw)
        user = await get_user_by_tg_id(tg_id)
        if action == "ban" and not user:
            try:
                await message.delete()
            except Exception:
                pass
            err_text = f'Пользователь с tg_id "{raw}" не найден в БД. Забанивать можно только зарегистрированных в боте пользователей.'
            keyboard = InlineKeyboardBuilder()
            keyboard.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:users"))
            ban_msg_id = data.get("ban_msg_id")
            if ban_msg_id:
                try:
                    await bot.edit_message_text(
                        chat_id=message.chat.id,
                        message_id=ban_msg_id,
                        text=err_text,
                        reply_markup=keyboard.as_markup(),
                    )
                except Exception:
                    await message.answer(err_text, reply_markup=keyboard.as_markup())
            else:
                await message.answer(err_text, reply_markup=keyboard.as_markup())
            return
        username_display = f"@{user.username}" if user and user.username else str(tg_id)
    else:
        uname = raw.lstrip("@")
        user = await get_user_by_username(uname)
        if user:
            tg_id = user.tg_user_id
            username_display = f"@{user.username}" if user.username else str(tg_id)
        else:
            # Редактируем сообщение бота и удаляем сообщение пользователя (без нового сообщения)
            try:
                await message.delete()
            except Exception:
                pass
            err_text = f'Пользователь "{raw}" не найден в БД. Попробуйте ввести tg_id.'
            keyboard = InlineKeyboardBuilder()
            keyboard.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:users"))
            ban_msg_id = data.get("ban_msg_id")
            if ban_msg_id:
                try:
                    await bot.edit_message_text(
                        chat_id=message.chat.id,
                        message_id=ban_msg_id,
                        text=err_text,
                        reply_markup=keyboard.as_markup(),
                    )
                except Exception:
                    await message.answer(err_text, reply_markup=keyboard.as_markup())
            else:
                await message.answer(err_text, reply_markup=keyboard.as_markup())
            return
    # Проверка: уже в бане при бане / не в бане при разбане
    already_banned = await is_banned(tg_id)
    if action == "ban" and already_banned:
        try:
            await message.delete()
        except Exception:
            pass
        err_text = f'Пользователь "{username_display}" уже в черном списке.'
        keyboard = InlineKeyboardBuilder()
        keyboard.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:users"))
        ban_msg_id = data.get("ban_msg_id")
        if ban_msg_id:
            try:
                await bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=ban_msg_id,
                    text=err_text,
                    reply_markup=keyboard.as_markup(),
                )
            except Exception:
                await message.answer(err_text, reply_markup=keyboard.as_markup())
        else:
            await message.answer(err_text, reply_markup=keyboard.as_markup())
        return
    if action == "unban" and not already_banned:
        try:
            await message.delete()
        except Exception:
            pass
        if raw.lstrip("-").isdigit():
            err_text = f'❌ Пользователя с tg_id "{raw}" нет в черном списке. 👤'
        else:
            display_input = raw if raw.startswith("@") else f"@{raw.lstrip('@')}"
            err_text = f'❌ Пользователя с username "{display_input}" нет в черном списке. 👤'
        keyboard = InlineKeyboardBuilder()
        keyboard.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:users"))
        ban_msg_id = data.get("ban_msg_id")
        if ban_msg_id:
            try:
                await bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=ban_msg_id,
                    text=err_text,
                    reply_markup=keyboard.as_markup(),
                )
            except Exception:
                await message.answer(err_text, reply_markup=keyboard.as_markup())
        else:
            await message.answer(err_text, reply_markup=keyboard.as_markup())
        return
    # Сохраняем данные пользователя в state для подтверждения
    await state.update_data(
        ban_tg_id=tg_id,
        ban_username_display=username_display
    )
    # Удаляем сообщение пользователя и редактируем сообщение бота на подтверждение
    try:
        await message.delete()
    except Exception:
        pass
    ban_msg_id = data.get("ban_msg_id")
    if action == "ban":
        text = f'Пользователь "{username_display}" будет добавлен в черный список (удален из канала) бота.'
    else:
        text = f'Пользователь "{username_display}" будет удален из черного списка бота.'
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text="❌ Отмена", callback_data="admin:users"))
    keyboard.row(InlineKeyboardButton(text="✅ Подтвердить", callback_data="admin:users:confirm"))
    if ban_msg_id:
        try:
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=ban_msg_id,
                text=text,
                reply_markup=keyboard.as_markup(),
            )
        except Exception:
            await message.answer(text, reply_markup=keyboard.as_markup())
    else:
        await message.answer(text, reply_markup=keyboard.as_markup())


async def admin_users_ban_unban_confirm(callback: types.CallbackQuery, state: FSMContext):
    """Подтверждение бана/разбана и выполнение (в т.ч. бан/разбан в канале)."""
    await callback.answer()
    if not await check_admin_rights(callback.from_user.id):
        return
    data = await state.get_data()
    action = data.get("ban_action")
    tg_id = data.get("ban_tg_id")
    username_display = data.get("ban_username_display", str(tg_id))
    if action not in ("ban", "unban") or tg_id is None:
        await state.clear()
        await admin_users_menu(callback, state)
        return
    tg_id = int(tg_id)
    channel_id = CHANNEL_ID or (f"@{CHANNEL_USERNAME}" if CHANNEL_USERNAME else None)
    if action == "ban":
        await add_to_blacklist(tg_id)
        invalidate_banned_cache()
        if channel_id:
            try:
                await bot.ban_chat_member(chat_id=channel_id, user_id=tg_id)
            except Exception as e:
                logger.warning(f"Не удалось забанить в канале {channel_id}: {e}")
        text = f'Пользователь "{username_display}" добавлен в черный список бота.'
    else:
        # Разбан пользователя
        await remove_from_blacklist(tg_id)
        invalidate_banned_cache()
        logger.info(f"Пользователь {username_display} (tg_id: {tg_id}) удален из черного списка")
        # Проверяем, что пользователь действительно удален
        is_still_banned = await is_banned(tg_id)
        if is_still_banned:
            logger.error(f"ОШИБКА: Пользователь {tg_id} все еще в черном списке после разбана!")
        if channel_id:
            try:
                await bot.unban_chat_member(chat_id=channel_id, user_id=tg_id)
            except Exception as e:
                logger.warning(f"Не удалось разбанить в канале {channel_id}: {e}")
        text = f'Пользователь "{username_display}" удален из черного списка бота.'
    await state.clear()
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text="👥 Управление пользователями", callback_data="admin:users"))
    await callback.message.edit_text(text, reply_markup=keyboard.as_markup())


