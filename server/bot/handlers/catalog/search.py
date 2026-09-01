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

async def search_back_to_main_menu_from_input_callback(callback: types.CallbackQuery, state: FSMContext):
    """Возврат в главное меню из запроса поиска"""
    await callback.answer()
    await state.clear()

    # Редактируем сообщение на главное меню
    from src.bot.handlers.start import get_main_menu_text
    from src.bot.keyboards.keyboards import main_menu_kb
    menu_text = await get_main_menu_text()
    user_id = callback.from_user.id if callback.from_user else None

    try:
        await callback.message.edit_text(
            text=menu_text,
            parse_mode='HTML',
            reply_markup=await main_menu_kb(user_id)
        )
        await state.update_data(main_menu_msg_id=callback.message.message_id)
    except Exception as e:
        logger.debug(f"Не удалось отредактировать сообщение поиска на главное меню: {e}")
        from src.bot.handlers.start import send_main_menu
        await send_main_menu(callback, state=state)
        try:
            await callback.message.delete()
        except Exception:
            pass


async def search_start_handler(callback: types.CallbackQuery, state: FSMContext):
    """Начать поиск"""
    await callback.answer()
    
    await state.set_state(SearchState.query)
    
    # Редактируем сообщение главного меню на сообщение с просьбой ввести запрос
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text=BACK_BTN, callback_data="search_back_to_main_menu"))
    try:
        await callback.message.edit_text(SEARCH_MESSAGE, reply_markup=keyboard.as_markup())
        await state.update_data(search_request_msg_id=callback.message.message_id)
    except:
        # Если не удалось отредактировать, отправляем новое
        msg = await callback.message.answer(SEARCH_MESSAGE, reply_markup=keyboard.as_markup())
        await state.update_data(search_request_msg_id=msg.message_id)


