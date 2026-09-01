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

async def seller_profile_callback(callback: types.CallbackQuery, state: FSMContext):
    """Показать профиль продавца"""
    await callback.answer()
    
    # деактивируем кнопки
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except:
        pass
    
    seller_id = int(callback.data.split(':')[1])
    
    # Пытаемся найти ad_id из предыдущего сообщения (если пришли из деталей объявления)
    # Ищем в состоянии или в тексте предыдущего сообщения
    data = await state.get_data()
    ad_id = data.get('last_viewed_ad_id')
    
    # Сохраняем seller_id и ad_id в состоянии для последующего возврата
    await state.update_data(last_viewed_seller_id=seller_id, last_viewed_ad_id=ad_id)
    await show_seller_profile(callback.message, seller_id, ad_id, from_user=callback.from_user, state=state)


async def show_seller_profile(message: types.Message, seller_id: int, ad_id: int = None, page: int = 1, edit: bool = False, from_user=None, state: FSMContext = None):
    """Показать профиль продавца (пагинация по 10 объявлений на страницу).
    from_user: при вызове с callback.message передавать callback.from_user, иначе в лог «Профиль и контакты» попадёт бот.

    Args:
        message: Сообщение для ответа
        seller_id: ID продавца
        ad_id: ID объявления, с которого пришли (для определения типа контакта)
        page: Номер страницы (1-based)
        edit: Если True — редактировать сообщение вместо отправки нового
    """
    viewer = from_user if from_user is not None else getattr(message, "from_user", None)
    seller = await get_user_by_id(seller_id)
    
    if not seller:
        await message.answer("❌ Продавец не найден.")
        return
    
    # Фиксируем просмотр профиля в БД (для статистики в админке). viewer — кто смотрит; при callback.message это callback.from_user
    if viewer and ad_id:
        buyer = await get_user_by_tg_id(viewer.id)
        if not buyer:
            buyer = await create_or_update_user(message, from_user=viewer)
        if buyer:
            await log_contact_request(buyer.id, seller_id, ad_id)
    
    # Проверяем, есть ли уже отзыв от текущего пользователя (viewer — кто смотрит профиль)
    has_review = False
    if viewer:
        buyer = await get_user_by_tg_id(viewer.id)
        if buyer and buyer.id != seller_id:
            existing_review = await get_user_review_by_reviewer(seller_id, buyer.id)
            has_review = existing_review is not None
    
    # Получаем статистику
    avg_rating = await get_user_average_rating(seller_id)
    reviews_count = await count_user_reviews(seller_id)
    approved_ads = await get_user_ads(seller_id, status='approved')
    sold_ads = await get_user_ads(seller_id, status='sold')
    # Сортируем каждую группу по дате создания (новые сначала), активные идут первыми
    approved_ads.sort(key=lambda x: x.created_at, reverse=True)
    sold_ads.sort(key=lambda x: x.created_at, reverse=True)
    all_ads = approved_ads + sold_ads
    
    # Получаем имя продавца - показываем только first_name
    display_name = seller.first_name or "Пользователь"
    
    # Формируем контакт для связи
    # Используем contact_method конкретного объявления, если ad_id передан
    contact_info = ""
    specific_ad = None
    if ad_id:
        # Ищем конкретное объявление и используем его contact_method
        specific_ad = await get_ad_by_id(ad_id)
    
    if specific_ad and specific_ad.contact_method:
        contact_value = specific_ad.contact_method
        # Определяем тип контакта по значению
        if contact_value.replace('+', '').replace(' ', '').isdigit():
            phone_display = format_phone_for_display(contact_value)
            contact_info = f"контакт для связи: {phone_display}"
        elif contact_value.startswith('@'):
            # Это Telegram username
            contact_info = f"контакт для связи: {contact_value}"
        elif contact_value.startswith('tg://'):
            # Это ссылка на Telegram профиль
            contact_info = f"контакт для связи: <a href=\"{contact_value}\">Связаться с продавцом</a>"
        elif contact_value == 'phone' and seller.phone:
            phone_display = format_phone_for_display(seller.phone)
            contact_info = f"контакт для связи: {phone_display}"
        else:
            # Обратная совместимость: старый формат или по умолчанию
            if seller.username:
                contact_info = f"контакт для связи: @{seller.username}"
            else:
                contact_link = f"tg://user?id={seller.tg_user_id}"
                contact_info = f"контакт для связи: <a href=\"{contact_link}\">Связаться с продавцом</a>"
    else:
        # Обратная совместимость: если нет ad_id или contact_method
        # Используем контакт из профиля продавца
        if seller.phone:
            phone_display = format_phone_for_display(seller.phone)
            contact_info = f"контакт для связи: {phone_display}"
        elif seller.username:
            contact_info = f"контакт для связи: @{seller.username}"
        else:
            # Создаем ссылку на Telegram
            contact_link = f"tg://user?id={seller.tg_user_id}"
            contact_info = f"контакт для связи: <a href=\"{contact_link}\">Связаться с продавцом</a>"
    
    # Формируем ссылку на рейтинг
    from src.bot.settings.settings import BOT_USERNAME
    if BOT_USERNAME:
        rating_link = f"https://t.me/{BOT_USERNAME}?start=rate_seller_{seller_id}"
    else:
        rating_link = f"/start rate_seller_{seller_id}"
    
    rating_display = "нет оценок"
    if reviews_count > 0:
        rating_display = f"{avg_rating}/5"
    rating_count_text = f" • {reviews_count} оц." if reviews_count > 0 else ""

    # Формируем текст профиля
    text = f"<b>ПРОФИЛЬ ПРОДАВЦА</b>\n"
    text += f"👤 {display_name}\n"
    if getattr(seller, 'is_trusted_seller', False):
        text += "✅ Доверенный продавец\n"
    text += f"{contact_info}\n\n"
    # Рейтинг со счётчиком оценок
    text += f"⭐ <a href=\"{rating_link}\">Рейтинг</a> ({rating_display}){rating_count_text}\n"
    # Счётчики объявлений
    text += f"📦 Активных: {len(approved_ads)} | Снято: {len(sold_ads)}\n\n"

    total_ads = len(all_ads)
    per_page = 10
    total_pages = (total_ads + per_page - 1) // per_page if total_ads else 1
    page = max(1, min(page, total_pages))
    start_idx = (page - 1) * per_page
    page_ads = all_ads[start_idx:start_idx + per_page]

    # Формируем список объявлений с разделителем между активными и проданными
    approved_count = len(approved_ads)
    if total_ads > 0:
        text += f"📦 Товары продавца:\n"
    shown_sold_header = False
    for i, ad in enumerate(page_ads, start=start_idx + 1):
        # Показываем разделитель перед первым проданным объявлением
        global_idx = start_idx + (i - start_idx - 1)
        if not shown_sold_header and (start_idx + (i - start_idx - 1)) >= approved_count and sold_ads:
            text += "\n<b>— Снятые товары —</b>\n"
            shown_sold_header = True
        size_text = f" ({ad.size})" if ad.size else ""
        from src.bot.settings.settings import BOT_USERNAME
        # _p = из профиля продавца, чтобы в карточке «Назад» была кнопка, а не ссылка в канал
        if BOT_USERNAME:
            ad_link = f"https://t.me/{BOT_USERNAME}?start=item_{ad.id}_p"
        else:
            ad_link = f"item_{ad.id}_p"
        text += f"{i}. <a href=\"{ad_link}\">{ad.title}{size_text}</a>\n"
    remaining = total_ads - start_idx - len(page_ads)
    if remaining > 0:
        text += f"... и еще {remaining} товаров\n"
    if total_pages > 1:
        text += f"<i>Стр. {page} из {total_pages}</i>\n"
    text += f"\n<i>Выберите необходимое действие</i>"

    reply_markup = seller_profile_kb(seller_id, has_review=has_review, total_ads=total_ads, page=page)
    profile_msg_id = None
    if edit:
        try:
            await message.edit_text(text, parse_mode='HTML', reply_markup=reply_markup, disable_web_page_preview=True)
            profile_msg_id = message.message_id
        except Exception:
            sent = await message.answer(text, parse_mode='HTML', reply_markup=reply_markup, disable_web_page_preview=True)
            profile_msg_id = sent.message_id
    else:
        sent = await message.answer(text, parse_mode='HTML', reply_markup=reply_markup, disable_web_page_preview=True)
        profile_msg_id = sent.message_id
    if state and profile_msg_id is not None:
        chat_id = message.chat.id if hasattr(message, 'chat') else None
        await state.update_data(seller_profile_msg_id=profile_msg_id, seller_profile_chat_id=chat_id)


