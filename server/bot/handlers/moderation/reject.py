"""
Обработчик модерации объявлений
"""

from aiogram import Dispatcher, types, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import InputMediaPhoto
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton
from loguru import logger
from src.bot.logging_config import log_moderation

from src.bot.database.states import ModerationState
from src.bot.database.methods import (
    get_ad_by_id, get_ad_photos, approve_ad, reject_ad,
    get_user_by_id, is_moderator,
    get_ad_edit, get_edit_photos, apply_ad_edit, delete_ad_edit_return_info,
)
from src.bot.keyboards.keyboards import *
from src.bot.keyboards.key_text import *
from src.bot.settings.constants import *
from src.bot.settings.settings import CHANNEL_ID, CHANNEL_USERNAME, MODERATION_CHAT_ID, BOT_USERNAME
from src.bot.loader import bot


# === ОДОБРЕНИЕ ===

# === ОТКЛОНЕНИЕ ===

async def reject_ad_callback(callback: types.CallbackQuery, state: FSMContext):
    """Начать процесс отклонения объявления"""
    await callback.answer()
    
    # Проверяем права модератора
    user_id = callback.from_user.id
    is_mod = await is_moderator(user_id)
    logger.info(f"🔵 Проверка прав для отклонения: user {user_id}, is_moderator: {is_mod}")
    
    if not is_mod:
        from src.bot.settings.settings import ADMIN_IDS
        logger.warning(f"🔴 User {user_id} не является модератором! ADMIN_IDS={ADMIN_IDS}")
        await callback.answer("❌ У вас нет прав модератора.", show_alert=True)
        return
    
    ad_id = int(callback.data.split(':')[1])
    
    # Получаем объявление
    ad = await get_ad_by_id(ad_id)
    if not ad:
        await callback.answer("❌ Объявление не найдено.", show_alert=True)
        return
    
    if ad.status != 'pending':
        await callback.answer("❌ Объявление уже обработано.", show_alert=True)
        return
    
    # деактивируем кнопки
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except:
        pass
    
    # Сохраняем ID объявления в состоянии
    await state.update_data(rejecting_ad_id=ad_id)
    await state.set_state(ModerationState.rejection_reason)
    
    # Редактируем текущее сообщение на выбор причины отклонения
    rejection_message = f"Выберите причину отклонения для объявления #{ad_id}:"
    try:
        await callback.message.edit_text(
            rejection_message,
            reply_markup=rejection_reasons_kb()
        )
    except:
        # Если не удалось отредактировать, отправляем новое
        await callback.message.answer(
            rejection_message,
            reply_markup=rejection_reasons_kb()
        )


async def rejection_reason_callback(callback: types.CallbackQuery, state: FSMContext):
    """Обработка выбора причины отклонения"""
    await callback.answer()
    
    reason_key = callback.data.split(':')[1]
    
    if reason_key == 'other':
        await state.update_data(last_rejection_msg_id=callback.message.message_id)
        try:
            await callback.message.edit_text(REJECTION_OTHER_MESSAGE)
        except Exception:
            msg = await callback.message.answer(REJECTION_OTHER_MESSAGE)
            await state.update_data(last_rejection_msg_id=msg.message_id)
        return
    
    reason = REJECTION_REASONS[reason_key]
    await state.update_data(moderator_user_id=callback.from_user.id, moderator_username=callback.from_user.username or callback.from_user.first_name)

    data = await state.get_data()
    if data.get("rejecting_edit_id"):
        await process_rejection_edit(callback.message, state, reason)
    else:
        await process_rejection_with_edit(callback.message, state, reason)


