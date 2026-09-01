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

async def my_ad_confirm_edit_callback(callback: types.CallbackQuery, state: FSMContext):
    """Подтверждение редактирования и отправка на модерацию"""
    await callback.answer()
    
    ad_id = int(callback.data.split(':')[1])
    data = await state.get_data()
    pending_changes = data.get('pending_changes', {})
    edited_fields = data.get('edited_fields', [])
    
    if not pending_changes and not edited_fields:
        await callback.answer("❌ Нет изменений для отправки на модерацию.", show_alert=True)
        return
    
    ad = await get_ad_by_id(ad_id)
    if not ad:
        await callback.answer("❌ Объявление не найдено.", show_alert=True)
        await state.clear()
        return

    # Редактирование одобренного объявления: копия в ad_edits, оригинал не трогаем
    if ad.status == AdStatus.approved.value or ad.status == 'approved':
        if await exists_edit_for_ad(ad_id):
            await callback.answer("По этому объявлению уже есть редактирование на модерации. Дождитесь решения.", show_alert=True)
            return
        # Собираем данные копии: оригинал + правки
        base = {
            'title': ad.title, 'description': ad.description, 'price': ad.price,
            'city': ad.city, 'country': ad.country, 'category': ad.category,
            'subcategory': ad.subcategory, 'size': ad.size, 'condition': ad.condition,
            'ad_type': getattr(ad, 'ad_type', 'Продажа'),
            'delivery_method': getattr(ad, 'delivery_method', None),
            'contact_method': ad.contact_method,
        }
        overlay = {k: v for k, v in pending_changes.items() if k != 'status'}
        edit_data = {**base, **overlay}
        edit_data['seller_user_id'] = ad.seller_user_id

        if 'photos' in edited_fields:
            photos_state = data.get('photos', [])
            cover_file_id = data.get('cover_photo_file_id')
            if not photos_state:
                await callback.answer("❌ Нет фото для отправки на модерацию.", show_alert=True)
                return
            photos = [{'file_id': p['file_id'], 'position': p.get('position', i)} for i, p in enumerate(photos_state, 1)]
        else:
            ps = await get_ad_photos(ad_id)
            photos = [{'file_id': p.file_id, 'position': p.position} for p in ps]
            cover_file_id = getattr(ad, 'cover_file_id', None)

        try:
            edit_id = await create_ad_edit(ad_id, edit_data, photos, cover_file_id)
        except Exception as e:
            logger.error(f"create_ad_edit объявления #{ad_id}: {e}", exc_info=True)
            await callback.answer("❌ Ошибка при создании копии. Попробуйте позже.", show_alert=True)
            return

        preview_data = {
            **edit_data,
            'photos': [{'file_id': p['file_id']} for p in photos],
        }
        await send_edit_to_moderation(edit_id, ad_id, preview_data, edited_fields)
        chat_id = data.get('my_ad_chat_id', callback.message.chat.id)
        current_msg_id = callback.message.message_id
        await state.update_data(moderation_sent_msg_id=current_msg_id, moderation_sent_chat_id=chat_id)
        await state.update_data(edited_fields=[], pending_changes={})
        text = "✅ Ваше объявление отправлено на модерацию!"
        keyboard = InlineKeyboardBuilder()
        keyboard.row(InlineKeyboardButton(text=BACK_BTN, callback_data="back_after_moderation"))
        try:
            await callback.message.edit_text(text, parse_mode='HTML', reply_markup=keyboard.as_markup())
        except Exception:
            await callback.message.answer(text, parse_mode='HTML', reply_markup=keyboard.as_markup())
        logger.info(f"Пользователь {callback.from_user.id} отредактировал одобренное объявление #{ad_id}, создана копия #{edit_id}, отправлено на модерацию")
        return

    # Редактирование отклонённого/другого: как раньше — правим объявление и шлём на модерацию
    if pending_changes:
        pending_changes = dict(pending_changes)
        pending_changes['status'] = 'pending'
        await update_ad(ad_id, **pending_changes)
        logger.info(f"Применены изменения к объявлению #{ad_id}: {list(pending_changes.keys())}")
    else:
        await update_ad(ad_id, status='pending')

    ad = await get_ad_by_id(ad_id)
    if not ad:
        await callback.answer("❌ Объявление не найдено.", show_alert=True)
        await state.clear()
        return

    photos = await get_ad_photos(ad_id)
    preview_data = {
        'title': ad.title, 'description': ad.description, 'price': ad.price,
        'city': ad.city, 'country': ad.country, 'category': ad.category,
        'subcategory': ad.subcategory, 'size': ad.size, 'condition': ad.condition,
        'ad_type': ad.ad_type, 'delivery_method': ad.delivery_method,
        'contact_method': ad.contact_method,
        'photos': [{'file_id': p.file_id} for p in photos],
    }
    await send_to_moderation(ad_id, preview_data, edited_fields=edited_fields)
    chat_id = data.get('my_ad_chat_id', callback.message.chat.id)
    current_msg_id = callback.message.message_id
    await state.update_data(moderation_sent_msg_id=current_msg_id, moderation_sent_chat_id=chat_id)
    await state.update_data(edited_fields=[], pending_changes={})
    text = "✅ Ваше объявление отправлено на модерацию!"
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text=BACK_BTN, callback_data="back_after_moderation"))
    try:
        await callback.message.edit_text(text, parse_mode='HTML', reply_markup=keyboard.as_markup())
    except Exception:
        await callback.message.answer(text, parse_mode='HTML', reply_markup=keyboard.as_markup())
    logger.info(f"Пользователь {callback.from_user.id} отредактировал объявление #{ad_id}, изменено: {edited_fields}, отправлено на модерацию")


async def back_after_moderation_callback(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'Назад' после отправки на модерацию"""
    await callback.answer()
    
    data = await state.get_data()
    chat_id = data.get('moderation_sent_chat_id', callback.message.chat.id)
    current_msg_id = data.get('moderation_sent_msg_id', callback.message.message_id)
    
    # Удаляем первое сообщение с информацией об объявлении
    await delete_my_ad_info_message(state, chat_id)
    
    # Удаляем все предыдущие сообщения (до 30 последних, кроме текущего)
    try:
        from src.bot.loader import bot
        for i in range(1, 31):
            try:
                msg_id_to_delete = current_msg_id - i
                if msg_id_to_delete > 0:
                    await bot.delete_message(chat_id=chat_id, message_id=msg_id_to_delete)
            except:
                pass
    except:
        pass
    
    # Показываем панель "Мои объявления"
    user = await get_user_by_tg_id(callback.from_user.id)
    if user:
        ads = await get_user_ads(user.id)
        
        await _show_my_ads_page(callback, ads, page=0, edit=True, state=state)
    
    await state.clear()


