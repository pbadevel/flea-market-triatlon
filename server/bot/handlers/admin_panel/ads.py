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
from src.bot.settings.constants import DEFAULT_CITIES
from src.bot.loader import bot
from src.bot.keyboards.keyboards import ad_in_channel_kb
from src.bot.utils.channel_utils import format_active_caption
from sqlalchemy import select, func
from src.bot.database.methods import async_session
from src.models import User, Ad, Review
from src.bot.middlewares.throttle_middleware import invalidate_banned_cache


# === /post_attach (пост в канал с кнопкой на бота) ===

from ._common import *

# === РАЗДЕЛ "ОБЪЯВЛЕНИЯ" ===

async def admin_ads_menu(callback: types.CallbackQuery, state: FSMContext):
    """Меню объявлений"""
    await callback.answer()
    
    if not await check_admin_rights(callback.from_user.id):
        await callback.answer("❌ У вас нет прав доступа.", show_alert=True)
        return
    
    await state.set_state(AdminPanelState.ads_menu)
    
    text = "📦 <b>ОБЪЯВЛЕНИЯ</b>\n\nВы находитесь в пункте 'ОБЪЯВЛЕНИЯ', выберите действие:"
    
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text="👁 Посмотреть объявление", callback_data="admin:ads:view"))
    keyboard.row(InlineKeyboardButton(text="✏️ Редактировать объявление", callback_data="admin:ads:edit"))
    keyboard.row(InlineKeyboardButton(text="🗑 Удалить объявление", callback_data="admin:ads:delete"))
    keyboard.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:back"))
    
    try:
        await callback.message.edit_text(text, parse_mode='HTML', reply_markup=keyboard.as_markup())
    except:
        await callback.message.answer(text, parse_mode='HTML', reply_markup=keyboard.as_markup())


# === УДАЛЕНИЕ ОБЪЯВЛЕНИЯ ===

async def admin_ads_delete_start(callback: types.CallbackQuery, state: FSMContext):
    """Начало процесса удаления объявления"""
    await callback.answer()
    
    await state.set_state(AdminPanelState.delete_ad_input)
    
    text = "🗑 <b>Удаление объявления</b>\n\nУкажите номер объявления для удаления:"
    
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:ads"))
    
    try:
        msg = await callback.message.edit_text(text, parse_mode='HTML', reply_markup=keyboard.as_markup())
        await state.update_data(delete_ad_msg_id=msg.message_id)
    except:
        msg = await callback.message.answer(text, parse_mode='HTML', reply_markup=keyboard.as_markup())
        await state.update_data(delete_ad_msg_id=msg.message_id)