async def rejection_back_callback(callback: types.CallbackQuery, state: FSMContext):
    """Вернуться к кнопкам Одобрить/Отклонить после выбора 'Отклонить'"""
    await callback.answer()

    data = await state.get_data()
    edit_id = data.get("rejecting_edit_id")
    ad_id = data.get("rejecting_ad_id")

    if edit_id:
        edit = await get_ad_edit(edit_id)
        if not edit:
            await callback.answer("Не удалось восстановить редактирование.", show_alert=True)
            await state.clear()
            return
        try:
            await callback.message.edit_text(
                f"Модерация редактирования (оригинал #{edit.original_ad_id}):",
                reply_markup=moderation_edit_kb(edit_id)
            )
        except Exception as e:
            logger.error(f"Ошибка при возврате из причин отклонения редактирования (edit_id={edit_id}): {e}")
        await state.clear()
        return

    if not ad_id:
        await callback.answer("Не удалось восстановить объявление.", show_alert=True)
        await state.clear()
        return

    try:
        await callback.message.edit_text(
            f"Модерация объявления #{ad_id}:",
            reply_markup=moderation_kb(int(ad_id))
        )
    except Exception as e:
        logger.error(f"Ошибка при возврате из причин отклонения (ad_id={ad_id}): {e}")
    await state.clear()


async def rejection_reason_text_handler(message: types.Message, state: FSMContext):
    """Обработка ввода текстовой причины отклонения"""
    reason = message.text.strip()
    
    if not reason:
        await message.answer("❌ Причина не может быть пустой.")
        return
    
    # Удаляем сообщение пользователя
    try:
        await message.delete()
    except:
        pass
    
    data = await state.get_data()
    last_msg_id = data.get('last_rejection_msg_id')
    await state.update_data(moderator_user_id=message.from_user.id, moderator_username=message.from_user.username or message.from_user.first_name)

    class FakeMessage:
        def __init__(self, chat_id, message_id):
            self.chat = types.Chat(id=chat_id, type="private")
            self.message_id = message_id
            self.text = ""
            self.from_user = message.from_user

        async def edit_text(self, text, parse_mode=None, reply_markup=None):
            await bot.edit_message_text(chat_id=self.chat.id, message_id=self.message_id, text=text, parse_mode=parse_mode, reply_markup=reply_markup)

    if last_msg_id:
        fake_msg = FakeMessage(message.chat.id, last_msg_id)
        if data.get("rejecting_edit_id"):
            await process_rejection_edit(fake_msg, state, reason)
        else:
            await process_rejection_with_edit(fake_msg, state, reason)
    else:
        if data.get("rejecting_edit_id"):
            await process_rejection_edit(message, state, reason)
        else:
            await process_rejection(message, state, reason)


async def process_rejection_with_edit(message: types.Message, state: FSMContext, reason: str):
    """Обработать отклонение объявления с редактированием сообщения"""
    data = await state.get_data()
    ad_id = data.get('rejecting_ad_id')
    
    if not ad_id:
        try:
            await message.edit_text("❌ Ошибка: объявление не найдено.")
        except:
            await message.answer("❌ Ошибка: объявление не найдено.")
        await state.clear()
        return
    
    # отклоняем
    logger.info(f"отклоняю объявление #{ad_id} с причиной: {reason}")
    await reject_ad(ad_id, reason)
    
    # получаем инфо
    ad = await get_ad_by_id(ad_id)
    if not ad:
        logger.error(f"объявление #{ad_id} не найдено после отклонения")
        try:
            await message.edit_text("❌ Ошибка: объявление не найдено.")
        except:
            await message.answer("❌ Ошибка: объявление не найдено.")
        await state.clear()
        return
    
    seller = await get_user_by_id(ad.seller_user_id)
    
    # уведомляем продавца
    if seller:
        try:
            notification_text = AD_REJECTED_MESSAGE.format(title=ad.title, reason=reason)
            logger.info(f"отправляю уведомление продавцу {seller.tg_user_id} об отклонении объявления #{ad_id}")
            
            from aiogram.utils.keyboard import InlineKeyboardBuilder
            from aiogram.types import InlineKeyboardButton
            keyboard = InlineKeyboardBuilder()
            keyboard.row(InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"my_ad_edit_rejected:{ad_id}"))
            keyboard.row(InlineKeyboardButton(text="🏠 В главное меню", callback_data="main_menu"))
            
            await bot.send_message(
                chat_id=seller.tg_user_id,
                text=notification_text,
                parse_mode='HTML',
                reply_markup=keyboard.as_markup()
            )
            logger.info(f"уведомление продавцу {seller.tg_user_id} успешно отправлено")
        except Exception as e:
            logger.error(f"ошибка уведомления продавца {seller.tg_user_id} об отклонении объявления #{ad_id}: {e}", exc_info=True)
    else:
        logger.warning(f"продавец объявления #{ad_id} не найден, уведомление не отправлено")
    
    # Редактируем сообщение модератора на результат отклонения
    result_text = f"❌ Объявление #{ad_id} отклонено.\nПричина: {reason}"
    try:
        await message.edit_text(result_text)
    except:
        # Если не удалось отредактировать, отправляем новое
        await message.answer(result_text)
    
    # логируем
    data = await state.get_data()
    user_id = data.get('moderator_user_id')
    mod_username = data.get('moderator_username', 'Unknown')
    if not user_id and hasattr(message, 'from_user') and message.from_user:
        user_id = message.from_user.id
        mod_username = message.from_user.username or message.from_user.first_name or 'Unknown'
    if user_id:
        log_moderation(user_id, mod_username, ad_id, "отклонил", reason)
    
    await state.clear()


