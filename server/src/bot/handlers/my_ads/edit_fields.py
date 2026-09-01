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

async def my_ad_edit_field_callback(callback: types.CallbackQuery, state: FSMContext):
    """Начало редактирования конкретного поля"""
    await callback.answer()
    
    parts = callback.data.split(':')
    field = parts[1]  # title, description, city
    ad_id = int(parts[2])
    
    ad = await get_ad_by_id(ad_id)
    if not ad:
        await callback.answer("❌ Объявление не найдено.", show_alert=True)
        return
    
    await state.update_data(editing_ad_id=ad_id, editing_field=field)
    
    # Специальная обработка для фото
    if field == 'photos':
        # Переходим к редактированию обложки (первый этап)
        await state.set_state(MyAdsState.edit_cover_photo)
        # Сохраняем информацию о том, является ли это отклоненным объявлением
        is_rejected = ad.status == AdStatus.rejected.value
        await state.update_data(editing_ad_id=ad_id, photos=[], is_rejected_ad=is_rejected)
        
        text = "📲 **Отправьте обложку для вашего объявления**\n\n"
        text += "(_Одно изображение._)"
        
        from src.bot.keyboards.keyboards import cover_photo_request_kb
        keyboard = cover_photo_request_kb()
        
        # Редактируем сообщение вместо отправки нового
        try:
            await callback.message.edit_text(text, parse_mode='Markdown', reply_markup=keyboard)
            await state.update_data(cover_photo_request_msg_id=callback.message.message_id, last_msg_with_keyboard=callback.message.message_id)
        except:
            msg = await callback.message.answer(text, parse_mode='Markdown', reply_markup=keyboard)
            await state.update_data(cover_photo_request_msg_id=msg.message_id, last_msg_with_keyboard=msg.message_id)
        return
    
    # Специальная обработка для города - показываем кнопки
    if field == 'city':
        await state.set_state(MyAdsState.edit_city_select)
        await state.update_data(editing_ad_id=ad_id, editing_field=field)
        
        current_city = ad.city or 'Не указано'
        text = f"✏️ <b>Редактирование города</b>\n\n"
        text += f"Текущее значение: {current_city}\n\n"
        text += "Выберите новый город:"
        
        from src.bot.keyboards.keyboards import cities_kb
        keyboard = cities_kb()
        
        # Редактируем сообщение вместо отправки нового
        try:
            await callback.message.edit_text(text, parse_mode='HTML', reply_markup=keyboard)
            await state.update_data(last_msg_with_keyboard=callback.message.message_id)
        except:
            msg = await callback.message.answer(text, parse_mode='HTML', reply_markup=keyboard)
            await state.update_data(last_msg_with_keyboard=msg.message_id)
        return
    
    # Специальная обработка для категории - показываем кнопки
    if field == 'category':
        await state.set_state(MyAdsState.edit_category)
        await state.update_data(editing_ad_id=ad_id, editing_field=field)
        
        current_category = CATEGORIES.get(ad.category, ad.category) if ad.category else 'Не указано'
        text = f"✏️ <b>Редактирование категории</b>\n\n"
        text += f"Текущее значение: {current_category}\n\n"
        text += "Выберите новую категорию:"
        
        from src.bot.keyboards.keyboards import categories_kb
        keyboard = categories_kb()
        
        # Редактируем сообщение вместо отправки нового
        try:
            await callback.message.edit_text(text, parse_mode='HTML', reply_markup=keyboard)
            await state.update_data(last_msg_with_keyboard=callback.message.message_id)
        except:
            msg = await callback.message.answer(text, parse_mode='HTML', reply_markup=keyboard)
            await state.update_data(last_msg_with_keyboard=msg.message_id)
        return
    
    # Специальная обработка для размера - показываем кнопки
    if field == 'size':
        await state.set_state(MyAdsState.edit_size)
        await state.update_data(editing_ad_id=ad_id, editing_field=field)
        
        current_size = ad.size or 'Не указано'
        text = f"✏️ <b>Редактирование размера</b>\n\n"
        text += f"Текущее значение: {current_size}\n\n"
        text += "Выберите новый размер:"
        
        from src.bot.keyboards.keyboards import sizes_kb
        keyboard = sizes_kb()
        
        # Редактируем сообщение вместо отправки нового
        try:
            await callback.message.edit_text(text, parse_mode='HTML', reply_markup=keyboard)
            await state.update_data(last_msg_with_keyboard=callback.message.message_id)
        except:
            msg = await callback.message.answer(text, parse_mode='HTML', reply_markup=keyboard)
            await state.update_data(last_msg_with_keyboard=msg.message_id)
        return
    
    # Специальная обработка для контакта: выбор Телеграмм / Телефон. Назад ведёт в меню выбора поля (my_ad_edit_other)
    if field == 'contact':
        await state.set_state(MyAdsState.edit_contact)
        await state.update_data(editing_ad_id=ad_id, editing_field=field)
        data_contact = await state.get_data()
        current = (data_contact.get('pending_changes') or {}).get('contact_method')
        if current is None:
            current = getattr(ad, 'contact_method', None) or 'Не указано'
        if current and current != 'Не указано':
            current_display = format_contact_for_display(current) or current
        else:
            current_display = 'Не указано'
        text = f"✏️ <b>Редактирование контакта</b>\n\n"
        text += f"Текущий контакт: {current_display}\n\n"
        text += "Выберите способ связи:"
        keyboard = InlineKeyboardBuilder()
        keyboard.row(InlineKeyboardButton(text=CONTACT_TELEGRAM_BTN, callback_data=f"my_ad_edit_contact:telegram:{ad_id}"))
        keyboard.row(InlineKeyboardButton(text=CONTACT_PHONE_BTN, callback_data=f"my_ad_edit_contact:phone:{ad_id}"))
        keyboard.row(InlineKeyboardButton(text=BACK_BTN, callback_data=f"my_ad_edit_other:{ad_id}"))
        try:
            await callback.message.edit_text(text, parse_mode='HTML', reply_markup=keyboard.as_markup())
            await state.update_data(last_msg_with_keyboard=callback.message.message_id)
        except Exception:
            msg = await callback.message.answer(text, parse_mode='HTML', reply_markup=keyboard.as_markup())
            await state.update_data(last_msg_with_keyboard=msg.message_id)
        return
    
    field_names = {
        'title': 'название',
        'description': 'описание',
        'city': 'город'
    }
    
    state_map = {
        'title': MyAdsState.edit_title,
        'description': MyAdsState.edit_description,
        'city': MyAdsState.edit_city
    }
    
    await state.set_state(state_map[field])
    
    current_value = getattr(ad, field, 'Не указано')
    if field == 'description' and not current_value:
        current_value = 'Не указано'
    
    text = f"✏️ <b>Редактирование {field_names[field]}</b>\n\n"
    text += f"Текущее значение: {current_value}\n\n"
    text += f"Введите новое значение для {field_names[field]}:"
    
    if field == 'description':
        text += "\n\n⚠️ Максимум 650 символов."
    
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text=BACK_BTN, callback_data=f"my_ad_edit_other:{ad_id}"))
    
    # Редактируем сообщение вместо отправки нового
    try:
        await callback.message.edit_text(text, parse_mode='HTML', reply_markup=keyboard.as_markup())
        await state.update_data(edit_request_msg_id=callback.message.message_id, last_msg_with_keyboard=callback.message.message_id)
    except:
        msg = await callback.message.answer(text, parse_mode='HTML', reply_markup=keyboard.as_markup())
        await state.update_data(edit_request_msg_id=msg.message_id, last_msg_with_keyboard=msg.message_id)