async def admin_ads_delete_input(message: types.Message, state: FSMContext):
    """Обработка ввода номера объявления для удаления. Редактируем сообщение бота, удаляем сообщение пользователя."""
    # Удаляем сообщение пользователя с номером объявления
    try:
        await message.delete()
    except Exception:
        pass

    data = await state.get_data()
    prev_msg_id = data.get('delete_ad_msg_id')

    try:
        ad_id = int(message.text.strip())
    except ValueError:
        err_text = "❌ Неверный формат. Укажите числовой ID объявления."
        keyboard = InlineKeyboardBuilder()
        keyboard.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:ads"))
        if prev_msg_id:
            try:
                await bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=prev_msg_id,
                    text=err_text,
                    parse_mode='HTML',
                    reply_markup=keyboard.as_markup(),
                )
            except Exception:
                await message.answer(err_text, parse_mode='HTML', reply_markup=keyboard.as_markup())
        else:
            await message.answer(err_text, parse_mode='HTML', reply_markup=keyboard.as_markup())
        return

    ad = await get_ad_by_id(ad_id)
    if not ad:
        err_text = f"❌ Объявление #{ad_id} не найдено."
        keyboard = InlineKeyboardBuilder()
        keyboard.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:ads"))
        if prev_msg_id:
            try:
                await bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=prev_msg_id,
                    text=err_text,
                    parse_mode='HTML',
                    reply_markup=keyboard.as_markup(),
                )
            except Exception:
                await message.answer(err_text, parse_mode='HTML', reply_markup=keyboard.as_markup())
        else:
            await message.answer(err_text, parse_mode='HTML', reply_markup=keyboard.as_markup())
        return

    # Сохраняем ID в состояние
    await state.update_data(delete_ad_id=ad_id)
    await state.set_state(AdminPanelState.delete_ad_confirm)

    text = f"📦 <b>Объявление #{ad.id}</b>\n\n"
    text += f"<b>{ad.title}</b>\n"
    ad_type_text = getattr(ad, 'ad_type', 'Продажа')
    text += f"💰 {ad.price} ₽ | 📋 {ad_type_text} | 📍 {ad.city}\n"
    text += f"📊 Статус: {ad.status}\n\n"
    text += "❗️ Вы действительно хотите удалить это объявление?"

    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text="🗑 УДАЛИТЬ", callback_data=f"admin:ads:delete:confirm:{ad_id}"))
    keyboard.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:ads"))

    if prev_msg_id:
        try:
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=prev_msg_id,
                text=text,
                parse_mode='HTML',
                reply_markup=keyboard.as_markup(),
            )
        except Exception:
            await message.answer(text, parse_mode='HTML', reply_markup=keyboard.as_markup())
    else:
        await message.answer(text, parse_mode='HTML', reply_markup=keyboard.as_markup())


async def admin_ads_delete_confirm(callback: types.CallbackQuery, state: FSMContext):
    """Подтверждение удаления объявления"""
    await callback.answer()
    
    ad_id = int(callback.data.split(':')[-1])
    
    # Удаляем объявление (включая из канала)
    from src.bot.handlers.my_ads import delete_ad_with_channel
    await delete_ad_with_channel(ad_id)
    
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:ads:delete:back"))
    await callback.message.edit_text(
        f"✅ Объявление #{ad_id} успешно удалено.",
        parse_mode='HTML',
        reply_markup=keyboard.as_markup()
    )
    
    logger.info(f"Админ {callback.from_user.id} удалил объявление #{ad_id}")
    
    await state.clear()


async def admin_ads_delete_back(callback: types.CallbackQuery, state: FSMContext):
    """После удаления объявления — кнопка «Назад» возвращает в меню «ОБЪЯВЛЕНИЯ»."""
    await callback.answer()
    if not await check_admin_rights(callback.from_user.id):
        return
    await state.set_state(AdminPanelState.ads_menu)
    text = "📦 <b>ОБЪЯВЛЕНИЯ</b>\n\nВы находитесь в пункте 'ОБЪЯВЛЕНИЯ', выберите действие:"
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text="👁 Посмотреть объявление", callback_data="admin:ads:view"))
    keyboard.row(InlineKeyboardButton(text="✏️ Редактировать объявление", callback_data="admin:ads:edit"))
    keyboard.row(InlineKeyboardButton(text="🗑 Удалить объявление", callback_data="admin:ads:delete"))
    keyboard.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:back"))
    try:
        await callback.message.edit_text(text, parse_mode='HTML', reply_markup=keyboard.as_markup())
    except Exception:
        await callback.message.answer(text, parse_mode='HTML', reply_markup=keyboard.as_markup())


# === РЕДАКТИРОВАНИЕ ОБЪЯВЛЕНИЯ ===

async def admin_ads_edit_start(callback: types.CallbackQuery, state: FSMContext):
    """Начало процесса редактирования объявления"""
    await callback.answer()
    
    await state.set_state(AdminPanelState.edit_ad_input)
    
    text = "✏️ <b>Редактирование объявления</b>\n\nУкажите номер объявления для редактирования:"
    
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:ads"))
    
    try:
        msg = await callback.message.edit_text(text, parse_mode='HTML', reply_markup=keyboard.as_markup())
        await state.update_data(edit_ad_input_msg_id=msg.message_id)
    except:
        msg = await callback.message.answer(text, parse_mode='HTML', reply_markup=keyboard.as_markup())
        await state.update_data(edit_ad_input_msg_id=msg.message_id)


