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
    remove_channel_boost_from_queue,
)
from src.models import AdStatus, AdPhoto
from src.bot.keyboards.keyboards import back_kb, photo_step_kb, confirm_kb, cities_kb, countries_kb, categories_kb, subcategories_kb, sizes_kb
from src.bot.keyboards.key_text import BACK_BTN, SEND_TO_MODERATION_BTN, PAGIN_PREV, PAGIN_NEXT, CONTACT_TELEGRAM_BTN, CONTACT_PHONE_BTN, MY_ADS_LIST_BTN
from src.bot.settings.constants import (
    PHOTO_FIRST_MESSAGE, PHOTO_ERROR_MESSAGE, PHOTO_MAX_ERROR, PHOTO_MIN_ERROR,
    PHONE_INPUT_MESSAGE,
    CATEGORIES, CONFIRM_MESSAGE, DEFAULT_CITIES, CIS_COUNTRIES,
    CITY_CUSTOM_MESSAGE, COUNTRY_CUSTOM_MESSAGE, SUBCATEGORIES, SIZE_REQUIRED_SUBCATEGORIES,
    SIZE_MESSAGE, SIZE_CUSTOM_MESSAGE, CATEGORY_MESSAGE, SUBCATEGORY_MESSAGE, LOCATION_MESSAGE
)
from src.bot.utils.image_utils import add_logo_watermark_to_photo
from src.bot.utils.helpers import format_phone_for_display, format_contact_for_display
from src.bot.utils.channel_utils import format_archive_caption
from src.bot.loader import bot
from src.bot.handlers.add_ad import send_to_moderation, send_edit_to_moderation
from sqlalchemy import delete
from src.bot.database.methods import async_session
from math import ceil

MY_ADS_PER_PAGE = 10


from ._common import *

async def my_ad_republish_callback(callback: types.CallbackQuery, state: FSMContext):
    """
    Возврат неактивного объявления: отправка на модерацию в чат модераторов.
    После одобрения объявление снова появится в канале.
    """
    await callback.answer()

    ad_id = int(callback.data.split(':')[1])
    ad = await get_ad_by_id(ad_id)

    if not ad:
        await callback.answer("❌ Объявление не найдено.", show_alert=True)
        return

    user = await get_user_by_tg_id(callback.from_user.id)
    if not user or ad.seller_user_id != user.id:
        await callback.answer("❌ Это не ваше объявление.", show_alert=True)
        return

    if ad.status not in ('unpublished', 'removed', 'paused'):
        await callback.answer("❌ Можно отправить на модерацию только неактивные объявления.", show_alert=True)
        return

    photos = await get_ad_photos(ad_id)
    if not photos:
        await callback.answer("❌ У объявления нет фото, отправка на модерацию невозможна.", show_alert=True)
        return

    # Собираем data для send_to_moderation из объявления
    data = {
        'title': ad.title,
        'price': ad.price,
        'city': ad.city,
        'country': ad.country or 'Россия',
        'category': ad.category,
        'subcategory': ad.subcategory or '',
        'size': ad.size or '',
        'condition': ad.condition,
        'description': ad.description or '',
        'ad_type': getattr(ad, 'ad_type', 'Продажа') or 'Продажа',
        'delivery_method': ad.delivery_method or '',
        'contact_method': getattr(ad, 'contact_method', 'telegram') or 'telegram',
        'photos': [{'file_id': p.file_id} for p in photos],
    }

    await update_ad(ad_id, status='pending', inactive_since=None)
    await send_to_moderation(ad_id, data)

    data_state = await state.get_data()
    chat_id = data_state.get('my_ad_chat_id', callback.message.chat.id)
    await delete_my_ad_info_message(state, chat_id)

    try:
        await callback.message.delete()
    except Exception:
        pass

    from src.bot.settings.constants import SENT_TO_MODERATION_MESSAGE
    await callback.message.answer(SENT_TO_MODERATION_MESSAGE, parse_mode='HTML')
    logger.info(f"Пользователь {callback.from_user.id} отправил неактивное объявление #{ad_id} на модерацию")

    from src.bot.handlers.start import send_main_menu
    await send_main_menu(callback.message, state=state)
    await state.clear()


