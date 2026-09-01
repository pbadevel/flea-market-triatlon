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


from .browse import *
from .details import *
from .seller import *
from .reviews import *
from .search import *
from .filter import *
from .back import *
from ._common import *

def register_catalog_handlers(dp: Dispatcher):
    """Регистрация обработчиков каталога"""
    
    # Каталог
    dp.callback_query.register(catalog_handler, F.data == "catalog")
    dp.callback_query.register(catalog_all_callback, F.data == "catalog_all")
    dp.callback_query.register(catalog_rent_callback, F.data == "catalog_rent")
    dp.callback_query.register(catalog_category_callback, F.data.startswith("catalog_cat:"))
    dp.callback_query.register(catalog_category_all_callback, F.data.startswith("catalog_cat_all:"))
    dp.callback_query.register(catalog_bike_group_callback, F.data.startswith("catalog_bike_group:"))
    dp.callback_query.register(catalog_bike_group_all_callback, F.data.startswith("catalog_bike_group_all:"))
    dp.callback_query.register(catalog_subcategory_callback, F.data.startswith("catalog_subcat:"))
    dp.callback_query.register(catalog_next_callback, F.data.startswith("cat_next:"))
    dp.callback_query.register(catalog_prev_callback, F.data.startswith("cat_prev:"))
    dp.callback_query.register(catalog_next_group_callback, F.data.startswith("cat_next_group:"))
    dp.callback_query.register(catalog_prev_group_callback, F.data.startswith("cat_prev_group:"))
    dp.callback_query.register(back_to_categories_callback, F.data == "back_to_categories")
    dp.callback_query.register(back_to_bike_group_callback, F.data == "back_to_bike_group")
    dp.callback_query.register(back_to_category_subcategories_callback, F.data == "back_to_category_subcategories")
    dp.callback_query.register(catalog_page_callback, F.data.startswith("catalog_page:"))
    
    # Детали объявления
    dp.callback_query.register(ad_details_callback, F.data.startswith("details:"))
    dp.callback_query.register(unpublished_ad_callback, F.data.startswith("unpublished:"))
    dp.callback_query.register(sold_ad_callback, F.data.startswith("sold:"))
    dp.message.register(ad_details_command, F.text.startswith("/details_"))
    
    # Связь с продавцом
    dp.callback_query.register(contact_seller_callback, F.data.startswith("contact_seller:"))
    
    # Профиль продавца и пагинация профиля
    dp.callback_query.register(seller_profile_callback, F.data.startswith("seller_profile:"))
    dp.callback_query.register(seller_profile_page_callback, F.data.startswith("seller_profile_page:"))
    
    # Отзывы
    dp.callback_query.register(reviews_callback, F.data.startswith("reviews:"))
    dp.callback_query.register(leave_review_callback, F.data.startswith("leave_review:"))
    dp.message.register(review_comment_handler, StateFilter(ReviewState.comment), F.text)
    dp.callback_query.register(review_back_callback, StateFilter(ReviewState.comment), F.data == "back")
    dp.callback_query.register(review_skip_callback, StateFilter(ReviewState.comment), F.data == "skip")
    dp.callback_query.register(review_rating_callback, F.data.startswith("rating:"))
    dp.callback_query.register(complaint_callback, F.data.startswith("complaint:"))
    
    # Товары продавца
    dp.callback_query.register(seller_ads_callback, F.data.startswith("seller_ads:"))
    
    # Обработчик "Назад" для каталога и профилей (регистрируется после обработчиков с состояниями)
    dp.callback_query.register(catalog_back_callback, F.data == "back")
    dp.callback_query.register(catalog_back_callback, F.data == "back_from_rate")
    
    # Поиск
    dp.callback_query.register(search_start_handler, F.data == "main_menu:search")
    dp.message.register(search_query_handler, StateFilter(SearchState.query), F.text)
    dp.callback_query.register(search_back_to_menu_callback, F.data == "search_back_to_menu")
    dp.callback_query.register(search_back_to_main_menu_from_input_callback, F.data == "search_back_to_main_menu")
    
    # Фильтры каталога
    dp.callback_query.register(catalog_filter_callback, F.data.startswith("catalog_filter:"))
    dp.message.register(catalog_custom_city_handler, StateFilter(SearchState.custom_city_filter), F.text)
    dp.message.register(catalog_custom_country_handler, StateFilter(SearchState.custom_country_filter), F.text)
    dp.callback_query.register(catalog_country_callback, F.data.startswith("catalog_country:"))
    dp.callback_query.register(catalog_city_from_country_callback, F.data.startswith("catalog_city_from_country:"))
    dp.callback_query.register(noop_callback, F.data == "noop")
    
    # Главное меню
    dp.callback_query.register(main_menu_callback, F.data == "main_menu")
    
    # Закрыть детали объявления
    dp.callback_query.register(close_ad_details_callback, F.data.startswith("close_ad:"))