async def admin_ads_edit_input(message: types.Message, state: FSMContext):
    """Обработка ввода номера объявления для редактирования"""
    # Деактивируем кнопки в предыдущем сообщении
    data = await state.get_data()
    prev_msg_id = data.get('edit_ad_input_msg_id')
    if prev_msg_id:
        try:
            await bot.edit_message_reply_markup(
                chat_id=message.chat.id,
                message_id=prev_msg_id,
                reply_markup=None
            )
        except:
            pass
    
    try:
        ad_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Неверный формат. Укажите числовой ID объявления.")
        return
    
    ad = await get_ad_by_id(ad_id)
    if not ad:
        await message.answer(f"❌ Объявление #{ad_id} не найдено.")
        return
    
    # Сохраняем ID в состояние
    await state.update_data(edit_ad_id=ad_id)
    await state.set_state(AdminPanelState.edit_ad_menu)
    
    # Показываем меню редактирования
    await show_edit_menu(message, ad)


async def show_edit_menu(message: types.Message, ad):
    """Показать меню редактирования объявления"""
    text = _edit_menu_text(ad)
    keyboard = _edit_menu_keyboard(ad)
    await message.answer(text, parse_mode='HTML', reply_markup=keyboard.as_markup())


def _edit_menu_text(ad) -> str:
    """Текст меню редактирования объявления"""
    text = f"✏️ <b>Редактирование объявления #{ad.id}</b>\n\n"
    text += f"📝 <b>Название:</b> {ad.title}\n"
    text += f"💰 <b>Цена:</b> {ad.price} ₽\n"
    ad_type_text = getattr(ad, 'ad_type', 'Продажа')
    text += f"📋 <b>Тип:</b> {ad_type_text}\n"
    text += f"📍 <b>Город:</b> {ad.city}\n"
    contact_display = (ad.contact_method or "Не указан")[:40] + ("..." if (ad.contact_method or "") and len(ad.contact_method or "") > 40 else "")
    text += f"📞 <b>Контакт:</b> {contact_display}\n"
    text += f"📝 <b>Описание:</b> {ad.description[:50]}..." if ad.description and len(ad.description) > 50 else f"📝 <b>Описание:</b> {ad.description or 'Не указано'}\n"
    text += "\n\nВыберите, что хотите изменить:"
    return text


def _edit_menu_keyboard(ad) -> InlineKeyboardBuilder:
    """Клавиатура меню редактирования объявления"""
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text="📝 Изменить название", callback_data=f"admin:ads:edit:title:{ad.id}"))
    keyboard.row(InlineKeyboardButton(text="📄 Изменить описание", callback_data=f"admin:ads:edit:description:{ad.id}"))
    keyboard.row(InlineKeyboardButton(text="💰 Изменить цену", callback_data=f"admin:ads:edit:price:{ad.id}"))
    keyboard.row(InlineKeyboardButton(text="📍 Изменить город", callback_data=f"admin:ads:edit:city:{ad.id}"))
    keyboard.row(InlineKeyboardButton(text="📞 Изменить контакт", callback_data=f"admin:ads:edit:contact:{ad.id}"))
    keyboard.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:ads"))
    return keyboard