async def process_rejection(message: types.Message, state: FSMContext, reason: str):
    """Обработать отклонение объявления (старая версия для совместимости)"""
    await process_rejection_with_edit(message, state, reason)


# === МОДЕРАЦИЯ РЕДАКТИРОВАНИЯ (КОПИЯ ОБЪЯВЛЕНИЯ) ===

async def reject_edit_callback(callback: types.CallbackQuery, state: FSMContext):
    """Начать процесс отклонения редактирования: показать причины (как для объявлений)."""
    await callback.answer()
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

    if not await is_moderator(callback.from_user.id):
        await callback.answer("❌ У вас нет прав модератора.", show_alert=True)
        return

    edit_id = int(callback.data.split(":")[1])
    edit = await get_ad_edit(edit_id)
    if not edit:
        await callback.answer("❌ Копия объявления не найдена.", show_alert=True)
        return

    original_ad_id = edit.original_ad_id
    await state.update_data(rejecting_edit_id=edit_id)
    await state.set_state(ModerationState.rejection_reason)

    msg = f"Выберите причину отклонения для редактирования (оригинал #{original_ad_id}):"
    try:
        await callback.message.edit_text(msg, reply_markup=rejection_reasons_kb())
    except Exception:
        await callback.message.answer(msg, reply_markup=rejection_reasons_kb())


async def process_rejection_edit(message: types.Message, state: FSMContext, reason: str):
    """Отклонить редактирование: удалить копию, уведомить продавца с причиной. Оригинал не трогаем."""
    data = await state.get_data()
    edit_id = data.get("rejecting_edit_id")
    if not edit_id:
        try:
            await message.edit_text("❌ Ошибка: копия объявления не найдена.")
        except Exception:
            await message.answer("❌ Ошибка: копия объявления не найдена.")
        await state.clear()
        return

    info = await delete_ad_edit_return_info(edit_id)
    if not info:
        try:
            await message.edit_text("❌ Копия объявления не найдена.")
        except Exception:
            await message.answer("❌ Копия объявления не найдена.")
        await state.clear()
        return

    title, seller_user_id, original_ad_id = info
    title_display = (title[:25] + "...") if len(title) > 25 else title

    seller = await get_user_by_id(seller_user_id)
    if seller:
        try:
            text = f"Редактирование объявления с названием «{title_display}» не одобрено.\nПричина: {reason}"
            await bot.send_message(
                seller.tg_user_id,
                text,
                reply_markup=InlineKeyboardBuilder().row(InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")).as_markup(),
            )
        except Exception as e:
            logger.error(f"уведомление продавца об отклонении редактирования: {e}")

    result_text = f"❌ Редактирование (оригинал #{original_ad_id}) отклонено.\nПричина: {reason}"
    try:
        await message.edit_text(result_text)
    except Exception:
        await message.answer(result_text)

    uid = data.get("moderator_user_id") or (message.from_user.id if getattr(message, "from_user", None) else None)
    uname = data.get("moderator_username") or (getattr(message.from_user, "username", None) or getattr(message.from_user, "first_name", None) if getattr(message, "from_user", None) else "Unknown")
    if uid:
        log_moderation(uid, uname, original_ad_id, "отклонил редактирование", reason)
    await state.clear()


