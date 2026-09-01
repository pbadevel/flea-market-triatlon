"""
Админ-панель для управления ботом
"""

from aiogram import Dispatcher, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton
from loguru import logger

from datetime import datetime, timedelta
from io import BytesIO
from openpyxl import Workbook

from src.bot.database.states import AdminPanelState, PostAttachState
from src.bot.database.methods import (
    get_ad_by_id, update_ad, mark_ad_removed,
    set_moderator, get_user_by_id, is_moderator,
    count_users, count_banned, get_users_csv_rows,
    add_to_blacklist, remove_from_blacklist, is_banned, get_user_by_username, get_user_by_tg_id,
    get_details_stats_aggregated, get_contact_stats_aggregated,
    get_details_detailed_rows, get_contact_detailed_rows,
    get_total_placed_sold_removed, get_top_placed, get_top_sold, get_top_removed,
    get_top_reviews_activity,
    count_trusted_sellers, set_trusted_seller, is_trusted_seller,
)
from src.bot.settings.settings import ADMIN_IDS, CHANNEL_ID, CHANNEL_USERNAME, BOT_USERNAME
from src.bot.settings.constants import CONDITIONS, DEFAULT_CITIES
from src.bot.loader import bot
from src.bot.keyboards.keyboards import ad_in_channel_kb
from sqlalchemy import select, func
from src.bot.database.methods import async_session
from src.models import User, Ad, Review
from src.bot.middlewares.throttle_middleware import invalidate_banned_cache


# === /post_attach (пост в канал с кнопкой на бота) ===

from .post import *
from .trusted import *
from .users import *
from .stats import *
from .ads import *
from .moderators import *
from .logs import *
from .boost_settings import *
from ._common import *