def _admin_cities_kb(ad_id: int) -> InlineKeyboardBuilder:
    """Клавиатура выбора города для админки (как у пользователей, callback admin:ads:edit:city_select:KEY:ad_id)."""
    from src.bot.keyboards.key_text import OTHER_CITY_BTN
    keyboard = InlineKeyboardBuilder()
    cities = [
        ("Калининград", "kaliningrad"),
        ("Владивосток", "vladivostok"),
        ("Екатеринбург", "ekb"),
        ("Новосибирск", "novosibirsk"),
        ("Казань", "kazan"),
        ("Нижний Новгород", "nn"),
        ("Самара", "samara"),
        ("Ростов-на-Дону", "rostov"),
        ("Краснодар", "krasnodar"),
        ("Сочи", "sochi"),
        ("Уфа", "ufa"),
        ("Челябинск", "chelyabinsk"),
        ("Пермь", "perm"),
        ("Тюмень", "tyumen"),
        ("Омск", "omsk"),
        ("Воронеж", "voronezh"),
        ("Красноярск", "krasnoyarsk"),
        ("Ижевск", "izhevsk"),
        ("Санкт-Петербург", "spb"),
        ("Москва", "moscow"),
    ]
    for i in range(0, len(cities), 2):
        row = cities[i : i + 2]
        keyboard.row(*[
            InlineKeyboardButton(text=name, callback_data=f"admin:ads:edit:city_select:{key}:{ad_id}")
            for name, key in row
        ])
    keyboard.row(InlineKeyboardButton(text=OTHER_CITY_BTN, callback_data=f"admin:ads:edit:city_select:other:{ad_id}"))
    keyboard.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"admin:ads:edit:back:{ad_id}"))
    return keyboard


async def admin_ads_edit_field(callback: types.CallbackQuery, state: FSMContext):
    """Начало редактирования конкретного поля"""
    await callback.answer()

    parts = callback.data.split(':')
    field = parts[3]  # title, description, price, city, contact
    ad_id = int(parts[4])

    await state.update_data(edit_ad_id=ad_id, edit_field=field)

    # Город — выбор кнопками, как у пользователей
    if field == 'city':
        await state.set_state(AdminPanelState.edit_ad_city_select)
        text = "📍 Выберите город:"
        keyboard = _admin_cities_kb(ad_id)
        try:
            msg = await callback.message.edit_text(text, parse_mode='HTML', reply_markup=keyboard.as_markup())
            await state.update_data(edit_field_msg_id=msg.message_id)
        except Exception:
            msg = await callback.message.answer(text, parse_mode='HTML', reply_markup=keyboard.as_markup())
            await state.update_data(edit_field_msg_id=msg.message_id)
        return

    # Контакт — отдельный поток (Telegram / телефон)
    if field == 'contact':
        await _admin_ads_edit_contact_start(callback, state, ad_id)
        return

    field_names = {
        'title': 'название',
        'description': 'описание',
        'price': 'цену',
    }
    state_map = {
        'title': AdminPanelState.edit_ad_title,
        'description': AdminPanelState.edit_ad_description,
        'price': AdminPanelState.edit_ad_price,
    }
    if field not in state_map:
        return
    await state.set_state(state_map[field])
    text = f"✏️ Введите новое значение для поля <b>{field_names[field]}</b>:"
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"admin:ads:edit:back:{ad_id}"))
    try:
        msg = await callback.message.edit_text(text, parse_mode='HTML', reply_markup=keyboard.as_markup())
        await state.update_data(edit_field_msg_id=msg.message_id)
    except Exception:
        msg = await callback.message.answer(text, parse_mode='HTML', reply_markup=keyboard.as_markup())
        await state.update_data(edit_field_msg_id=msg.message_id)


