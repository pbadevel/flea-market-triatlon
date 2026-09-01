"""
Обработчики для раздела "Мои объявления"
"""

from aiogram import Dispatcher, types, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton, FSInputFile
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


async def _show_my_ads_page(callback_or_msg, ads: list, page: int = 0, edit: bool = True, state: FSMContext = None):
    """Показать страницу списка 'Мои объявления' с пагинацией"""
    target = callback_or_msg.message if hasattr(callback_or_msg, 'message') else callback_or_msg
    pending_ads = [ad for ad in ads if ad.status == AdStatus.pending.value]
    approved_ads = [ad for ad in ads if ad.status == AdStatus.approved.value]
    rejected_ads = [ad for ad in ads if ad.status == AdStatus.rejected.value]
    sold_ads = [ad for ad in ads if ad.status == AdStatus.sold.value or ad.status == 'sold']
    unpublished_ads = [ad for ad in ads if ad.status in ('unpublished', 'removed', 'paused')]

    text = "📋 <b>Мои объявления</b>\n\n"
    text += f"✅ Активных: {len(approved_ads)}\n"
    text += f"📴 Неактивных: {len(unpublished_ads)}\n"
    if rejected_ads:
        text += f"❌ Отклонено: {len(rejected_ads)}\n"
    text += "\nВыберите объявление для просмотра или редактирования:"

    total_pages = ceil(len(ads) / MY_ADS_PER_PAGE) if ads else 1
    start_idx = page * MY_ADS_PER_PAGE
    end_idx = start_idx + MY_ADS_PER_PAGE
    page_ads = ads[start_idx:end_idx]

    keyboard = InlineKeyboardBuilder()
    for ad in page_ads:
        status_emoji = {
            AdStatus.pending.value: "⏳",
            AdStatus.approved.value: "✅",
            AdStatus.rejected.value: "❌",
            AdStatus.sold.value: "💰",
            'sold': "💰",
            'unpublished': "📴",
            'removed': "📴",  # старые записи в БД
            'paused': "⏸️",
        }
        emoji = status_emoji.get(ad.status, "📦")
        suffix = ""
        if (ad.status == AdStatus.approved.value or ad.status == "approved") and await exists_edit_for_ad(ad.id):
            suffix = " (ред. на мод.)"
        label = f"{emoji} #{ad.id} - {ad.title[:30]}{'...' if len(ad.title) > 30 else ''}{suffix}"
        keyboard.row(InlineKeyboardButton(text=label, callback_data=f"my_ad:{ad.id}"))

    if total_pages > 1:
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton(text=PAGIN_PREV, callback_data=f"my_ads_page:{page-1}"))
        if page < total_pages - 1:
            nav_buttons.append(InlineKeyboardButton(text=PAGIN_NEXT, callback_data=f"my_ads_page:{page+1}"))
        if nav_buttons:
            keyboard.row(*nav_buttons)
    keyboard.row(InlineKeyboardButton(text=BACK_BTN, callback_data="back_to_menu"))

    try:
        if edit:
            await target.edit_text(text, parse_mode='HTML', reply_markup=keyboard.as_markup())
        else:
            await target.answer(text, parse_mode='HTML', reply_markup=keyboard.as_markup())
    except Exception:
        if edit:
            await target.answer(text, parse_mode='HTML', reply_markup=keyboard.as_markup())
        else:
            await target.answer(text, parse_mode='HTML', reply_markup=keyboard.as_markup())


def needs_size(category: str, subcategory: str) -> bool:
    """Проверяет, нужен ли размер для данной категории и подкатегории"""
    # Для категорий "swim", "bike" и "run" размер обязателен всегда
    if category in ['swim', 'bike', 'run']:
        return True
    
    if not subcategory:
        return False
    
    # Для остальных категорий проверяем по списку подкатегорий
    return subcategory in SIZE_REQUIRED_SUBCATEGORIES

