"""
Обработчик каталога и карточек товаров
"""

from aiogram import Dispatcher, types, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest
from loguru import logger
from src.bot.logging_config import log_contact_request, log_ad_view
from math import ceil

from src.bot.database.states import ReviewState, SearchState
from src.bot.database.methods import (
    get_approved_ads, count_approved_ads, get_ad_by_id, get_ad_photos,
    get_user_by_id, get_user_by_tg_id, create_or_update_user, log_contact_request,
    log_details_view,
    get_user_reviews, count_user_reviews, get_user_average_rating, create_review,
    search_ads, get_user_ads, get_user_review_by_reviewer,
    count_ads_by_category, count_ads_by_subcategory, get_ads_by_category,
    count_ads_by_ad_type, get_ads_by_subcategories, count_ads_by_subcategories
)
from src.bot.keyboards.keyboards import *
from src.bot.keyboards.key_text import *
from src.bot.settings.constants import *
from src.bot.loader import bot
from src.bot.utils.helpers import format_phone_for_display
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

ITEMS_PER_PAGE = 20
CARDS_PER_PAGE = 5  # Количество карточек на странице
REVIEWS_PER_PAGE = 5


from ._common import *

async def catalog_filter_callback(callback: types.CallbackQuery, state: FSMContext):
    """Обработка фильтров каталога"""
    await callback.answer()
    
    parts = callback.data.split(':')
    filter_type = parts[1] if len(parts) > 1 else None
    filter_value = parts[2] if len(parts) > 2 else None
    
    logger.debug(f"catalog_filter_callback: filter_type={filter_type}, filter_value={filter_value}, callback_data={callback.data}")
    
    # Определяем текущий фильтр по типу объявления из state или текста сообщения
    data = await state.get_data()
    filter_ad_type = data.get('current_filter_ad_type')
    if not filter_ad_type and callback.message.text and "♻️ <b>Аренда</b>" in callback.message.text:
        filter_ad_type = "Аренда"
    
    if filter_type == 'city' and filter_value:
        # Применяем фильтр по городу
        # Сохраняем ID текущего сообщения для последующего удаления при вводе другого города
        await state.update_data(catalog_msg_id=callback.message.message_id)
        result = await show_catalog_page(callback.message, 0, edit=True, filter_city=filter_value, filter_ad_type=filter_ad_type, state=state)
        # Если это новое сообщение (не edit), сохраняем его ID
        if result:
            await state.update_data(catalog_msg_id=result.message_id)
    elif filter_type == 'country' and filter_value:
        # Применяем фильтр по стране
        # Сохраняем ID текущего сообщения для последующего удаления при вводе другой страны
        await state.update_data(catalog_msg_id=callback.message.message_id)
        result = await show_catalog_page(callback.message, 0, edit=True, filter_country=filter_value, filter_ad_type=filter_ad_type, state=state)
        # Если это новое сообщение (не edit), сохраняем его ID
        if result:
            await state.update_data(catalog_msg_id=result.message_id)
    elif filter_type == 'other_city':
        logger.info(f"Обработка 'Другой город': callback_data={callback.data}, message_id={callback.message.message_id}")
        # Запрашиваем ввод города
        await state.set_state(SearchState.custom_city_filter)
        # Сохраняем ID текущего сообщения с каталогом для последующего редактирования
        await state.update_data(catalog_msg_id=callback.message.message_id)
        # Определяем текущий фильтр по типу для кнопки "Назад"
        data = await state.get_data()
        filter_ad_type = data.get('current_filter_ad_type')
        selected_country_key = data.get('selected_country_key')
        logger.debug(f"Другой город: filter_ad_type={filter_ad_type}, selected_country_key={selected_country_key}")
        
        # Если была выбрана страна, возвращаем к выбору городов для этой страны
        if selected_country_key:
            back_callback = f"catalog_country:{selected_country_key}"
        else:
            back_callback = "catalog_rent" if filter_ad_type == "Аренда" else "catalog_all"
        
        # Редактируем текущее сообщение на запрос ввода города
        keyboard = InlineKeyboardBuilder().row(
            InlineKeyboardButton(text=BACK_BTN, callback_data=back_callback)
        ).as_markup()
        
        # Пытаемся отредактировать сообщение
        try:
            # Сначала пробуем edit_message_text
            await bot.edit_message_text(
                chat_id=callback.message.chat.id,
                message_id=callback.message.message_id,
                text="🌆 Введите название города:",
                parse_mode=None,
                reply_markup=keyboard
            )
            await state.update_data(city_input_msg_id=callback.message.message_id)
            return
        except TelegramBadRequest as e:
            error_msg = str(e).lower()
            if "message is not modified" in error_msg:
                await state.update_data(city_input_msg_id=callback.message.message_id)
                return
            # Если сообщение с медиа, пробуем edit_message_caption или edit_message_media
            try:
                # Пробуем удалить старое сообщение и отправить новое
                try:
                    await bot.delete_message(chat_id=callback.message.chat.id, message_id=callback.message.message_id)
                except:
                    pass
                msg = await callback.message.answer(
                    "🌆 Введите название города:",
                    reply_markup=keyboard
                )
                await state.update_data(city_input_msg_id=msg.message_id)
            except Exception as e2:
                logger.error(f"Ошибка при обработке 'Другой город': {e2}")
                msg = await callback.message.answer(
                    "🌆 Введите название города:",
                    reply_markup=keyboard
                )
                await state.update_data(city_input_msg_id=msg.message_id)
        except Exception as e:
            logger.error(f"Неожиданная ошибка при редактировании сообщения для ввода города: {e}")
            try:
                # Пробуем удалить старое сообщение и отправить новое
                try:
                    await bot.delete_message(chat_id=callback.message.chat.id, message_id=callback.message.message_id)
                except:
                    pass
                msg = await callback.message.answer(
                    "🌆 Введите название города:",
                    reply_markup=keyboard
                )
                await state.update_data(city_input_msg_id=msg.message_id)
            except Exception as e2:
                logger.error(f"Ошибка при отправке нового сообщения для ввода города: {e2}")
                msg = await callback.message.answer(
                    "🌆 Введите название города:",
                    reply_markup=keyboard
                )
                await state.update_data(city_input_msg_id=msg.message_id)
    elif filter_type == 'other_country':
        # Показываем список стран для выбора
        # Сохраняем ID текущего сообщения с каталогом для последующего редактирования
        await state.update_data(catalog_msg_id=callback.message.message_id)
        # Определяем текущий фильтр по типу для кнопки "Назад"
        data = await state.get_data()
        filter_ad_type = data.get('current_filter_ad_type')
        back_callback = "catalog_rent" if filter_ad_type == "Аренда" else "catalog_all"
        
        # Создаем клавиатуру со странами
        # Заменяем кнопку "Назад" на кнопку возврата в каталог
        # Создаем новую клавиатуру с кнопкой "Назад" для каталога
        from src.bot.settings.constants import CIS_COUNTRIES
        from src.bot.keyboards.key_text import OTHER_COUNTRY_BTN
        
        keyboard_builder = InlineKeyboardBuilder()
        
        # Преобразуем страны в список для удобства
        countries = [(country_key, country_data) for country_key, country_data in CIS_COUNTRIES.items()]
        
        # Добавляем страны по 2 в ряд
        for i in range(0, len(countries), 2):
            row_countries = countries[i:i+2]
            keyboard_builder.row(*[
                InlineKeyboardButton(
                    text=f"{country_data['flag']} {country_data['name']}", 
                    callback_data=f"catalog_country:{country_key}"
                ) for country_key, country_data in row_countries
            ])
        
        keyboard_builder.row(InlineKeyboardButton(text=OTHER_COUNTRY_BTN, callback_data="catalog_country:other"))
        keyboard_builder.row(InlineKeyboardButton(text=BACK_BTN, callback_data=back_callback))
        
        keyboard = keyboard_builder.as_markup()
        
        # Редактируем текущее сообщение на выбор страны
        try:
            await bot.edit_message_text(
                chat_id=callback.message.chat.id,
                message_id=callback.message.message_id,
                text="Выберите страну:",
                reply_markup=keyboard
            )
            return
        except TelegramBadRequest as e:
            # Если сообщение не изменилось или другая ошибка Telegram API
            error_msg = str(e).lower()
            if "message is not modified" in error_msg:
                # Сообщение уже такое же, просто сохраняем ID
                await state.update_data(country_input_msg_id=callback.message.message_id)
                return
            # Для других ошибок Telegram API логируем и отправляем новое сообщение
            logger.error(f"Ошибка Telegram API при редактировании сообщения для ввода страны: {e}")
            msg = await callback.message.answer(
                "🌍 Введите название страны:",
                reply_markup=keyboard
            )
            await state.update_data(country_input_msg_id=msg.message_id)
        except Exception as e:
            # Для других неожиданных ошибок логируем и отправляем новое сообщение
            logger.error(f"Неожиданная ошибка при редактировании сообщения для ввода страны: {e}")
            msg = await callback.message.answer(
                "🌍 Введите название страны:",
                reply_markup=keyboard
            )
            await state.update_data(country_input_msg_id=msg.message_id)
    elif filter_type == 'reset':
        # Сбрасываем фильтр
        # Определяем текущий фильтр по типу объявления из state или текста сообщения
        data = await state.get_data()
        filter_ad_type = data.get('current_filter_ad_type')
        if not filter_ad_type and callback.message.text and "♻️ <b>Аренда</b>" in callback.message.text:
            filter_ad_type = "Аренда"
        # Сохраняем ID текущего сообщения для последующего удаления
        await state.update_data(catalog_msg_id=callback.message.message_id)
        result = await show_catalog_page(callback.message, 0, edit=True, filter_ad_type=filter_ad_type, state=state)
        # Если это новое сообщение (не edit), сохраняем его ID
        if result:
            await state.update_data(catalog_msg_id=result.message_id)