async def admin_ads_edit_field_input(message: types.Message, state: FSMContext):
    """Обработка ввода нового значения поля"""
    # Деактивируем кнопки в предыдущем сообщении
    data = await state.get_data()
    prev_msg_id = data.get('edit_field_msg_id')
    if prev_msg_id:
        try:
            await bot.edit_message_reply_markup(
                chat_id=message.chat.id,
                message_id=prev_msg_id,
                reply_markup=None
            )
        except:
            pass
    
    ad_id = data.get('edit_ad_id')
    field = data.get('edit_field')
    
    value = message.text.strip()
    
    # Валидация
    if field == 'price':
        try:
            value = int(value)
        except ValueError:
            await message.answer("❌ Цена должна быть числом.")
            return
    
    # Обновляем объявление
    update_data = {field: value}
    success = await update_ad(ad_id, **update_data)

    if success:
        logger.info(f"Админ {message.from_user.id} обновил объявление #{ad_id}: {field} = {value}")
        ad = await get_ad_by_id(ad_id)
        # Обновляем пост в канале, если объявление опубликовано (используем только что сохранённые значения)
        if ad.channel_message_id and ad.status == "approved":
            try:
                channel_target = f"@{CHANNEL_USERNAME}" if CHANNEL_USERNAME else CHANNEL_ID
                seller = await get_user_by_id(ad.seller_user_id)
                is_trusted = getattr(seller, "is_trusted_seller", False) if seller else False
                caption = format_active_caption(ad, is_trusted)
                await bot.edit_message_caption(
                    chat_id=channel_target,
                    message_id=ad.channel_message_id,
                    caption=caption,
                    parse_mode="HTML",
                    reply_markup=ad_in_channel_kb(ad_id, BOT_USERNAME),
                )
                logger.info(f"Сообщение объявления #{ad_id} в канале обновлено после редактирования админом")
            except Exception as e:
                logger.warning(f"Не удалось обновить пост в канале для объявления #{ad_id}: {e}")

        # Удаляем сообщение пользователя и редактируем сообщение бота на «Поле обновлено» с кнопкой «Назад»
        try:
            await message.delete()
        except Exception:
            pass
        success_text = "✅ Поле обновлено успешно!"
        back_kb = InlineKeyboardBuilder()
        back_kb.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"admin:ads:edit:back:{ad_id}"))
        if prev_msg_id:
            try:
                await bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=prev_msg_id,
                    text=success_text,
                    parse_mode="HTML",
                    reply_markup=back_kb.as_markup(),
                )
            except Exception:
                await message.answer(success_text, parse_mode="HTML", reply_markup=back_kb.as_markup())
        else:
            await message.answer(success_text, parse_mode="HTML", reply_markup=back_kb.as_markup())
    else:
        await message.answer(f"❌ Не удалось обновить объявление.")

    await state.set_state(AdminPanelState.edit_ad_menu)


async def admin_ads_edit_city_select(callback: types.CallbackQuery, state: FSMContext):
    """Обработка выбора города кнопкой (admin:ads:edit:city_select:KEY:ad_id)."""
    await callback.answer()
    parts = callback.data.split(':')
    # admin:ads:edit:city_select:KEY:ad_id
    if len(parts) < 5:
        return
    city_key = parts[4]
    ad_id = int(parts[5])
    data = await state.get_data()
    prev_msg_id = data.get('edit_field_msg_id')

    if city_key == 'other':
        await state.update_data(edit_ad_id=ad_id, edit_field='city')
        await state.set_state(AdminPanelState.edit_ad_city)
        text = "✏️ Введите название города:"
        keyboard = InlineKeyboardBuilder()
        keyboard.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"admin:ads:edit:back:{ad_id}"))
        try:
            msg = await callback.message.edit_text(text, parse_mode='HTML', reply_markup=keyboard.as_markup())
            await state.update_data(edit_field_msg_id=msg.message_id)
        except Exception:
            msg = await callback.message.answer(text, parse_mode='HTML', reply_markup=keyboard.as_markup())
            await state.update_data(edit_field_msg_id=msg.message_id)
        return

    if city_key not in DEFAULT_CITIES:
        await callback.answer("❌ Неизвестный город.", show_alert=True)
        return

    city = DEFAULT_CITIES[city_key]
    success = await update_ad(ad_id, city=city)
    if not success:
        await callback.answer("❌ Не удалось обновить город.", show_alert=True)
        return

    ad = await get_ad_by_id(ad_id)
    if ad.channel_message_id and ad.status == "approved":
        try:
            channel_target = f"@{CHANNEL_USERNAME}" if CHANNEL_USERNAME else CHANNEL_ID
            seller = await get_user_by_id(ad.seller_user_id)
            is_trusted = getattr(seller, "is_trusted_seller", False) if seller else False
            caption = format_active_caption(ad, is_trusted)
            await bot.edit_message_caption(
                chat_id=channel_target,
                message_id=ad.channel_message_id,
                caption=caption,
                parse_mode="HTML",
                reply_markup=ad_in_channel_kb(ad_id, BOT_USERNAME),
            )
        except Exception as e:
            logger.warning(f"Не удалось обновить пост в канале для объявления #{ad_id}: {e}")

    success_text = "✅ Поле обновлено успешно!"
    back_kb = InlineKeyboardBuilder()
    back_kb.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"admin:ads:edit:back:{ad_id}"))
    try:
        await callback.message.edit_text(success_text, parse_mode='HTML', reply_markup=back_kb.as_markup())
    except Exception:
        await callback.message.answer(success_text, parse_mode='HTML', reply_markup=back_kb.as_markup())
    await state.set_state(AdminPanelState.edit_ad_menu)


