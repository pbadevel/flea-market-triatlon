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

# === /post_attach (пост в канал с кнопкой на бота) ===

async def post_attach_command(message: types.Message, state: FSMContext):
    """Команда /post_attach: запросить текст поста, затем текст кнопки, затем опубликовать и закрепить."""
    if not await check_admin_rights(message.from_user.id):
        await message.answer("❌ У вас нет прав доступа.")
        return

    await state.clear()
    await message.answer(
        'Пришлите текст для поста, например: '
        '<code>Для размещения объявления о продаже или аренде воспользуйтесь ботом</code>',
        parse_mode='HTML'
    )
    await state.set_state(PostAttachState.post_text)


async def post_attach_text_handler(message: types.Message, state: FSMContext):
    """Шаг 1: сохраняем текст поста, просим текст кнопки."""
    if not await check_admin_rights(message.from_user.id):
        await message.answer("❌ У вас нет прав доступа.")
        return

    await state.update_data(post_text=message.text)
    await message.answer('Пришлите текст для кнопки, например: <code>Продать</code>', parse_mode='HTML')
    await state.set_state(PostAttachState.post_button_text)


async def post_attach_button_text_handler(message: types.Message, state: FSMContext):
    """Шаг 2: публикуем пост в канале и закрепляем."""
    if not await check_admin_rights(message.from_user.id):
        await message.answer("❌ У вас нет прав доступа.")
        return

    data = await state.get_data()
    post_text = data.get("post_text") or ""
    button_text = message.text

    channel_target = f"@{CHANNEL_USERNAME}" if CHANNEL_USERNAME else CHANNEL_ID

    # ссылка на бота (аналог config.tg_bot.link_bot)
    bot_link = f"https://t.me/{BOT_USERNAME}" if BOT_USERNAME else None

    keyboard = None
    if bot_link:
        kb = InlineKeyboardBuilder()
        kb.row(InlineKeyboardButton(text=button_text, url=bot_link))
        keyboard = kb.as_markup()

    sent = await bot.send_message(
        chat_id=channel_target,
        text=post_text,
        parse_mode='HTML',
        reply_markup=keyboard
    )

    try:
        await bot.pin_chat_message(chat_id=channel_target, message_id=sent.message_id)
    except Exception as e:
        logger.warning(f"Не удалось закрепить пост (chat_id={channel_target}, message_id={sent.message_id}): {e}")

    await message.answer("✅ Пост размещён и закреплён в ресурсе.")
    await state.clear()