async def catalog_custom_city_handler(message: types.Message, state: FSMContext):
    """Обработка ввода пользовательского города для фильтра"""
    city = message.text.strip()
    
    # Получаем ID сообщений
    data = await state.get_data()
    city_input_msg_id = data.get('city_input_msg_id')
    
    # Удаляем сообщение пользователя
    try:
        await message.delete()
    except:
        pass
    
    # Редактируем сообщение с запросом ввода города на каталог с фильтром
    # Используем city_input_msg_id, если оно есть, иначе используем catalog_msg_id
    msg_to_edit_id = city_input_msg_id if city_input_msg_id else data.get('catalog_msg_id')
    
    if msg_to_edit_id:
        try:
            # Создаем фиктивное сообщение для редактирования
            class FakeMessage:
                def __init__(self, chat_id, message_id):
                    self.chat = types.Chat(id=chat_id, type="private")
                    self.message_id = message_id
                    self.text = ""
                
                async def edit_text(self, text, parse_mode=None, reply_markup=None):
                    await bot.edit_message_text(
                        chat_id=self.chat.id,
                        message_id=self.message_id,
                        text=text,
                        parse_mode=parse_mode,
                        reply_markup=reply_markup
                    )
            
            fake_msg_obj = FakeMessage(message.chat.id, msg_to_edit_id)
            # Получаем текущий фильтр по типу из state
            filter_ad_type = data.get('current_filter_ad_type')
            # Получаем выбранную страну, если она была выбрана
            selected_country = data.get('selected_country')
            # Показываем каталог с фильтром, редактируя сообщение с запросом
            await show_catalog_page(fake_msg_obj, 0, edit=True, filter_city=city, filter_country=selected_country, filter_ad_type=filter_ad_type, state=state)
            # Сохраняем ID сообщения каталога в state
            await state.update_data(catalog_msg_id=msg_to_edit_id)
        except Exception as e:
            # Если не удалось отредактировать, удаляем старое и отправляем новое
            if city_input_msg_id:
                try:
                    await bot.delete_message(chat_id=message.chat.id, message_id=city_input_msg_id)
                except:
                    pass
            # Получаем текущий фильтр по типу из state
            filter_ad_type = data.get('current_filter_ad_type')
            # Получаем выбранную страну, если она была выбрана
            selected_country = data.get('selected_country')
            # Показываем каталог с фильтром
            sent_msg = await show_catalog_page(message, 0, filter_city=city, filter_country=selected_country, filter_ad_type=filter_ad_type, state=state)
            # Сохраняем ID нового сообщения каталога в state
            if sent_msg:
                await state.update_data(catalog_msg_id=sent_msg.message_id)
    else:
        # Получаем текущий фильтр по типу из state
        filter_ad_type = data.get('current_filter_ad_type')
        # Получаем выбранную страну, если она была выбрана
        selected_country = data.get('selected_country')
        # Если нет ID сообщения для редактирования, отправляем новое
        sent_msg = await show_catalog_page(message, 0, filter_city=city, filter_country=selected_country, filter_ad_type=filter_ad_type, state=state)
        # Сохраняем ID нового сообщения каталога в state
        if sent_msg:
            await state.update_data(catalog_msg_id=sent_msg.message_id)
    
    # Очищаем только фильтры ввода
    await state.update_data(
        city_input_msg_id=None,
        country_input_msg_id=None,
        selected_country=None,
        selected_country_key=None
    )