async def my_ad_sold_confirm_callback(callback: types.CallbackQuery, state: FSMContext):
    """Подтверждение пометки объявления как проданного"""
    await callback.answer()
    
    ad_id = int(callback.data.split(':')[1])
    
    text = "💰 <b>Подтверждение</b>\n\n"
    text += "Отметить объявление как проданное?\n\n"
    text += "📌 Объявление:\n"
    text += "• В канале карточка станет «ЗАКРЫТО» (при недавней публикации пост может быть удалён)\n"
    text += "• Будет скрыто из каталога\n"
    text += "• Будет показано в вашем профиле\n"
    text += "• Редактирование будет недоступно"
    
    keyboard = InlineKeyboardBuilder()
    keyboard.row(
        InlineKeyboardButton(text="✅ Да, продано", callback_data=f"my_ad_sold_execute:{ad_id}"),
        InlineKeyboardButton(text="❌ Отмена", callback_data=f"my_ad_sold_cancel:{ad_id}")
    )
    
    # Заменяем сообщение "Выберите действие:" на подтверждение
    try:
        await callback.message.edit_text(text, parse_mode='HTML', reply_markup=keyboard.as_markup())
    except:
        # Если не удалось отредактировать (например, сообщение уже изменено), отправляем новое
        await callback.message.answer(text, parse_mode='HTML', reply_markup=keyboard.as_markup())


async def my_ad_sold_execute_callback(callback: types.CallbackQuery, state: FSMContext):
    """Выполнение пометки объявления как проданного"""
    await callback.answer()
    
    ad_id = int(callback.data.split(':')[1])
    ad = await get_ad_by_id(ad_id)
    
    if not ad:
        await callback.answer("❌ Объявление не найдено.", show_alert=True)
        return
    
    # Проверяем, что это объявление пользователя
    user = await get_user_by_tg_id(callback.from_user.id)
    if not user or ad.seller_user_id != user.id:
        await callback.answer("❌ Это не ваше объявление.", show_alert=True)
        return
    
    # Отмечаем как проданное
    await update_ad(ad_id, status='sold')
    
    # В канале: если прошло менее 48 ч — удаляем пост; иначе — формат «ЗАКРЫТО»
    from src.bot.utils.channel_utils import remove_or_archive_channel_post
    channel_deleted = await remove_or_archive_channel_post(ad, reason="продажа")
    
    # Удаляем первое сообщение с информацией об объявлении
    data = await state.get_data()
    chat_id = data.get('my_ad_chat_id', callback.message.chat.id)
    await delete_my_ad_info_message(state, chat_id)
    
    # Заменяем сообщение подтверждения на результат и главное меню
    result_text = f"✅ Объявление #{ad_id} отмечено как проданное.\n\n"
    if channel_deleted:
        result_text += "Объявление удалено из канала и скрыто из каталога."
    else:
        result_text += "Объявление скрыто из каталога. Карточка в канале показана как «ЗАКРЫТО»."
    
    from src.bot.handlers.start import send_main_menu
    
    # Заменяем сообщение подтверждения на результат
    try:
        await callback.message.edit_text(result_text, parse_mode='HTML')
    except:
        pass
    
    # Отправляем главное меню
    await send_main_menu(callback, state=state)
    
    # Удаляем сообщение с результатом после отправки главного меню
    try:
        await callback.message.delete()
    except:
        pass
    
    logger.info(f"Пользователь {callback.from_user.id} отметил объявление #{ad_id} как проданное")
    
    # Очищаем состояние
    await state.clear()


async def my_ad_unpublish_confirm_callback(callback: types.CallbackQuery, state: FSMContext):
    """Подтверждение снятия объявления с публикации"""
    await callback.answer()
    
    ad_id = int(callback.data.split(':')[1])
    
    text = "📴 <b>Подтверждение</b>\n\n"
    text += "Снять объявление с публикации?\n\n"
    text += "📌 Объявление:\n"
    text += "• В канале карточка станет «ЗАКРЫТО» (при недавней публикации пост может быть удалён)\n"
    text += "• Будет скрыто из каталога\n"
    text += "• Будет показано в вашем профиле\n"
    text += "• Редактирование и повторная публикация будут доступны"
    
    keyboard = InlineKeyboardBuilder()
    keyboard.row(
        InlineKeyboardButton(text="✅ Да, снять", callback_data=f"my_ad_unpublish_execute:{ad_id}"),
        InlineKeyboardButton(text="❌ Отмена", callback_data=f"my_ad_unpublish_cancel:{ad_id}")
    )
    
    # Заменяем сообщение "Выберите действие:" на подтверждение
    try:
        await callback.message.edit_text(text, parse_mode='HTML', reply_markup=keyboard.as_markup())
    except:
        # Если не удалось отредактировать (например, сообщение уже изменено), отправляем новое
        await callback.message.answer(text, parse_mode='HTML', reply_markup=keyboard.as_markup())