async def search_query_handler(message: types.Message, state: FSMContext):
    """Обработка поискового запроса"""
    query = message.text.strip()
    
    # Получаем ID сообщения с просьбой ввести запрос
    data = await state.get_data()
    search_request_msg_id = data.get('search_request_msg_id')
    
    # Удаляем сообщение пользователя с запросом
    try:
        await message.delete()
    except:
        pass
    
    if len(query) < 2:
        # Если запрос слишком короткий, редактируем сообщение с запросом
        if search_request_msg_id:
            try:
                await bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=search_request_msg_id,
                    text="❌ Запрос должен содержать минимум 2 символа.",
                    reply_markup=InlineKeyboardBuilder().row(
                        InlineKeyboardButton(text=BACK_BTN, callback_data="search_back_to_main_menu")
                    ).as_markup()
                )
                return
            except:
                # Если не удалось отредактировать, отправляем новое
                await message.answer("❌ Запрос должен содержать минимум 2 символа.")
                return
        else:
            await message.answer("❌ Запрос должен содержать минимум 2 символа.")
            return
    
    # Выполняем поиск с обработкой ошибок
    try:
        results = await search_ads(query)
        logger.info(f"Поиск по запросу '{query}': найдено результатов: {len(results) if results else 0}")
    except Exception as e:
        logger.error(f"Ошибка при поиске объявлений по запросу '{query}': {e}", exc_info=True)
        # При любой ошибке показываем сообщение "не найдено"
        results = []
    
    if not results or len(results) == 0:
        # Формируем сообщение с запросом пользователя
        no_results_text = f'❌ По вашему запросу "{query}" ничего не найдено.'
        
        # Создаем клавиатуру с кнопкой "Назад в главное меню"
        from src.bot.keyboards.keyboards import InlineKeyboardBuilder, InlineKeyboardButton
        from src.bot.keyboards.key_text import BACK_BTN
        keyboard = InlineKeyboardBuilder()
        keyboard.row(InlineKeyboardButton(text=BACK_BTN, callback_data="search_back_to_menu"))
        
        logger.info(f"Отправка сообщения об отсутствии результатов с кнопкой 'Назад'")
        # Всегда пытаемся отредактировать существующее сообщение
        if search_request_msg_id:
            try:
                await bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=search_request_msg_id,
                    text=no_results_text,
                    reply_markup=keyboard.as_markup()
                )
                logger.info(f"Сообщение об отсутствии результатов отредактировано успешно")
                # НЕ очищаем state, чтобы пользователь мог сразу ввести новый запрос
                # Устанавливаем состояние поиска заново
                from src.bot.database.states import SearchState
                await state.set_state(SearchState.query)
                # Сохраняем ID сообщения для последующего редактирования
                await state.update_data(search_request_msg_id=search_request_msg_id)
                return
            except Exception as e:
                logger.error(f"Ошибка при редактировании сообщения об отсутствии результатов: {e}")
                # Если не удалось отредактировать (например, сообщение было удалено), отправляем новое
                try:
                    msg = await message.answer(no_results_text, reply_markup=keyboard.as_markup())
                    logger.info(f"Сообщение об отсутствии результатов отправлено успешно, message_id: {msg.message_id}")
                    # Сохраняем ID нового сообщения
                    search_request_msg_id = msg.message_id
                except Exception as e2:
                    logger.error(f"Ошибка при отправке сообщения об отсутствии результатов поиска: {e2}", exc_info=True)
                    await message.answer(no_results_text)
        else:
            # Если нет ID сообщения для редактирования, отправляем новое
            try:
                msg = await message.answer(no_results_text, reply_markup=keyboard.as_markup())
                logger.info(f"Сообщение об отсутствии результатов отправлено успешно, message_id: {msg.message_id}")
                # Сохраняем ID нового сообщения
                search_request_msg_id = msg.message_id
            except Exception as e:
                logger.error(f"Ошибка при отправке сообщения об отсутствии результатов поиска: {e}", exc_info=True)
                await message.answer(no_results_text)
        
        # НЕ очищаем state, чтобы пользователь мог сразу ввести новый запрос
        # Устанавливаем состояние поиска заново
        from src.bot.database.states import SearchState
        await state.set_state(SearchState.query)
        # Сохраняем ID сообщения для последующего редактирования
        await state.update_data(search_request_msg_id=search_request_msg_id)
        return
    
    # Получаем username бота для deep links
    from src.bot.settings.settings import BOT_USERNAME
    bot_username = BOT_USERNAME or "baraholka_tg_av_bot"
    
    # Определяем флаг страны
    def get_country_flag(country_name):
        """Получить флаг страны по названию"""
        if not country_name:
            return "🇷🇺"  # По умолчанию Россия
        
        country_lower = country_name.lower().strip()
        
        # Варианты названий России
        russia_variants = ['россия', 'российская федерация', 'рф', 'russia', 'russian federation']
        if country_lower in russia_variants:
            return "🇷🇺"
        
        # Проверяем страны из CIS_COUNTRIES
        from src.bot.settings.constants import CIS_COUNTRIES
        for key, data in CIS_COUNTRIES.items():
            if data['name'].lower() == country_lower:
                return data['flag']
        
        return "🇷🇺"  # По умолчанию
    
    text = f"🔍 <b>Результаты поиска:</b> \"{query}\"\n\n"
    
    for ad in results:
        # Определяем флаг страны
        country_flag = get_country_flag(ad.country)
        
        # Формируем размер/описание
        size_info = ""
        if ad.size:
            size_info = f" ({ad.size})"
        
        # Формируем цену
        price_text = f"{ad.price}₽" if ad.price else "Цена не указана"
        
        # Формируем город
        city_text = f"{ad.city}"
        
        # Создаем deep link для товара
        deep_link_url = f"https://t.me/{bot_username}?start=item_{ad.id}"
        
        # Добавляем товар в список со ссылкой
        text += f"{country_flag} <a href=\"{deep_link_url}\">{ad.title}</a>{size_info} {price_text} {city_text}\n"
    
    # Создаем клавиатуру с кнопкой "Назад"
    from src.bot.keyboards.keyboards import InlineKeyboardBuilder, InlineKeyboardButton
    from src.bot.keyboards.key_text import BACK_BTN
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text=BACK_BTN, callback_data="search_back_to_menu"))
    
    # Пытаемся отредактировать сообщение с запросом на результаты поиска
    if search_request_msg_id:
        try:
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=search_request_msg_id,
                text=text,
                parse_mode='HTML',
                reply_markup=keyboard.as_markup()
            )
            # НЕ очищаем state, чтобы пользователь мог сразу ввести новый запрос
            # Устанавливаем состояние поиска заново
            from src.bot.database.states import SearchState
            await state.set_state(SearchState.query)
            # Сохраняем ID сообщения для последующего редактирования
            await state.update_data(search_request_msg_id=search_request_msg_id, search_results_msg_id=search_request_msg_id)
            return
        except Exception as e:
            logger.error(f"Ошибка при редактировании сообщения с результатами поиска: {e}")
            # Если не удалось отредактировать, отправляем новое сообщение
            msg = await message.answer(text, parse_mode='HTML', reply_markup=keyboard.as_markup())
            # НЕ очищаем state, чтобы пользователь мог сразу ввести новый запрос
            from src.bot.database.states import SearchState
            await state.set_state(SearchState.query)
            await state.update_data(search_request_msg_id=msg.message_id, search_results_msg_id=msg.message_id)
            return
    
    # Если нет ID сообщения для редактирования, отправляем новое
    msg = await message.answer(text, parse_mode='HTML', reply_markup=keyboard.as_markup())
    # НЕ очищаем state, чтобы пользователь мог сразу ввести новый запрос
    from src.bot.database.states import SearchState
    await state.set_state(SearchState.query)
    # Сохраняем ID сообщения для последующего редактирования
    await state.update_data(search_request_msg_id=msg.message_id, search_results_msg_id=msg.message_id)