async def my_ad_edit_field_handler(message: types.Message, state: FSMContext):
    """Обработка ввода нового значения поля"""
    data = await state.get_data()
    ad_id = data.get('editing_ad_id')
    field = data.get('editing_field')
    
    if not ad_id or not field:
        await message.answer("❌ Ошибка: данные не найдены.")
        await state.clear()
        return
    
    value = message.text.strip()
    
    # Валидация
    if field == 'title':
        if len(value) < 1 or len(value) > 150:
            await message.answer("❌ Название должно быть от 1 до 150 символов.")
            return
    elif field == 'description':
        if len(value) > 650:
            await message.answer("❌ Описание должно быть не более 650 символов.")
            return
    
    # Получаем объявление
    ad = await get_ad_by_id(ad_id)
    if not ad:
        await message.answer("❌ Объявление не найдено.")
        await state.clear()
        return
    
    # НЕ обновляем объявление в БД! Сохраняем изменения только в state
    # Изменения будут применены только после одобрения модератором
    
    # Сохраняем изменения во временное хранилище
    pending_changes = data.get('pending_changes', {})
    pending_changes[field] = value
    
    # Добавляем поле в список измененных
    edited_fields = data.get('edited_fields', [])
    if field not in edited_fields:
        edited_fields.append(field)
    
    await state.update_data(edited_fields=edited_fields, pending_changes=pending_changes)
    
    # Удаляем сообщение пользователя
    try:
        await message.delete()
    except:
        pass
    
    # Удаляем сообщение с запросом ввода
    edit_request_msg_id = data.get('edit_request_msg_id')
    if edit_request_msg_id:
        try:
            from src.bot.loader import bot
            await bot.delete_message(chat_id=message.chat.id, message_id=edit_request_msg_id)
        except:
            pass
    
    # Возвращаемся в меню редактирования
    await return_to_edit_menu(message, state, ad_id)