async def delete_my_ad_info_message(state: FSMContext, chat_id: int):
    """Удалить сообщение(я) с информацией об объявлении.

    Объявление с несколькими фото отправляется медиа-группой, а Telegram
    присылает каждое фото отдельным сообщением. Поэтому удаляем ВСЕ сообщения
    группы, а не только первое (иначе часть фото остаётся в чате)."""
    data = await state.get_data()

    # Все ID сообщений группы (новый формат). Для обратной совместимости
    # добавляем и одиночный my_ad_info_msg_id, если список пуст.
    msg_ids = list(data.get('my_ad_info_msg_ids') or [])
    single_id = data.get('my_ad_info_msg_id')
    if single_id and single_id not in msg_ids:
        msg_ids.append(single_id)

    for msg_id in msg_ids:
        try:
            await bot.delete_message(chat_id=chat_id, message_id=msg_id)
        except Exception:
            pass

    if msg_ids:
        await state.update_data(my_ad_info_msg_id=None, my_ad_info_msg_ids=[])


def _build_edit_other_menu(ad_id: int, ad, edited_fields: list = None) -> tuple:
    """Собрать текст и клавиатуру меню «Редактирование других параметров». edited_fields — список изменённых полей для блока «Изменено»."""
    text = f"📝 <b>Редактирование других параметров</b>\n\n"
    if edited_fields:
        field_names = {
            'title': 'Название', 'description': 'Описание', 'category': 'Категория',
            'size': 'Размер', 'city': 'Город', 'contact': 'Контакт', 'photos': 'Фото'
        }
        text += "✏️ <b>Изменено:</b>\n"
        for field in edited_fields:
            text += f"  • {field_names.get(field, field)}\n"
        text += "\n"
    text += "Выберите, что хотите изменить:\n\n"
    text += "⚠️ <b>Внимание:</b> Изменения будут отправлены на модерацию."
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text="📝 Название", callback_data=f"my_ad_edit_field:title:{ad_id}"))
    keyboard.row(InlineKeyboardButton(text="📄 Описание", callback_data=f"my_ad_edit_field:description:{ad_id}"))
    if needs_size(ad.category, ad.subcategory):
        keyboard.row(InlineKeyboardButton(text="📏 Размер", callback_data=f"my_ad_edit_field:size:{ad_id}"))
    keyboard.row(InlineKeyboardButton(text="📍 Город", callback_data=f"my_ad_edit_field:city:{ad_id}"))
    keyboard.row(InlineKeyboardButton(text="📞 Контакт", callback_data=f"my_ad_edit_field:contact:{ad_id}"))
    keyboard.row(InlineKeyboardButton(text="📸 Изменить фото", callback_data=f"my_ad_edit_field:photos:{ad_id}"))
    keyboard.row(InlineKeyboardButton(text=BACK_BTN, callback_data=f"my_ad_edit:{ad_id}"))
    return text, keyboard.as_markup()


async def update_channel_message(ad_id: int, ad, price_change: bool = False):
    """Обновить сообщение объявления в канале."""
    from src.bot.settings.settings import CHANNEL_ID, CHANNEL_USERNAME, BOT_USERNAME
    from src.bot.keyboards.keyboards import ad_in_channel_kb
    from src.bot.utils.channel_utils import format_active_caption, format_price_change_caption

    if not ad.channel_message_id:
        return

    seller = await get_user_by_id(ad.seller_user_id)
    is_trusted = getattr(seller, 'is_trusted_seller', False) if seller else False

    if price_change:
        caption = format_price_change_caption(ad, is_trusted)
    else:
        caption = format_active_caption(ad, is_trusted)

    channel_target = f"@{CHANNEL_USERNAME}" if CHANNEL_USERNAME else CHANNEL_ID

    try:
        await bot.edit_message_caption(
            chat_id=channel_target,
            message_id=ad.channel_message_id,
            caption=caption,
            parse_mode='HTML',
            reply_markup=ad_in_channel_kb(ad_id, BOT_USERNAME)
        )
        logger.info(f"Сообщение объявления #{ad_id} в канале обновлено")
    except Exception as e:
        logger.error(f"Ошибка обновления сообщения в канале для объявления #{ad_id}: {e}")