def register_admin_panel_handlers(dp: Dispatcher):
    """Регистрация обработчиков админ-панели"""
    
    # Главное меню
    dp.message.register(admin_command, Command("admin"))

    # /post_attach
    dp.message.register(post_attach_command, Command("post_attach"))
    dp.message.register(post_attach_text_handler, StateFilter(PostAttachState.post_text), F.text)
    dp.message.register(post_attach_button_text_handler, StateFilter(PostAttachState.post_button_text), F.text)
    
    # Навигация
    dp.callback_query.register(admin_back, F.data == "admin:back")
    dp.callback_query.register(admin_exit, F.data == "admin:exit")

    # Роли (заглушка)
    dp.callback_query.register(admin_roles_stub, F.data == "admin:roles")
    
    # Доверенный продавец
    dp.callback_query.register(admin_trusted_menu, F.data == "admin:trusted")
    dp.callback_query.register(admin_trusted_assign_start, F.data == "admin:trusted:assign")
    dp.callback_query.register(admin_trusted_assign_confirm, F.data == "admin:trusted:assign:confirm")
    dp.callback_query.register(admin_trusted_revoke_start, F.data == "admin:trusted:revoke")
    dp.callback_query.register(admin_trusted_revoke_confirm, F.data == "admin:trusted:revoke:confirm")
    dp.callback_query.register(admin_trusted_revoke_back, F.data == "admin:trusted:revoke:back")
    dp.message.register(admin_trusted_assign_input, StateFilter(AdminPanelState.trusted_seller_assign_input), F.text)
    dp.message.register(admin_trusted_revoke_input, StateFilter(AdminPanelState.trusted_seller_revoke_input), F.text)

    # Управление пользователями
    dp.callback_query.register(admin_users_menu, F.data == "admin:users")
    dp.callback_query.register(admin_users_csv, F.data == "admin:users:csv")
    dp.callback_query.register(admin_users_ban_start, F.data == "admin:users:ban")
    dp.callback_query.register(admin_users_unban_start, F.data == "admin:users:unban")
    dp.callback_query.register(admin_users_ban_unban_confirm, F.data == "admin:users:confirm")
    dp.message.register(admin_users_ban_unban_input, StateFilter(AdminPanelState.ban_unban_input), F.text)

    # Статистика
    dp.callback_query.register(admin_stats_menu, F.data == "admin:stats")
    dp.callback_query.register(admin_stats_transitions_menu, F.data == "admin:stats:transitions")
    dp.callback_query.register(admin_stats_transitions_all, F.data == "admin:stats:trans:all")
    dp.callback_query.register(admin_stats_transitions_today, F.data == "admin:stats:trans:today")
    dp.callback_query.register(admin_stats_transitions_period_start, F.data == "admin:stats:trans:period")
    dp.callback_query.register(admin_stats_ratings, F.data == "admin:stats:ratings")
    dp.callback_query.register(admin_stats_period_ask_interval, F.data == "admin:stats:period")
    dp.callback_query.register(admin_stats_period_back, F.data == "admin:stats:period:back")
    dp.callback_query.register(admin_stats_period_back, F.data == "admin:stats:period:back")
    dp.callback_query.register(admin_stats_period_placed, F.data == "admin:stats:period:placed")
    dp.callback_query.register(admin_stats_period_sold, F.data == "admin:stats:period:sold")
    dp.callback_query.register(admin_stats_period_removed, F.data == "admin:stats:period:removed")
    dp.callback_query.register(admin_stats_period_top_placed, F.data == "admin:stats:period:top_placed")
    dp.callback_query.register(admin_stats_period_top_reviews, F.data == "admin:stats:period:top_reviews")
    dp.message.register(admin_stats_transitions_period_input, StateFilter(AdminPanelState.stats_transitions_period_input), F.text)
    dp.message.register(admin_stats_period_input, StateFilter(AdminPanelState.stats_period_input), F.text)

    # Раздел "Объявления"
    dp.callback_query.register(admin_ads_menu, F.data == "admin:ads")
    dp.callback_query.register(admin_ads_delete_start, F.data == "admin:ads:delete")
    dp.callback_query.register(admin_ads_edit_start, F.data == "admin:ads:edit")
    dp.callback_query.register(admin_ads_view_start, F.data == "admin:ads:view")
    dp.callback_query.register(admin_ads_delete_confirm, F.data.startswith("admin:ads:delete:confirm:"))
    dp.callback_query.register(admin_ads_delete_back, F.data == "admin:ads:delete:back")
    dp.callback_query.register(admin_ads_edit_city_select, F.data.startswith("admin:ads:edit:city_select:"))
    dp.callback_query.register(admin_ads_edit_contact_choice, F.data.startswith("admin:ads:edit:contact_choice:"))
    dp.callback_query.register(admin_ads_edit_field, F.data.startswith("admin:ads:edit:") & ~F.data.startswith("admin:ads:edit:back:") & ~F.data.startswith("admin:ads:edit:city_select:") & ~F.data.startswith("admin:ads:edit:contact_choice:"))
    dp.callback_query.register(admin_edit_back, F.data.startswith("admin:ads:edit:back:"))
    # Ввод для объявлений
    dp.message.register(admin_ads_delete_input, StateFilter(AdminPanelState.delete_ad_input), F.text)
    dp.message.register(admin_ads_edit_input, StateFilter(AdminPanelState.edit_ad_input), F.text)
    dp.message.register(admin_ads_view_input, StateFilter(AdminPanelState.view_ad_input), F.text)
    dp.message.register(admin_ads_edit_field_input, StateFilter(
        AdminPanelState.edit_ad_title,
        AdminPanelState.edit_ad_description,
        AdminPanelState.edit_ad_price,
        AdminPanelState.edit_ad_city
    ), F.text)
    dp.message.register(admin_ads_edit_contact_phone_input, StateFilter(AdminPanelState.edit_ad_contact_phone), F.text)
    # Раздел "Модераторы"
    dp.callback_query.register(admin_moderators_menu, F.data == "admin:moderators")
    dp.callback_query.register(admin_moderators_list, F.data == "admin:mods:list")
    dp.callback_query.register(admin_moderators_add_start, F.data == "admin:mods:add")
    dp.callback_query.register(admin_moderators_remove_start, F.data == "admin:mods:remove")
    
    # Ввод для модераторов
    dp.message.register(admin_moderators_add_input, StateFilter(AdminPanelState.add_moderator_input), F.text)
    dp.message.register(admin_moderators_remove_input, StateFilter(AdminPanelState.remove_moderator_input), F.text)
    
    # Раздел "Логи"
    dp.callback_query.register(admin_logs, F.data == "admin:logs")

    # Настройки поднятия (п.2.4)
    dp.callback_query.register(admin_boost_settings_menu, F.data == "admin:boost")
    dp.callback_query.register(admin_boost_set_field_start, F.data.startswith("admin:boost:set:"))
    dp.callback_query.register(admin_boost_toggle_test, F.data == "admin:boost:toggle_test")
    dp.message.register(admin_boost_set_field_input, StateFilter(AdminPanelState.boost_settings_input), F.text)

    # Автоподнятие — новый UI (п.2.4 доработка)
    dp.callback_query.register(admin_autoboost_menu, F.data == "admin:autoboost")
    # А) Интервалы
    dp.callback_query.register(admin_autoboost_intervals_menu, F.data == "admin:autoboost:intervals")
    dp.callback_query.register(admin_autoboost_intervals_regular, F.data == "admin:autoboost:intervals:regular")
    dp.callback_query.register(admin_autoboost_intervals_trusted, F.data == "admin:autoboost:intervals:trusted")
    dp.callback_query.register(admin_autoboost_intervals_regular_custom, F.data == "admin:autoboost:intervals:regular:custom")
    dp.callback_query.register(admin_autoboost_intervals_trusted_custom, F.data == "admin:autoboost:intervals:trusted:custom")
    dp.message.register(admin_autoboost_interval_input, StateFilter(AdminPanelState.auto_boost_interval_input), F.text)
    # Б) Кол-во
    dp.callback_query.register(admin_autoboost_counts_menu, F.data == "admin:autoboost:counts")
    dp.callback_query.register(admin_autoboost_counts_regular, F.data == "admin:autoboost:counts:regular")
    dp.callback_query.register(admin_autoboost_counts_trusted, F.data == "admin:autoboost:counts:trusted")
    dp.message.register(admin_autoboost_count_input, StateFilter(AdminPanelState.auto_boost_count_input), F.text)
