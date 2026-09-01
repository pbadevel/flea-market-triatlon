"""
Обработчик каталога и карточек товаров
"""

from aiogram import Dispatcher, types, F
from aiogram.filters import StateFilter
from aiogram.types import FSInputFile
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
from src.bot.utils.helpers import get_full_storage_path
from src.bot.utils.channel_utils import format_active_caption
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

ITEMS_PER_PAGE = 20
CARDS_PER_PAGE = 5  # Количество карточек на странице
REVIEWS_PER_PAGE = 5


def _build_category_path(category: str, subcategory: str = None, subcategories: list = None,
                         current_bike_group: str = None) -> str:
    """Построить строку 'Вы смотрите: Категория - Подкатегория - ...'
    Примеры:
    - 3 уровня: Вы смотрите: Велоспорт - Велосипеды - ТТ
    - 2 уровня: Вы смотрите: Плавание - Гидрокостюмы
    """
    from src.bot.settings.constants import CATEGORIES, SUBCATEGORIES, BIKE_SUBCATEGORY_GROUPS
    
    cat_name = CATEGORIES.get(category, category)
    parts = [cat_name]
    
    if current_bike_group and current_bike_group in BIKE_SUBCATEGORY_GROUPS:
        group = BIKE_SUBCATEGORY_GROUPS[current_bike_group]
        parts.append(group["name"])
        if subcategory and subcategory in group.get("subcategories", {}):
            parts.append(group["subcategories"][subcategory])
    elif subcategory and subcategory != 'all':
        sub_name = SUBCATEGORIES.get(category, {}).get(subcategory, subcategory)
        if sub_name:
            parts.append(sub_name)
    elif subcategories and category in SUBCATEGORIES:
        for group_key, group in BIKE_SUBCATEGORY_GROUPS.items():
            group_subs = list(group.get("subcategories", {}).keys())
            if set(subcategories) <= set(group_subs):
                parts.append(group["name"])
                break
    
    return "Вы смотрите: " + " - ".join(parts)