async def my_ad_edit_contact_callback(callback: types.CallbackQuery, state: FSMContext):
    """Обработка выбора контакта: Telegram или Телефон (кнопки my_ad_edit_contact:telegram/phone:ad_id)."""
    await callback.answer()
    parts = callback.data.split(':')
    if len(parts) < 3:
        return
    choice = parts[1]  # telegram | phone
    ad_id = int(parts[2])
    ad = await get_ad_by_id(ad_id)
    if not ad:
        await callback.answer("❌ Объявление не найдено.", show_alert=True)
        return
    data = await state.get_data()
    pending_changes = data.get('pending_changes', {})
    edited_fields = data.get('edited_fields', [])
    if choice == 'telegram':
        user = await get_user_by_tg_id(callback.from_user.id)
        if not user:
            user = await create_or_update_user(callback.message, from_user=callback.from_user)
        contact_value = f"@{user.username}" if user.username else f"tg://user?id={user.tg_user_id}"
        pending_changes['contact_method'] = contact_value
        if 'contact' not in edited_fields:
            edited_fields.append('contact')
        await state.update_data(pending_changes=pending_changes, edited_fields=edited_fields)
        await state.set_state(MyAdsState.edit_other)
        await return_to_edit_menu(callback, state, ad_id)
        return
    if choice == 'phone':
        await state.set_state(MyAdsState.edit_contact_phone)
        await state.update_data(editing_ad_id=ad_id, editing_field='contact')
        text = PHONE_INPUT_MESSAGE
        keyboard = InlineKeyboardBuilder()
        keyboard.row(InlineKeyboardButton(text=BACK_BTN, callback_data=f"my_ad_edit_other:{ad_id}"))
        try:
            await callback.message.edit_text(text, parse_mode='HTML', reply_markup=keyboard.as_markup())
            await state.update_data(last_msg_with_keyboard=callback.message.message_id)
        except Exception:
            msg = await callback.message.answer(text, parse_mode='HTML', reply_markup=keyboard.as_markup())
            await state.update_data(last_msg_with_keyboard=msg.message_id)
        return


