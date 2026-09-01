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

async def my_ad_edit_city_callback(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик выбора города при редактировании"""
    await callback.answer()
    
    data = await state.get_data()
    ad_id = data.get('editing_ad_id')
    
    if not ad_id:
        await callback.answer("❌ Ошибка: объявление не найдено.", show_alert=True)
        await state.clear()
        return
    
    city_key = callback.data.split(':')[1]
    
    if city_key == 'other':
        await state.set_state(MyAdsState.edit_city_custom)
        
        msg = await callback.message.answer(
            CITY_CUSTOM_MESSAGE,
            reply_markup=back_kb()
        )
        await state.update_data(last_msg_with_keyboard=msg.message_id)
        
        try:
            await callback.message.delete()
        except:
            pass
    elif city_key == 'other_country':
        msg = await callback.message.answer(
            "Выберите страну:",
            reply_markup=countries_kb()
        )
        await state.update_data(last_msg_with_keyboard=msg.message_id)
        
        try:
            await callback.message.delete()
        except:
            pass
    else:
        city = DEFAULT_CITIES[city_key]
        
        # НЕ обновляем объявление в БД! Сохраняем изменения только в state
        pending_changes = data.get('pending_changes', {})
        pending_changes['city'] = city
        pending_changes['country'] = None
        
        # Добавляем поле в список измененных
        edited_fields = data.get('edited_fields', [])
        if 'city' not in edited_fields:
            edited_fields.append('city')
        
        await state.update_data(edited_fields=edited_fields, pending_changes=pending_changes)
        
        try:
            await callback.message.delete()
        except:
            pass
        
        # Возвращаемся в меню редактирования
        await return_to_edit_menu(callback, state, ad_id)


async def my_ad_edit_country_callback(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик выбора страны при редактировании"""
    await callback.answer()
    
    data = await state.get_data()
    ad_id = data.get('editing_ad_id')
    
    if not ad_id:
        await callback.answer("❌ Ошибка: объявление не найдено.", show_alert=True)
        await state.clear()
        return
    
    country_key = callback.data.split(':')[1]
    
    if country_key == 'other':
        await state.set_state(MyAdsState.edit_city_custom)
        try:
            await callback.message.edit_text(
                COUNTRY_CUSTOM_MESSAGE,
                reply_markup=back_kb()
            )
        except:
            msg = await callback.message.answer(
                COUNTRY_CUSTOM_MESSAGE,
                reply_markup=back_kb()
            )
            await state.update_data(last_msg_with_keyboard=msg.message_id)
            return
        await state.update_data(last_msg_with_keyboard=callback.message.message_id)
    else:
        # Предустановленная страна - показываем список городов
        country = CIS_COUNTRIES[country_key]['name']
        await state.update_data(country=country, selected_country_key=country_key)
        await state.set_state(MyAdsState.edit_city_after_country)
        
        # Показываем список городов страны
        from src.bot.keyboards.keyboards import country_cities_kb
        try:
            await callback.message.edit_text(
                "📍 Выберите город:",
                reply_markup=country_cities_kb(country_key)
            )
            await state.update_data(last_msg_with_keyboard=callback.message.message_id)
        except:
            msg = await callback.message.answer(
                "📍 Выберите город:",
                reply_markup=country_cities_kb(country_key)
            )
            await state.update_data(last_msg_with_keyboard=msg.message_id)


async def my_ad_edit_city_custom_handler(message: types.Message, state: FSMContext):
    """Обработчик ввода собственного города при редактировании"""
    data = await state.get_data()
    ad_id = data.get('editing_ad_id')
    
    if not ad_id:
        await message.answer("❌ Ошибка: объявление не найдено.")
        await state.clear()
        return
    
    city = message.text.strip()
    
    if not city or len(city) > 100:
        await message.answer("❌ Название города должно быть от 1 до 100 символов.")
        return
    
    country = data.get('country')
    
    # НЕ обновляем объявление в БД! Сохраняем изменения только в state
    pending_changes = data.get('pending_changes', {})
    pending_changes['city'] = city
    if country:
        pending_changes['country'] = country
    else:
        pending_changes['country'] = None
    
    # Добавляем поле в список измененных
    edited_fields = data.get('edited_fields', [])
    if 'city' not in edited_fields:
        edited_fields.append('city')
    
    await state.update_data(edited_fields=edited_fields, pending_changes=pending_changes)
    
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
    
    # Возвращаемся в меню редактирования
    await return_to_edit_menu(message, state, ad_id)


async def my_ad_edit_country_custom_handler(message: types.Message, state: FSMContext):
    """Обработчик ввода собственной страны при редактировании"""
    data = await state.get_data()
    ad_id = data.get('editing_ad_id')
    
    if not ad_id:
        await message.answer("❌ Ошибка: объявление не найдено.")
        await state.clear()
        return
    
    country = message.text.strip()
    
    if not country or len(country) > 100:
        await message.answer("❌ Название страны должно быть от 1 до 100 символов.")
        return
    
    await state.update_data(country=country)
    await state.set_state(MyAdsState.edit_city_after_country)
    
    # Удаляем предыдущие сообщения
    last_msg_id = data.get('last_msg_with_keyboard')
    if last_msg_id:
        try:
            await bot.delete_message(chat_id=message.chat.id, message_id=last_msg_id)
        except:
            pass
    
    # Удаляем сообщение пользователя
    try:
        await message.delete()
    except:
        pass
    
    # Просим ввести город
    msg = await message.answer(
        CITY_CUSTOM_MESSAGE,
        reply_markup=back_kb()
    )
    await state.update_data(last_msg_with_keyboard=msg.message_id)


async def my_ad_edit_city_from_country_callback(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик выбора города из списка стран при редактировании"""
    await callback.answer()
    
    data = await state.get_data()
    ad_id = data.get('editing_ad_id')
    
    if not ad_id:
        await callback.answer("❌ Ошибка: объявление не найдено.", show_alert=True)
        await state.clear()
        return
    
    # Получаем данные из callback_data: city_from_country:country_key:city_index
    parts = callback.data.split(':')
    if len(parts) < 3:
        await callback.answer("❌ Ошибка выбора города.", show_alert=True)
        return
    
    country_key = parts[1]
    try:
        city_index = int(parts[2])
    except (ValueError, IndexError):
        await callback.answer("❌ Ошибка выбора города.", show_alert=True)
        return
    
    # Получаем название города по индексу
    if country_key not in CIS_COUNTRIES or 'cities' not in CIS_COUNTRIES[country_key]:
        await callback.answer("❌ Ошибка выбора города.", show_alert=True)
        return
    
    cities = CIS_COUNTRIES[country_key]['cities']
    if city_index < 0 or city_index >= len(cities):
        await callback.answer("❌ Ошибка выбора города.", show_alert=True)
        return
    
    city = cities[city_index]
    country = data.get('country', CIS_COUNTRIES.get(country_key, {}).get('name', ''))
    
    # НЕ обновляем объявление в БД! Сохраняем изменения только в state
    pending_changes = data.get('pending_changes', {})
    pending_changes['city'] = city
    pending_changes['country'] = country
    
    # Добавляем поле в список измененных
    edited_fields = data.get('edited_fields', [])
    if 'city' not in edited_fields:
        edited_fields.append('city')
    
    await state.update_data(edited_fields=edited_fields, pending_changes=pending_changes)
    
    # Возвращаемся в меню редактирования
    await return_to_edit_menu(callback.message, state, ad_id)


async def my_ad_edit_city_after_country_handler(message: types.Message, state: FSMContext):
    """Обработчик ввода города после выбора страны при редактировании (для ввода вручную, если нужно)"""
    data = await state.get_data()
    ad_id = data.get('editing_ad_id')
    country = data.get('country')
    
    if not ad_id:
        await message.answer("❌ Ошибка: объявление не найдено.")
        await state.clear()
        return
    
    city = message.text.strip()
    
    if not city or len(city) > 100:
        # Просто удаляем сообщение пользователя
        try:
            await message.delete()
        except:
            pass
        return
    
    # НЕ обновляем объявление в БД! Сохраняем изменения только в state
    pending_changes = data.get('pending_changes', {})
    pending_changes['city'] = city
    pending_changes['country'] = country
    
    # Добавляем поле в список измененных
    edited_fields = data.get('edited_fields', [])
    if 'city' not in edited_fields:
        edited_fields.append('city')
    
    await state.update_data(edited_fields=edited_fields, pending_changes=pending_changes)
    
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
    
    # Возвращаемся в меню редактирования
    await return_to_edit_menu(message, state, ad_id)


async def my_ad_edit_city_back_callback(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'Назад' при редактировании города"""
    await callback.answer()
    
    data = await state.get_data()
    ad_id = data.get('editing_ad_id')
    current_state = await state.get_state()
    
    if not ad_id:
        await callback.answer("❌ Ошибка: объявление не найдено.", show_alert=True)
        await state.clear()
        return
    
    # Если мы в состоянии выбора города после выбора страны - возвращаемся к списку городов страны
    if current_state == MyAdsState.edit_city_after_country:
        selected_country_key = data.get('selected_country_key')
        
        # Если есть выбранная страна, возвращаемся к списку городов этой страны
        if selected_country_key and selected_country_key in CIS_COUNTRIES:
            from src.bot.keyboards.keyboards import country_cities_kb
            try:
                await callback.message.edit_text(
                    "📍 Выберите город:",
                    reply_markup=country_cities_kb(selected_country_key)
                )
                await state.update_data(last_msg_with_keyboard=callback.message.message_id)
            except:
                msg = await callback.message.answer(
                    "📍 Выберите город:",
                    reply_markup=country_cities_kb(selected_country_key)
                )
                await state.update_data(last_msg_with_keyboard=msg.message_id)
            return
        else:
            # Возвращаемся к выбору страны
            await state.set_state(MyAdsState.edit_city_select)
            from src.bot.keyboards.keyboards import cities_kb
            try:
                await callback.message.edit_text(
                    LOCATION_MESSAGE,
                    reply_markup=cities_kb()
                )
                await state.update_data(last_msg_with_keyboard=callback.message.message_id)
            except:
                msg = await callback.message.answer(
                    LOCATION_MESSAGE,
                    reply_markup=cities_kb()
                )
                await state.update_data(last_msg_with_keyboard=msg.message_id)
            return
    
    # Возвращаемся к меню редактирования других параметров
    ad = await get_ad_by_id(ad_id)
    if not ad:
        await callback.answer("❌ Объявление не найдено.", show_alert=True)
        await state.clear()
        return
    
    await state.update_data(editing_ad_id=ad_id)
    await state.set_state(MyAdsState.edit_other)
    
    # Получаем список измененных полей
    data = await state.get_data()
    edited_fields = data.get('edited_fields', [])
    
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
    
    keyboard.row(InlineKeyboardButton(text=BACK_BTN, callback_data=f"my_ad_edit:{ad_id}"))
    
    await callback.message.answer(text, parse_mode='HTML', reply_markup=keyboard.as_markup())
    try:
        await callback.message.delete()
    except:
        pass