async def show_catalog_page(message: types.Message, page: int, edit: bool = False, filter_city: str = None, filter_country: str = None, filter_ad_type: str = None, state: FSMContext = None):
    """Показать страницу каталога с возможностью фильтрации"""
    # Получаем все объявления (потом отфильтруем)
    all_ads = await get_approved_ads(limit=100000, offset=0)
    
    # Применяем фильтр по типу объявления
    if filter_ad_type:
        from src.models import AdType
        # Используем значение из enum для сравнения
        filter_value = AdType.rent.value if filter_ad_type == "Аренда" else filter_ad_type
        all_ads = [ad for ad in all_ads if ad.ad_type == filter_value]
    
    # Применяем фильтры
    if filter_city:
        all_ads = [ad for ad in all_ads if ad.city and ad.city.lower() == filter_city.lower()]
    elif filter_country:
        # Нормализуем ввод страны
        filter_country_normalized = filter_country.lower().strip()
        
        # Варианты названий России
        russia_variants = ['россия', 'российская федерация', 'рф', 'russia', 'russian federation']
        
        # Проверяем, ищет ли пользователь Россию
        is_russia = filter_country_normalized in russia_variants
        
        if is_russia:
            # Для России учитываем объявления, где country is None (российские города по умолчанию)
            # или country содержит варианты названия России
            all_ads = [ad for ad in all_ads if (
                ad.country is None or 
                ad.country == "" or
                ad.country.lower().strip() in russia_variants
            )]
        else:
            # Для других стран ищем точное совпадение или похожие варианты
            # Также проверяем совпадение с названиями из CIS_COUNTRIES
            from src.bot.settings.constants import CIS_COUNTRIES
            matching_countries = set()
            
            # Добавляем введенное название
            matching_countries.add(filter_country_normalized)
            
            # Проверяем совпадение с названиями из CIS_COUNTRIES
            for country_key, country_data in CIS_COUNTRIES.items():
                country_name = country_data['name'].lower()
                if filter_country_normalized == country_name or filter_country_normalized in country_name or country_name in filter_country_normalized:
                    matching_countries.add(country_name)
                    matching_countries.add(country_data['name'])  # Добавляем оригинальное название
            
            # Фильтруем объявления
            all_ads = [ad for ad in all_ads if (
                ad.country and 
                ad.country.lower().strip() in matching_countries
            )]
    
    total_ads = len(all_ads)
    
    if total_ads == 0:
        text = "📭 В каталоге пока нет объявлений"
        if filter_ad_type:
            text += f" с типом {filter_ad_type}"
        if filter_city:
            text += f" для города {filter_city}"
        elif filter_country:
            text += f" для страны {filter_country}"
        text += "."
        
        # Добавляем кнопку "Назад"
        keyboard = InlineKeyboardBuilder()
        
        # Проверяем, была ли выбрана страна из списка
        selected_country_key = None
        if state:
            data = await state.get_data()
            selected_country_key = data.get('selected_country_key')
        
        # Если был выбран город и есть selected_country_key, возвращаем к выбору городов для этой страны
        if filter_city and selected_country_key:
            # Возвращаем к выбору городов для выбранной страны
            keyboard.row(InlineKeyboardButton(text=BACK_BTN, callback_data=f"catalog_country:{selected_country_key}"))
        elif filter_city or filter_country:
            # Если есть фильтр по городу/стране, но нет selected_country_key, возвращаем к списку всех товаров или аренде
            if filter_ad_type == "Аренда":
                keyboard.row(InlineKeyboardButton(text=BACK_BTN, callback_data="catalog_rent"))
            else:
                keyboard.row(InlineKeyboardButton(text=BACK_BTN, callback_data="catalog_all"))
        else:
            # Возвращаем к категориям
            keyboard.row(InlineKeyboardButton(text=BACK_BTN, callback_data="back_to_categories"))
        
        if edit:
            await message.edit_text(text, reply_markup=keyboard.as_markup())
            # Сохраняем ID сообщения для последующего редактирования
            if hasattr(message, 'message_id') and state:
                await state.update_data(empty_catalog_msg_id=message.message_id)
            return None
        else:
            sent_msg = await message.answer(text, reply_markup=keyboard.as_markup())
            # Сохраняем ID сообщения для последующего редактирования
            if state and sent_msg:
                await state.update_data(empty_catalog_msg_id=sent_msg.message_id)
            return sent_msg
    
    total_pages = ceil(total_ads / ITEMS_PER_PAGE)
    # Пагинация
    start_idx = page * ITEMS_PER_PAGE
    end_idx = min(start_idx + ITEMS_PER_PAGE, total_ads)
    ads = all_ads[start_idx:end_idx]
    
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
    
    # Определяем заголовок в зависимости от фильтра по типу
    if filter_ad_type == "Аренда":
        text = f"♻️ <b>Аренда</b> (стр. {page + 1}/{total_pages})\n"
    else:
        text = f"📦 <b>Все товары</b> (стр. {page + 1}/{total_pages})\n"
    
    if filter_city:
        text += f"📍 Выбран город: {filter_city}\n"
    elif filter_country:
        text += f"🌍 Выбрана страна: {filter_country}\n"
    text += f"Первыми показаны товары из вашей страны"
    if filter_city:
        text += f" и выбранного города"
    text += "\n\n"
    
    for ad in ads:
        # Определяем флаг страны
        country_flag = get_country_flag(ad.country)
        
        # Форматируем цену с пробелами
        price_formatted = f"{ad.price:,}".replace(",", " ")
        
        # Формируем размер (если есть)
        size_info = f" ({ad.size})" if ad.size else ""
        
        # Создаем deep link для товара
        deep_link_url = f"https://t.me/{bot_username}?start=item_{ad.id}"
        
        # Добавляем товар в список: флаг, название со ссылкой, размер, цена, город
        text += f"{country_flag} <a href=\"{deep_link_url}\">{ad.title}{size_info}</a> {price_formatted}₽ г. {ad.city}\n"
    
    # Создаем клавиатуру с пагинацией и фильтрами
    keyboard = InlineKeyboardBuilder()
    
    # Добавляем кнопки пагинации (только если больше 1 страницы)
    if total_pages > 1:
        nav_buttons = []
        if page > 0:
            callback_data = f"catalog_page:{page-1}"
            if filter_ad_type:
                callback_data += f":ad_type:{filter_ad_type}"
            if filter_city:
                callback_data += f":city:{filter_city}"
            elif filter_country:
                callback_data += f":country:{filter_country}"
            nav_buttons.append(InlineKeyboardButton(text="◀️", callback_data=callback_data))
        
        # Показываем текущую страницу
        nav_buttons.append(InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="noop"))
        
        if page < total_pages - 1:
            callback_data = f"catalog_page:{page+1}"
            if filter_ad_type:
                callback_data += f":ad_type:{filter_ad_type}"
            if filter_city:
                callback_data += f":city:{filter_city}"
            elif filter_country:
                callback_data += f":country:{filter_country}"
            nav_buttons.append(InlineKeyboardButton(text="▶️", callback_data=callback_data))
        
        keyboard.row(*nav_buttons)
    
    # Добавляем фильтры по городам (в 2 столбца)
    filter_cities = [
        ("📍 Москва", "catalog_filter:city:Москва"),
        ("📍 Санкт-Петербург", "catalog_filter:city:Санкт-Петербург"),
    ]
    
    for i in range(0, len(filter_cities), 2):
        row_cities = filter_cities[i:i+2]
        keyboard.row(*[InlineKeyboardButton(text=city[0], callback_data=city[1]) for city in row_cities])
    
    # Кнопки "Другой город" и "Другая страна" в один ряд
    keyboard.row(
        InlineKeyboardButton(text="🌆 Другой город", callback_data="catalog_filter:other_city"),
        InlineKeyboardButton(text="🌍 Другая страна", callback_data="catalog_filter:other_country")
    )
    
    # Кнопка "Сбросить фильтр" только если фильтр активен
    if filter_city or filter_country:
        keyboard.row(InlineKeyboardButton(text="❌ Сбросить фильтр", callback_data="catalog_filter:reset"))
    
    # Кнопка "Назад" вместо "Главное меню"
    keyboard.row(InlineKeyboardButton(text=BACK_BTN, callback_data="back_to_categories"))
    
    keyboard = keyboard.as_markup()
    
    if edit:
        await message.edit_text(text, parse_mode='HTML', reply_markup=keyboard)
        return None
    else:
        # Отправляем новое сообщение и возвращаем его для сохранения ID
        sent_msg = await message.answer(text, parse_mode='HTML', reply_markup=keyboard)
        return sent_msg