# === ПАГИНАЦИЯ ПРОФИЛЯ ПРОДАВЦА ===

async def seller_profile_page_callback(callback: types.CallbackQuery, state: FSMContext):
    """Переключение страницы в профиле продавца (10 объявлений на страницу)."""
    await callback.answer()
    parts = callback.data.split(":")
    if len(parts) < 3:
        return
    try:
        seller_id = int(parts[1])
        page = int(parts[2])
    except (ValueError, IndexError):
        return
    data = await state.get_data()
    ad_id = data.get("last_viewed_ad_id")
    await state.update_data(last_viewed_seller_id=seller_id)
    await show_seller_profile(callback.message, seller_id, ad_id, page=page, edit=True, from_user=callback.from_user, state=state)


# === ТОВАРЫ ПРОДАВЦА ===

SELLER_ADS_PER_PAGE = 5  # Количество товаров на странице
async def seller_ads_callback(callback: types.CallbackQuery, state: FSMContext):
    """Показать товары продавца с пагинацией"""
    await callback.answer()
    
    # Парсим callback_data: seller_ads:seller_id:page
    parts = callback.data.split(':')
    if len(parts) < 3:
        await callback.answer("❌ Ошибка: неверный формат данных.", show_alert=True)
        return
    
    try:
        seller_id = int(parts[1])
        page = int(parts[2])
    except (ValueError, IndexError):
        await callback.answer("❌ Ошибка: неверный формат данных.", show_alert=True)
        return
    
    # Сохраняем seller_id в state для возврата в профиль
    await state.update_data(last_viewed_seller_id=seller_id, came_from_seller_ads=True)
    
    await show_seller_ads_page(callback.message, seller_id, page, edit=True, state=state)