async def my_ad_edit_contact_phone_handler(message: types.Message, state: FSMContext):
    """Ввод номера телефона при редактировании контакта (сохраняем в pending_changes, не в БД)."""
    data = await state.get_data()
    ad_id = data.get('editing_ad_id')
    if not ad_id:
        await state.clear()
        return
    phone = message.text.strip().replace(' ', '').replace('-', '').replace('+', '')
    if not phone.isdigit() or len(phone) != 11:
        try:
            await message.delete()
        except Exception:
            pass
        err = "❌ Номер должен содержать ровно 11 цифр (без +). Введите ещё раз."
        keyboard = InlineKeyboardBuilder()
        keyboard.row(InlineKeyboardButton(text=BACK_BTN, callback_data=f"my_ad_edit_other:{ad_id}"))
        last_msg_id = data.get('last_msg_with_keyboard')
        if last_msg_id:
            try:
                await bot.edit_message_text(
                    chat_id=message.chat.id, message_id=last_msg_id,
                    text=err, parse_mode='HTML', reply_markup=keyboard.as_markup(),
                )
                await state.update_data(last_msg_with_keyboard=last_msg_id)
            except Exception:
                await message.answer(err, parse_mode='HTML', reply_markup=keyboard.as_markup())
        else:
            await message.answer(err, parse_mode='HTML', reply_markup=keyboard.as_markup())
        return
    pending_changes = data.get('pending_changes', {})
    pending_changes['contact_method'] = phone
    edited_fields = data.get('edited_fields', [])
    if 'contact' not in edited_fields:
        edited_fields.append('contact')
    await state.update_data(pending_changes=pending_changes, edited_fields=edited_fields)
    try:
        await message.delete()
    except Exception:
        pass
    edit_request_msg_id = data.get('edit_request_msg_id')
    if edit_request_msg_id:
        try:
            await bot.delete_message(chat_id=message.chat.id, message_id=edit_request_msg_id)
        except Exception:
            pass
    await return_to_edit_menu(message, state, ad_id)


def _build_edit_other_menu(ad_id: int, ad, edited_fields: list = None) -> tuple:
    """Собрать текст и клавиатуру меню «Редактирование других параметров». edited_fields — список изменённых полей для блока «Изменено»."""
    text = f"📝 <b>Редактирование других параметров</b>\n\n"
    if edited_fields:
        field_names = {
            'title': 'Название', 'description': 'Описание', 'category': 'Категория',
            'size': 'Размер', 'city': 'Город', 'contact': 'Контакт', 'photos': 'Фото'
        }
        text += "✏️ <b>Изменено:</b>\n"
        for field in edited_fields:
            text += f"  • {field_names.get(field, field)}\n"
        text += "\n"
    text += "Выберите, что хотите изменить:\n\n"
    text += "⚠️ <b>Внимание:</b> Изменения будут отправлены на модерацию."
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text="📝 Название", callback_data=f"my_ad_edit_field:title:{ad_id}"))
    keyboard.row(InlineKeyboardButton(text="📄 Описание", callback_data=f"my_ad_edit_field:description:{ad_id}"))
    if needs_size(ad.category, ad.subcategory):
        keyboard.row(InlineKeyboardButton(text="📏 Размер", callback_data=f"my_ad_edit_field:size:{ad_id}"))
    keyboard.row(InlineKeyboardButton(text="📍 Город", callback_data=f"my_ad_edit_field:city:{ad_id}"))
    keyboard.row(InlineKeyboardButton(text="📞 Контакт", callback_data=f"my_ad_edit_field:contact:{ad_id}"))
    keyboard.row(InlineKeyboardButton(text="📸 Изменить фото", callback_data=f"my_ad_edit_field:photos:{ad_id}"))
    keyboard.row(InlineKeyboardButton(text=BACK_BTN, callback_data=f"my_ad_edit:{ad_id}"))
    return text, keyboard.as_markup()