async def show_category_items(message: types.Message, category: str, subcategory: str = None, page: int = 0, state: FSMContext = None):
    """Показать товары категории/подкатегории как карточки (по 10 за раз)"""
    from src.bot.settings.constants import CATEGORIES, SUBCATEGORIES
    
    # Удаляем предыдущие карточки, разделитель и сообщение навигации, если они есть
    if state:
        data = await state.get_data()
        prev_card_ids = data.get('category_cards_message_ids', [])
        prev_nav_id = data.get('category_nav_message_id')
        prev_sep_id = data.get('category_separator_message_id')
        for card_id in prev_card_ids:
            try:
                await bot.delete_message(chat_id=message.chat.id, message_id=card_id)
            except:
                pass
        if prev_nav_id:
            try:
                await bot.delete_message(chat_id=message.chat.id, message_id=prev_nav_id)
            except:
                pass
        if prev_sep_id:
            try:
                await bot.delete_message(chat_id=message.chat.id, message_id=prev_sep_id)
            except:
                pass
    
    # Получаем общее количество товаров
    if subcategory:
        total_ads = await count_ads_by_subcategory(category, subcategory)
    else:
        total_ads = await count_ads_by_category(category)
    
    if total_ads == 0:
        text = "📭 В этой категории пока нет товаров."
        keyboard = InlineKeyboardBuilder()
        # Определяем, куда возвращаться: к группе, к категории или к списку категорий
        if state:
            data = await state.get_data()
            if data.get('current_bike_group'):
                # Если мы в группе, возвращаемся к группе
                keyboard.row(InlineKeyboardButton(text=BACK_BTN, callback_data="back_to_bike_group"))
            elif data.get('current_category'):
                # Если мы в категории (но не в группе), возвращаемся к подкатегориям категории
                keyboard.row(InlineKeyboardButton(text=BACK_BTN, callback_data="back_to_category_subcategories"))
            else:
                # Иначе возвращаемся к категориям
                keyboard.row(InlineKeyboardButton(text=BACK_BTN, callback_data="back_to_categories"))
        else:
            keyboard.row(InlineKeyboardButton(text=BACK_BTN, callback_data="back_to_categories"))
        
        # Пытаемся отредактировать сообщение категории, если оно есть в state
        if state:
            data = await state.get_data()
            category_msg_id = data.get('category_msg_id')
            # Если есть сохраненное сообщение категории (сообщение с подкатегориями), редактируем его
            if category_msg_id:
                try:
                    await bot.edit_message_text(
                        chat_id=message.chat.id,
                        message_id=category_msg_id,
                        text=text,
                        reply_markup=keyboard.as_markup()
                    )
                    # Сохраняем ID сообщения для последующего редактирования
                    await state.update_data(empty_category_msg_id=category_msg_id)
                    return
                except:
                    pass
            
            # Если сообщение категории не найдено, пытаемся отредактировать текущее сообщение
            # (если message - это callback.message)
            if hasattr(message, 'edit_text'):
                try:
                    sent_msg = await message.edit_text(text, reply_markup=keyboard.as_markup())
                    await state.update_data(empty_category_msg_id=sent_msg.message_id)
                    return
                except:
                    pass
        
        # Если не удалось отредактировать, отправляем новое
        sent_msg = await message.answer(text, reply_markup=keyboard.as_markup())
        # Сохраняем ID сообщения для последующего редактирования
        if state:
            await state.update_data(empty_category_msg_id=sent_msg.message_id)
        return
    
    # Получаем товары для текущей страницы
    ads = await get_ads_by_category(category, subcategory, limit=CARDS_PER_PAGE, offset=page * CARDS_PER_PAGE)
    
    if not ads:
        text = "📭 Больше нет товаров."
        await message.answer(text)
        return
    
    # Разделитель перед карточками: "Вы смотрите: Категория - Подкатегория"
    current_bike_group = (await state.get_data()).get('current_bike_group') if state else None
    separator_text = _build_category_path(category, subcategory, current_bike_group=current_bike_group)
    sep_msg = await message.answer(separator_text)
    sep_id = sep_msg.message_id
    
    # Показываем каждый товар как карточку и сохраняем message_id
    card_message_ids = []
    for ad in ads:
        msg = await show_ad_card(message, ad)
        if msg:
            card_message_ids.append(msg.message_id)
    
    # Сохраняем message_id разделителя и карточек в состоянии
    if state:
        await state.update_data(
            category_separator_message_id=sep_id,
            category_cards_message_ids=card_message_ids,
            category_current_page=page,
            category_name=category,
            category_subcategory=subcategory,
            category_total_ads=total_ads
        )
    
    # Показываем навигацию
    shown_count = min((page + 1) * CARDS_PER_PAGE, total_ads)
    text = f"Продолжить просмотр? {shown_count} товаров из {total_ads}"
    
    keyboard = InlineKeyboardBuilder()
    
    # Кнопка "Продолжить" - только если есть еще товары
    if shown_count < total_ads:
        keyboard.row(InlineKeyboardButton(text="▶️ Продолжить", callback_data=f"cat_next:{category}:{subcategory or 'all'}:{page+1}"))
    
    # Кнопка "Вернуться на шаг" - только если не на первой странице
    if page > 0:
        keyboard.row(InlineKeyboardButton(text="◀️ Вернуться на шаг", callback_data=f"cat_prev:{category}:{subcategory or 'all'}:{page-1}"))
    
    # Определяем, куда возвращаться: к группе, к категории или к списку категорий
    if state:
        data = await state.get_data()
        if data.get('current_bike_group'):
            # Если мы в группе, возвращаемся к группе
            keyboard.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_bike_group"))
        elif data.get('current_category'):
            # Если мы в категории (но не в группе), возвращаемся к подкатегориям категории
            keyboard.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_category_subcategories"))
        else:
            # Иначе возвращаемся к категориям
            keyboard.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_categories"))
    else:
        keyboard.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_categories"))
    
    nav_msg = await message.answer(text, reply_markup=keyboard.as_markup())
    
    # Сохраняем message_id навигационного сообщения
    if state:
        await state.update_data(category_nav_message_id=nav_msg.message_id)


