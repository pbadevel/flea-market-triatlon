"""
Handler: создание объявления (FSM).
Портировано из barakholka с адаптацией под flea-market.
"""

import os
import uuid
import aiofiles
from typing import Optional
from sqlalchemy import select

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter, Command
from aiogram.exceptions import TelegramBadRequest

from src.config import settings
from src.logging import get_logger
from src.kit.database.service import database_service
from src.services import ad_service, user_service
from src.models import Ad, AdPhoto
from src.schemas.ads import AdPhotoCreate
from src.bot.states import AddAdState
from src.bot.keyboards import *
from src.bot.texts import *
from src.bot.tg_services import tg_service_notifier
from src.utils import crop_center, add_logo_to_image

router = Router()
log = get_logger()


# ===========================
#  Вход — выбор типа
# ===========================

@router.callback_query(lambda c: c.data == "menu:create_ad")
async def start_ad_type(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.set_state(AddAdState.ad_type)
    try:
        await callback.message.edit_text(AD_TYPE_MESSAGE, reply_markup=ad_type_kb())
    except TelegramBadRequest:
        await callback.message.answer(AD_TYPE_MESSAGE, reply_markup=ad_type_kb())
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("ad_type:"))
async def process_ad_type(callback: CallbackQuery, state: FSMContext):
    ad_type = callback.data.split(":")[1]  # sale / rent
    if ad_type == "back":
        await start_ad_type(callback, state)
        return
    await state.update_data(ad_type="Продажа" if ad_type == "sale" else "Аренда", photos=[])
    await state.set_state(AddAdState.category)
    try:
        await callback.message.edit_text(CATEGORY_MESSAGE, reply_markup=await categories_kb())
    except TelegramBadRequest:
        pass
    await callback.answer()


# ===========================
#  Выбор категории
# ===========================

