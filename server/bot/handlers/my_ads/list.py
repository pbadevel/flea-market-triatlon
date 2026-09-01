"""
Обработчики для раздела "Мои объявления"
"""

from aiogram import Dispatcher, types, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton
from loguru import logger

from src.bot.database.states import MyAdsState
from src.bot.database.methods import (
    get_user_by_tg_id, get_user_by_id, get_user_ads, get_ad_by_id, update_ad, get_ad_photos, add_ad_photos,
    create_ad_edit, exists_edit_for_ad, delete_edits_for_ad, create_or_update_user,
    get_boost_settings, get_daily_boost_count, log_boost, execute_ad_boost,
)
from src.models import AdStatus, AdPhoto
from src.bot.keyboards.keyboards import back_kb, photo_step_kb, confirm_kb, cities_kb, countries_kb, categories_kb, subcategories_kb, sizes_kb
from src.bot.keyboards.key_text import BACK_BTN, SEND_TO_MODERATION_BTN, PAGIN_PREV, PAGIN_NEXT, CONTACT_TELEGRAM_BTN, CONTACT_PHONE_BTN
from src.bot.settings.constants import (
    PHOTO_FIRST_MESSAGE, PHOTO_ERROR_MESSAGE, PHOTO_MAX_ERROR, PHOTO_MIN_ERROR,
    PHONE_INPUT_MESSAGE,
    CATEGORIES, CONDITIONS, CONFIRM_MESSAGE, DEFAULT_CITIES, CIS_COUNTRIES,
    CITY_CUSTOM_MESSAGE, COUNTRY_CUSTOM_MESSAGE, SUBCATEGORIES, SIZE_REQUIRED_SUBCATEGORIES,
    SIZE_MESSAGE, SIZE_CUSTOM_MESSAGE, CATEGORY_MESSAGE, SUBCATEGORY_MESSAGE, LOCATION_MESSAGE
)
from src.bot.utils.image_utils import add_logo_watermark_to_photo
from src.bot.utils.helpers import format_phone_for_display, format_contact_for_display
from src.bot.loader import bot
from src.bot.handlers.add_ad import send_to_moderation, send_edit_to_moderation
from sqlalchemy import delete
from src.bot.database.methods import async_session
from math import ceil

MY_ADS_PER_PAGE = 10


from ._common import *
from ._common import _show_my_ads_page

async def my_ads_handler(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'Мои объявления'"""
    await callback.answer()
    
    # Удаляем первое сообщение с информацией об объявлении, если оно есть
    data = await state.get_data()
    chat_id = data.get('my_ad_chat_id', callback.message.chat.id)
    await delete_my_ad_info_message(state, chat_id)
    
    await state.clear()
    
    # Получаем пользователя
    user = await get_user_by_tg_id(callback.from_user.id)
    if not user:
        await callback.answer("❌ Пользователь не найден.", show_alert=True)
        return
    
    # Получаем все объявления пользователя
    ads = await get_user_ads(user.id)
    
    if not ads:
        text = "📭 У вас пока нет объявлений.\n\nСоздайте первое объявление через 'Создать объявление' "
        keyboard = InlineKeyboardBuilder()
        keyboard.row(InlineKeyboardButton(text=BACK_BTN, callback_data="back_to_menu"))
        
        # Заменяем сообщение главного меню на сообщение "Нет объявлений"
        try:
            await callback.message.edit_text(text, reply_markup=keyboard.as_markup())
        except:
            # Если не удалось отредактировать, отправляем новое
            await callback.message.answer(text, reply_markup=keyboard.as_markup())
        return
    
    await _show_my_ads_page(callback, ads, page=0, edit=True, state=state)


async def my_ads_page_callback(callback: types.CallbackQuery, state: FSMContext):
    """Пагинация списка 'Мои объявления'"""
    await callback.answer()
    try:
        page = int(callback.data.split(':')[1])
    except (ValueError, IndexError):
        page = 0
    user = await get_user_by_tg_id(callback.from_user.id)
    if not user:
        return
    ads = await get_user_ads(user.id)
    if not ads:
        return
    await _show_my_ads_page(callback, ads, page=page, edit=True, state=state)


