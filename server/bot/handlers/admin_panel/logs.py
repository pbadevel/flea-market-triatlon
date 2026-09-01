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

# === РАЗДЕЛ "ЛОГИ" ===

async def admin_logs(callback: types.CallbackQuery, state: FSMContext):
    """Отправка логов"""
    await callback.answer()
    
    if not await check_admin_rights(callback.from_user.id):
        await callback.answer("❌ У вас нет прав доступа.", show_alert=True)
        return
    
    await callback.message.answer("📋 Отправляю логи...")
    
    from pathlib import Path
    from aiogram.types import FSInputFile
    
    log_dir = Path("logs")
    
    if not log_dir.exists():
        await callback.message.answer("❌ Папка logs не найдена")
        return
    
    # Отправляем основные логи
    logs_to_send = ['user_actions.log', 'ads.log', 'moderation.log']
    
    for log_name in logs_to_send:
        log_file = log_dir / log_name
        if log_file.exists() and log_file.stat().st_size > 0:
            try:
                document = FSInputFile(str(log_file))
                await callback.message.answer_document(
                    document=document,
                    caption=f"📄 {log_name}"
                )
            except Exception as e:
                logger.error(f"Ошибка при отправке лога {log_name}: {e}")
    
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:back"))
    
    await callback.message.answer("✅ Логи отправлены.", reply_markup=keyboard.as_markup())


# === НАВИГАЦИЯ ===

