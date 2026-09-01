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

async def catalog_handler(callback: types.CallbackQuery, state: FSMContext):
    """Показать каталог объявлений (категории)"""
    await callback.answer()
    
    # Удаляем предыдущие сообщения (детали объявления, профиль продавца и т.д.)
    data = await state.get_data()
    ad_details_msg_id = data.get('ad_details_msg_id')
    category_msg_id = data.get('category_msg_id')
    
    # Удаляем сообщение "Выберите действие:" из деталей объявления
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
    
    # Удаляем текущее сообщение (профиль продавца или детали объявления)
    try:
        await callback.message.delete()
    except:
        pass
    
    # Удаляем карточки, разделитель и навигационное сообщение, если они есть
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
    
    await state.clear()
    await state.update_data(
        category_cards_message_ids=[],
        category_nav_message_id=None,
        category_separator_message_id=None,
        ad_details_msg_id=None,
        category_msg_id=None,
        current_filter_ad_type=None
    )
    
    # Показываем категории
    text = "📂 Выберите категорию товаров:"
    
    # Подсчитываем товары по категориям
    categories_data = {}
    total_ads = 0
    for cat_key, cat_name in CATEGORIES.items():
        count = await count_ads_by_category(cat_key)
        categories_data[cat_key] = (cat_name, count)
        total_ads += count
    
    # Подсчитываем объявления с типом "Аренда"
    from src.models import AdType
    from loguru import logger
    rent_type_value = AdType.rent.value
    logger.info(f"Counting rent ads with type value: '{rent_type_value}' (repr: {repr(rent_type_value)}, len: {len(rent_type_value)})")
    logger.info(f"AdType.rent = {AdType.rent}, AdType.rent.value = {AdType.rent.value}")
    rent_ads_count = await count_ads_by_ad_type(rent_type_value)
    logger.info(f"Rent ads count result: {rent_ads_count}")
    
    keyboard = catalog_categories_kb(categories_data, total_ads, rent_ads_count)
    
    # Пытаемся отредактировать сообщение, если это возможно
    try:
        await callback.message.edit_text(text, reply_markup=keyboard)
    except:
        await callback.message.answer(text, reply_markup=keyboard)


async def catalog_all_callback(callback: types.CallbackQuery, state: FSMContext):
    """Показать все товары списком"""
    await callback.answer()
    
    # Получаем данные из state для удаления предыдущих сообщений
    data = await state.get_data()
    catalog_msg_id = data.get('catalog_msg_id')
    city_input_msg_id = data.get('city_input_msg_id')
    country_input_msg_id = data.get('country_input_msg_id')
    empty_catalog_msg_id = data.get('empty_catalog_msg_id')
    current_msg_id = callback.message.message_id
    
    # Проверяем, является ли текущее сообщение сообщением с запросом ввода
    is_city_input_msg = (city_input_msg_id == current_msg_id) or \
                        (callback.message.text and "🌆 Введите название города:" in callback.message.text)
    is_country_input_msg = (country_input_msg_id == current_msg_id) or \
                           (callback.message.text and "🌍 Введите название страны:" in callback.message.text)
    
    # Если текущее сообщение - это сообщение с запросом ввода, редактируем его
    # Если нет - удаляем сообщения с запросами ввода (если они не являются текущим)
    if is_city_input_msg or is_country_input_msg:
        # Текущее сообщение - это запрос ввода, редактируем его на каталог
        # Не удаляем его, так как будем редактировать
        pass
    else:
        # Удаляем сообщение с запросом ввода города, если есть и это не текущее сообщение
        if city_input_msg_id and city_input_msg_id != current_msg_id:
            try:
                await bot.delete_message(chat_id=callback.message.chat.id, message_id=city_input_msg_id)
            except:
                pass
        
        # Удаляем сообщение с запросом ввода страны, если есть и это не текущее сообщение
        if country_input_msg_id and country_input_msg_id != current_msg_id:
            try:
                await bot.delete_message(chat_id=callback.message.chat.id, message_id=country_input_msg_id)
            except:
                pass
    
    # Редактируем текущее сообщение на каталог
    sent_msg = await show_catalog_page(callback.message, 0, edit=True, state=state)
    
    # Сохраняем ID сообщения каталога в state для последующего удаления
    if current_msg_id:
        await state.update_data(catalog_msg_id=current_msg_id)
    
    # Удаляем предыдущее сообщение с каталогом, если оно есть (но не текущее)
    # Делаем это ПОСЛЕ редактирования, чтобы не удалить текущее сообщение
    if catalog_msg_id and catalog_msg_id != current_msg_id:
        try:
            await bot.delete_message(chat_id=callback.message.chat.id, message_id=catalog_msg_id)
        except:
            pass
    
    # Очищаем только фильтры, но оставляем catalog_msg_id
    await state.update_data(
        city_input_msg_id=None,
        country_input_msg_id=None,
        current_filter_ad_type=None,
        selected_country=None,
        selected_country_key=None
    )


