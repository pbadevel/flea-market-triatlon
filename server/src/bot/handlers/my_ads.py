"""
Handler: мои объявления — просмотр, редактирование, удаление.
"""

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.logging import get_logger
from src.kit.database.service import database_service
from src.services import user_service, ad_service
from src.models import Ad, AdStatus
from src.bot.keyboards import *
from src.bot.texts import *

router = Router()
log = get_logger()


@router.callback_query(lambda c: c.data == "menu:my_ads")
async def my_ads_list(callback: CallbackQuery, state: FSMContext):
    """Показать список объявлений пользователя."""
    await state.clear()
    tg_user = callback.from_user

    async with database_service.get_session() as session:
        user = await user_service.get_or_create_by_tg(session, tg_user)

        result = await session.execute(
            select(Ad).where(Ad.seller_user_id == user.id)
            .options(selectinload(Ad.photos))
            .order_by(Ad.created_at.desc())
        )
        ads = result.scalars().unique().all()

    if not ads:
        text = "📂 У вас пока нет объявлений."
        try:
            await callback.message.edit_text(text, reply_markup=await main_menu_kb(user.id))
        except TelegramBadRequest:
            await callback.message.answer(text, reply_markup=await main_menu_kb(user.id))
        await callback.answer()
        return

    text = "📂 <b>Мои объявления</b>\n\n"
    for i, ad in enumerate(ads, 1):
        status_emoji = {
            "pending": "🕒",
            "approved": "✅",
            "rejected": "❌",
            "sold": "💵",
            "removed": "🗑️",
        }.get(ad.status, "❓")
        text += f"{i}. {status_emoji} <b>{ad.title}</b> — {ad.price}₽\n"
        text += f"   Статус: {ad.status} | {ad.city}\n\n"

    # Кнопки для каждого объявления
    builder = InlineKeyboardBuilder()
    for ad in ads[:10]:
        builder.row(InlineKeyboardButton(
            text=f"{'✅' if ad.status == 'approved' else '📝'} {ad.title[:30]}",
            callback_data=f"myad_view:{ad.id}"
        ))
    builder.row(InlineKeyboardButton(text=MAIN_MENU_BTN, callback_data="menu:main"))
    builder.row(InlineKeyboardButton(text=CREATE_AD_BTN, callback_data="menu:create_ad"))

    try:
        await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="html")
    except TelegramBadRequest:
        await callback.message.answer(text, reply_markup=builder.as_markup(), parse_mode="html")
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("myad_view:"))
async def myad_detail(callback: CallbackQuery, state: FSMContext):
    """Показать детали объявления."""
    ad_id = int(callback.data.split(":")[1])
    tg_user = callback.from_user

    async with database_service.get_session() as session:
        user = await user_service.get_or_create_by_tg(session, tg_user)

        result = await session.execute(
            select(Ad).where(Ad.id == ad_id, Ad.seller_user_id == user.id)
            .options(selectinload(Ad.photos))
        )
        ad = result.scalars().unique().first()

    if not ad:
        await callback.answer("❌ Объявление не найдено", show_alert=True)
        return

    status_emoji = {"pending": "🕒", "approved": "✅", "rejected": "❌", "sold": "💵", "removed": "🗑️"}.get(ad.status, "❓")
    text = f"{status_emoji} <b>{ad.title}</b>\n\n"
    text += f"💰 Цена: {ad.price} ₽\n"
    text += f"📍 Город: {ad.city}\n"
    if ad.country:
        text += f"🌍 Страна: {ad.country}\n"
    text += f"📁 Категория: {ad.category}\n"
    if ad.subcategory:
        text += f"📂 Подкатегория: {ad.subcategory}\n"
    if ad.size:
        text += f"📏 Размер: {ad.size}\n"
    text += f"♻️ Состояние: {ad.condition}\n"
    text += f"📌 Статус: <b>{ad.status}</b>\n"
    if ad.rejection_reason:
        text += f"❌ Причина отказа: {ad.rejection_reason}\n"
    text += f"📅 Создано: {ad.created_at.strftime('%d.%m.%Y %H:%M')}\n"
    text += f"📸 Фото: {len(ad.photos)} шт.\n"

    if ad.status == "approved":
        text += "\n💡 <i>Чтобы изменить цену, отредактируйте или создайте новое.</i>"

    # Кнопки действий
    builder = InlineKeyboardBuilder()
    if ad.status in ("pending", "approved"):
        if ad.status == "approved":
            builder.row(InlineKeyboardButton(
                text="💵 Отметить проданным",
                callback_data=f"myad_sold:{ad.id}"
            ))
        builder.row(InlineKeyboardButton(
            text="🗑️ Снять с публикации",
            callback_data=f"myad_remove:{ad.id}"
        ))
    elif ad.status == "rejected":
        text += "\n\n✏️ Отредактируйте объявление и отправьте на повторную модерацию."
    builder.row(InlineKeyboardButton(text=BACK_BTN, callback_data="menu:my_ads"))

    try:
        await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="html")
    except TelegramBadRequest:
        pass
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("myad_sold:"))
async def myad_sold(callback: CallbackQuery):
    """Отметить как проданное."""
    ad_id = int(callback.data.split(":")[1])
    tg_user = callback.from_user

    async with database_service.get_session() as session:
        user = await user_service.get_or_create_by_tg(session, tg_user)
        result = await session.execute(
            select(Ad).where(Ad.id == ad_id, Ad.seller_user_id == user.id)
        )
        ad = result.scalars().first()

        if ad:
            ad.status = "sold"
            await session.commit()

    await callback.answer("✅ Объявление отмечено как проданное", show_alert=True)
    await my_ads_list(callback, None)


@router.callback_query(lambda c: c.data.startswith("myad_remove:"))
async def myad_remove(callback: CallbackQuery, state: FSMContext):
    """Снять объявление."""
    ad_id = int(callback.data.split(":")[1])
    tg_user = callback.from_user

    async with database_service.get_session() as session:
        user = await user_service.get_or_create_by_tg(session, tg_user)
        result = await session.execute(
            select(Ad).where(Ad.id == ad_id, Ad.seller_user_id == user.id)
        )
        ad = result.scalars().first()

        if ad:
            ad.status = "removed"
            await session.commit()

    await callback.answer("🗑️ Объявление снято с публикации", show_alert=True)
    await my_ads_list(callback, state)