async def catalog_country_callback(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик выбора страны для фильтра каталога"""
    await callback.answer()
    
    country_key = callback.data.split(':')[1]
    
    # Определяем текущий фильтр по типу для кнопки "Назад"
    data = await state.get_data()
    filter_ad_type = data.get('current_filter_ad_type')
    back_callback = "catalog_rent" if filter_ad_type == "Аренда" else "catalog_all"
    
    if country_key == 'other':
        # Ввод собственной страны
        await state.set_state(SearchState.custom_country_filter)
        from src.bot.keyboards.keyboards import back_kb
        try:
            await callback.message.edit_text(
                "🌍 Введите название страны:",
                reply_markup=back_kb()
            )
            await state.update_data(country_input_msg_id=callback.message.message_id)
        except:
            msg = await callback.message.answer(
                "🌍 Введите название страны:",
                reply_markup=back_kb()
            )
            await state.update_data(country_input_msg_id=msg.message_id)
    else:
        # Предустановленная страна - показываем список городов или запрашиваем ввод
        from src.bot.settings.constants import CIS_COUNTRIES
        country = CIS_COUNTRIES[country_key]['name']
        await state.update_data(selected_country_key=country_key, selected_country=country)
        
        # Проверяем, есть ли список городов для этой страны
        if country_key in CIS_COUNTRIES and 'cities' in CIS_COUNTRIES[country_key] and CIS_COUNTRIES[country_key]['cities']:
            # Есть список городов - показываем его
            await state.set_state(SearchState.custom_city_filter)
            from src.bot.keyboards.keyboards import country_cities_kb
            from aiogram.utils.keyboard import InlineKeyboardBuilder
            from aiogram.types import InlineKeyboardButton
            from src.bot.keyboards.key_text import BACK_BTN
            
            # Создаем клавиатуру с городами
            cities = CIS_COUNTRIES[country_key]['cities']
            keyboard_builder = InlineKeyboardBuilder()
            
            # Добавляем города по 2 в ряд
            for i in range(0, len(cities), 2):
                row_cities = cities[i:i+2]
                keyboard_builder.row(*[
                    InlineKeyboardButton(
                        text=city,
                        callback_data=f"catalog_city_from_country:{country_key}:{i+j}"
                    ) for j, city in enumerate(row_cities)
                ])
            
            # Кнопка "Другой город" если есть список городов
            keyboard_builder.row(InlineKeyboardButton(text="🌆 Другой город", callback_data="catalog_filter:other_city"))
            keyboard_builder.row(InlineKeyboardButton(text=BACK_BTN, callback_data="catalog_filter:other_country"))
            
            keyboard = keyboard_builder.as_markup()
            
            try:
                await callback.message.edit_text(
                    "📍 Выберите город:",
                    reply_markup=keyboard
                )
                await state.update_data(city_input_msg_id=callback.message.message_id)
            except:
                msg = await callback.message.answer(
                    "📍 Выберите город:",
                    reply_markup=keyboard
                )
                await state.update_data(city_input_msg_id=msg.message_id)
        else:
            # Нет списка городов - запрашиваем ввод города
            await state.set_state(SearchState.custom_city_filter)
            from src.bot.keyboards.keyboards import back_kb
            try:
                await callback.message.edit_text(
                    "📍 Введите название города:",
                    reply_markup=back_kb()
                )
                await state.update_data(city_input_msg_id=callback.message.message_id)
            except:
                msg = await callback.message.answer(
                    "📍 Введите название города:",
                    reply_markup=back_kb()
                )
                await state.update_data(city_input_msg_id=msg.message_id)


async def catalog_city_from_country_callback(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик выбора города из списка стран для фильтра каталога"""
    await callback.answer()
    
    # Получаем данные из callback_data: catalog_city_from_country:country_key:city_index
    parts = callback.data.split(':')
    if len(parts) < 3:
        await callback.answer("❌ Ошибка: неверный формат данных.", show_alert=True)
        return
    
    country_key = parts[1]
    city_index = int(parts[2])
    
    from src.bot.settings.constants import CIS_COUNTRIES
    if country_key not in CIS_COUNTRIES or 'cities' not in CIS_COUNTRIES[country_key]:
        await callback.answer("❌ Ошибка: страна не найдена.", show_alert=True)
        return
    
    cities = CIS_COUNTRIES[country_key]['cities']
    if city_index < 0 or city_index >= len(cities):
        await callback.answer("❌ Ошибка: город не найден.", show_alert=True)
        return
    
    city = cities[city_index]
    country = CIS_COUNTRIES[country_key]['name']
    
    # Определяем текущий фильтр по типу
    data = await state.get_data()
    filter_ad_type = data.get('current_filter_ad_type')
    
    # Сохраняем selected_country_key для возможности вернуться к выбору городов
    await state.update_data(selected_country_key=country_key, selected_country=country)
    
    # Применяем фильтр по стране и городу
    await state.update_data(catalog_msg_id=callback.message.message_id)
    result = await show_catalog_page(callback.message, 0, edit=True, filter_country=country, filter_city=city, filter_ad_type=filter_ad_type, state=state)
    if result:
        await state.update_data(catalog_msg_id=result.message_id)


async def catalog_custom_country_handler(message: types.Message, state: FSMContext):
    """Обработка ввода пользовательской страны для фильтра"""
    country = message.text.strip()
    
    # Получаем ID сообщений
    data = await state.get_data()
    country_input_msg_id = data.get('country_input_msg_id')
    
    # Удаляем сообщение пользователя
    try:
        await message.delete()
    except:
        pass
    
    # Редактируем сообщение с запросом ввода страны на каталог с фильтром
    # Используем country_input_msg_id, если оно есть, иначе используем catalog_msg_id
    msg_to_edit_id = country_input_msg_id if country_input_msg_id else data.get('catalog_msg_id')
    
    if msg_to_edit_id:
        try:
            # Создаем фиктивное сообщение для редактирования
            class FakeMessage:
                def __init__(self, chat_id, message_id):
                    self.chat = types.Chat(id=chat_id, type="private")
                    self.message_id = message_id
                    self.text = ""
                
                async def edit_text(self, text, parse_mode=None, reply_markup=None):
                    await bot.edit_message_text(
                        chat_id=self.chat.id,
                        message_id=self.message_id,
                        text=text,
                        parse_mode=parse_mode,
                        reply_markup=reply_markup
                    )
            
            fake_msg_obj = FakeMessage(message.chat.id, msg_to_edit_id)
            # Получаем текущий фильтр по типу из state
            filter_ad_type = data.get('current_filter_ad_type')
            # Показываем каталог с фильтром, редактируя сообщение с запросом
            await show_catalog_page(fake_msg_obj, 0, edit=True, filter_country=country, filter_ad_type=filter_ad_type, state=state)
            # Сохраняем ID сообщения каталога в state
            await state.update_data(catalog_msg_id=msg_to_edit_id)
        except Exception as e:
            # Если не удалось отредактировать, удаляем старое и отправляем новое
            if country_input_msg_id:
                try:
                    await bot.delete_message(chat_id=message.chat.id, message_id=country_input_msg_id)
                except:
                    pass
            # Получаем текущий фильтр по типу из state
            filter_ad_type = data.get('current_filter_ad_type')
            # Показываем каталог с фильтром
            sent_msg = await show_catalog_page(message, 0, filter_country=country, filter_ad_type=filter_ad_type, state=state)
            # Сохраняем ID нового сообщения каталога в state
            if sent_msg:
                await state.update_data(catalog_msg_id=sent_msg.message_id)
    else:
        # Получаем текущий фильтр по типу из state
        filter_ad_type = data.get('current_filter_ad_type')
        # Если нет ID сообщения для редактирования, отправляем новое
        sent_msg = await show_catalog_page(message, 0, filter_country=country, filter_ad_type=filter_ad_type, state=state)
        # Сохраняем ID нового сообщения каталога в state
        if sent_msg:
            await state.update_data(catalog_msg_id=sent_msg.message_id)
    
    # Очищаем только фильтры ввода
    await state.update_data(
        city_input_msg_id=None,
        country_input_msg_id=None,
        selected_country=None,
        selected_country_key=None
    )