async def catalog_rent_callback(callback: types.CallbackQuery, state: FSMContext):
    """Показать все объявления с типом 'Аренда' списком"""
    await callback.answer()
    
    # Получаем данные из state для удаления предыдущих сообщений
    data = await state.get_data()
    catalog_msg_id = data.get('catalog_msg_id')
    city_input_msg_id = data.get('city_input_msg_id')
    country_input_msg_id = data.get('country_input_msg_id')
    empty_catalog_msg_id = data.get('empty_catalog_msg_id')
    current_msg_id = callback.message.message_id
    
    # Проверяем, является ли текущее сообщение сообщением с запросом ввода
    is_city_input_msg = (city_input_msg_id == current_msg_id) or \
                        (callback.message.text and "🌆 Введите название города:" in callback.message.text)
    is_country_input_msg = (country_input_msg_id == current_msg_id) or \
                           (callback.message.text and "🌍 Введите название страны:" in callback.message.text)
    
    # Если текущее сообщение - это сообщение с запросом ввода, редактируем его
    # Если нет - удаляем сообщения с запросами ввода (если они не являются текущим)
    if is_city_input_msg or is_country_input_msg:
        # Текущее сообщение - это запрос ввода, редактируем его на каталог
        # Не удаляем его, так как будем редактировать
        pass
    else:
        # Удаляем сообщение с запросом ввода города, если есть и это не текущее сообщение
        if city_input_msg_id and city_input_msg_id != current_msg_id:
            try:
                await bot.delete_message(chat_id=callback.message.chat.id, message_id=city_input_msg_id)
            except:
                pass
        
        # Удаляем сообщение с запросом ввода страны, если есть и это не текущее сообщение
        if country_input_msg_id and country_input_msg_id != current_msg_id:
            try:
                await bot.delete_message(chat_id=callback.message.chat.id, message_id=country_input_msg_id)
            except:
                pass
    
    # Редактируем текущее сообщение на каталог с фильтром по типу "Аренда"
    sent_msg = await show_catalog_page(callback.message, 0, edit=True, filter_ad_type="Аренда", state=state)
    
    # Сохраняем ID сообщения каталога в state для последующего удаления
    if current_msg_id:
        await state.update_data(catalog_msg_id=current_msg_id)
    
    # Удаляем предыдущее сообщение с каталогом, если оно есть (но не текущее)
    # Делаем это ПОСЛЕ редактирования, чтобы не удалить текущее сообщение
    if catalog_msg_id and catalog_msg_id != current_msg_id:
        try:
            await bot.delete_message(chat_id=callback.message.chat.id, message_id=catalog_msg_id)
        except:
            pass
    
    # Сохраняем фильтр по типу в state для использования в обработчиках фильтров
    await state.update_data(
        city_input_msg_id=None,
        country_input_msg_id=None,
        current_filter_ad_type="Аренда"
    )