async def my_ad_unpublish_execute_callback(callback: types.CallbackQuery, state: FSMContext):
    """Выполнение снятия объявления с публикации"""
    await callback.answer()
    
    ad_id = int(callback.data.split(':')[1])
    ad = await get_ad_by_id(ad_id)
    
    if not ad:
        await callback.answer("❌ Объявление не найдено.", show_alert=True)
        return
    
    user = await get_user_by_tg_id(callback.from_user.id)
    if not user or ad.seller_user_id != user.id:
        await callback.answer("❌ Это не ваше объявление.", show_alert=True)
        return

    # Если было редактирование на модерации — удаляем копию
    await delete_edits_for_ad(ad_id)
    await remove_channel_boost_from_queue(ad_id)

    from datetime import datetime as _dt
    await update_ad(ad_id, status='unpublished', inactive_since=_dt.utcnow())

    # В канале: если прошло менее 48 ч — удаляем пост; иначе — архивный формат «ЗАКРЫТО»
    from src.bot.utils.channel_utils import remove_or_archive_channel_post
    channel_deleted = await remove_or_archive_channel_post(ad, reason="снято с публикации")

    # Удаляем первое сообщение с информацией об объявлении
    data = await state.get_data()
    chat_id = data.get('my_ad_chat_id', callback.message.chat.id)
    await delete_my_ad_info_message(state, chat_id)
    
    # Заменяем сообщение подтверждения на результат с кнопкой закрытия
    result_text = f"✅ Объявление #{ad_id} снято с публикации.\n\n"
    if channel_deleted:
        result_text += f"Объявление удалено из канала и скрыто из каталога.\n"
    else:
        result_text += f"В канале карточка показана как «ЗАКРЫТО», объявление скрыто из каталога.\n"
    result_text += f"Вы можете продолжить редактирование."

    ok_kb = InlineKeyboardBuilder()
    ok_kb.row(InlineKeyboardButton(text=MY_ADS_LIST_BTN, callback_data="back_from_ad_details"))

    # Заменяем сообщение подтверждения на результат
    try:
        await callback.message.edit_text(result_text, parse_mode='HTML', reply_markup=ok_kb.as_markup())
    except:
        await callback.message.answer(result_text, parse_mode='HTML', reply_markup=ok_kb.as_markup())
    
    logger.info(f"Пользователь {callback.from_user.id} снял объявление #{ad_id} с публикации")
    
    # Очищаем состояние
    await state.clear()


async def my_ad_unpublish_ok_callback(callback: types.CallbackQuery, state: FSMContext):
    """Старые сообщения с [ОК] после снятия — вернуться к списку объявлений."""
    from src.bot.handlers.my_ads.details import back_from_ad_details_callback
    await back_from_ad_details_callback(callback, state)


async def my_ad_sold_cancel_callback(callback: types.CallbackQuery, state: FSMContext):
    """Отмена пометки объявления как проданного - возврат к меню действий"""
    await callback.answer()
    
    ad_id = int(callback.data.split(':')[1])
    ad = await get_ad_by_id(ad_id)
    
    if not ad:
        await callback.answer("❌ Объявление не найдено.", show_alert=True)
        return
    
    # Формируем клавиатуру с кнопками действий (как в my_ad_details_callback)
    keyboard = InlineKeyboardBuilder()
    
    if ad.status == AdStatus.approved.value:
        keyboard.row(
            InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"my_ad_edit:{ad.id}"),
            InlineKeyboardButton(text="🚀 Поднять", callback_data=f"my_ad_boost:{ad.id}")
        )
    elif ad.status == AdStatus.rejected.value:
        keyboard.row(InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"my_ad_edit_rejected:{ad.id}"))
    elif ad.status in ('unpublished', 'removed', 'paused'):
        keyboard.row(InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"my_ad_edit:{ad.id}"))
        keyboard.row(InlineKeyboardButton(text=SEND_TO_MODERATION_BTN, callback_data=f"my_ad_republish:{ad.id}"))

    if ad.status == AdStatus.approved.value:
        keyboard.row(
            InlineKeyboardButton(text="📴 Снять с публикации", callback_data=f"my_ad_unpublish_confirm:{ad.id}")
        )

    keyboard.row(InlineKeyboardButton(text=BACK_BTN, callback_data="back_from_ad_details"))

    try:
        await callback.message.edit_text("Выберите действие:", reply_markup=keyboard.as_markup())
    except Exception:
        await callback.message.answer("Выберите действие:", reply_markup=keyboard.as_markup())


