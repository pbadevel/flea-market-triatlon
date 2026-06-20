"""
Handler: каталог объявлений — просмотр с пагинацией.
"""

from math import ceil
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest
from sqlalchemy import select, func
from sqlalchemy.orm import joinedload, selectinload

from src.logging import get_logger
from src.kit.database.service import database_service
from src.kit.utils import map_country, get_ru_condition
from src.models import Ad, AdStatus, AdPhoto, Review, User
from src.bot.keyboards import *
from src.bot.texts import *
from src.bot.states import SearchState

router = Router()
log = get_logger()

ITEMS_PER_PAGE = 5
CARDS_PER_PAGE = 5


# ===========================
#  Каталог — список категорий
# ===========================

@router.callback_query(lambda c: c.data == "menu:catalog")
async def catalog_handler(callback: CallbackQuery, state: FSMContext):
    """Показать список категорий для просмотра."""
    await state.clear()

    text = "📋 <b>Каталог объявлений</b>\n\nВыберите категорию:"
    try:
        await callback.message.edit_text(text, reply_markup=await categories_kb())
    except TelegramBadRequest:
        await callback.message.answer(text, reply_markup=await categories_kb())
    await callback.answer()


# ===========================
#  Категория → товары
# ===========================

@router.callback_query(lambda c: c.data.startswith("cat_view:") or c.data.startswith("cat_ads:"))
async def category_ads_callback(callback: CallbackQuery, state: FSMContext):
    data = callback.data
    prefix = "cat_view:" if data.startswith("cat_view:") else "cat_ads:"
    parts = data.replace(prefix, "").split(":")
    cat_key = parts[0]
    page = int(parts[1]) if len(parts) > 1 else 1

    await _show_category_ads(callback, cat_key, page)


async def _show_category_ads(callback: CallbackQuery, cat_key: str, page: int = 1):
    """Показать список объявлений в категории с пагинацией."""
    async with database_service.get_session() as session:
        count_result = await session.execute(
            select(func.count()).select_from(Ad).where(
                Ad.status == AdStatus.approved,
                Ad.category == cat_key,
            )
        )
        total = count_result.scalar() or 0
        total_pages = max(1, ceil(total / ITEMS_PER_PAGE))

        result = await session.execute(
            select(Ad)
            .where(Ad.status == AdStatus.approved, Ad.category == cat_key)
            .options(selectinload(Ad.photos), joinedload(Ad.seller))
            .order_by(Ad.created_at.desc())
            .offset((page - 1) * ITEMS_PER_PAGE)
            .limit(ITEMS_PER_PAGE)
        )
        ads = result.scalars().unique().all()

    if not ads:
        await callback.answer("📭 В этой категории пока нет объявлений", show_alert=True)
        return

    text = f"📋 <b>Категория: {cat_key}</b>\nВсего: {total}\n\n"
    for i, ad in enumerate(ads, 1):
        seller_name = f"@{ad.seller.username}" if ad.seller and ad.seller.username else f"ID{ad.seller_user_id}"
        text += f"{i}. <b>{ad.title}</b> — {ad.price}₽\n   {ad.city} | {seller_name}\n"

    text += f"\nСтраница {page}/{total_pages}"

    try:
        await callback.message.edit_text(
            text,
            reply_markup=catalog_pagination_kb(page, total_pages, "cat_ads", cat_key),
            parse_mode="html",
        )
    except TelegramBadRequest:
        pass
    await callback.answer()


# ===========================
#  Просмотр деталей объявления
# ===========================

@router.callback_query(lambda c: c.data.startswith("view_ad:"))
async def view_ad(callback: CallbackQuery, state: FSMContext):
    ad_id = int(callback.data.split(":")[1])
    async with database_service.get_session() as session:
        result = await session.execute(
            select(Ad).where(Ad.id == ad_id)
            .options(
                selectinload(Ad.photos),
                joinedload(Ad.seller).selectinload(User.reviews_received).selectinload(Review.reviewer),
            )
        )
        ad = result.scalars().unique().first()

    if not ad:
        await callback.answer("❌ Объявление не найдено", show_alert=True)
        return

    # Формируем текст
    text = f"<b>{ad.title}</b>\n\n"
    text += f"💰 <b>Цена:</b> {ad.price} ₽\n"
    text += f"📍 <b>Город:</b> {ad.city}\n"
    if ad.country:
        text += f"🌍 <b>Страна:</b> {ad.country}\n"
    text += f"📁 <b>Категория:</b> {ad.category}\n"
    if ad.subcategory:
        text += f"📂 <b>Подкатегория:</b> {ad.subcategory}\n"
    if ad.size:
        text += f"📏 <b>Размер:</b> {ad.size}\n"
    text += f"♻️ <b>Состояние:</b> {ad.condition}\n"
    if ad.description:
        text += f"\n📝 <b>Описание:</b>\n{ad.description[:500]}\n"
    text += f"\n👤 <b>Продавец:</b> "
    if ad.seller:
        text += f"@{ad.seller.username}" if ad.seller.username else f"{ad.seller.first_name} (ID{ad.seller.id})"
    else:
        text += f"ID{ad.seller_user_id}"

    # Кнопка "Показать контакты" + назад
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text="📞 Показать контакты",
        callback_data=f"show_contacts:{ad.id}"
    ))
    builder.row(InlineKeyboardButton(text=BACK_BTN, callback_data="menu:catalog"))
    builder.row(InlineKeyboardButton(text=MAIN_MENU_BTN, callback_data="menu:main"))

    try:
        await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="html")
    except TelegramBadRequest:
        await callback.message.answer(text, reply_markup=builder.as_markup(), parse_mode="html")
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("show_contacts:"))
async def show_contacts(callback: CallbackQuery, state: FSMContext):
    """Показать контакты продавца."""
    ad_id = int(callback.data.split(":")[1])
    async with database_service.get_session() as session:
        result = await session.execute(
            select(Ad).where(Ad.id == ad_id).options(joinedload(Ad.seller))
        )
        ad = result.scalars().first()

    if not ad or not ad.seller:
        await callback.answer("❌ Продавец не найден", show_alert=True)
        return

    seller = ad.seller
    text = f"👤 <b>Продавец</b>\n\n"
    if seller.username:
        text += f"Telegram: @{seller.username}\n"
    elif seller.first_name:
        text += f"Имя: {seller.first_name}\n"
    text += f"Способ связи: {ad.contact_method}\n"
    if seller.phone:
        text += f"Телефон: +{seller.phone}\n"

    text += f"\n📋 <b>{ad.title}</b> — {ad.price}₽"

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=BACK_BTN, callback_data=f"view_ad:{ad_id}"))

    try:
        await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="html")
    except TelegramBadRequest:
        pass
    await callback.answer()