async def return_to_edit_menu(message_or_callback, state: FSMContext, ad_id: int = None):
    """Вернуться в меню редактирования после изменения поля"""
    # Получаем ad_id из state, если не передан
    if not ad_id:
        data = await state.get_data()
        ad_id = data.get('editing_ad_id')
    
    if not ad_id:
        if hasattr(message_or_callback, 'answer'):
            await message_or_callback.answer("❌ Ошибка: объявление не найдено.")
        await state.clear()
        return
    
    # Получаем объявление
    ad = await get_ad_by_id(ad_id)
    if not ad:
        if hasattr(message_or_callback, 'answer'):
            await message_or_callback.answer("❌ Объявление не найдено.")
        await state.clear()
        return
    
    # Определяем, является ли это отклоненным объявлением
    is_rejected = ad.status == AdStatus.rejected.value
    
    # Возвращаемся в меню редактирования
    await state.set_state(MyAdsState.edit_other)
    
    # Получаем список измененных полей
    data = await state.get_data()
    edited_fields = data.get('edited_fields', [])
    
    if is_rejected:
        text = f"📝 <b>Редактирование отклоненного объявления #{ad.id}</b>\n\n"
    else:
        text = f"📝 <b>Редактирование других параметров</b>\n\n"
    
    # Показываем список измененных полей
    if edited_fields:
        field_names = {
            'title': 'Название',
            'description': 'Описание',
            'category': 'Категория',
            'size': 'Размер',
            'city': 'Город',
            'contact': 'Контакт',
            'photos': 'Фото'
        }
        text += "✏️ <b>Изменено:</b>\n"
        for field in edited_fields:
            field_name = field_names.get(field, field)
            text += f"  • {field_name}\n"
        text += "\n"
    
    text += "Выберите, что хотите изменить:\n\n"
    text += "⚠️ <b>Внимание:</b> Изменения будут отправлены на модерацию."
    
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(
        text="📝 Название",
        callback_data=f"my_ad_edit_field:title:{ad_id}"
    ))
    keyboard.row(InlineKeyboardButton(
        text="📄 Описание",
        callback_data=f"my_ad_edit_field:description:{ad_id}"
    ))
    # Показываем кнопку размера только если размер требуется для данной подкатегории
    if needs_size(ad.category, ad.subcategory):
        keyboard.row(InlineKeyboardButton(
            text="📏 Размер",
            callback_data=f"my_ad_edit_field:size:{ad_id}"
        ))
    keyboard.row(InlineKeyboardButton(
        text="📍 Город",
        callback_data=f"my_ad_edit_field:city:{ad_id}"
    ))
    keyboard.row(InlineKeyboardButton(
        text="📞 Контакт",
        callback_data=f"my_ad_edit_field:contact:{ad_id}"
    ))
    keyboard.row(InlineKeyboardButton(
        text="📸 Изменить фото",
        callback_data=f"my_ad_edit_field:photos:{ad_id}"
    ))
    
    # Показываем кнопку "Отправить на модерацию" только если есть изменения
    if edited_fields:
        keyboard.row(InlineKeyboardButton(
            text=SEND_TO_MODERATION_BTN,
            callback_data=f"my_ad_confirm_edit:{ad_id}"
        ))
    
    if is_rejected:
        keyboard.row(InlineKeyboardButton(text=BACK_BTN, callback_data=f"my_ad:{ad_id}"))
    else:
        keyboard.row(InlineKeyboardButton(text=BACK_BTN, callback_data=f"my_ad_edit:{ad_id}"))
    
    # Редактируем сообщение в зависимости от типа объекта
    if isinstance(message_or_callback, types.Message):
        # Для Message нужно найти последнее сообщение с клавиатурой
        data = await state.get_data()
        last_msg_id = data.get('last_msg_with_keyboard')
        if last_msg_id:
            try:
                from src.bot.loader import bot
                await bot.edit_message_text(
                    chat_id=message_or_callback.chat.id,
                    message_id=last_msg_id,
                    text=text,
                    parse_mode='HTML',
                    reply_markup=keyboard.as_markup()
                )
                await state.update_data(last_msg_with_keyboard=last_msg_id)
                return
            except:
                pass
        # Если не удалось отредактировать, отправляем новое
        msg = await message_or_callback.answer(text, parse_mode='HTML', reply_markup=keyboard.as_markup())
        await state.update_data(last_msg_with_keyboard=msg.message_id)
    else:
        # Для CallbackQuery редактируем текущее сообщение
        try:
            await message_or_callback.message.edit_text(text, parse_mode='HTML', reply_markup=keyboard.as_markup())
            await state.update_data(last_msg_with_keyboard=message_or_callback.message.message_id)
        except:
            msg = await message_or_callback.message.answer(text, parse_mode='HTML', reply_markup=keyboard.as_markup())
            await state.update_data(last_msg_with_keyboard=msg.message_id)