async def _admin_ads_edit_contact_start(callback: types.CallbackQuery, state: FSMContext, ad_id: int):
    """Показать выбор способа связи при редактировании контакта."""
    await state.update_data(edit_ad_id=ad_id, edit_field='contact')
    text = "📞 Выберите способ связи:"
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text="💬 Telegram", callback_data=f"admin:ads:edit:contact_choice:telegram:{ad_id}"))
    keyboard.row(InlineKeyboardButton(text="📱 Номер телефона", callback_data=f"admin:ads:edit:contact_choice:phone:{ad_id}"))
    keyboard.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"admin:ads:edit:back:{ad_id}"))
    try:
        msg = await callback.message.edit_text(text, parse_mode='HTML', reply_markup=keyboard.as_markup())
        await state.update_data(edit_field_msg_id=msg.message_id)
    except Exception:
        msg = await callback.message.answer(text, parse_mode='HTML', reply_markup=keyboard.as_markup())
        await state.update_data(edit_field_msg_id=msg.message_id)


async def admin_ads_edit_contact_choice(callback: types.CallbackQuery, state: FSMContext):
    """Обработка выбора способа связи: Telegram или телефон (admin:ads:edit:contact_choice:choice:ad_id)."""
    await callback.answer()
    parts = callback.data.split(':')
    if len(parts) < 5:
        return
    choice = parts[4]  # telegram | phone
    ad_id = int(parts[5])
    data = await state.get_data()
    prev_msg_id = data.get('edit_field_msg_id')

    if choice == 'telegram':
        ad = await get_ad_by_id(ad_id)
        if not ad:
            await callback.answer("❌ Объявление не найдено.", show_alert=True)
            return
        user = await get_user_by_id(ad.seller_user_id)
        if user:
            contact_value = f"@{user.username}" if user.username else f"tg://user?id={user.tg_user_id}"
        else:
            await callback.answer("❌ Пользователь не найден.", show_alert=True)
            return
        success = await update_ad(ad_id, contact_method=contact_value)
        if not success:
            await callback.answer("❌ Не удалось обновить контакт.", show_alert=True)
            return
        success_text = "✅ Контакт обновлён (Telegram)."
        back_kb = InlineKeyboardBuilder()
        back_kb.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"admin:ads:edit:back:{ad_id}"))
        try:
            await callback.message.edit_text(success_text, parse_mode='HTML', reply_markup=back_kb.as_markup())
        except Exception:
            await callback.message.answer(success_text, parse_mode='HTML', reply_markup=back_kb.as_markup())
        await state.set_state(AdminPanelState.edit_ad_menu)
        return

    if choice == 'phone':
        await state.set_state(AdminPanelState.edit_ad_contact_phone)
        await state.update_data(edit_ad_id=ad_id)
        text = "✏️ Введите номер телефона (11 цифр, без +):"
        keyboard = InlineKeyboardBuilder()
        keyboard.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"admin:ads:edit:back:{ad_id}"))
        try:
            msg = await callback.message.edit_text(text, parse_mode='HTML', reply_markup=keyboard.as_markup())
            await state.update_data(edit_field_msg_id=msg.message_id)
        except Exception:
            msg = await callback.message.answer(text, parse_mode='HTML', reply_markup=keyboard.as_markup())
            await state.update_data(edit_field_msg_id=msg.message_id)


