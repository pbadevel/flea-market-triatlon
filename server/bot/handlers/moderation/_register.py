"""
Обработчик модерации объявлений
"""

from aiogram import Dispatcher, types, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import InputMediaPhoto
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton
from loguru import logger
from src.bot.logging_config import log_moderation

from src.bot.database.states import ModerationState
from src.bot.database.methods import (
    get_ad_by_id, get_ad_photos, approve_ad, reject_ad,
    get_user_by_id, is_moderator,
    get_ad_edit, get_edit_photos, apply_ad_edit, delete_ad_edit_return_info,
)
from src.bot.keyboards.keyboards import *
from src.bot.keyboards.key_text import *
from src.bot.settings.constants import *
from src.bot.settings.settings import CHANNEL_ID, CHANNEL_USERNAME, MODERATION_CHAT_ID, BOT_USERNAME
from src.bot.loader import bot


# === ОДОБРЕНИЕ ===

from .approve import *
from .reject import *

def register_moderation_handlers(dp: Dispatcher):
    """Регистрация обработчиков модерации"""
    
    # Одобрение и отклонение
    dp.callback_query.register(approve_ad_callback, F.data.startswith("mod_approve:"))
    dp.callback_query.register(reject_ad_callback, F.data.startswith("mod_reject:"))
    # Модерация редактирования (копия объявления)
    dp.callback_query.register(approve_edit_callback, F.data.startswith("mod_approve_edit:"))
    dp.callback_query.register(reject_edit_callback, F.data.startswith("mod_reject_edit:"))
    
    # Одобрение и отклонение с комментарием
    dp.callback_query.register(approve_with_comment_callback, F.data.startswith("mod_approve_with_comment:"))
    dp.callback_query.register(reject_with_comment_callback, F.data.startswith("mod_reject_with_comment:"))
    
    # Комментарий для модерации
    dp.callback_query.register(moderation_comment_callback, F.data.startswith("mod_comment:"))
    dp.message.register(moderation_comment_handler, StateFilter(ModerationState.comment), F.text)
    
    # Выбор причины отклонения
    dp.callback_query.register(rejection_reason_callback, StateFilter(ModerationState.rejection_reason), F.data.startswith("reject_reason:"))
    dp.callback_query.register(rejection_back_callback, StateFilter(ModerationState.rejection_reason), F.data == "reject_back")
    
    # Ввод текстовой причины
    dp.message.register(rejection_reason_text_handler, StateFilter(ModerationState.rejection_reason), F.text)