async def my_ad_unpublish_cancel_callback(callback: types.CallbackQuery, state: FSMContext):
    """Отмена снятия объявления с публикации - возврат к меню действий"""
    await callback.answer()

    ad_id = int(callback.data.split(':')[1])
    ad = await get_ad_by_id(ad_id)

    if not ad:
        await callback.answer("❌ Объявление не найдено.", show_alert=True)
        return

    keyboard = InlineKeyboardBuilder()

    if ad.status == AdStatus.approved.value:
        keyboard.row(
            InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"my_ad_edit:{ad.id}"),
            InlineKeyboardButton(text="🚀 Поднять", callback_data=f"my_ad_boost:{ad.id}")
        )
    elif ad.status == AdStatus.rejected.value:
        keyboard.row(InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"my_ad_edit_rejected:{ad.id}"))
    elif ad.status in ('unpublished', 'removed', 'paused'):
        keyboard.row(InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"my_ad_edit:{ad.id}"))
        keyboard.row(InlineKeyboardButton(text=SEND_TO_MODERATION_BTN, callback_data=f"my_ad_republish:{ad.id}"))

    if ad.status == AdStatus.approved.value:
        keyboard.row(
            InlineKeyboardButton(text="📴 Снять с публикации", callback_data=f"my_ad_unpublish_confirm:{ad.id}")
        )

    keyboard.row(InlineKeyboardButton(text=BACK_BTN, callback_data="back_from_ad_details"))

    try:
        await callback.message.edit_text("Выберите действие:", reply_markup=keyboard.as_markup())
    except Exception:
        await callback.message.answer("Выберите действие:", reply_markup=keyboard.as_markup())


async def my_ad_delete_callback(callback: types.CallbackQuery, state: FSMContext):
    """Удаление объявления (только для админов)"""
    await callback.answer()
    
    # Проверяем права админа
    from src.bot.settings.settings import ADMIN_IDS
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Только администраторы могут удалять объявления.", show_alert=True)
        return
    
    ad_id = int(callback.data.split(':')[1])
    ad = await get_ad_by_id(ad_id)
    
    if not ad:
        await callback.answer("❌ Объявление не найдено.", show_alert=True)
        return
    
    # Удаляем объявление (включая из канала)
    await delete_ad_with_channel(ad_id)
    
    await callback.message.answer(
        f"✅ Объявление #{ad_id} успешно удалено администратором."
    )
    logger.info(f"Администратор {callback.from_user.id} удалил объявление #{ad_id}")
    
    # Возвращаемся к списку объявлений
    try:
        await callback.message.delete()
    except:
        pass
    
    await my_ads_handler(callback, state)


async def delete_ad_with_channel(ad_id: int):
    """
    Удалить объявление и сообщение из канала (при удалении админом и при «Снять с публикации»).
    - До 48 ч с публикации: сообщение в канале удаляется.
    - От 48 ч: сообщение редактируется — подпись «ЗАКРЫТО» (как у проданного), без кнопок.
    - Объявлению присваивается статус «Снято с публикации» (unpublished), как если снял пользователь.
    """
    from src.bot.database.methods import mark_ad_removed
    from src.bot.utils.channel_utils import remove_or_archive_channel_post
    ad = await get_ad_by_id(ad_id)
    if not ad:
        await mark_ad_removed(ad_id)
        return

    await remove_or_archive_channel_post(ad, reason="снято админом")

    await mark_ad_removed(ad_id)

