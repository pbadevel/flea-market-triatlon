"""Файл - с клавиатурами"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from loguru import logger
from .key_text import *
from src.bot.settings.constants import *


# === ГЛАВНОЕ МЕНЮ ===

async def main_menu_kb(user_id: int = None) -> InlineKeyboardMarkup:
    """Клавиатура главного меню
    
    Args:
        user_id: ID пользователя для подсчета объявлений (опционально)
    """
    keyboard = InlineKeyboardBuilder()
    keyboard.row(
        InlineKeyboardButton(text=CATALOG_BTN, callback_data="main_menu:catalog"),
        InlineKeyboardButton(text=SEARCH_BTN, callback_data="main_menu:search")
    )
    keyboard.row(
        InlineKeyboardButton(text=CREATE_AD_BTN, callback_data="main_menu:create_ad")
    )
    
    # Формируем текст кнопки "Мои объявления" с счетчиком
    if user_id:
        from src.bot.database.methods import count_user_ads, get_user_by_tg_id
        try:
            # Получаем пользователя по tg_user_id, чтобы получить внутренний id
            user = await get_user_by_tg_id(user_id)
            if user:
                # Используем внутренний id пользователя для подсчета объявлений
                ads_count = await count_user_ads(user.id)
                my_ads_text = f"{MY_ADS_BTN} ({ads_count})"
            else:
                my_ads_text = MY_ADS_BTN
        except Exception as e:
            logger.error(f"Ошибка при подсчете объявлений пользователя {user_id}: {e}")
            my_ads_text = MY_ADS_BTN
    else:
        my_ads_text = MY_ADS_BTN
    
    keyboard.row(
        InlineKeyboardButton(text=my_ads_text, callback_data="main_menu:my_ads")
    )
    keyboard.row(
        InlineKeyboardButton(text=RULES_BTN, callback_data="main_menu:rules"),
        InlineKeyboardButton(text=SUPPORT_BTN, callback_data="main_menu:support")
    )
    return keyboard.as_markup()


def ad_type_selection_kb() -> InlineKeyboardMarkup:
    """Клавиатура выбора типа объявления"""
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text=AD_TYPE_SALE_BTN, callback_data="ad_type_selection:sale"))
    keyboard.row(InlineKeyboardButton(text=AD_TYPE_RENT_BTN, callback_data="ad_type_selection:rent"))
    keyboard.row(InlineKeyboardButton(text=BACK_BTN, callback_data="ad_type_selection:back"))
    return keyboard.as_markup()


# === СОЗДАНИЕ ОБЪЯВЛЕНИЯ ===

def cover_photo_request_kb() -> InlineKeyboardMarkup:
    """Клавиатура для запроса обложки"""
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text="◀️ Назад", callback_data="back"))
    return keyboard.as_markup()


def cover_photo_kb() -> InlineKeyboardMarkup:
    """Клавиатура для этапа добавления обложки"""
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text="Подтвердить ✅", callback_data="cover_photo_confirm"))
    keyboard.row(InlineKeyboardButton(text="◀️ Назад", callback_data="back"))
    return keyboard.as_markup()


def additional_photos_kb(photo_count: int, category: str = None) -> InlineKeyboardMarkup:
    """Клавиатура для этапа добавления остальных фото"""
    keyboard = InlineKeyboardBuilder()
    
    # Для категории "slots" достаточно только обложки, поэтому показываем кнопку "Продолжить" сразу
    # Для остальных категорий кнопка "Продолжить" только если есть хотя бы одно дополнительное фото (кроме обложки)
    if category == "slots":
        # Для "slots" показываем кнопку "Продолжить" даже если только обложка
        keyboard.row(InlineKeyboardButton(text="Продолжить⏩", callback_data="photo_done"))
    elif photo_count > 1:  # Обложка + хотя бы одно дополнительное фото
        keyboard.row(InlineKeyboardButton(text="Продолжить⏩", callback_data="photo_done"))
    
    # Кнопка "Удалить последнее изображение" если есть хотя бы одно дополнительное фото
    if photo_count > 1:
        keyboard.row(InlineKeyboardButton(text="🗑️Удалить последнее изображение", callback_data="photo_delete_last"))
    
    keyboard.row(InlineKeyboardButton(text="◀️Назад", callback_data="back"))
    
    return keyboard.as_markup()


def photo_step_kb(photo_count: int, category: str = None) -> InlineKeyboardMarkup:
    """Клавиатура для шага загрузки фото (старая версия, для совместимости)"""
    keyboard = InlineKeyboardBuilder()
    
    # Определяем минимальное количество фото для категории
    min_photos = 2  # По умолчанию 2 фото
    if category == "slots":
        min_photos = 1
    
    # кнопка "Продолжить" только если фото >= минимального количества для категории
    if photo_count >= min_photos:
        keyboard.row(InlineKeyboardButton(text=DONE_BTN, callback_data="photo_done"))
    
    if photo_count > 0:
        keyboard.row(InlineKeyboardButton(text=DELETE_LAST_BTN, callback_data="photo_delete_last"))
    
    keyboard.row(InlineKeyboardButton(text=CANCEL_BTN, callback_data="cancel"))
    
    return keyboard.as_markup()


def back_kb() -> InlineKeyboardMarkup:
    """Кнопка назад"""
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text=BACK_BTN, callback_data="back"))
    return keyboard.as_markup()


def back_and_skip_kb() -> InlineKeyboardMarkup:
    """Кнопки назад и пропустить"""
    keyboard = InlineKeyboardBuilder()
    keyboard.row(
        InlineKeyboardButton(text=SKIP_BTN, callback_data="skip"),
        InlineKeyboardButton(text=BACK_BTN, callback_data="back")
    )
    return keyboard.as_markup()


def cities_kb() -> InlineKeyboardMarkup:
    """Клавиатура выбора города (в два столбца)"""
    keyboard = InlineKeyboardBuilder()
    
    # Города в два столбца
    # Москва и СПб в конце (над кнопками "Другой город" и "Другая страна")
    # Калининград и Владивосток в начале (вместо Москвы и СПб)
    cities = [
        ("Калининград", "city:kaliningrad"),
        ("Владивосток", "city:vladivostok"),
        ("Екатеринбург", "city:ekb"),
        ("Новосибирск", "city:novosibirsk"),
        ("Казань", "city:kazan"),
        ("Нижний Новгород", "city:nn"),
        ("Самара", "city:samara"),
        ("Ростов-на-Дону", "city:rostov"),
        ("Краснодар", "city:krasnodar"),
        ("Сочи", "city:sochi"),
        ("Уфа", "city:ufa"),
        ("Челябинск", "city:chelyabinsk"),
        ("Пермь", "city:perm"),
        ("Тюмень", "city:tyumen"),
        ("Омск", "city:omsk"),
        ("Воронеж", "city:voronezh"),
        ("Красноярск", "city:krasnoyarsk"),
        ("Ижевск", "city:izhevsk"),
        ("Санкт-Петербург", "city:spb"),
        ("Москва", "city:moscow"),
    ]
    
    # Добавляем города по 2 в ряд
    for i in range(0, len(cities), 2):
        row_cities = cities[i:i+2]
        keyboard.row(*[InlineKeyboardButton(text=city[0], callback_data=city[1]) for city in row_cities])
    
    # Другой город и другая страна в один ряд
    keyboard.row(
        InlineKeyboardButton(text=OTHER_CITY_BTN, callback_data="city:other"),
        InlineKeyboardButton(text=OTHER_COUNTRY_BTN, callback_data="city:other_country")
    )
    keyboard.row(InlineKeyboardButton(text=BACK_BTN, callback_data="back"))
    
    return keyboard.as_markup()


def countries_kb() -> InlineKeyboardMarkup:
    """Клавиатура выбора страны (в два столбца)"""
    keyboard = InlineKeyboardBuilder()
    
    # Преобразуем страны в список для удобства
    countries = [(country_key, country_data) for country_key, country_data in CIS_COUNTRIES.items()]
    
    # Добавляем страны по 2 в ряд
    for i in range(0, len(countries), 2):
        row_countries = countries[i:i+2]
        keyboard.row(*[
            InlineKeyboardButton(
                text=f"{country_data['flag']} {country_data['name']}", 
                callback_data=f"country:{country_key}"
            ) for country_key, country_data in row_countries
        ])
    
    keyboard.row(InlineKeyboardButton(text=OTHER_COUNTRY_BTN, callback_data="country:other"))
    keyboard.row(InlineKeyboardButton(text=BACK_BTN, callback_data="back"))
    
    return keyboard.as_markup()


def country_cities_kb(country_key: str) -> InlineKeyboardMarkup:
    """Клавиатура выбора города для выбранной страны (в два столбца)"""
    keyboard = InlineKeyboardBuilder()
    
    # Получаем города для страны
    if country_key in CIS_COUNTRIES and 'cities' in CIS_COUNTRIES[country_key]:
        cities = CIS_COUNTRIES[country_key]['cities']
        
        # Добавляем города по 2 в ряд
        for i in range(0, len(cities), 2):
            row_cities = cities[i:i+2]
            buttons = []
            for city in row_cities:
                # Используем индекс города для callback_data, чтобы избежать проблем с спецсимволами
                city_index = cities.index(city)
                buttons.append(InlineKeyboardButton(
                    text=city,
                    callback_data=f"city_from_country:{country_key}:{city_index}"
                ))
            keyboard.row(*buttons)
    else:
        # Если города не найдены, возвращаем пустую клавиатуру
        pass
    
    keyboard.row(InlineKeyboardButton(text=BACK_BTN, callback_data="back"))
    
    return keyboard.as_markup()


def categories_kb(ad_type: str = None) -> InlineKeyboardMarkup:
    """Клавиатура выбора категории"""
    keyboard = InlineKeyboardBuilder()
    
    for cat_key, cat_name in CATEGORIES.items():
        # Для аренды исключаем категорию "slots"
        if ad_type == "Аренда" and cat_key == "slots":
            continue
        keyboard.row(InlineKeyboardButton(text=cat_name, callback_data=f"cat:{cat_key}"))
    
    keyboard.row(InlineKeyboardButton(text=BACK_BTN, callback_data="back"))
    
    return keyboard.as_markup()


def subcategories_kb(category: str) -> InlineKeyboardMarkup:
    """Клавиатура выбора подкатегории"""
    keyboard = InlineKeyboardBuilder()
    
    subcats = SUBCATEGORIES.get(category, {})
    
    # Для категории "bike" (велоспорт) показываем группы и обычные подкатегории
    if category == "bike":
        from src.bot.settings.constants import BIKE_SUBCATEGORY_GROUPS
        # Порядок: 1) Велосипеды, 2) Колёса, 3) Экипировка, 4) Запчасти, 5) Аксессуары, 6) Велочемоданы
        # Сначала группа "Велосипеды"
        if "bicycles" in BIKE_SUBCATEGORY_GROUPS:
            keyboard.row(InlineKeyboardButton(text=BIKE_SUBCATEGORY_GROUPS["bicycles"]["name"], callback_data=f"bike_group:bicycles"))
        # Затем "Колёса" (первая обычная подкатегория)
        if "wheels" in subcats:
            keyboard.row(InlineKeyboardButton(text=subcats["wheels"], callback_data=f"subcat:wheels"))
        # Затем группа "Экипировка" (3-я в списке)
        if "equipment" in BIKE_SUBCATEGORY_GROUPS:
            keyboard.row(InlineKeyboardButton(text=BIKE_SUBCATEGORY_GROUPS["equipment"]["name"], callback_data=f"bike_group:equipment"))
        # Затем остальные обычные подкатегории (Запчасти, Аксессуары, Велочемоданы)
        for subcat_key, subcat_name in subcats.items():
            if not subcat_key.endswith("_group") and subcat_key != "wheels":
                keyboard.row(InlineKeyboardButton(text=subcat_name, callback_data=f"subcat:{subcat_key}"))
    else:
        # Для остальных категорий - по одной кнопке в ряд
        for subcat_key, subcat_name in subcats.items():
            keyboard.row(InlineKeyboardButton(text=subcat_name, callback_data=f"subcat:{subcat_key}"))
    
    keyboard.row(InlineKeyboardButton(text=BACK_BTN, callback_data="back"))
    
    return keyboard.as_markup()


def bike_group_subcategories_kb(group_key: str) -> InlineKeyboardMarkup:
    """Клавиатура подкатегорий внутри группы велоспорта"""
    keyboard = InlineKeyboardBuilder()
    
    from src.bot.settings.constants import BIKE_SUBCATEGORY_GROUPS
    group_data = BIKE_SUBCATEGORY_GROUPS.get(group_key)
    
    if group_data:
        for subcat_key, subcat_name in group_data["subcategories"].items():
            keyboard.row(InlineKeyboardButton(text=subcat_name, callback_data=f"subcat:{subcat_key}"))
    
    keyboard.row(InlineKeyboardButton(text=BACK_BTN, callback_data="back"))
    
    return keyboard.as_markup()


def sizes_kb() -> InlineKeyboardMarkup:
    """Клавиатура выбора размера"""
    keyboard = InlineKeyboardBuilder()
    
    # Добавляем стандартные размеры по 3 в ряд
    for i in range(0, len(SIZES), 3):
        row_sizes = SIZES[i:i+3]
        keyboard.row(*[InlineKeyboardButton(text=size, callback_data=f"size:{size}") for size in row_sizes])
    
    keyboard.row(InlineKeyboardButton(text=INPUT_MANUALLY_BTN, callback_data="size:manual"))
    keyboard.row(InlineKeyboardButton(text=NO_SIZE_BTN, callback_data="size:none"))
    keyboard.row(InlineKeyboardButton(text=BACK_BTN, callback_data="back"))
    
    return keyboard.as_markup()


def conditions_kb() -> InlineKeyboardMarkup:
    """Клавиатура выбора состояния"""
    keyboard = InlineKeyboardBuilder()
    
    for cond_key, cond_name in CONDITIONS.items():
        keyboard.row(InlineKeyboardButton(text=cond_name, callback_data=f"cond:{cond_key}"))
    
    keyboard.row(InlineKeyboardButton(text=BACK_BTN, callback_data="back"))
    
    return keyboard.as_markup()


def ad_type_kb() -> InlineKeyboardMarkup:
    """Клавиатура выбора типа объявления"""
    keyboard = InlineKeyboardBuilder()
    
    keyboard.row(InlineKeyboardButton(text=AD_TYPE_SALE_BTN, callback_data="ad_type:sale"))
    keyboard.row(InlineKeyboardButton(text=AD_TYPE_RENT_BTN, callback_data="ad_type:rent"))
    keyboard.row(InlineKeyboardButton(text=BACK_BTN, callback_data="back"))
    
    return keyboard.as_markup()


def delivery_method_kb() -> InlineKeyboardMarkup:
    """Клавиатура выбора способа доставки"""
    keyboard = InlineKeyboardBuilder()
    
    keyboard.row(InlineKeyboardButton(text=DELIVERY_PICKUP_BTN, callback_data="delivery:pickup"))
    keyboard.row(InlineKeyboardButton(text=DELIVERY_SHIPPING_BTN, callback_data="delivery:shipping"))
    keyboard.row(InlineKeyboardButton(text="🚚 Оба варианта", callback_data="delivery:both"))
    keyboard.row(InlineKeyboardButton(text=BACK_BTN, callback_data="back"))
    
    return keyboard.as_markup()


def contact_method_kb() -> InlineKeyboardMarkup:
    """Клавиатура выбора способа связи"""
    keyboard = InlineKeyboardBuilder()
    
    keyboard.row(InlineKeyboardButton(text=CONTACT_TELEGRAM_BTN, callback_data="contact:telegram"))
    keyboard.row(InlineKeyboardButton(text=CONTACT_PHONE_BTN, callback_data="contact:phone"))
    keyboard.row(InlineKeyboardButton(text=BACK_BTN, callback_data="back"))
    
    return keyboard.as_markup()


def confirm_kb() -> InlineKeyboardMarkup:
    """Клавиатура подтверждения объявления"""
    keyboard = InlineKeyboardBuilder()
    
    keyboard.row(InlineKeyboardButton(text=SEND_TO_MODERATION_BTN, callback_data="confirm_send"))
    keyboard.row(InlineKeyboardButton(text=BACK_BTN, callback_data="back"))
    
    return keyboard.as_markup()


def main_menu_from_moderation_kb() -> InlineKeyboardMarkup:
    """Клавиатура для возврата в главное меню после отправки на модерацию"""
    keyboard = InlineKeyboardBuilder()
    
    keyboard.row(InlineKeyboardButton(text=MENU_BTN, callback_data="main_menu_from_moderation"))
    
    return keyboard.as_markup()


# === МОДЕРАЦИЯ ===

def moderation_kb(ad_id: int) -> InlineKeyboardMarkup:
    """Клавиатура модерации объявления"""
    from src.bot.keyboards.key_text import APPROVE_BTN, REJECT_BTN
    keyboard = InlineKeyboardBuilder()
    
    keyboard.row(
        InlineKeyboardButton(text=APPROVE_BTN, callback_data=f"mod_approve:{ad_id}"),
        InlineKeyboardButton(text=REJECT_BTN, callback_data=f"mod_reject:{ad_id}")
    )
    
    return keyboard.as_markup()


def moderation_edit_kb(edit_id: int) -> InlineKeyboardMarkup:
    """Клавиатура модерации редактирования (копия объявления)"""
    from src.bot.keyboards.key_text import APPROVE_BTN, REJECT_BTN
    keyboard = InlineKeyboardBuilder()
    keyboard.row(
        InlineKeyboardButton(text=APPROVE_BTN, callback_data=f"mod_approve_edit:{edit_id}"),
        InlineKeyboardButton(text=REJECT_BTN, callback_data=f"mod_reject_edit:{edit_id}")
    )
    return keyboard.as_markup()


def rejection_reasons_kb() -> InlineKeyboardMarkup:
    """Клавиатура выбора причины отклонения"""
    keyboard = InlineKeyboardBuilder()
    
    for reason_key, reason_text in REJECTION_REASONS.items():
        keyboard.row(InlineKeyboardButton(text=reason_text, callback_data=f"reject_reason:{reason_key}"))
    
    keyboard.row(InlineKeyboardButton(text=REJECTION_OTHER_BTN, callback_data="reject_reason:other"))

    # Возврат на шаг назад (к кнопкам Одобрить/Отклонить)
    keyboard.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="reject_back"))
    
    return keyboard.as_markup()


# === КАТАЛОГ И КАРТОЧКА ТОВАРА ===

def ad_in_channel_kb(ad_id: int, bot_username: str = None, unpublished: bool = False, sold: bool = False) -> InlineKeyboardMarkup:
    """Клавиатура под объявлением в канале - только кнопка 'Подробнее'
    
    unpublished: если True, кнопка "Подробнее" показывает alert (снято с публикации)
    sold: если True, кнопка "Подробнее" показывает alert (продано)
    """
    keyboard = InlineKeyboardBuilder()
    
    if unpublished:
        keyboard.row(
            InlineKeyboardButton(text="📘 Подробнее", callback_data=f"unpublished:{ad_id}")
        )
    elif sold:
        keyboard.row(
            InlineKeyboardButton(text="📘 Подробнее", callback_data=f"sold:{ad_id}")
        )
    elif bot_username:
        # Убираем @ если есть и приводим к нижнему регистру (Telegram требует lowercase)
        bot_username_clean = bot_username.lstrip('@').lower()
        keyboard.row(
            InlineKeyboardButton(text="📘 Подробнее", url=f"https://t.me/{bot_username_clean}?start=item_{ad_id}")
        )
    else:
        keyboard.row(
            InlineKeyboardButton(text="📘 Подробнее", callback_data=f"details:{ad_id}")
        )
    
    return keyboard.as_markup()


def ad_details_kb(ad_id: int, seller_id: int, first_photo_msg_id: int = 0, photos_count: int = 0) -> InlineKeyboardMarkup:
    """Клавиатура детальной карточки товара — кнопка «◀️ Назад» (callback, без ссылки в канал).
    В callback_data кодируются ID первого фото и кол-во фото, чтобы кнопка «Назад»
    могла удалить фотографии даже если state потерялся (рестарт бота и т.п.)."""
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(
        text="◀️ Назад",
        callback_data=f"close_ad:{first_photo_msg_id}:{photos_count}",
    ))
    return keyboard.as_markup()


def seller_profile_kb(seller_id: int, has_review: bool = False, total_ads: int = 0, page: int = 1) -> InlineKeyboardMarkup:
    """Клавиатура профиля продавца. Пагинация [◀️][▶️] при total_ads > 10."""
    keyboard = InlineKeyboardBuilder()
    
    # Пагинация: 10 объявлений на страницу
    if total_ads > 10:
        total_pages = (total_ads + 9) // 10
        nav_buttons = []
        if page > 1:
            nav_buttons.append(InlineKeyboardButton(text=PAGIN_PREV, callback_data=f"seller_profile_page:{seller_id}:{page - 1}"))
        if page < total_pages:
            nav_buttons.append(InlineKeyboardButton(text=PAGIN_NEXT, callback_data=f"seller_profile_page:{seller_id}:{page + 1}"))
        if nav_buttons:
            keyboard.row(*nav_buttons)
    
    keyboard.row(InlineKeyboardButton(text=BACK_BTN, callback_data="back"))
    
    return keyboard.as_markup()


def review_rating_kb(seller_id: int, include_complaint: bool = True) -> InlineKeyboardMarkup:
    """Клавиатура оценки продавца"""
    keyboard = InlineKeyboardBuilder()
    
    # Создаем кнопки в столбик, каждая с соответствующим количеством звезд (от 5 до 1)
    for i in range(5, 0, -1):
        stars = "⭐" * i
        keyboard.row(InlineKeyboardButton(text=stars, callback_data=f"rating:{seller_id}:{i}"))
    
    # Добавляем кнопку "Пожаловаться", если нужно
    if include_complaint:
        keyboard.row(InlineKeyboardButton(text="⚠️ Пожаловаться", callback_data=f"complaint:{seller_id}"))
    
    keyboard.row(InlineKeyboardButton(text=BACK_BTN, callback_data="back"))
    
    return keyboard.as_markup()


def reviews_pagination_kb(seller_id: int, page: int, total_pages: int, has_review: bool = False) -> InlineKeyboardMarkup:
    """Клавиатура пагинации отзывов"""
    keyboard = InlineKeyboardBuilder()
    
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text=PREV_BTN, callback_data=f"reviews:{seller_id}:{page-1}"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(text=NEXT_BTN, callback_data=f"reviews:{seller_id}:{page+1}"))
    
    if nav_buttons:
        keyboard.row(*nav_buttons)
    
    if has_review:
        keyboard.row(InlineKeyboardButton(text=EDIT_REVIEW_BTN, callback_data=f"leave_review:{seller_id}"))
    else:
        keyboard.row(InlineKeyboardButton(text=LEAVE_REVIEW_BTN, callback_data=f"leave_review:{seller_id}"))
    keyboard.row(InlineKeyboardButton(text=BACK_BTN, callback_data="back"))
    
    return keyboard.as_markup()


def catalog_categories_kb(categories_data: dict, total_ads: int, rent_ads_count: int = 0) -> InlineKeyboardMarkup:
    """Клавиатура категорий каталога"""
    keyboard = InlineKeyboardBuilder()
    
    # Кнопка "Все объявления"
    keyboard.row(InlineKeyboardButton(text=f"Все объявления ({total_ads})", callback_data="catalog_all"))
    
    # Кнопка "Аренда" (без количества)
    keyboard.row(InlineKeyboardButton(text="♻️ Аренда", callback_data="catalog_rent"))
    
    # Кнопки категорий
    for cat_key, (cat_name, count) in categories_data.items():
        keyboard.row(InlineKeyboardButton(text=f"{cat_name} ({count})", callback_data=f"catalog_cat:{cat_key}"))
    
    # Назад
    keyboard.row(InlineKeyboardButton(text=BACK_BTN, callback_data="main_menu"))
    
    return keyboard.as_markup()


def catalog_subcategories_kb(category: str, subcats_data: dict, total_in_cat: int) -> InlineKeyboardMarkup:
    """Клавиатура подкатегорий"""
    keyboard = InlineKeyboardBuilder()
    
    # Кнопка "Все товары" в категории
    keyboard.row(InlineKeyboardButton(text=f"Все товары ({total_in_cat})", callback_data=f"catalog_cat_all:{category}"))
    
    # Кнопки подкатегорий
    # Для категории "bike" (велоспорт) показываем группы и обычные подкатегории
    if category == "bike":
        from src.bot.settings.constants import BIKE_SUBCATEGORY_GROUPS
        # Сначала показываем группы с подсчетом товаров внутри группы
        for group_key, group_data in BIKE_SUBCATEGORY_GROUPS.items():
            # Считаем общее количество товаров в группе
            group_count = 0
            for subcat_key in group_data["subcategories"].keys():
                if subcat_key in subcats_data:
                    group_count += subcats_data[subcat_key][1]
            # Показываем группу всегда, даже если товаров нет
            keyboard.row(InlineKeyboardButton(
                text=f"{group_data['name']} ({group_count})",
                callback_data=f"catalog_bike_group:{group_key}"
            ))
        # Затем обычные подкатегории (не группы)
        for subcat_key, (subcat_name, count) in subcats_data.items():
            if not subcat_key.endswith("_group") and subcat_key not in ["bicycles_tt", "bicycles_road", "bicycles_other", "equipment_shoes", "equipment_wear", "equipment_helmets"]:
                keyboard.row(InlineKeyboardButton(text=f"{subcat_name} ({count})", callback_data=f"catalog_subcat:{category}:{subcat_key}"))
    else:
        # Для остальных категорий - по одной кнопке в ряд
        for subcat_key, (subcat_name, count) in subcats_data.items():
            keyboard.row(InlineKeyboardButton(text=f"{subcat_name} ({count})", callback_data=f"catalog_subcat:{category}:{subcat_key}"))
    
    keyboard.row(InlineKeyboardButton(text=BACK_BTN, callback_data="back_to_categories"))
    
    return keyboard.as_markup()


def catalog_bike_group_subcategories_kb(group_key: str, subcats_data: dict) -> InlineKeyboardMarkup:
    """Клавиатура подкатегорий внутри группы велоспорта для каталога"""
    keyboard = InlineKeyboardBuilder()
    
    from src.bot.settings.constants import BIKE_SUBCATEGORY_GROUPS
    group_data = BIKE_SUBCATEGORY_GROUPS.get(group_key)
    
    # Подсчитываем общее количество товаров в группе
    # subcats_data имеет формат: {subcat_key: (subcat_name, count)}
    total_in_group = 0
    if subcats_data:
        for subcat_key in subcats_data:
            if isinstance(subcats_data[subcat_key], tuple) and len(subcats_data[subcat_key]) == 2:
                _, count = subcats_data[subcat_key]
                if isinstance(count, int):
                    total_in_group += count
    
    # Добавляем кнопку "Все [название группы]" в начале
    if group_key == "bicycles":
        keyboard.row(InlineKeyboardButton(
            text=f"Все велосипеды ({total_in_group})",
            callback_data=f"catalog_bike_group_all:bicycles"
        ))
    elif group_key == "equipment":
        keyboard.row(InlineKeyboardButton(
            text=f"Вся экипировка ({total_in_group})",
            callback_data=f"catalog_bike_group_all:equipment"
        ))
    
    if group_data:
        for subcat_key, subcat_name in group_data["subcategories"].items():
            count = subcats_data.get(subcat_key, (subcat_name, 0))[1] if subcat_key in subcats_data else 0
            keyboard.row(InlineKeyboardButton(
                text=f"{subcat_name} ({count})",
                callback_data=f"catalog_subcat:bike:{subcat_key}"
            ))
    
    # Возврат к списку подкатегорий велоспорта, а не к категориям
    keyboard.row(InlineKeyboardButton(text=BACK_BTN, callback_data="catalog_cat:bike"))
    
    return keyboard.as_markup()


def catalog_pagination_kb(page: int, total_pages: int) -> InlineKeyboardMarkup:
    """Клавиатура пагинации каталога"""
    keyboard = InlineKeyboardBuilder()
    
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text=PREV_BTN, callback_data=f"catalog_page:{page-1}"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(text=NEXT_BTN, callback_data=f"catalog_page:{page+1}"))
    
    if nav_buttons:
        keyboard.row(*nav_buttons)
    
    keyboard.row(InlineKeyboardButton(text=MENU_BTN, callback_data="main_menu"))
    
    return keyboard.as_markup()


# === НАПОМИНАНИЕ / ПОДНЯТИЕ ===

def reminder_kb(ad_id: int) -> InlineKeyboardMarkup:
    """Клавиатура напоминания о поднятии объявления (старая, для совместимости)"""
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text=BOOST_AD_BTN, callback_data=f"boost:{ad_id}"))
    keyboard.row(
        InlineKeyboardButton(text=MARK_SOLD_BTN, callback_data=f"mark_sold:{ad_id}"),
        InlineKeyboardButton(text=MARK_REMOVED_BTN, callback_data=f"mark_removed:{ad_id}")
    )
    return keyboard.as_markup()


def boost_reminder_dm_kb(ad_id: int) -> InlineKeyboardMarkup:
    """Клавиатура напоминания об автоподнятии в ЛС пользователю"""
    keyboard = InlineKeyboardBuilder()
    keyboard.row(
        InlineKeyboardButton(text="🆙 Поднять", callback_data=f"boost_confirm:{ad_id}"),
        InlineKeyboardButton(text="⏸️ Снять с публикации", callback_data=f"boost_unpublish:{ad_id}")
    )
    keyboard.row(InlineKeyboardButton(text="ОК", callback_data="boost_reminder_ok"))
    return keyboard.as_markup()


def boost_info_kb(ad_id: int, boost_available: bool, boosts_left: int) -> InlineKeyboardMarkup:
    """Клавиатура экрана информации о поднятии в разделе «Мои объявления»"""
    keyboard = InlineKeyboardBuilder()
    if boost_available:
        keyboard.row(InlineKeyboardButton(
            text=f"Поднять 🟢 ({boosts_left})",
            callback_data=f"boost_execute:{ad_id}"
        ))
    else:
        keyboard.row(InlineKeyboardButton(
            text=f"Поднять 🔴 ({boosts_left})",
            callback_data=f"boost_not_ready:{ad_id}"
        ))
    keyboard.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"my_ad:{ad_id}"))
    return keyboard.as_markup()