async def catalog_category_callback(callback: types.CallbackQuery, state: FSMContext):
    """Показать подкатегории или товары категории"""
    await callback.answer()
    
    category = callback.data.split(':')[1]
    
    # Удаляем карточки, разделитель и навигационное сообщение, если они есть
    if state:
        data = await state.get_data()
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
            category_separator_message_id=None
        )
    
    # Проверяем, есть ли подкатегории
    subcats = SUBCATEGORIES.get(category, {})
    
    if not subcats:
        # Если подкатегорий нет, сразу показываем товары
        # Удаляем сообщение категории перед показом товаров
        try:
            await callback.message.delete()
        except:
            pass
        await show_category_items(callback.message, category, None, 0, state)
        return
    
    # Показываем подкатегории
    cat_name = CATEGORIES.get(category, category)
    text = f"📂 Категория: {cat_name}"
    
    # Подсчитываем товары по подкатегориям
    total_in_cat = await count_ads_by_category(category)
    subcats_data = {}
    
    # Для велоспорта нужно также считать товары в группах
    if category == "bike":
        from src.bot.settings.constants import BIKE_SUBCATEGORY_GROUPS
        # Считаем товары для подкатегорий внутри групп
        for group_key, group_data in BIKE_SUBCATEGORY_GROUPS.items():
            for subcat_key, subcat_name in group_data["subcategories"].items():
                count = await count_ads_by_subcategory(category, subcat_key)
                subcats_data[subcat_key] = (subcat_name, count)
        # Считаем товары для обычных подкатегорий (не группы)
        for subcat_key, subcat_name in subcats.items():
            if not subcat_key.endswith("_group"):
                count = await count_ads_by_subcategory(category, subcat_key)
                subcats_data[subcat_key] = (subcat_name, count)
    else:
        for subcat_key, subcat_name in subcats.items():
            count = await count_ads_by_subcategory(category, subcat_key)
            subcats_data[subcat_key] = (subcat_name, count)
    
    keyboard = catalog_subcategories_kb(category, subcats_data, total_in_cat)
    
    try:
        msg = await callback.message.edit_text(text, reply_markup=keyboard)
        # Сохраняем ID сообщения категории для последующего удаления
        await state.update_data(category_msg_id=msg.message_id)
    except:
        msg = await callback.message.answer(text, reply_markup=keyboard)
        # Сохраняем ID сообщения категории для последующего удаления
        await state.update_data(category_msg_id=msg.message_id)


async def catalog_category_all_callback(callback: types.CallbackQuery, state: FSMContext):
    """Показать все товары категории"""
    await callback.answer()
    
    category = callback.data.split(':')[1]
    
    # Сохраняем информацию о категории в state для правильного возврата
    if state:
        # Сохраняем category_msg_id перед удалением, чтобы можно было вернуться к подкатегориям
        category_msg_id = callback.message.message_id
        await state.update_data(
            current_category=category,
            category_msg_id=category_msg_id,
            current_bike_group=None  # Очищаем информацию о группе, так как мы в категории
        )
    
    # Удаляем сообщение категории перед показом товаров
    try:
        await callback.message.delete()
    except:
        pass
    
    await show_category_items(callback.message, category, None, 0, state)


async def catalog_bike_group_callback(callback: types.CallbackQuery, state: FSMContext):
    """Показать подкатегории внутри группы велоспорта"""
    await callback.answer()
    
    group_key = callback.data.split(':')[1]
    
    # Подсчитываем товары по подкатегориям в группе
    from src.bot.settings.constants import BIKE_SUBCATEGORY_GROUPS
    group_data = BIKE_SUBCATEGORY_GROUPS.get(group_key)
    
    if not group_data:
        return
    
    subcats_data = {}
    for subcat_key in group_data["subcategories"].keys():
        count = await count_ads_by_subcategory("bike", subcat_key)
        subcat_name = group_data["subcategories"][subcat_key]
        subcats_data[subcat_key] = (subcat_name, count)
    
    # Показываем подкатегории группы
    cat_name = CATEGORIES.get("bike", "ВЕЛОСПОРТ")
    text = f"📂 Категория: {cat_name}\n📁 Группа: {group_data['name']}"
    
    # Сохраняем информацию о группе в state для правильного возврата
    if state:
        await state.update_data(current_bike_group=group_key, bike_group_msg_id=callback.message.message_id)
    
    from src.bot.keyboards.keyboards import catalog_bike_group_subcategories_kb
    keyboard = catalog_bike_group_subcategories_kb(group_key, subcats_data)
    
    try:
        await callback.message.edit_text(text, reply_markup=keyboard)
    except:
        await callback.message.answer(text, reply_markup=keyboard)