# ===========================
#  Поиск
# ===========================

@router.callback_query(lambda c: c.data == "menu:search")
async def search_start(callback: CallbackQuery, state: FSMContext):
    from src.bot.states import SearchState
    await state.set_state(SearchState.query)
    try:
        await callback.message.edit_text(SEARCH_MESSAGE, reply_markup=back_kb("menu:main"))
    except TelegramBadRequest:
        pass
    await callback.answer()


@router.message(SearchState.query)
async def search_query(message: Message, state: FSMContext):

    query = message.text.strip() if message.text else ""
    if len(query) < 2:
        await message.answer("❌ Минимум 2 символа для поиска.")
        return

    async with database_service.get_session() as session:
        result = await session.execute(
            select(Ad)
            .where(
                Ad.status == AdStatus.approved,
                (Ad.title.ilike(f"%{query}%")) | (Ad.description.ilike(f"%{query}%"))
            )
            .options(selectinload(Ad.photos))
            .order_by(Ad.created_at.desc())
            .limit(10)
        )
        ads = result.scalars().all()

    await state.clear()

    if not ads:
        await message.answer(SEARCH_NO_RESULTS, reply_markup=await main_menu_kb(message.from_user.id))
        return

    text = f"🔍 <b>Результаты поиска: «{query}»</b>\n\n"
    for ad in ads:
        text += f"• <b>{ad.title}</b> — {ad.price}₽ — {ad.city}\n"

    text += f"\nНайдено: {len(ads)}"
    await message.answer(text, reply_markup=await main_menu_kb(message.from_user.id), parse_mode="html")


# ===========================
#  Отзывы
# ===========================

@router.callback_query(lambda c: c.data.startswith("reviews:"))
async def show_reviews(callback: CallbackQuery):
    seller_id = int(callback.data.split(":")[1])
    async with database_service.get_session() as session:
        reviews_result = await session.execute(
            select(Review)
            .where(Review.reviewed_user_id == seller_id)
            .options(joinedload(Review.reviewer))
            .order_by(Review.created_at.desc())
            .limit(5)
        )
        reviews = reviews_result.scalars().all()

        avg_result = await session.execute(
            select(func.avg(Review.rating)).where(Review.reviewed_user_id == seller_id)
        )
        avg = avg_result.scalar()

    text = f"⭐ <b>Отзывы о продавце</b>\n"
    if avg:
        text += f"Средняя оценка: {round(avg, 1)}\n"
    text += f"\n"

    if not reviews:
        text += "Пока нет отзывов."
    else:
        for r in reviews:
            reviewer = f"@{r.reviewer.username}" if r.reviewer and r.reviewer.username else f"ID{r.reviewer_user_id}"
            text += f"\n⭐ {'★' * r.rating}{'☆' * (5 - r.rating)} от {reviewer}"
            if r.comment:
                text += f"\n   {r.comment[:100]}"

    await callback.answer(text, show_alert=True)


@router.callback_query(lambda c: c.data.startswith("detail:"))
async def detail_button_handler(callback: CallbackQuery):
    """Обработчик кнопки 'Подробнее' из канала."""
    ad_id = callback.data.split(":")[1]
    
    async with database_service.get_session() as session:
        result = await session.execute(
            select(Ad).where(Ad.id == int(ad_id)).options(
                joinedload(Ad.photos),
                joinedload(Ad.seller),
            )
        )
        ad = result.scalars().first()
        
        if not ad:
            await callback.answer("Объявление не найдено", show_alert=True)
            return
        
        country_ru = map_country(ad.country) if ad.country else None
        location = f"{country_ru} - {ad.city}" if country_ru else ad.city
        
        msg = (
            f"🛍 <b>{ad.title}</b>\n\n"
            f"📍 {location}\n"
            f"🏷 {ad.category}{f' → {ad.subcategory}' if ad.subcategory else ''}\n"
            f"📦 {get_ru_condition(ad.condition)}\n"
            f"💰 <b>{ad.price:,} ₽</b>\n"
        )
        if ad.description:
            msg += f"\n📝 {ad.description[:500]}"
        
        msg += f"\n\n👤 Продавец: @{ad.seller.username if ad.seller and ad.seller.username else 'не указан'}"
        if ad.seller and ad.seller.first_name:
            msg += f" ({ad.seller.first_name})"
        
        await callback.answer(
            "Скоро здесь будет ссылка на сайт 🚀",
            show_alert=True,
        )