async def show_category_items_by_subcategories(message: types.Message, category: str, subcategories: list, page: int = 0, state: FSMContext = None):
    """Показать товары из нескольких подкатегорий как карточки (по 10 за раз)"""
    from src.bot.settings.constants import CATEGORIES, SUBCATEGORIES
    
    # Удаляем предыдущие карточки, разделитель и сообщение навигации, если они есть
    if state:
        data = await state.get_data()
        prev_card_ids = data.get('category_cards_message_ids', [])
        prev_nav_id = data.get('category_nav_message_id')
        prev_sep_id = data.get('category_separator_message_id')
        for card_id in prev_card_ids:
            try:
                await bot.delete_message(chat_id=message.chat.id, message_id=card_id)
            except:
                pass
        if prev_nav_id:
            try:
                await bot.delete_message(chat_id=message.chat.id, message_id=prev_nav_id)
            except:
                pass
        if prev_sep_id:
            try:
                await bot.delete_message(chat_id=message.chat.id, message_id=prev_sep_id)
            except:
                pass
    
    # Получаем общее количество товаров
    total_ads = await count_ads_by_subcategories(category, subcategories)
    
    if total_ads == 0:
        text = "📭 В этой категории пока нет товаров."
        keyboard = InlineKeyboardBuilder()
        # Всегда возвращаемся к группе, так как эта функция используется только для групп
        keyboard.row(InlineKeyboardButton(text=BACK_BTN, callback_data="back_to_bike_group"))
        
        # Пытаемся отредактировать сообщение категории, если оно есть в state
        if state:
            data = await state.get_data()
            category_msg_id = data.get('category_msg_id')
            if category_msg_id:
                try:
                    await bot.edit_message_text(
                        chat_id=message.chat.id,
                        message_id=category_msg_id,
                        text=text,
                        reply_markup=keyboard.as_markup()
                    )
                    await state.update_data(empty_category_msg_id=category_msg_id)
                    return
                except:
                    pass
        
        sent_msg = await message.answer(text, reply_markup=keyboard.as_markup())
        if state:
            await state.update_data(empty_category_msg_id=sent_msg.message_id)
        return
    
    # Получаем товары для текущей страницы
    ads = await get_ads_by_subcategories(category, subcategories, limit=CARDS_PER_PAGE, offset=page * CARDS_PER_PAGE)
    
    if not ads:
        text = "📭 Больше нет товаров."
        await message.answer(text)
        return
    
    # Разделитель перед карточками: "Вы смотрите: Категория - Группа"
    current_bike_group = (await state.get_data()).get('current_bike_group') if state else None
    separator_text = _build_category_path(category, subcategories=subcategories,
                                          current_bike_group=current_bike_group)
    sep_msg = await message.answer(separator_text)
    sep_id = sep_msg.message_id
    
    # Показываем каждый товар как карточку и сохраняем message_id
    card_message_ids = []
    for ad in ads:
        msg = await show_ad_card(message, ad)
        if msg:
            card_message_ids.append(msg.message_id)
    
    # Сохраняем message_id разделителя и карточек в состоянии
    if state:
        await state.update_data(
            category_separator_message_id=sep_id,
            category_cards_message_ids=card_message_ids,
            category_current_page=page,
            category_name=category,
            category_subcategories=subcategories,
            category_total_ads=total_ads
        )
    
    # Показываем навигацию
    shown_count = min((page + 1) * CARDS_PER_PAGE, total_ads)
    text = f"Продолжить просмотр? {shown_count} товаров из {total_ads}"
    
    keyboard = InlineKeyboardBuilder()
    
    # Кнопка "Продолжить" - только если есть еще товары
    if shown_count < total_ads:
        # Используем специальный callback для навигации по группе
        keyboard.row(InlineKeyboardButton(text="▶️ Продолжить", callback_data=f"cat_next_group:{category}:{page+1}"))
    
    # Кнопка "Вернуться на шаг" - только если не на первой странице
    if page > 0:
        keyboard.row(InlineKeyboardButton(text="◀️ Вернуться на шаг", callback_data=f"cat_prev_group:{category}:{page-1}"))
    
    # Всегда возвращаемся к группе, так как эта функция используется только для групп
    keyboard.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_bike_group"))
    
    nav_msg = await message.answer(text, reply_markup=keyboard.as_markup())
    
    if state:
        await state.update_data(category_nav_message_id=nav_msg.message_id)


