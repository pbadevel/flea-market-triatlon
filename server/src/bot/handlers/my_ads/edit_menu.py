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

async def my_ad_edit_callback(callback: types.CallbackQuery, state: FSMContext):
    """Меню редактирования объявления"""
    await callback.answer()
    
    # НЕ удаляем первое сообщение с информацией об объявлении - оно должно оставаться для справки
    # Удалим его только после отправки на модерацию
    
    ad_id = int(callback.data.split(':')[1])
    ad = await get_ad_by_id(ad_id)
    
    if not ad:
        await callback.answer("❌ Объявление не найдено.", show_alert=True)
        return
    
    # Проверяем, что это объявление пользователя
    user = await get_user_by_tg_id(callback.from_user.id)
    if not user or ad.seller_user_id != user.id:
        await callback.answer("❌ Это не ваше объявление.", show_alert=True)
        return
    
    # Проверяем статус - можно редактировать одобренные, отклоненные и снятые с публикации
    if ad.status not in [AdStatus.approved.value, AdStatus.rejected.value, 'unpublished', 'removed']:
        await callback.answer("❌ Можно редактировать только одобренные, отклоненные или снятые с публикации объявления.", show_alert=True)
        return
    
    if (ad.status == AdStatus.approved.value or ad.status == "approved") and await exists_edit_for_ad(ad_id):
        await callback.answer("По этому объявлению уже есть редактирование на модерации. Дождитесь решения.", show_alert=True)
        return
    
    # Получаем список измененных полей из state
    data = await state.get_data()
    edited_fields = data.get('edited_fields', [])
    
    await state.update_data(editing_ad_id=ad_id)
    await state.set_state(MyAdsState.edit_menu)
    
    text = f"✏️ <b>Редактирование объявления #{ad.id}</b>\n\n"
    
    # Если есть изменения, показываем их
    if edited_fields:
        field_names = {
            'title': 'Название',
            'description': 'Описание',
            'category': 'Категория',
            'size': 'Размер',
            'city': 'Город',
            'contact': 'Контакт',
            'photos': 'Фото'
        }
        text += "✏️ <b>Изменено:</b>\n"
        for field in edited_fields:
            field_name = field_names.get(field, field)
            text += f"  • {field_name}\n"
        text += "\n"
    
    text += "Выберите, что хотите изменить:\n\n"
    text += "💰 <b>Цена</b> - изменение без модерации\n"
    text += "📝 <b>Другие параметры</b> - изменение с модерацией"
    
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(
        text="💰 Изменить цену",
        callback_data=f"my_ad_edit_price:{ad.id}"
    ))
    keyboard.row(InlineKeyboardButton(
        text="📝 Изменить другие параметры",
        callback_data=f"my_ad_edit_other:{ad.id}"
    ))
    
    # Показываем кнопку "Отправить на модерацию" только если есть изменения
    if edited_fields:
        keyboard.row(InlineKeyboardButton(
            text=SEND_TO_MODERATION_BTN,
            callback_data=f"my_ad_confirm_edit:{ad_id}"
        ))
    
    keyboard.row(InlineKeyboardButton(text=BACK_BTN, callback_data=f"my_ad:{ad.id}"))
    
    await callback.message.answer(text, parse_mode='HTML', reply_markup=keyboard.as_markup())
    try:
        await callback.message.delete()
    except:
        pass


async def my_ad_edit_other_callback(callback: types.CallbackQuery, state: FSMContext):
    """Начало редактирования других параметров (с модерацией)"""
    await callback.answer()
    
    ad_id = int(callback.data.split(':')[1])
    ad = await get_ad_by_id(ad_id)
    
    if not ad:
        await callback.answer("❌ Объявление не найдено.", show_alert=True)
        return
    
    await state.update_data(editing_ad_id=ad_id)
    await state.set_state(MyAdsState.edit_other)
    
    text = f"📝 <b>Редактирование других параметров</b>\n\n"
    text += "Выберите, что хотите изменить:\n\n"
    text += "⚠️ <b>Внимание:</b> Изменения будут отправлены на модерацию."
    
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(
        text="📝 Название",
        callback_data=f"my_ad_edit_field:title:{ad_id}"
    ))
    keyboard.row(InlineKeyboardButton(
        text="📄 Описание",
        callback_data=f"my_ad_edit_field:description:{ad_id}"
    ))
    # Показываем кнопку размера только если размер требуется для данной подкатегории
    if needs_size(ad.category, ad.subcategory):
        keyboard.row(InlineKeyboardButton(
            text="📏 Размер",
            callback_data=f"my_ad_edit_field:size:{ad_id}"
        ))
    keyboard.row(InlineKeyboardButton(
        text="📍 Город",
        callback_data=f"my_ad_edit_field:city:{ad_id}"
    ))
    keyboard.row(InlineKeyboardButton(
        text="📞 Контакт",
        callback_data=f"my_ad_edit_field:contact:{ad_id}"
    ))
    keyboard.row(InlineKeyboardButton(
        text="📸 Изменить фото",
        callback_data=f"my_ad_edit_field:photos:{ad_id}"
    ))
    keyboard.row(InlineKeyboardButton(text=BACK_BTN, callback_data=f"my_ad_edit:{ad_id}"))
    
    # Редактируем сообщение вместо отправки нового
    try:
        await callback.message.edit_text(text, parse_mode='HTML', reply_markup=keyboard.as_markup())
        await state.update_data(last_msg_with_keyboard=callback.message.message_id)
    except:
        msg = await callback.message.answer(text, parse_mode='HTML', reply_markup=keyboard.as_markup())
        await state.update_data(last_msg_with_keyboard=msg.message_id)


