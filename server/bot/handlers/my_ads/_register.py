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


from .list import *
from .details import *
from .edit_menu import *
from .edit_price import *
from .edit_fields import *
from .edit_city import *
from .edit_category import *
from .edit_confirm import *
from .edit_photos import *
from .status import *
from ._common import *


# Обработчики поднятия — см. handlers/my_ads_boost.py
from src.bot.handlers.my_ads_boost import (
    my_ad_boost_callback,
    my_ad_boost_not_ready_callback,
    my_ad_boost_execute_callback,
    boost_execute_main_menu_callback,
    boost_queue_to_my_ads_callback,
    boost_confirm_from_dm_callback,
    boost_unpublish_from_dm_callback,
    boost_reminder_ok_callback,
    boost_pause_auto_ok_callback,
    boost_unpublish_ok_callback,
)

def register_my_ads_handlers(dp: Dispatcher):
    """Регистрация обработчиков 'Мои объявления'"""
    dp.callback_query.register(my_ads_handler, F.data == "main_menu:my_ads")
    dp.callback_query.register(my_ads_page_callback, F.data.startswith("my_ads_page:"))
    dp.callback_query.register(back_from_ad_details_callback, F.data == "back_from_ad_details")
    dp.callback_query.register(my_ad_details_callback, F.data.startswith("my_ad:"))
    dp.callback_query.register(my_ad_edit_callback, F.data.startswith("my_ad_edit:"))
    dp.callback_query.register(my_ad_edit_rejected_callback, F.data.startswith("my_ad_edit_rejected:"))
    
    # Новые обработчики для Продано и Снять с публикации
    dp.callback_query.register(my_ad_sold_confirm_callback, F.data.startswith("my_ad_sold_confirm:"))
    dp.callback_query.register(my_ad_sold_execute_callback, F.data.startswith("my_ad_sold_execute:"))
    dp.callback_query.register(my_ad_sold_cancel_callback, F.data.startswith("my_ad_sold_cancel:"))
    dp.callback_query.register(my_ad_unpublish_confirm_callback, F.data.startswith("my_ad_unpublish_confirm:"))
    dp.callback_query.register(my_ad_unpublish_execute_callback, F.data.startswith("my_ad_unpublish_execute:"))
    dp.callback_query.register(my_ad_unpublish_cancel_callback, F.data.startswith("my_ad_unpublish_cancel:"))
    dp.callback_query.register(my_ad_unpublish_ok_callback, F.data.startswith("my_ad_unpublish_ok:"))
    dp.callback_query.register(my_ad_republish_callback, F.data.startswith("my_ad_republish:"))
    
    dp.callback_query.register(my_ad_delete_callback, F.data.startswith("my_ad_delete:"))
    dp.callback_query.register(my_ad_edit_price_callback, F.data.startswith("my_ad_edit_price:"))
    dp.callback_query.register(my_ads_price_main_menu_callback, F.data == "my_ads_price_main_menu")
    dp.callback_query.register(my_ad_edit_other_callback, F.data.startswith("my_ad_edit_other:"))
    dp.callback_query.register(my_ad_edit_field_callback, F.data.startswith("my_ad_edit_field:"))
    dp.callback_query.register(my_ad_edit_contact_callback, F.data.startswith("my_ad_edit_contact:"))
    
    dp.message.register(my_ad_edit_price_handler, StateFilter(MyAdsState.edit_price), F.text)
    dp.message.register(my_ad_edit_field_handler, StateFilter(MyAdsState.edit_title), F.text)
    dp.message.register(my_ad_edit_field_handler, StateFilter(MyAdsState.edit_description), F.text)
    dp.message.register(my_ad_edit_field_handler, StateFilter(MyAdsState.edit_city), F.text)
    dp.message.register(my_ad_edit_contact_phone_handler, StateFilter(MyAdsState.edit_contact_phone), F.text)
    
    # Редактирование фото - двухэтапный процесс
    # Этап 1: Редактирование обложки
    dp.message.register(my_ad_edit_cover_photo_handler, StateFilter(MyAdsState.edit_cover_photo), F.photo)
    dp.callback_query.register(my_ad_edit_cover_photo_confirm_callback, StateFilter(MyAdsState.edit_cover_photo), F.data == "cover_photo_confirm")
    dp.callback_query.register(my_ad_edit_cover_photo_retry_callback, StateFilter(MyAdsState.edit_cover_photo), F.data == "cover_photo_retry")
    dp.callback_query.register(my_ad_edit_cover_photo_back_callback, StateFilter(MyAdsState.edit_cover_photo), F.data == "back")
    
    # Этап 2: Редактирование дополнительных фото
    dp.message.register(my_ad_edit_additional_photos_handler, StateFilter(MyAdsState.edit_additional_photos), F.photo)
    dp.callback_query.register(my_ad_edit_additional_photos_done_callback, StateFilter(MyAdsState.edit_additional_photos), F.data == "photo_done")
    dp.callback_query.register(my_ad_edit_additional_photos_delete_last_callback, StateFilter(MyAdsState.edit_additional_photos), F.data == "photo_delete_last")
    dp.callback_query.register(my_ad_edit_additional_photos_back_callback, StateFilter(MyAdsState.edit_additional_photos), F.data == "back")
    
    dp.callback_query.register(my_ad_confirm_edit_callback, F.data.startswith("my_ad_confirm_edit:"))
    dp.callback_query.register(back_after_moderation_callback, F.data == "back_after_moderation")
    
    # Редактирование города (кнопки выбора)
    dp.callback_query.register(my_ad_edit_city_callback, StateFilter(MyAdsState.edit_city_select), F.data.startswith("city:"))
    dp.callback_query.register(my_ad_edit_country_callback, StateFilter(MyAdsState.edit_city_select), F.data.startswith("country:"))
    dp.callback_query.register(my_ad_edit_city_from_country_callback, StateFilter(MyAdsState.edit_city_after_country), F.data.startswith("city_from_country:"))
    dp.message.register(my_ad_edit_city_custom_handler, StateFilter(MyAdsState.edit_city_custom), F.text)
    # my_ad_edit_country_custom_handler используется для ввода страны, которая сейчас не нужна
    dp.message.register(my_ad_edit_city_after_country_handler, StateFilter(MyAdsState.edit_city_after_country), F.text)
    
    # Обработчик "Назад" для редактирования города
    dp.callback_query.register(my_ad_edit_city_back_callback, StateFilter(MyAdsState.edit_city_select), F.data == "back")
    dp.callback_query.register(my_ad_edit_city_back_callback, StateFilter(MyAdsState.edit_city_custom), F.data == "back")
    dp.callback_query.register(my_ad_edit_city_back_callback, StateFilter(MyAdsState.edit_city_after_country), F.data == "back")
    
    # Редактирование категории
    dp.callback_query.register(my_ad_edit_category_callback, StateFilter(MyAdsState.edit_category), F.data.startswith("cat:"))
    dp.callback_query.register(my_ad_edit_bike_group_callback, StateFilter(MyAdsState.edit_subcategory), F.data.startswith("bike_group:"))
    dp.callback_query.register(my_ad_edit_subcategory_callback, StateFilter(MyAdsState.edit_subcategory), F.data.startswith("subcat:"))
    dp.callback_query.register(my_ad_edit_category_back_callback, StateFilter(MyAdsState.edit_category), F.data == "back")
    dp.callback_query.register(my_ad_edit_category_back_callback, StateFilter(MyAdsState.edit_subcategory), F.data == "back")
    
    # Редактирование размера
    dp.callback_query.register(my_ad_edit_size_callback, StateFilter(MyAdsState.edit_size), F.data.startswith("size:"))
    dp.message.register(my_ad_edit_size_manual_handler, StateFilter(MyAdsState.edit_size_manual), F.text)
    dp.callback_query.register(my_ad_edit_size_back_callback, StateFilter(MyAdsState.edit_size), F.data == "back")
    dp.callback_query.register(my_ad_edit_size_back_callback, StateFilter(MyAdsState.edit_size_manual), F.data == "back")

    # === ПОДНЯТИЕ (BOOST) ===
    dp.callback_query.register(my_ad_boost_callback, F.data.startswith("my_ad_boost:"))
    dp.callback_query.register(my_ad_boost_not_ready_callback, F.data.startswith("boost_not_ready:"))
    dp.callback_query.register(my_ad_boost_execute_callback, F.data.startswith("boost_execute:"))
    dp.callback_query.register(boost_execute_main_menu_callback, F.data == "boost_execute_main_menu")
    dp.callback_query.register(boost_queue_to_my_ads_callback, F.data == "boost_queue_to_my_ads")
    # Из ЛС-напоминания
    dp.callback_query.register(boost_confirm_from_dm_callback, F.data.startswith("boost_confirm:"))
    dp.callback_query.register(boost_unpublish_from_dm_callback, F.data.startswith("boost_unpublish:"))
    dp.callback_query.register(boost_reminder_ok_callback, F.data == "boost_reminder_ok")
    dp.callback_query.register(boost_pause_auto_ok_callback, F.data.startswith("boost_pause_auto_ok:"))
    dp.callback_query.register(boost_unpublish_ok_callback, F.data.startswith("boost_unpublish_ok:"))