async def catalog_bike_group_all_callback(callback: types.CallbackQuery, state: FSMContext):
    """Показать все товары группы (Все велосипеды или Вся экипировка)"""
    await callback.answer()
    
    group_key = callback.data.split(':')[1]
    
    # Сохраняем информацию о группе в state для правильного возврата
    if state:
        await state.update_data(current_bike_group=group_key, bike_group_msg_id=callback.message.message_id)
    
    # Удаляем сообщение с группой перед показом товаров
    try:
        await callback.message.delete()
    except:
        pass
    
    # Получаем все подкатегории группы
    from src.bot.settings.constants import BIKE_SUBCATEGORY_GROUPS
    group_data = BIKE_SUBCATEGORY_GROUPS.get(group_key)
    
    if not group_data:
        return
    
    # Получаем все подкатегории группы
    subcategory_keys = list(group_data["subcategories"].keys())
    
    # Показываем товары из всех подкатегорий группы
    await show_category_items_by_subcategories(callback.message, "bike", subcategory_keys, 0, state)


async def catalog_subcategory_callback(callback: types.CallbackQuery, state: FSMContext):
    """Показать товары подкатегории"""
    await callback.answer()
    
    parts = callback.data.split(':')
    category = parts[1]
    subcategory = parts[2]
    
    # Проверяем, принадлежит ли подкатегория какой-то группе велоспорта
    group_key = None
    if category == "bike":
        from src.bot.settings.constants import BIKE_SUBCATEGORY_GROUPS
        for g_key, g_data in BIKE_SUBCATEGORY_GROUPS.items():
            if subcategory in g_data["subcategories"]:
                group_key = g_key
                break
    
    # Сохраняем информацию о группе/категории в state
    if state:
        data = await state.get_data()
        category_msg_id = data.get('category_msg_id')
        if category_msg_id:
            try:
                await bot.delete_message(chat_id=callback.message.chat.id, message_id=category_msg_id)
            except:
                pass
            await state.update_data(category_msg_id=None)
        
        # Если подкатегория принадлежит группе, сохраняем информацию о группе
        if group_key:
            await state.update_data(current_bike_group=group_key, current_category=None)
        else:
            # Если не принадлежит группе, сохраняем информацию о категории и очищаем группу
            await state.update_data(current_bike_group=None, current_category=category)
    
    # Удаляем сообщение с группой/подкатегорией перед показом товаров
    try:
        await callback.message.delete()
    except:
        pass
    
    # callback.message все еще содержит необходимые атрибуты (chat, from_user) после удаления
    await show_category_items(callback.message, category, subcategory, 0, state)


async def catalog_next_callback(callback: types.CallbackQuery, state: FSMContext):
    """Продолжить просмотр карточек (следующая страница)"""
    await callback.answer()
    
    parts = callback.data.split(':')
    category = parts[1]
    subcategory = parts[2] if parts[2] != 'all' else None
    page = int(parts[3])
    
    await show_category_items(callback.message, category, subcategory, page, state)


async def catalog_prev_callback(callback: types.CallbackQuery, state: FSMContext):
    """Вернуться на шаг назад (предыдущая страница карточек)"""
    await callback.answer()
    
    parts = callback.data.split(':')
    category = parts[1]
    subcategory = parts[2] if parts[2] != 'all' else None
    page = int(parts[3])
    
    await show_category_items(callback.message, category, subcategory, page, state)