async def show_seller_ads_page(message: types.Message, seller_id: int, page: int, edit: bool = False, state: FSMContext = None):
    """Показать страницу товаров продавца"""
    # Получаем товары продавца (только approved и sold)
    all_ads = []
    approved_ads = await get_user_ads(seller_id, status='approved')
    sold_ads = await get_user_ads(seller_id, status='sold')
    all_ads = approved_ads + sold_ads
    
    # Сортируем по дате создания (новые сначала)
    all_ads.sort(key=lambda x: x.created_at, reverse=True)
    
    total_ads = len(all_ads)
    
    if total_ads == 0:
        text = "📭 У продавца пока нет товаров."
        keyboard = InlineKeyboardBuilder()
        keyboard.row(InlineKeyboardButton(text=BACK_BTN, callback_data="back"))
        
        if edit:
            try:
                await message.edit_text(text, reply_markup=keyboard.as_markup())
            except:
                await message.answer(text, reply_markup=keyboard.as_markup())
        else:
            await message.answer(text, reply_markup=keyboard.as_markup())
        return
    
    # Получаем продавца для отображения username
    seller = await get_user_by_id(seller_id)
    seller_username = f"@{seller.username}" if seller and seller.username else "продавца"
    
    total_pages = ceil(total_ads / SELLER_ADS_PER_PAGE)
    
    # Получаем товары для текущей страницы
    start_idx = page * SELLER_ADS_PER_PAGE
    end_idx = start_idx + SELLER_ADS_PER_PAGE
    page_ads = all_ads[start_idx:end_idx]
    
    # Формируем текст
    text = f"Товары {seller_username}\n\n"
    
    for ad in page_ads:
        # Формируем ссылку на товар (_p = из профиля, «Назад» без ссылки в канал)
        from src.bot.settings.settings import BOT_USERNAME
        if BOT_USERNAME:
            ad_link = f"https://t.me/{BOT_USERNAME}?start=item_{ad.id}_p"
        else:
            ad_link = f"item_{ad.id}_p"
        
        # Определяем статус
        status_emoji = "✅" if ad.status == 'sold' else "📦"
        status_text = "💰 ПРОДАНО" if ad.status == 'sold' else ""
        
        # Формируем размер, если есть
        size_text = f" ({ad.size})" if ad.size else ""
        
        # Формируем строку товара
        ad_line = f"{status_emoji} <a href=\"{ad_link}\">{ad.title}{size_text}</a>"
        if status_text:
            ad_line += f" - {status_text}"
        ad_line += f" - {ad.price} ₽"
        text += f"{ad_line}\n"
    
    text += f"\n< {page + 1}\\{total_pages} >"
    
    # Создаем клавиатуру с пагинацией
    keyboard = InlineKeyboardBuilder()
    
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text=PREV_BTN, callback_data=f"seller_ads:{seller_id}:{page-1}"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(text=NEXT_BTN, callback_data=f"seller_ads:{seller_id}:{page+1}"))
    
    if nav_buttons:
        keyboard.row(*nav_buttons)
    
    keyboard.row(InlineKeyboardButton(text=BACK_BTN, callback_data="back"))
    
    if edit:
        try:
            await message.edit_text(text, parse_mode='HTML', reply_markup=keyboard.as_markup(), disable_web_page_preview=True)
        except:
            await message.answer(text, parse_mode='HTML', reply_markup=keyboard.as_markup(), disable_web_page_preview=True)
    else:
        await message.answer(text, parse_mode='HTML', reply_markup=keyboard.as_markup(), disable_web_page_preview=True)


# === ОТЗЫВЫ ===