async def show_edit_preview(message: types.Message, state: FSMContext, edited_field: str):
    """Показать предпросмотр после редактирования"""
    data = await state.get_data()
    preview_data = data.get('preview_data')
    ad_id = data.get('editing_ad_id')
    
    if not preview_data or not ad_id:
        await message.answer("❌ Ошибка: данные не найдены.")
        await state.clear()
        return
    
    # Формируем текст предпросмотра
    location = preview_data.get('city', 'Не указан')
    if preview_data.get('country'):
        location = f"{preview_data.get('city', 'Не указан')}, {preview_data['country']}"
    
    field_names = {
        'title': 'название',
        'description': 'описание',
        'city': 'город',
        'contact': 'Контакт',
        'photos': 'фото',
        'category': 'категория',
        'size': 'размер'
    }
    
    preview_text = f"👀 <b>Предпросмотр изменений</b>\n\n"
    preview_text += f"✏️ Изменено: <b>{field_names.get(edited_field, edited_field)}</b>\n\n"
    preview_text += f"<b>{preview_data['title']}</b>\n\n"
    
    # Категория и подкатегория
    category_name = CATEGORIES.get(preview_data.get('category', ''), preview_data.get('category', 'Не указано'))
    subcategory_name = ''
    if preview_data.get('category') and preview_data.get('subcategory'):
        subcats = SUBCATEGORIES.get(preview_data['category'], {})
        subcategory_name = subcats.get(preview_data['subcategory'], preview_data['subcategory'])
    
    if subcategory_name:
        preview_text += f"📦 Категория: {category_name} → {subcategory_name}\n"
    else:
        preview_text += f"📦 Категория: {category_name}\n"
    
    preview_text += f"♻️ Состояние: {CONDITIONS.get(preview_data.get('condition', ''), preview_data.get('condition', 'Не указано'))}\n"
    
    if preview_data.get('size'):
        preview_text += f"📏 Размер: {preview_data['size']}\n"
    
    if preview_data.get('description'):
        preview_text += f"\n📝 <b>Описание:</b>\n<blockquote>{preview_data['description']}</blockquote>\n"
    
    preview_text += f"\n💰 Цена: {preview_data['price']} ₽\n"
    ad_type_text = preview_data.get('ad_type', 'Продажа')
    preview_text += f"📋 Тип: {ad_type_text}\n"
    preview_text += f"📍 Местоположение: {location}\n"
    
    delivery_method = preview_data.get('delivery_method', 'Не указан')
    preview_text += f"🚚 Доставка: {delivery_method}\n"
    
    # Отправляем первое фото с превью
    photos = preview_data.get('photos', [])
    if photos:
        photo_union = photos[0].file_id
        
        if (not photos[0].file_id) and photos[0].storage_path:
            photo_union = FSInputFile(photos[0].storage_path)

        await message.answer_photo(
            photo=photo_union,
            caption=preview_text,
            parse_mode='HTML'
        )
    else:
        await message.answer(
            preview_text,
            parse_mode='HTML'
        )
    
    # Отправляем кнопку подтверждения
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(
        text=SEND_TO_MODERATION_BTN,
        callback_data=f"my_ad_confirm_edit:{ad_id}"
    ))
    keyboard.row(InlineKeyboardButton(
        text=BACK_BTN,
        callback_data=f"my_ad_edit:{ad_id}"
    ))
    
    msg = await message.answer(
        CONFIRM_MESSAGE,
        reply_markup=keyboard.as_markup()
    )
    await state.update_data(confirm_edit_msg_id=msg.message_id)