async def catalog_next_group_callback(callback: types.CallbackQuery, state: FSMContext):
    """Продолжить просмотр карточек группы (следующая страница)"""
    await callback.answer()
    
    parts = callback.data.split(':')
    category = parts[1]
    page = int(parts[2])
    
    data = await state.get_data()
    subcategories = data.get('category_subcategories', [])
    
    await show_category_items_by_subcategories(callback.message, category, subcategories, page, state)


async def catalog_prev_group_callback(callback: types.CallbackQuery, state: FSMContext):
    """Вернуться на шаг назад группы (предыдущая страница карточек)"""
    await callback.answer()
    
    parts = callback.data.split(':')
    category = parts[1]
    page = int(parts[2])
    
    data = await state.get_data()
    subcategories = data.get('category_subcategories', [])
    
    await show_category_items_by_subcategories(callback.message, category, subcategories, page, state)


async def back_to_category_subcategories_callback(callback: types.CallbackQuery, state: FSMContext):
    """Вернуться к подкатегориям категории"""
    await callback.answer()
    
    if not state:
        return
    
    data = await state.get_data()
    category = data.get('current_category')
    
    if not category:
        # Если нет информации о категории, возвращаемся к категориям
        await back_to_categories_callback(callback, state)
        return
    
    # Получаем подкатегории категории
    subcats = SUBCATEGORIES.get(category, {})
    
    if not subcats:
        # Если подкатегорий нет, возвращаемся к категориям
        await back_to_categories_callback(callback, state)
        return
    
    # Подсчитываем товары по подкатегориям
    cat_name = CATEGORIES.get(category, category)
    text = f"📂 Категория: {cat_name}"
    
    total_in_cat = await count_ads_by_category(category)
    subcats_data = {}
    
    # Для велоспорта нужно также считать товары в группах
    if category == "bike":
        from src.bot.settings.constants import BIKE_SUBCATEGORY_GROUPS
        # Считаем товары для подкатегорий внутри групп
        for group_key, group_data in BIKE_SUBCATEGORY_GROUPS.items():
            for subcat_key, subcat_name in group_data["subcategories"].items():
                count = await count_ads_by_subcategory(category, subcat_key)
                subcats_data[subcat_key] = (subcat_name, count)
        # Считаем товары для обычных подкатегорий (не группы)
        for subcat_key, subcat_name in subcats.items():
            if not subcat_key.endswith("_group"):
                count = await count_ads_by_subcategory(category, subcat_key)
                subcats_data[subcat_key] = (subcat_name, count)
    else:
        for subcat_key, subcat_name in subcats.items():
            count = await count_ads_by_subcategory(category, subcat_key)
            subcats_data[subcat_key] = (subcat_name, count)
    
    from src.bot.keyboards.keyboards import catalog_subcategories_kb
    keyboard = catalog_subcategories_kb(category, subcats_data, total_in_cat)
    
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


async def back_to_bike_group_callback(callback: types.CallbackQuery, state: FSMContext):
    """Вернуться к группе велоспорта"""
    await callback.answer()
    
    if not state:
        return
    
    data = await state.get_data()
    group_key = data.get('current_bike_group')
    
    if not group_key:
        # Если нет информации о группе, возвращаемся к категориям
        await back_to_categories_callback(callback, state)
        return
    
    from src.bot.settings.constants import BIKE_SUBCATEGORY_GROUPS
    group_data = BIKE_SUBCATEGORY_GROUPS.get(group_key)
    
    if not group_data:
        await back_to_categories_callback(callback, state)
        return
    
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


