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
from .details import show_ad_details
from .seller import show_seller_profile

async def catalog_back_callback(callback: types.CallbackQuery, state: FSMContext):
    """Универсальный обработчик кнопки 'Назад' для каталога и профилей"""
    await callback.answer()
    
    # Получаем данные из состояния
    data = await state.get_data()
    ad_id = data.get('last_viewed_ad_id')
    seller_id = data.get('last_viewed_seller_id')
    ad_details_msg_id = data.get('ad_details_msg_id')
    came_from_profile = data.get('came_from_profile', False)
    current_state = await state.get_state()
    
    # Если мы в процессе создания отзыва, не обрабатываем здесь
    from src.bot.database.states import ReviewState, SearchState
    if current_state and current_state in [ReviewState.comment, ReviewState.rating]:
        return  # Пусть обрабатывает review_back_callback
    
    # Если мы в состоянии ввода страны - возвращаемся к выбору стран
    if current_state == SearchState.custom_country_filter:
        # Определяем текущий фильтр по типу для кнопки "Назад"
        filter_ad_type = data.get('current_filter_ad_type')
        back_callback = "catalog_rent" if filter_ad_type == "Аренда" else "catalog_all"
        
        # Создаем клавиатуру со странами
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        from aiogram.types import InlineKeyboardButton
        from src.bot.settings.constants import CIS_COUNTRIES
        from src.bot.keyboards.key_text import OTHER_COUNTRY_BTN, BACK_BTN
        
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
            await callback.message.edit_text(
                "Выберите страну:",
                reply_markup=keyboard
            )
        except:
            await callback.message.answer(
                "Выберите страну:",
                reply_markup=keyboard
            )
        return
    
    # Если мы в состоянии ввода города - возвращаемся к выбору городов или стран
    if current_state == SearchState.custom_city_filter:
        selected_country_key = data.get('selected_country_key')
        
        if selected_country_key:
            # Возвращаемся к выбору городов для выбранной страны
            from src.bot.settings.constants import CIS_COUNTRIES
            from aiogram.utils.keyboard import InlineKeyboardBuilder
            from aiogram.types import InlineKeyboardButton
            from src.bot.keyboards.key_text import BACK_BTN
            
            # Проверяем, есть ли список городов для этой страны
            if selected_country_key in CIS_COUNTRIES and 'cities' in CIS_COUNTRIES[selected_country_key] and CIS_COUNTRIES[selected_country_key]['cities']:
                # Есть список городов - показываем его
                cities = CIS_COUNTRIES[selected_country_key]['cities']
                keyboard_builder = InlineKeyboardBuilder()
                
                # Добавляем города по 2 в ряд
                for i in range(0, len(cities), 2):
                    row_cities = cities[i:i+2]
                    keyboard_builder.row(*[
                        InlineKeyboardButton(
                            text=city,
                            callback_data=f"catalog_city_from_country:{selected_country_key}:{i+j}"
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
                except:
                    await callback.message.answer(
                        "📍 Выберите город:",
                        reply_markup=keyboard
                    )
            else:
                # Нет списка городов - возвращаемся к выбору стран
                filter_ad_type = data.get('current_filter_ad_type')
                back_callback = "catalog_rent" if filter_ad_type == "Аренда" else "catalog_all"
                
                from src.bot.keyboards.key_text import OTHER_COUNTRY_BTN
                keyboard_builder = InlineKeyboardBuilder()
                
                countries = [(country_key, country_data) for country_key, country_data in CIS_COUNTRIES.items()]
                
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
                
                try:
                    await callback.message.edit_text(
                        "Выберите страну:",
                        reply_markup=keyboard
                    )
                except:
                    await callback.message.answer(
                        "Выберите страну:",
                        reply_markup=keyboard
                    )
        else:
            # Нет выбранной страны - возвращаемся к выбору стран
            filter_ad_type = data.get('current_filter_ad_type')
            back_callback = "catalog_rent" if filter_ad_type == "Аренда" else "catalog_all"
            
            from src.bot.settings.constants import CIS_COUNTRIES
            from src.bot.keyboards.key_text import OTHER_COUNTRY_BTN
            keyboard_builder = InlineKeyboardBuilder()
            
            countries = [(country_key, country_data) for country_key, country_data in CIS_COUNTRIES.items()]
            
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
            
            try:
                await callback.message.edit_text(
                    "Выберите страну:",
                    reply_markup=keyboard
                )
            except:
                await callback.message.answer(
                    "Выберите страну:",
                    reply_markup=keyboard
                )
        return
    
    # Проверяем, находимся ли мы непосредственно в деталях объявления
    # (т.е. текущее сообщение - это сообщение с деталями объявления)
    is_in_ad_details = (
        ad_details_msg_id and 
        callback.message.message_id == ad_details_msg_id
    )
    
    # Если пришли из страницы оценки (deep link) - удаляем сообщение
    rate_seller_msg_id = data.get('rate_seller_msg_id')
    came_from_deep_link = data.get('came_from_deep_link', False)
    
    # Если пришли из страницы оценки (deep link) - просто удаляем сообщение
    if callback.data == "back_from_rate" or (rate_seller_msg_id and callback.message.message_id == rate_seller_msg_id) or came_from_deep_link:
        try:
            await callback.message.delete()
        except:
            pass
        await state.clear()
        # НЕ возвращаемся в главное меню, просто удаляем сообщение
        return
    
    # Сначала проверяем: мы в деталях объявления (кнопка «Назад» под карточкой)
    # Тогда только удаляем сообщения, профиль не показываем
    if is_in_ad_details:
        # Получаем ID первого фото и количество фото
        first_photo_msg_id = data.get('first_photo_msg_id')
        photos_count = data.get('photos_count', 0)
        current_msg_id = callback.message.message_id
        came_from_seller_profile = data.get('came_from_seller_profile', False)
        came_from_catalog = data.get('came_from_catalog', False)
        came_from_channel = data.get('came_from_channel', False)
        channel_message_id = data.get('channel_message_id')
        channel_username = data.get('channel_username') or ''

        # Удаляем сообщение с деталями и фото
        try:
            await callback.message.delete()
        except Exception:
            pass
        if first_photo_msg_id and photos_count > 0:
            try:
                for i in range(photos_count):
                    try:
                        await bot.delete_message(chat_id=callback.message.chat.id, message_id=first_photo_msg_id + i)
                    except Exception:
                        pass
            except Exception:
                pass

        nav_stack = list(data.get('nav_stack', []))

        if came_from_seller_profile:
            if nav_stack:
                prev = nav_stack.pop()
                await state.update_data(
                    nav_stack=nav_stack,
                    ad_details_msg_id=prev.get('ad_details_msg_id'),
                    first_photo_msg_id=prev.get('first_photo_msg_id'),
                    photos_count=prev.get('photos_count', 0),
                    last_viewed_ad_id=prev.get('last_viewed_ad_id'),
                    came_from_catalog=prev.get('came_from_catalog', False),
                    came_from_channel=prev.get('came_from_channel', False),
                    channel_message_id=prev.get('channel_message_id'),
                    channel_username=prev.get('channel_username'),
                    came_from_seller_profile=False,
                )
            else:
                await state.update_data(
                    ad_details_msg_id=None,
                    first_photo_msg_id=None,
                    photos_count=0,
                    came_from_seller_profile=False,
                )
            return
        elif came_from_catalog:
            await state.update_data(
                ad_details_msg_id=None,
                first_photo_msg_id=None,
                photos_count=0,
                came_from_catalog=False,
            )
            return
        elif came_from_channel:
            await state.clear()
            from src.bot.handlers.start import send_main_menu
            await send_main_menu(callback, state=state)
        else:
            await state.update_data(
                ad_details_msg_id=None,
                first_photo_msg_id=None,
                photos_count=0,
            )
    elif (came_from_profile or data.get('came_from_seller_ads', False)) and seller_id:
        # Если пришли из товаров продавца или из профиля (отзывы и т.д.) — возвращаемся к профилю
        current_msg_id = callback.message.message_id
        await state.update_data(came_from_profile=False, came_from_seller_ads=False)
        await show_seller_profile(callback.message, seller_id, ad_id, from_user=callback.from_user, state=state)
        try:
            await callback.message.delete()
        except:
            pass
    # Если текущее сообщение — профиль продавца (кнопка «Назад» в профиле)
    elif callback.message.text and "ПРОФИЛЬ ПРОДАВЦА" in callback.message.text:
        try:
            await callback.message.delete()
        except Exception:
            pass
        # Не очищаем state полностью: сохраняем came_from_catalog и данные объявления,
        # чтобы при следующем «Назад» (на карточке объявления) закрыть только объявление, а не открывать главное меню
        await state.update_data(last_viewed_seller_id=None, seller_profile_msg_id=None, seller_profile_chat_id=None)
        return
    # Если есть ad_id и мы НЕ в деталях объявления - возвращаемся к деталям объявления
    elif ad_id:
        # Сохраняем ID сообщения для последующего удаления
        current_msg_id = callback.message.message_id
        
        # Если сообщение "Выберите действие:" существует, просто восстанавливаем кнопки
        if ad_details_msg_id:
            try:
                # Получаем объявление для создания клавиатуры
                ad = await get_ad_by_id(ad_id)
                if ad:
                    photo_id = data.get('first_photo_msg_id') or 0
                    photo_cnt = data.get('photos_count', 0)
                    await bot.edit_message_reply_markup(
                        chat_id=callback.message.chat.id,
                        message_id=ad_details_msg_id,
                        reply_markup=ad_details_kb(ad_id, ad.seller_user_id, photo_id, photo_cnt)
                    )
            except Exception as e:
                logger.warning(f"Не удалось восстановить кнопки в сообщении {ad_details_msg_id}: {e}")
                # Если не удалось восстановить, показываем детали объявления заново
                await show_ad_details(callback.message, ad_id, state, from_user=callback.from_user)
        else:
            # Если сообщения нет, показываем детали объявления заново
            await show_ad_details(callback.message, ad_id, state, from_user=callback.from_user)
        
        # Потом удаляем текущее сообщение (отзывы, контакт продавца и т.д.)
        try:
            await callback.message.delete()
        except:
            pass
    # Если есть seller_id, но нет ad_id - просто удаляем сообщение профиля
    elif seller_id:
        # Удаляем сообщение профиля продавца
        try:
            await callback.message.delete()
        except:
            pass
        
        # Очищаем состояние
        await state.clear()
        # НЕ открываем главное меню, просто удаляем сообщение
        return
    # Проверяем, находимся ли мы в группе велоспорта
    elif data.get('current_bike_group'):
        # Возвращаемся к группе велоспорта
        group_key = data.get('current_bike_group')
        from src.bot.settings.constants import BIKE_SUBCATEGORY_GROUPS
        group_data = BIKE_SUBCATEGORY_GROUPS.get(group_key)
        
        if group_data:
            # Подсчитываем товары по подкатегориям в группе
            subcats_data = {}
            for subcat_key in group_data["subcategories"].keys():
                count = await count_ads_by_subcategory("bike", subcat_key)
                subcat_name = group_data["subcategories"][subcat_key]
                subcats_data[subcat_key] = (subcat_name, count)
            
            # Показываем подкатегории группы
            cat_name = CATEGORIES.get("bike", "ВЕЛОСПОРТ")
            text = f"📂 Категория: {cat_name}\n📁 Группа: {group_data['name']}"
            
            from src.bot.keyboards.keyboards import catalog_bike_group_subcategories_kb
            keyboard = catalog_bike_group_subcategories_kb(group_key, subcats_data)
            
            # Удаляем карточки, разделитель и навигационное сообщение
            prev_card_ids = data.get('category_cards_message_ids', [])
            prev_nav_id = data.get('category_nav_message_id')
            prev_sep_id = data.get('category_separator_message_id')
            for card_id in prev_card_ids:
                try:
                    await bot.delete_message(chat_id=callback.message.chat.id, message_id=card_id)
                except:
                    pass
            if prev_nav_id:
                try:
                    await bot.delete_message(chat_id=callback.message.chat.id, message_id=prev_nav_id)
                except:
                    pass
            if prev_sep_id:
                try:
                    await bot.delete_message(chat_id=callback.message.chat.id, message_id=prev_sep_id)
                except:
                    pass
            await state.update_data(
                category_cards_message_ids=[],
                category_nav_message_id=None,
                category_separator_message_id=None,
                category_subcategories=None
            )
            
            try:
                await callback.message.edit_text(text, reply_markup=keyboard)
            except:
                await callback.message.answer(text, reply_markup=keyboard)
            return
    
    # Иначе возвращаемся в каталог
    else:
        # Сначала показываем каталог
        sent_msg = await show_catalog_page(callback.message, 0, edit=False, state=state)
        
        # Сохраняем ID сообщения каталога в state
        if sent_msg:
            await state.update_data(catalog_msg_id=sent_msg.message_id)
        
        # Потом удаляем предыдущие сообщения
        try:
            await callback.message.delete()
        except:
            pass


async def main_menu_callback(callback: types.CallbackQuery, state: FSMContext):
    """Вернуться в главное меню"""
    await callback.answer()
    
    # Получаем данные из состояния перед очисткой
    data = await state.get_data()
    ad_details_msg_id = data.get('ad_details_msg_id')
    category_msg_id = data.get('category_msg_id')
    catalog_msg_id = data.get('catalog_msg_id')
    city_input_msg_id = data.get('city_input_msg_id')
    country_input_msg_id = data.get('country_input_msg_id')
    empty_category_msg_id = data.get('empty_category_msg_id')
    empty_catalog_msg_id = data.get('empty_catalog_msg_id')
    current_msg_id = callback.message.message_id
    
    # Проверяем, является ли текущее сообщение сообщением каталога или категорий
    # Если да, пытаемся отредактировать его на главное меню
    is_catalog_or_category_msg = False
    is_categories_msg = False
    if callback.message.text:
        if "📂 Выберите категорию товаров:" in callback.message.text:
            is_categories_msg = True
            is_catalog_or_category_msg = True
        else:
            catalog_texts = [
                "📭 В каталоге пока нет объявлений",
                "В этой категории пока нет товаров",
                "📂 Категория:",
                "📦 <b>Все товары</b>",
                "📦 Все товары",
                "🏠 <b>Аренда</b>"
            ]
            is_catalog_or_category_msg = any(text in callback.message.text for text in catalog_texts)
    
    # Если это сообщение каталога/категорий или сообщение с пустой категорией/каталогом,
    # редактируем его на главное меню
    if is_catalog_or_category_msg or empty_category_msg_id == current_msg_id or empty_catalog_msg_id == current_msg_id:
        from src.bot.handlers.start import get_main_menu_text
        from src.bot.keyboards.keyboards import main_menu_kb
        menu_text = await get_main_menu_text()
        try:
            await callback.message.edit_text(
                text=menu_text,
                parse_mode='HTML',
                disable_web_page_preview=True,
                reply_markup=await main_menu_kb(callback.from_user.id if hasattr(callback, 'from_user') else None)
            )
            # Сохраняем ID сообщения главного меню
            await state.update_data(main_menu_msg_id=current_msg_id)
            
            # НЕ удаляем предыдущие сообщения, так как это может удалить важные сообщения
            # await delete_previous_messages(callback.message.chat.id, current_msg_id, 20)
            
            # Очищаем только данные каталога, но сохраняем main_menu_msg_id
            await state.update_data(
                category_msg_id=None,
                catalog_msg_id=None,
                city_input_msg_id=None,
                country_input_msg_id=None,
                empty_category_msg_id=None,
                empty_catalog_msg_id=None
            )
            await state.clear()
            await state.update_data(main_menu_msg_id=current_msg_id)
            return
        except Exception as e:
            # Если не удалось отредактировать, отправляем новое сообщение
            from src.bot.handlers.start import send_main_menu
            await send_main_menu(callback, state=state)
            
            # Получаем ID нового сообщения главного меню
            data_after = await state.get_data()
            new_main_menu_msg_id = data_after.get('main_menu_msg_id')
            
            # Удаляем текущее сообщение каталога/категорий (если это не то же самое, что новое главное меню)
            if current_msg_id != new_main_menu_msg_id:
                try:
                    await bot.delete_message(chat_id=callback.message.chat.id, message_id=current_msg_id)
                except:
                    pass
            
            # НЕ удаляем предыдущие сообщения, так как это может удалить важные сообщения
            # if new_main_menu_msg_id:
            #     await delete_previous_messages(callback.message.chat.id, new_main_menu_msg_id, 20)
            
            # Очищаем только данные каталога, но сохраняем main_menu_msg_id
            await state.update_data(
                category_msg_id=None,
                catalog_msg_id=None,
                city_input_msg_id=None,
                country_input_msg_id=None,
                empty_category_msg_id=None,
                empty_catalog_msg_id=None
            )
            await state.clear()
            if new_main_menu_msg_id:
                await state.update_data(main_menu_msg_id=new_main_menu_msg_id)
            return
    
    # Обычная логика: показываем главное меню и удаляем сообщения
    from src.bot.handlers.start import send_main_menu
    await send_main_menu(callback, state=state)
    
    # Потом удаляем сообщения
    # Удаляем сообщение "Выберите действие или закройте окно:" из деталей объявления
    if ad_details_msg_id:
        try:
            await bot.delete_message(chat_id=callback.message.chat.id, message_id=ad_details_msg_id)
        except:
            pass
    
    # Удаляем сообщение категории, если есть
    if category_msg_id:
        try:
            await bot.delete_message(chat_id=callback.message.chat.id, message_id=category_msg_id)
        except:
            pass
    
    # Удаляем сообщение каталога, если оно сохранено в state (но не текущее сообщение, которое мы только что отредактировали)
    if catalog_msg_id and catalog_msg_id != current_msg_id:
        try:
            await bot.delete_message(chat_id=callback.message.chat.id, message_id=catalog_msg_id)
        except:
            pass
    
    # Удаляем сообщение с запросом ввода города, если есть
    if city_input_msg_id:
        try:
            await bot.delete_message(chat_id=callback.message.chat.id, message_id=city_input_msg_id)
        except:
            pass
    
    # Удаляем сообщение с запросом ввода страны, если есть
    if country_input_msg_id:
        try:
            await bot.delete_message(chat_id=callback.message.chat.id, message_id=country_input_msg_id)
        except:
            pass
    
    # Удаляем текущее сообщение (каталог, детали объявления и т.д.), если это не сообщение каталога
    # НО НЕ удаляем, если это сообщение каталога, которое мы могли отредактировать
    if not is_catalog_or_category_msg and empty_category_msg_id != current_msg_id and empty_catalog_msg_id != current_msg_id:
        # Проверяем, не является ли текущее сообщение сообщением каталога (по тексту)
        is_current_catalog = False
        if callback.message.text:
            catalog_texts = [
                "📭 В каталоге пока нет объявлений",
                "В этой категории пока нет товаров",
                "📂 Категория:",
                "📦 <b>Все товары</b>",
                "📦 Все товары",
                "🏠 <b>Аренда</b>"
            ]
            is_current_catalog = any(text in callback.message.text for text in catalog_texts)
        
        if not is_current_catalog:
            try:
                await callback.message.delete()
            except:
                pass
    
    # НЕ удаляем предыдущие сообщения, так как это может удалить важные сообщения
    # try:
    #     for i in range(1, 21):
    #         try:
    #             msg_id_to_delete = current_msg_id - i
    #             if msg_id_to_delete > 0:
    #                 await bot.delete_message(chat_id=callback.message.chat.id, message_id=msg_id_to_delete)
    #         except:
    #             pass
    # except:
    #     pass
    
    # Очищаем state после удаления сообщений
    await state.clear()


# === РЕГИСТРАЦИЯ ОБРАБОТЧИКОВ ===