@router.callback_query(lambda c: c.data.startswith("cat:"))
async def process_category(callback: CallbackQuery, state: FSMContext):
    cat_key = callback.data.split(":", 1)[1]
    await state.update_data(category=cat_key)
    await state.set_state(AddAdState.subcategory)

    # Проверяем, есть ли подкатегории
    from src.models import SubcategoryModel, SubcategoryGroup

    async with database_service.get_session() as session:
        sub_count = await session.scalar(
            select(SubcategoryModel).where(
                SubcategoryModel.category_key == cat_key,
                SubcategoryModel.is_active.is_(True),
            ).limit(1)
        )
        has_subs = sub_count is not None

    if has_subs:
        try:
            await callback.message.edit_text(
                SUBCATEGORY_MESSAGE,
                reply_markup=await subcategories_kb(cat_key)
            )
        except TelegramBadRequest:
            pass
    else:
        # Категория без подкатегорий (slots)
        await state.set_state(AddAdState.photos)
        msg = PHOTO_FIRST_MESSAGE_SLOTS if cat_key == "slots" else PHOTO_FIRST_MESSAGE
        try:
            await callback.message.edit_text(msg, reply_markup=photo_kb(0, cat_key))
        except TelegramBadRequest:
            pass
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("sgrp:"))
async def process_group(callback: CallbackQuery, state: FSMContext):
    _, cat_key, group_key = callback.data.split(":", 2)
    await state.update_data(group_key=group_key)
    try:
        await callback.message.edit_text(
            f"Выберите подкатегорию:",
            reply_markup=await group_subs_kb(cat_key, group_key)
        )
    except TelegramBadRequest:
        pass
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("subcat:"))
async def process_subcategory(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split(":")
    cat_key = parts[1]
    sub_key = parts[2]
    await state.update_data(subcategory=sub_key)
    await state.set_state(AddAdState.photos)

    msg = PHOTO_FIRST_MESSAGE_SLOTS if cat_key == "slots" else PHOTO_FIRST_MESSAGE
    try:
        await callback.message.edit_text(msg, reply_markup=photo_kb(0, cat_key))
    except TelegramBadRequest:
        pass
    await callback.answer()


# ===========================
#  Фото
# ===========================

@router.message(AddAdState.photos, F.photo)
async def process_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    photos: list = data.get("photos", [])
    cat_key = data.get("category", "")

    if len(photos) >= 8:
        await message.answer(PHOTO_MAX_ERROR)
        return

    # Скачиваем фото
    photo = message.photo[-1]
    file_bytes = await message.bot.download(photo.file_id)
    file_bytes = file_bytes.read()

    # Обрезка по центру + логотип
    file_bytes = crop_center(file_bytes)
    file_bytes = add_logo_to_image(file_bytes)

    # Сохраняем локально
    ext = ".jpg"
    file_name = f"ads/{uuid.uuid4().hex}{ext}"
    file_path = os.path.join("uploads", file_name)
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    async with aiofiles.open(file_path, "wb") as f:
        await f.write(file_bytes)

    photos.append({"storage_path": file_name, "position": len(photos), "file_id": photo.file_id})
    await state.update_data(photos=photos)

    # Отвечаем в том же чате
    try:
        last_msg = await message.answer(
            PHOTO_ADDED_MESSAGE.format(count=len(photos)),
            reply_markup=photo_kb(len(photos), cat_key)
        )
    except TelegramBadRequest:
        pass

    # Удаляем сообщение с фото, чтобы не засорять
    try:
        await message.delete()
    except TelegramBadRequest:
        pass


@router.message(AddAdState.photos)
async def process_photo_invalid(message: Message, state: FSMContext):
    await message.answer(PHOTO_ERROR_MESSAGE)


@router.callback_query(lambda c: c.data == "photo:done", AddAdState.photos)
async def photo_done(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    photos: list = data.get("photos", [])
    cat_key = data.get("category", "")
    min_photos = 1 if cat_key == "slots" else 2

    if len(photos) < min_photos:
        await callback.answer(f"❌ Нужно минимум {min_photos} фото", show_alert=True)
        return

    await state.set_state(AddAdState.title)
    try:
        await callback.message.edit_text(TITLE_MESSAGE, reply_markup=cancel_kb("menu:main"))
    except TelegramBadRequest:
        await callback.message.answer(TITLE_MESSAGE, reply_markup=cancel_kb("menu:main"))
    await callback.answer()


@router.callback_query(lambda c: c.data == "photo:delete", AddAdState.photos)
async def photo_delete(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    photos: list = data.get("photos", [])
    if len(photos) > 1:
        removed = photos.pop()
        # Удаляем файл с диска
        _delete_photo_file(removed.get("storage_path"))
        await state.update_data(photos=photos)
        await callback.answer(f"🗑️ Удалено последнее фото")
        cat_key = data.get("category", "")
        try:
            await callback.message.edit_text(
                PHOTO_ADDED_MESSAGE.format(count=len(photos)),
                reply_markup=photo_kb(len(photos), cat_key)
            )
        except TelegramBadRequest:
            pass
    else:
        await callback.answer("❌ Нельзя удалить первое фото", show_alert=True)


@router.callback_query(lambda c: c.data == "photo:back")
async def photo_back(callback: CallbackQuery, state: FSMContext):
    # Проверяем, что мы в процессе создания объявления
    cur = await state.get_state()
    if not cur or not cur.startswith("AddAdState"):
        return
    await state.set_state(AddAdState.category)
    try:
        await callback.message.edit_text(CATEGORY_MESSAGE, reply_markup=await categories_kb())
    except TelegramBadRequest:
        pass
    await callback.answer()


# ===========================
#  Название
# ===========================

@router.message(AddAdState.title)
async def process_title(message: Message, state: FSMContext):
    title = message.text.strip() if message.text else ""
    if not title or len(title) > 100:
        await message.answer("❌ Название должно быть от 1 до 100 символов.")
        return
    await state.update_data(title=title)
    await state.set_state(AddAdState.price)
    await message.answer(PRICE_MESSAGE, reply_markup=cancel_kb("menu:main"))


# ===========================
#  Цена
# ===========================

@router.message(AddAdState.price)
async def process_price(message: Message, state: FSMContext):
    try:
        price = int(message.text.strip())
        if price < 0 or price > 99_999_99:
            await message.answer(PRICE_ERROR_MESSAGE)
            return
        await state.update_data(price=price)
    except ValueError:
        await message.answer(PRICE_ERROR_MESSAGE)
        return

    # Город — покажем клавиатуру с выбором города
    await state.set_state(AddAdState.city)
    await message.answer(LOCATION_MESSAGE, reply_markup=await _city_kb())


async def _city_kb() -> InlineKeyboardMarkup:
    """Клавиатура с популярными городами + свой вариант."""
    builder = InlineKeyboardBuilder()
    popular = ["Москва", "Санкт-Петербург", "Сочи", "Краснодар", "Казань",
               "Екатеринбург", "Новосибирск"]
    for city in popular:
        builder.row(InlineKeyboardButton(text=city, callback_data=f"city:{city}"))
    builder.row(InlineKeyboardButton(text="📝 Свой город", callback_data="city:custom"))
    builder.row(InlineKeyboardButton(text=BACK_BTN, callback_data="city:back"))
    return builder.as_markup()


# ===========================
#  Город
# ===========================

@router.callback_query(lambda c: c.data.startswith("city:"))
async def process_city_cb(callback: CallbackQuery, state: FSMContext):
    city = callback.data.split(":", 1)[1]
    if city == "custom":
        await state.set_state(AddAdState.country)
        await callback.message.edit_text(COUNTRY_CUSTOM_MESSAGE, reply_markup=back_kb("city:back"))
        await callback.answer()
        return
    if city == "back":
        from .start import callback_main_menu
        await callback_main_menu(callback, state)
        return
    await state.update_data(city=city)
    await _after_city(callback, state)


@router.message(AddAdState.country)
async def process_city_text(message: Message, state: FSMContext):
    text = message.text.strip() if message.text else ""
    if not text:
        await message.answer("❌ Введите название города.")
        return
    await state.update_data(city=text, country=None)
    await _after_city(None, state, message)


async def _after_city(callback: Optional[CallbackQuery], state: FSMContext, msg: Optional[Message] = None):
    data = await state.get_data()
    cat_key = data.get("category", "")
    sub_key = data.get("subcategory", "")

    # Проверяем, нужен ли размер
    from src.kit.database.service import database_service
    from src.models import SubcategoryModel

    needs_size = False
    if sub_key:
        async with database_service.get_session() as session:
            result = await session.execute(
                select(SubcategoryModel).where(SubcategoryModel.key == sub_key)
            )
            sub = result.scalar_one_or_none()
            if sub and sub.requires_size:
                needs_size = True

    if needs_size:
        next_state = AddAdState.size
        text = SIZE_MESSAGE
        markup = cancel_kb("menu:main")
    else:
        next_state = AddAdState.condition
        text = CONDITION_MESSAGE
        markup = condition_kb()

    await state.set_state(next_state)
    target = callback if callback else msg
    if target:
        if callback:
            try:
                await callback.message.edit_text(text, reply_markup=markup)
            except TelegramBadRequest:
                pass
        else:
            await msg.answer(text, reply_markup=markup)


# ===========================
#  Размер
# ===========================

@router.message(AddAdState.size)
async def process_size(message: Message, state: FSMContext):
    size = message.text.strip() if message.text else ""
    if len(size) > 20:
        await message.answer("❌ Слишком длинный размер (макс. 20 символов).")
        return
    if size:
        await state.update_data(size=size)
    await state.set_state(AddAdState.condition)
    await message.answer(CONDITION_MESSAGE, reply_markup=condition_kb())


# ===========================
#  Состояние
# ===========================

@router.callback_query(lambda c: c.data.startswith("cond:"))
async def process_condition(callback: CallbackQuery, state: FSMContext):
    cond = callback.data.split(":")[1]
    if cond == "back":
        await state.set_state(AddAdState.price)
        await callback.message.edit_text(PRICE_MESSAGE, reply_markup=cancel_kb("menu:main"))
        await callback.answer()
        return

    await state.update_data(condition=cond)
    await state.set_state(AddAdState.description)
    try:
        await callback.message.edit_text(DESCRIPTION_MESSAGE, reply_markup=skip_kb())
    except TelegramBadRequest:
        pass
    await callback.answer()


# ===========================
#  Описание
# ===========================

@router.message(AddAdState.description)
async def process_description(message: Message, state: FSMContext):
    text = message.text.strip() if message.text else ""
    await state.update_data(description=text[:650] if text else "")
    await _after_description(message, state)


@router.callback_query(lambda c: c.data == "review:skip")
async def process_description_skip(callback: CallbackQuery, state: FSMContext):
    await state.update_data(description=None)
    target = callback.message
    await _after_description(target, state)
    await callback.answer()


async def _after_description(target, state: FSMContext):
    await state.set_state(AddAdState.delivery_method)
    try:
        await target.edit_text(DELIVERY_METHOD_MESSAGE, reply_markup=delivery_method_kb())
    except (TelegramBadRequest, AttributeError):
        await target.answer(DELIVERY_METHOD_MESSAGE, reply_markup=delivery_method_kb())


# ===========================
#  Способ доставки
# ===========================

@router.callback_query(lambda c: c.data.startswith("delivery:"))
async def process_delivery(callback: CallbackQuery, state: FSMContext):
    delivery = callback.data.split(":")[1]
    mapping = {"self": "Самовывоз", "ship": "Отправка"}
    await state.update_data(delivery_method=mapping.get(delivery, delivery))
    await state.set_state(AddAdState.contact_method)
    try:
        await callback.message.edit_text(CONTACT_METHOD_MESSAGE, reply_markup=contact_method_kb())
    except TelegramBadRequest:
        pass
    await callback.answer()


# ===========================
#  Способ связи
# ===========================

@router.callback_query(lambda c: c.data.startswith("contact:"))
async def process_contact(callback: CallbackQuery, state: FSMContext):
    contact = callback.data.split(":")[1]
    if contact == "back":
        await state.set_state(AddAdState.delivery_method)
        await callback.message.edit_text(DELIVERY_METHOD_MESSAGE, reply_markup=delivery_method_kb())
        await callback.answer()
        return

    mapping = {"telegram": "telegram", "phone": "phone", "both": "telegram"}
    await state.update_data(contact_method=mapping.get(contact, "telegram"))

    if contact == "phone" or contact == "both":
        await state.set_state(AddAdState.phone)
        await callback.message.edit_text(PHONE_INPUT_MESSAGE, reply_markup=skip_kb("phone:skip"))
        await callback.answer()
        return

    await _show_confirm(callback.message, state)
    await callback.answer()


@router.message(AddAdState.phone)
async def process_phone(message: Message, state: FSMContext):
    phone = message.text.strip() if message.text else ""
    phone = phone.replace("+", "").replace(" ", "").replace("-", "")
    if phone and len(phone) < 10:
        await message.answer("❌ Некорректный номер. Введите 11 цифр.")
        return
    await state.update_data(phone=phone or None)
    await _show_confirm(message, state)


@router.callback_query(lambda c: c.data == "phone:skip")
async def process_phone_skip(callback: CallbackQuery, state: FSMContext):
    await state.update_data(phone=None)
    await _show_confirm(callback.message, state)
    await callback.answer()


# ===========================
#  Подтверждение
# ===========================

async def _show_confirm(target, state: FSMContext):
    data = await state.get_data()
    await state.set_state(AddAdState.confirm)

    text = "📋 <b>Проверьте объявление:</b>\n\n"
    text += f"Тип: {data.get('ad_type', 'Продажа')}\n"
    text += f"Категория: {data.get('category', '-')}\n"
    if data.get("subcategory"):
        text += f"Подкатегория: {data['subcategory']}\n"
    text += f"Название: {data.get('title', '-')}\n"
    text += f"Цена: {data.get('price', '-')} ₽\n"
    text += f"Город: {data.get('city', '-')}\n"
    if data.get("size"):
        text += f"Размер: {data['size']}\n"
    text += f"Состояние: {data.get('condition', '-')}\n"
    if data.get("description"):
        text += f"Описание: {data['description'][:100]}...\n"
    text += f"Доставка: {data.get('delivery_method', '-')}\n"
    text += f"Фото: {len(data.get('photos', []))} шт.\n"

    try:
        await target.edit_text(text, reply_markup=confirm_kb(), parse_mode="html")
    except (TelegramBadRequest, AttributeError):
        await target.answer(text, reply_markup=confirm_kb(), parse_mode="html")


@router.callback_query(lambda c: c.data == "confirm:edit")
async def confirm_edit(callback: CallbackQuery, state: FSMContext):
    # Возвращаем к редактированию — просто начинаем заново
    await start_ad_type(callback, state)


@router.callback_query(lambda c: c.data == "confirm:yes")
async def confirm_submit(callback: CallbackQuery, state: FSMContext):
    """Финал: создаём объявление в БД и отправляем на модерацию."""
    data = await state.get_data()
    tg_user = callback.from_user

    if not tg_user:
        await callback.answer("❌ Ошибка: не удалось определить пользователя", show_alert=True)
        return

    async with database_service.get_session() as session:
        # Находим/создаём пользователя
        user = await user_service.get_or_create_by_tg(session, tg_user)

        # Создаём объявление
        ad = Ad(
            seller_user_id=user.id,
            title=data["title"],
            price=data["price"],
            city=data["city"],
            category=data["category"],
            subcategory=data.get("subcategory"),
            size=data.get("size"),
            condition=data.get("condition", "unknown"),
            description=data.get("description"),
            ad_type=data.get("ad_type", "Продажа"),
            delivery_method=data.get("delivery_method"),
            contact_method=data.get("contact_method", "telegram"),
            status="pending",
        )
        session.add(ad)
        await session.flush()

        # Сохраняем фото
        photos_data = data.get("photos", [])
        for ph in photos_data:
            ap = AdPhoto(
                ad_id=ad.id,
                file_id=ph.get("file_id"),
                storage_path=ph.get("storage_path"),
                position=ph["position"],
            )
            session.add(ap)

        await session.commit()
        await session.refresh(ad)

    # Отправляем на модерацию
    try:
        await tg_service_notifier.send_ad_for_moderation(ad)
    except Exception as e:
        log.error(f"Failed to send ad {ad.id} for moderation: {e}")

    await state.clear()

    try:
        await callback.message.edit_text(
            SENT_TO_MODERATION_MESSAGE,
            reply_markup=await main_menu_kb(user.id)
        )
    except TelegramBadRequest:
        await callback.message.answer(
            SENT_TO_MODERATION_MESSAGE,
            reply_markup=await main_menu_kb(user.id)
        )
    await callback.answer("✅ Объявление отправлено на модерацию!", show_alert=True)
    log.info(f"Ad #{ad.id} created by user #{user.id}")


# ===========================
#  Отмена (Command + Callback)
# ===========================

@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        await message.answer("Нет активного действия.", reply_markup=await main_menu_kb(message.from_user.id))
        return
    await state.clear()
    await message.answer("❌ Действие отменено.", reply_markup=await main_menu_kb(message.from_user.id))


@router.callback_query(lambda c: c.data == "CancelAdModeration")
async def cancel_ad_moderation(cb: CallbackQuery, state: FSMContext):
    from aiogram.types import Message as AiogramMessage
    await state.clear()
    try:
        await cb.message.edit_text("❌ Отменено.")
    except TelegramBadRequest:
        pass
    await cb.answer()


# ===========================
#  Helper: удаление файла
# ===========================

def _delete_photo_file(storage_path: str | None) -> None:
    if not storage_path:
        return
    import os
    filepath = os.path.join("uploads", storage_path)
    try:
        os.remove(filepath)
    except FileNotFoundError:
        pass