async def admin_ads_edit_contact_phone_input(message: types.Message, state: FSMContext):
    """Ввод номера телефона при редактировании контакта админом (11 цифр)."""
    data = await state.get_data()
    ad_id = data.get('edit_ad_id')
    prev_msg_id = data.get('edit_field_msg_id')
    if not ad_id:
        await state.clear()
        return

    phone = message.text.strip().replace(' ', '').replace('-', '').replace('+', '')
    if not phone.isdigit() or len(phone) != 11:
        try:
            await message.delete()
        except Exception:
            pass
        err = "❌ Номер должен содержать ровно 11 цифр (без +). Введите ещё раз."
        keyboard = InlineKeyboardBuilder()
        keyboard.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"admin:ads:edit:back:{ad_id}"))
        if prev_msg_id:
            try:
                await bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=prev_msg_id,
                    text=err,
                    parse_mode='HTML',
                    reply_markup=keyboard.as_markup(),
                )
            except Exception:
                await message.answer(err, parse_mode='HTML', reply_markup=keyboard.as_markup())
        else:
            await message.answer(err, parse_mode='HTML', reply_markup=keyboard.as_markup())
        return

    success = await update_ad(ad_id, contact_method=phone)
    try:
        await message.delete()
    except Exception:
        pass

    if success:
        success_text = "✅ Контакт обновлён (телефон)."
    else:
        success_text = "❌ Не удалось обновить контакт."
    back_kb = InlineKeyboardBuilder()
    back_kb.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"admin:ads:edit:back:{ad_id}"))
    if prev_msg_id:
        try:
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=prev_msg_id,
                text=success_text,
                parse_mode='HTML',
                reply_markup=back_kb.as_markup(),
            )
        except Exception:
            await message.answer(success_text, parse_mode='HTML', reply_markup=back_kb.as_markup())
    else:
        await message.answer(success_text, parse_mode='HTML', reply_markup=back_kb.as_markup())
    await state.set_state(AdminPanelState.edit_ad_menu)


# === ПРОСМОТР ОБЪЯВЛЕНИЯ ===

async def admin_ads_view_start(callback: types.CallbackQuery, state: FSMContext):
    """Начало просмотра объявления"""
    await callback.answer()
    
    await state.set_state(AdminPanelState.view_ad_input)
    
    text = "👁 <b>Просмотр объявления</b>\n\nУкажите номер объявления:"
    
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:ads"))
    
    try:
        msg = await callback.message.edit_text(text, parse_mode='HTML', reply_markup=keyboard.as_markup())
        await state.update_data(view_ad_msg_id=msg.message_id)
    except:
        msg = await callback.message.answer(text, parse_mode='HTML', reply_markup=keyboard.as_markup())
        await state.update_data(view_ad_msg_id=msg.message_id)


