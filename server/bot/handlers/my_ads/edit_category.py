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

async def my_ad_edit_category_callback(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик выбора категории при редактировании"""
    await callback.answer()
    
    data = await state.get_data()
    ad_id = data.get('editing_ad_id')
    
    if not ad_id:
        await callback.answer("❌ Ошибка: объявление не найдено.", show_alert=True)
        await state.clear()
        return
    
    category_key = callback.data.split(':')[1]
    await state.update_data(category=category_key)
    await state.set_state(MyAdsState.edit_subcategory)
    
    # Сначала отправляем новое сообщение
    msg = await callback.message.answer(
        SUBCATEGORY_MESSAGE,
        reply_markup=subcategories_kb(category_key)
    )
    await state.update_data(last_msg_with_keyboard=msg.message_id)
    
    # Потом удаляем предыдущее сообщение
    try:
        await callback.message.delete()
    except:
        pass


async def my_ad_edit_bike_group_callback(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик выбора группы велоспорта при редактировании"""
    await callback.answer()
    
    data = await state.get_data()
    ad_id = data.get('editing_ad_id')
    
    if not ad_id:
        await callback.answer("❌ Ошибка: объявление не найдено.", show_alert=True)
        await state.clear()
        return
    
    group_key = callback.data.split(':')[1]
    
    # Показываем подкатегории внутри группы
    from src.bot.keyboards.keyboards import bike_group_subcategories_kb
    try:
        await callback.message.edit_text(
            SUBCATEGORY_MESSAGE,
            reply_markup=bike_group_subcategories_kb(group_key)
        )
        await state.update_data(last_msg_with_keyboard=callback.message.message_id)
    except:
        msg = await callback.message.answer(
            SUBCATEGORY_MESSAGE,
            reply_markup=bike_group_subcategories_kb(group_key)
        )
        await state.update_data(last_msg_with_keyboard=msg.message_id)


async def my_ad_edit_subcategory_callback(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик выбора подкатегории при редактировании"""
    await callback.answer()
    
    data = await state.get_data()
    ad_id = data.get('editing_ad_id')
    category = data.get('category')
    
    if not ad_id:
        await callback.answer("❌ Ошибка: объявление не найдено.", show_alert=True)
        await state.clear()
        return
    
    subcategory_key = callback.data.split(':')[1]
    
    # Обновляем объявление
    success = await update_ad(ad_id, category=category, subcategory=subcategory_key)
    
    if not success:
        await callback.answer("❌ Не удалось обновить объявление.", show_alert=True)
        await state.clear()
        return
    
    # Добавляем поле в список измененных
    edited_fields = data.get('edited_fields', [])
    if 'category' not in edited_fields:
        edited_fields.append('category')
    
    await state.update_data(edited_fields=edited_fields)
    
    try:
        await callback.message.delete()
    except:
        pass
    
    # Возвращаемся в меню редактирования
    await return_to_edit_menu(callback, state, ad_id)


async def my_ad_edit_size_callback(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик выбора размера при редактировании"""
    await callback.answer()
    
    data = await state.get_data()
    ad_id = data.get('editing_ad_id')
    
    if not ad_id:
        await callback.answer("❌ Ошибка: объявление не найдено.", show_alert=True)
        await state.clear()
        return
    
    size_data = callback.data.split(':')[1]
    
    if size_data == 'manual':
        # Ввод размера вручную
        await state.set_state(MyAdsState.edit_size_manual)
        try:
            await callback.message.edit_text(
                SIZE_CUSTOM_MESSAGE,
                reply_markup=back_kb()
            )
            await state.update_data(last_msg_with_keyboard=callback.message.message_id)
            return
        except:
            msg = await callback.message.answer(
                SIZE_CUSTOM_MESSAGE,
                reply_markup=back_kb()
            )
            await state.update_data(last_msg_with_keyboard=msg.message_id)
            return
    else:
        # НЕ обновляем объявление в БД! Сохраняем изменения только в state
        pending_changes = data.get('pending_changes', {})
        if size_data == 'none':
            pending_changes['size'] = None
        else:
            pending_changes['size'] = size_data
        
        # Добавляем поле в список измененных
        edited_fields = data.get('edited_fields', [])
        if 'size' not in edited_fields:
            edited_fields.append('size')
        
        await state.update_data(edited_fields=edited_fields, pending_changes=pending_changes)
    
    # Получаем объявление для определения контекста
    ad = await get_ad_by_id(ad_id)
    if not ad:
        await callback.answer("❌ Объявление не найдено.", show_alert=True)
        await state.clear()
        return
    
    # Определяем, является ли это отклоненным объявлением
    is_rejected = ad.status == AdStatus.rejected.value
    
    # Возвращаемся в меню редактирования
    await state.set_state(MyAdsState.edit_other)
    
    try:
        await callback.message.delete()
    except:
        pass
    
    if is_rejected:
        text = f"📝 <b>Редактирование отклоненного объявления #{ad.id}</b>\n\n"
    else:
        text = f"📝 <b>Редактирование других параметров</b>\n\n"
    
    # Показываем список измененных полей
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
    
    # Показываем кнопку "Отправить на модерацию" только если есть изменения
    if edited_fields:
        keyboard.row(InlineKeyboardButton(
            text=SEND_TO_MODERATION_BTN,
            callback_data=f"my_ad_confirm_edit:{ad_id}"
        ))
    
    if is_rejected:
        keyboard.row(InlineKeyboardButton(text=BACK_BTN, callback_data=f"my_ad:{ad_id}"))
    else:
        keyboard.row(InlineKeyboardButton(text=BACK_BTN, callback_data=f"my_ad_edit:{ad_id}"))
    
    await callback.message.answer(text, parse_mode='HTML', reply_markup=keyboard.as_markup())


async def my_ad_edit_size_manual_handler(message: types.Message, state: FSMContext):
    """Обработчик ввода размера вручную при редактировании"""
    data = await state.get_data()
    ad_id = data.get('editing_ad_id')
    
    if not ad_id:
        await message.answer("❌ Ошибка: объявление не найдено.")
        await state.clear()
        return
    
    # Получаем объявление для определения контекста
    ad = await get_ad_by_id(ad_id)
    if not ad:
        await message.answer("❌ Объявление не найдено.")
        await state.clear()
        return
    
    # Определяем, является ли это отклоненным объявлением
    is_rejected = ad.status == AdStatus.rejected.value
    
    size = message.text.strip()
    
    if not size or len(size) > 6:
        # Просто удаляем сообщение пользователя без отправки сообщения об ошибке
        try:
            await message.delete()
        except:
            pass
        return
    
    # Удаляем сообщение пользователя
    try:
        await message.delete()
    except:
        pass
    
    # Для отклоненных объявлений сохраняем изменения в state, а не обновляем БД
    if is_rejected:
        # НЕ обновляем объявление в БД! Сохраняем изменения только в state
        pending_changes = data.get('pending_changes', {})
        pending_changes['size'] = size
        
        # Добавляем поле в список измененных
        edited_fields = data.get('edited_fields', [])
        if 'size' not in edited_fields:
            edited_fields.append('size')
        
        await state.update_data(edited_fields=edited_fields, pending_changes=pending_changes)
    else:
        # Для не отклоненных объявлений обновляем БД
        success = await update_ad(ad_id, size=size)
        
        if not success:
            await message.answer("❌ Не удалось обновить объявление.")
            await state.clear()
            return
        
        # Добавляем поле в список измененных
        edited_fields = data.get('edited_fields', [])
        if 'size' not in edited_fields:
            edited_fields.append('size')
        
        await state.update_data(edited_fields=edited_fields)
    
    # Удаляем предыдущие сообщения
    last_msg_id = data.get('last_msg_with_keyboard')
    if last_msg_id:
        try:
            await bot.delete_message(chat_id=message.chat.id, message_id=last_msg_id)
        except:
            pass
    
    # Возвращаемся в меню редактирования
    await state.set_state(MyAdsState.edit_other)
    
    # Получаем обновленные данные из state
    data = await state.get_data()
    edited_fields = data.get('edited_fields', [])
    
    # Удаляем предыдущие сообщения
    last_msg_id = data.get('last_msg_with_keyboard')
    if last_msg_id:
        try:
            await bot.delete_message(chat_id=message.chat.id, message_id=last_msg_id)
        except:
            pass
    
    try:
        await message.delete()
    except:
        pass
    
    if is_rejected:
        text = f"📝 <b>Редактирование отклоненного объявления #{ad.id}</b>\n\n"
    else:
        text = f"📝 <b>Редактирование других параметров</b>\n\n"
    
    # Показываем список измененных полей
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
    
    # Показываем кнопку "Отправить на модерацию" только если есть изменения
    if edited_fields:
        keyboard.row(InlineKeyboardButton(
            text=SEND_TO_MODERATION_BTN,
            callback_data=f"my_ad_confirm_edit:{ad_id}"
        ))
    
    if is_rejected:
        keyboard.row(InlineKeyboardButton(text=BACK_BTN, callback_data=f"my_ad:{ad_id}"))
    else:
        keyboard.row(InlineKeyboardButton(text=BACK_BTN, callback_data=f"my_ad_edit:{ad_id}"))
    
    await message.answer(text, parse_mode='HTML', reply_markup=keyboard.as_markup())


async def my_ad_edit_category_back_callback(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'Назад' при редактировании категории"""
    await callback.answer()
    
    data = await state.get_data()
    ad_id = data.get('editing_ad_id')
    current_state = await state.get_state()
    
    if not ad_id:
        await callback.answer("❌ Ошибка: объявление не найдено.", show_alert=True)
        await state.clear()
        return
    
    # Если мы в состоянии выбора подкатегории, возвращаемся к выбору категории или к списку подкатегорий велоспорта
    if current_state == MyAdsState.edit_subcategory:
        ad = await get_ad_by_id(ad_id)
        category = ad.category if ad else None
        
        # Если это велоспорт и мы внутри группы, возвращаемся к списку подкатегорий
        if category == "bike" and callback.data == "back":
            await state.set_state(MyAdsState.edit_subcategory)
            text = f"✏️ <b>Редактирование подкатегории</b>\n\n"
            text += "Выберите новую подкатегорию:"
            
            from src.bot.keyboards.keyboards import subcategories_kb
            keyboard = subcategories_kb(category)
            
            try:
                await callback.message.edit_text(text, parse_mode='HTML', reply_markup=keyboard)
            except:
                await callback.message.answer(text, parse_mode='HTML', reply_markup=keyboard)
                try:
                    await callback.message.delete()
                except:
                    pass
        else:
            # Возвращаемся к выбору категории
            await state.set_state(MyAdsState.edit_category)
            current_category = CATEGORIES.get(category, category) if category else 'Не указано'
            text = f"✏️ <b>Редактирование категории</b>\n\n"
            text += f"Текущее значение: {current_category}\n\n"
            text += "Выберите новую категорию:"
            
            from src.bot.keyboards.keyboards import categories_kb
            keyboard = categories_kb()
            
            await callback.message.answer(text, parse_mode='HTML', reply_markup=keyboard)
            try:
                await callback.message.delete()
            except:
                pass
    else:
        # Возвращаемся к меню редактирования других параметров
        ad = await get_ad_by_id(ad_id)
        if not ad:
            await callback.answer("❌ Объявление не найдено.", show_alert=True)
            await state.clear()
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
    
    await callback.message.answer(text, parse_mode='HTML', reply_markup=keyboard.as_markup())
    try:
        await callback.message.delete()
    except:
        pass


async def my_ad_edit_size_back_callback(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'Назад' при редактировании размера"""
    await callback.answer()
    
    data = await state.get_data()
    ad_id = data.get('editing_ad_id')
    current_state = await state.get_state()
    
    if not ad_id:
        await callback.answer("❌ Ошибка: объявление не найдено.", show_alert=True)
        await state.clear()
        return
    
    # Если мы в состоянии ввода размера вручную, возвращаемся к выбору размера
    if current_state == MyAdsState.edit_size_manual:
        await state.set_state(MyAdsState.edit_size)
        ad = await get_ad_by_id(ad_id)
        current_size = ad.size or 'Не указано'
        text = f"✏️ <b>Редактирование размера</b>\n\n"
        text += f"Текущее значение: {current_size}\n\n"
        text += "Выберите новый размер:"
        
        from src.bot.keyboards.keyboards import sizes_kb
        keyboard = sizes_kb()
        
        await callback.message.answer(text, parse_mode='HTML', reply_markup=keyboard)
        try:
            await callback.message.delete()
        except:
            pass
    else:
        # Возвращаемся к меню редактирования других параметров
        ad = await get_ad_by_id(ad_id)
        if not ad:
            await callback.answer("❌ Объявление не найдено.", show_alert=True)
            await state.clear()
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
        
        await callback.message.answer(text, parse_mode='HTML', reply_markup=keyboard.as_markup())
        try:
            await callback.message.delete()
        except:
            pass