async def back_to_categories_callback(callback: types.CallbackQuery, state: FSMContext):
    """Вернуться к списку категорий"""
    await callback.answer()
    
    # Удаляем карточки, разделитель и навигационное сообщение, если они есть
    if state:
        data = await state.get_data()
        prev_card_ids = data.get('category_cards_message_ids', [])
        prev_nav_id = data.get('category_nav_message_id')
        prev_sep_id = data.get('category_separator_message_id')
        empty_category_msg_id = data.get('empty_category_msg_id')
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
            empty_category_msg_id=None,
            current_bike_group=None,
            bike_group_msg_id=None,
            category_subcategories=None
        )
    
    text = "📂 Выберите категорию товаров:"
    
    # Подсчитываем товары по категориям
    categories_data = {}
    total_ads = 0
    for cat_key, cat_name in CATEGORIES.items():
        count = await count_ads_by_category(cat_key)
        categories_data[cat_key] = (cat_name, count)
        total_ads += count
    
    # Подсчитываем объявления с типом "Аренда"
    from src.models import AdType
    from loguru import logger
    rent_type_value = AdType.rent.value
    logger.info(f"Counting rent ads with type value: '{rent_type_value}' (repr: {repr(rent_type_value)}, len: {len(rent_type_value)})")
    logger.info(f"AdType.rent = {AdType.rent}, AdType.rent.value = {AdType.rent.value}")
    rent_ads_count = await count_ads_by_ad_type(rent_type_value)
    logger.info(f"Rent ads count result: {rent_ads_count}")
    
    keyboard = catalog_categories_kb(categories_data, total_ads, rent_ads_count)
    
    # Сбрасываем фильтр по типу при возврате к категориям
    if state:
        await state.update_data(current_filter_ad_type=None)
    
    # Пытаемся редактировать текущее сообщение
    # Это может быть:
    # 1. Сообщение с подкатегориями "📂 Категория: 💻 ЭЛЕКТРОНИКА"
    # 2. Сообщение "В этой категории пока нет товаров"
    # 3. Сообщение "В каталоге пока нет объявлений"
    # 4. Сообщение с товарами аренды "♻️ Аренда (стр. 1/1)"
    try:
        await callback.message.edit_text(text, parse_mode='HTML', reply_markup=keyboard)
        # Очищаем empty_category_msg_id и empty_catalog_msg_id, так как сообщение отредактировано
        if state:
            await state.update_data(empty_category_msg_id=None, empty_catalog_msg_id=None)
    except Exception as e:
        # Если не удалось отредактировать (например, сообщение слишком длинное),
        # удаляем старое сообщение и отправляем новое
        try:
            await callback.message.delete()
        except:
            pass
        await callback.message.answer(text, parse_mode='HTML', reply_markup=keyboard)


async def catalog_page_callback(callback: types.CallbackQuery, state: FSMContext):
    """Переключение страниц каталога"""
    await callback.answer()
    
    parts = callback.data.split(':')
    page = int(parts[1])
    
    # Проверяем наличие фильтров
    filter_ad_type = None
    filter_city = None
    filter_country = None
    if len(parts) > 2:
        i = 2
        while i < len(parts):
            if parts[i] == 'ad_type' and i + 1 < len(parts):
                filter_ad_type = parts[i + 1]
                i += 2
            elif parts[i] == 'city' and i + 1 < len(parts):
                filter_city = parts[i + 1]
                i += 2
            elif parts[i] == 'country' and i + 1 < len(parts):
                filter_country = parts[i + 1]
                i += 2
            else:
                i += 1
    
    await show_catalog_page(callback.message, page, edit=True, filter_city=filter_city, filter_country=filter_country, filter_ad_type=filter_ad_type, state=state)


async def catalog_page_callback(callback: types.CallbackQuery, state: FSMContext):
    """Переключение страниц каталога"""
    await callback.answer()
    
    parts = callback.data.split(':')
    page = int(parts[1])
    
    # Проверяем наличие фильтров
    filter_ad_type = None
    filter_city = None
    filter_country = None
    if len(parts) > 2:
        i = 2
        while i < len(parts):
            if parts[i] == 'ad_type' and i + 1 < len(parts):
                filter_ad_type = parts[i + 1]
                i += 2
            elif parts[i] == 'city' and i + 1 < len(parts):
                filter_city = parts[i + 1]
                i += 2
            elif parts[i] == 'country' and i + 1 < len(parts):
                filter_country = parts[i + 1]
                i += 2
            else:
                i += 1
    
    await show_catalog_page(callback.message, page, edit=True, filter_city=filter_city, filter_country=filter_country, filter_ad_type=filter_ad_type, state=state)


