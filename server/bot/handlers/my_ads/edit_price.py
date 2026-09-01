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

async def my_ad_edit_price_callback(callback: types.CallbackQuery, state: FSMContext):
    """Начало редактирования цены"""
    await callback.answer()
    
    ad_id = int(callback.data.split(':')[1])
    ad = await get_ad_by_id(ad_id)
    
    if not ad:
        await callback.answer("❌ Объявление не найдено.", show_alert=True)
        return
    
    await state.update_data(editing_ad_id=ad_id, editing_field='price')
    await state.set_state(MyAdsState.edit_price)
    
    text = f"💰 <b>Редактирование цены</b>\n\n"
    text += f"Текущая цена: {ad.price} ₽\n\n"
    text += "Введите новую цену (только число, до 7 знаков):"
    
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text=BACK_BTN, callback_data=f"my_ad_edit:{ad_id}"))
    
    msg = await callback.message.answer(text, parse_mode='HTML', reply_markup=keyboard.as_markup())
    # Сохраняем ID сообщения с запросом ввода цены для редактирования / удаления
    await state.update_data(last_msg_with_keyboard=msg.message_id, price_input_error_shown=False)
    try:
        await callback.message.delete()
    except:
        pass


async def my_ad_edit_price_handler(message: types.Message, state: FSMContext):
    """Обработка ввода новой цены"""
    data = await state.get_data()
    ad_id = data.get('editing_ad_id')
    
    if not ad_id:
        await message.answer("❌ Ошибка: объявление не найдено.")
        await state.clear()
        return
    
    last_msg_id = data.get('last_msg_with_keyboard')
    error_shown = data.get('price_input_error_shown', False)

    err_text = None
    try:
        new_price = int(message.text.strip())
        if new_price <= 0 or len(str(new_price)) > 7:
            err_text = "❌ Цена должна быть положительным числом до 7 знаков."
    except ValueError:
        err_text = "❌ Цена должна быть числом."

    if err_text:
        try:
            await message.delete()
        except Exception:
            pass
        if not error_shown and last_msg_id:
            ad = await get_ad_by_id(ad_id)
            if ad:
                prompt = (
                    f"💰 <b>Редактирование цены</b>\n\n"
                    f"Текущая цена: {ad.price} ₽\n\n"
                    f"Введите новую цену (только число, до 7 знаков):\n\n"
                    f"{err_text}"
                )
            else:
                prompt = err_text
            keyboard = InlineKeyboardBuilder()
            keyboard.row(InlineKeyboardButton(text=BACK_BTN, callback_data=f"my_ad_edit:{ad_id}"))
            try:
                await bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=last_msg_id,
                    text=prompt,
                    parse_mode='HTML',
                    reply_markup=keyboard.as_markup(),
                )
                await state.update_data(price_input_error_shown=True)
            except Exception:
                pass
        return

    # Обновляем цену без модерации
    success = await update_ad(ad_id, price=new_price)
    
    if success:
        # Обновляем сообщение в канале, если объявление уже опубликовано
        ad = await get_ad_by_id(ad_id)
        if ad.status == 'approved' and ad.channel_message_id:
            await update_channel_message(ad_id, ad, price_change=True)
        
        logger.info(f"Пользователь {message.from_user.id} обновил цену объявления #{ad_id} на {new_price}")
        
        # Удаляем сообщение пользователя с ценой
        try:
            await message.delete()
        except:
            pass
        
        # Удаляем сообщение с запросом ввода цены
        data = await state.get_data()
        last_msg_id = data.get('last_msg_with_keyboard')
        if last_msg_id:
            try:
                await bot.delete_message(chat_id=message.chat.id, message_id=last_msg_id)
            except:
                pass
        
        # Возвращаемся в меню редактирования с указанием, что цена изменена
        await state.update_data(editing_ad_id=ad_id, price_input_error_shown=False)
        await state.set_state(MyAdsState.edit_menu)
        
        text = f"✏️ <b>Редактирование объявления #{ad_id}</b>\n\n"
        text += f"✅ <b>Цена изменена:</b> {new_price} ₽\n\n"
        text += "Выберите, что хотите изменить:\n\n"
        text += "💰 <b>Цена</b> - изменение без модерации\n"
        text += "📝 <b>Другие параметры</b> - изменение с модерацией"
        
        keyboard = InlineKeyboardBuilder()
        keyboard.row(InlineKeyboardButton(
            text="💰 Изменить цену",
            callback_data=f"my_ad_edit_price:{ad_id}"
        ))
        keyboard.row(InlineKeyboardButton(
            text="📝 Изменить другие параметры",
            callback_data=f"my_ad_edit_other:{ad_id}"
        ))
        keyboard.row(InlineKeyboardButton(
            text="🏠 Главное меню",
            callback_data="my_ads_price_main_menu"
        ))
        
        # Получаем список измененных полей из state
        data = await state.get_data()
        edited_fields = data.get('edited_fields', [])
        
        # Показываем кнопку "Отправить на модерацию" только если есть изменения
        if edited_fields:
            keyboard.row(InlineKeyboardButton(
                text=SEND_TO_MODERATION_BTN,
                callback_data=f"my_ad_confirm_edit:{ad_id}"
            ))
        
        keyboard.row(InlineKeyboardButton(text=BACK_BTN, callback_data=f"my_ad:{ad_id}"))
        
        await message.answer(text, parse_mode='HTML', reply_markup=keyboard.as_markup())
    else:
        await message.answer("❌ Не удалось обновить цену.")
        await state.clear()


async def my_ads_price_main_menu_callback(callback: types.CallbackQuery, state: FSMContext):
    """Переход в главное меню после изменения цены с очисткой предыдущих сообщений."""
    await callback.answer()

    current_msg_id = callback.message.message_id

    from src.bot.handlers.start import get_main_menu_text
    from src.bot.keyboards.keyboards import main_menu_kb
    from src.bot.handlers.catalog.reviews import delete_previous_messages

    menu_text = await get_main_menu_text()
    try:
        await callback.message.edit_text(
            menu_text,
            parse_mode='HTML',
            reply_markup=await main_menu_kb(callback.from_user.id)
        )
        await state.update_data(main_menu_msg_id=callback.message.message_id)
    except Exception:
        from src.bot.handlers.start import send_main_menu
        await send_main_menu(callback, state=state)

    await delete_previous_messages(callback.message.chat.id, current_msg_id, 20)