async def show_ad_card(message: types.Message, ad):
    """Показать товар как карточку (обложка + краткое описание + кнопка)"""
    # Используем обработанную обложку (обрезанную с логотипом) из cover_file_id
    # Если её нет, используем первое фото (для старых объявлений)
    cover_photo = ad.cover_file_id

    if not cover_photo:
        # Для старых объявлений без cover_file_id используем первое фото
        photos = await get_ad_photos(ad.id)
        if not photos:
            return None
        
        cover_photo = photos[0].file_id
        
        if (not photos[0].file_id) and photos[0].storage_path:
            cover_photo = FSInputFile(get_full_storage_path(photos[0].storage_path))
        
    
    # Проверяем статус доверенного продавца и добавляем логотип в левый верхний угол
    # Пока закомментирована вставка второго лого (для доверенного продавца)
    seller = await get_user_by_id(ad.seller_user_id)
    is_trusted = seller.is_trusted_seller if seller else False
    
    # if is_trusted:
    #     # Добавляем логотип доверенного продавца в изображение
    #     from src.bot.utils.image_utils import add_trusted_seller_logo_to_photo
    #     try:
    #         cover_photo = await add_trusted_seller_logo_to_photo(
    #             file_id=cover_photo,
    #             chat_id=message.chat.id,
    #             bot=bot,
    #             logo_path="assets/logo.png"
    #         )
    #     except Exception as e:
    #         logger.error(f"Ошибка при добавлении логотипа доверенного продавца: {e}")
    #         # Продолжаем с исходным изображением в случае ошибки
    
    caption = format_active_caption(ad, is_trusted)
    
    # Кнопка "Подробнее"
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text="🔍 Подробнее", callback_data=f"details:{ad.id}"))
    
    # photo_union = photo.file_id
    
    # if (not photo.file_id) and photo.storage_path:
    #     photo_union = FSInputFile(photo.storage_path)


    msg = await message.answer_photo(
        photo=cover_photo,
        caption=caption,
        parse_mode='HTML',
        reply_markup=keyboard.as_markup()
    )
    
    return msg