async def admin_ads_view_input(message: types.Message, state: FSMContext):
    """Обработка ввода номера объявления для просмотра"""
    # Деактивируем кнопки в предыдущем сообщении
    data = await state.get_data()
    prev_msg_id = data.get('view_ad_msg_id')
    if prev_msg_id:
        try:
            await bot.edit_message_reply_markup(
                chat_id=message.chat.id,
                message_id=prev_msg_id,
                reply_markup=None
            )
        except:
            pass
    
    try:
        ad_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Неверный формат. Укажите числовой ID объявления.")
        return
    
    ad = await get_ad_by_id(ad_id)
    if not ad:
        await message.answer(f"❌ Объявление #{ad_id} не найдено.")
        return
    
    # Получаем информацию об авторе
    seller = await get_user_by_id(ad.seller_user_id)
    
    # Получаем количество объявлений и средний рейтинг автора
    async with async_session() as session:
        result = await session.execute(
            select(func.count(Ad.id)).where(Ad.seller_user_id == ad.seller_user_id)
        )
        seller_ads_count = result.scalar()
        
        # Получаем средний рейтинг из отзывов
        result = await session.execute(
            select(func.avg(Review.rating)).where(Review.reviewed_user_id == ad.seller_user_id)
        )
        avg_rating = result.scalar()
        seller_rating = round(avg_rating, 1) if avg_rating else 0
    
    # Формируем текст
    text = f"👁 <b>Объявление #{ad.id}</b>\n\n"
    text += f"<b>{ad.title}</b>\n\n"
    ad_type_text = getattr(ad, 'ad_type', 'Продажа')
    text += f"💰 <b>Цена:</b> {ad.price} ₽\n"
    text += f"📋 <b>Тип:</b> {ad_type_text}\n"
    text += f"📍 <b>Город:</b> {ad.city}"
    if ad.country:
        text += f", {ad.country}"
    text += "\n"
    text += f"📦 <b>Категория:</b> {ad.category} → {ad.subcategory}\n"
    if ad.size:
        text += f"📏 <b>Размер:</b> {ad.size}\n"
    text += f"♻️ <b>Состояние:</b> {ad.condition}\n"
    if ad.description:
        text += f"\n📝 <b>Описание:</b>\n{ad.description}\n"
    text += f"\n📊 <b>Статус:</b> {ad.status}\n"
    text += f"📅 <b>Создано:</b> {ad.created_at.strftime('%d.%m.%Y %H:%M')}\n"
    
    text += f"\n👤 <b>АВТОР:</b>\n"
    if seller:
        text += f"Имя: {seller.first_name or 'Не указано'}\n"
        if seller.username:
            text += f"Username: @{seller.username}\n"
        else:
            text += "Username: Не указан\n"
        text += f"ID: {seller.tg_user_id}\n"
        text += f"📦 Всего объявлений: {seller_ads_count}\n"
        text += f"⭐️ Рейтинг: {seller_rating}/5\n"
    
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:ads"))
    
    await message.answer(text, parse_mode='HTML', reply_markup=keyboard.as_markup())
    await state.clear()


# === РАЗДЕЛ "МОДЕРАТОРЫ" ===
# === НАВИГАЦИЯ ===

async def admin_edit_back(callback: types.CallbackQuery, state: FSMContext):
    """Возврат к меню редактирования объявления — редактируем текущее сообщение, не отправляем новое."""
    await callback.answer()

    ad_id = int(callback.data.split(':')[-1])
    ad = await get_ad_by_id(ad_id)

    if not ad:
        await callback.answer("❌ Объявление не найдено.", show_alert=True)
        return

    await state.set_state(AdminPanelState.edit_ad_menu)
    await state.update_data(edit_ad_id=ad_id)

    text = _edit_menu_text(ad)
    keyboard = _edit_menu_keyboard(ad)
    try:
        await callback.message.edit_text(text, parse_mode='HTML', reply_markup=keyboard.as_markup())
    except Exception:
        await callback.message.answer(text, parse_mode='HTML', reply_markup=keyboard.as_markup())


# === РЕГИСТРАЦИЯ ОБРАБОТЧИКОВ ===

# ============================================================
