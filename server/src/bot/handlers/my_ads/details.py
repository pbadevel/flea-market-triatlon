"""
Обработчики для раздела "Мои объявления"
"""
import os
from aiogram import Dispatcher, types, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton, BufferedInputFile, FSInputFile
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
from src.bot.settings.settings import TEST_MODE
from src.bot.utils.image_utils import add_logo_watermark_to_photo
from src.bot.utils.helpers import get_full_storage_path
from src.bot.loader import bot
from src.bot.handlers.add_ad import send_to_moderation, send_edit_to_moderation
from sqlalchemy import delete
from src.bot.database.methods import async_session
from math import ceil

MY_ADS_PER_PAGE = 10


from ._common import _show_my_ads_page, delete_my_ad_info_message, needs_size

async def my_ad_details_callback(callback: types.CallbackQuery, state: FSMContext):
    """Просмотр деталей объявления"""
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

    # Возврат с экрана поднятия: редактируем текущее сообщение на "Выберите действие:", не удаляем и не шлём новые
    current_text = (callback.message.text or callback.message.caption or "")
    if "Поднятие объявления" in current_text or "поднято!" in current_text.lower():
        keyboard = InlineKeyboardBuilder()
        is_pending = ad.status == AdStatus.pending.value or ad.status == "pending"
        has_edit_on_mod = (ad.status == AdStatus.approved.value or ad.status == "approved") and await exists_edit_for_ad(ad_id)
        on_moderation = is_pending or has_edit_on_mod
        if on_moderation:
            pass
        else:
            if ad.status == AdStatus.approved.value or ad.status == "approved":
                keyboard.row(
                    InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"my_ad_edit:{ad.id}"),
                    InlineKeyboardButton(text="🚀 Поднять", callback_data=f"my_ad_boost:{ad.id}")
                )
            elif ad.status == AdStatus.rejected.value:
                keyboard.row(InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"my_ad_edit_rejected:{ad.id}"))
            elif ad.status in ("unpublished", "removed", "paused"):
                keyboard.row(InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"my_ad_edit:{ad.id}"))
                keyboard.row(InlineKeyboardButton(text=SEND_TO_MODERATION_BTN, callback_data=f"my_ad_republish:{ad.id}"))
            if (ad.status == AdStatus.approved.value or ad.status == "approved"):
                keyboard.row(
                    InlineKeyboardButton(text="📴 Снять с публикации", callback_data=f"my_ad_unpublish_confirm:{ad.id}")
                )
        keyboard.row(InlineKeyboardButton(text=BACK_BTN, callback_data="back_from_ad_details"))
        try:
            await callback.message.edit_text("Выберите действие:", reply_markup=keyboard.as_markup())
        except Exception:
            await callback.message.answer("Выберите действие:", reply_markup=keyboard.as_markup())
        return
    
    # Получаем фото
    photos = await get_ad_photos(ad_id)
    
    # Формируем текст
    status_text = {
        AdStatus.pending.value: "⏳ На модерации",
        AdStatus.approved.value: "✅ Одобрено",
        AdStatus.rejected.value: "❌ Отклонено",
        AdStatus.sold.value: "✅ <b>ПРОДАНО</b>",
        'unpublished': "📴 Снято с публикации",
        'paused': "⏸️ Снято автоматически (нет ответа 7 дней)" if not TEST_MODE else "⏸️ Снято автоматически (нет ответа 35 мин)",
    }
    # старые записи в БД могли иметь status='removed' — показываем как «Снято с публикации»
    if ad.status == 'removed':
        status_str = "📴 Снято с публикации"
    else:
        status_str = status_text.get(ad.status, ad.status)
    if (ad.status == AdStatus.approved.value or ad.status == "approved") and await exists_edit_for_ad(ad_id):
        status_str = "✅ Одобрено (редактирование на модерации)"
    
    text = f"📦 <b>Объявление #{ad.id}</b>\n\n"
    text += f"📝 <b>Название:</b> {ad.title}\n"
    text += f"💰 <b>Цена:</b> {ad.price} ₽\n"
    ad_type_text = getattr(ad, 'ad_type', 'Продажа')
    text += f"📋 <b>Тип:</b> {ad_type_text}\n"
    text += f"📍 <b>Город:</b> {ad.city}\n"
    if ad.country:
        text += f"🌍 <b>Страна:</b> {ad.country}\n"
    # Статус отображается с форматированием (жирным для "Продано")
    text += f"📊 <b>Статус:</b> {status_str}\n"
    # Показываем причину отклонения только если объявление действительно отклонено
    if ad.status == AdStatus.rejected.value and ad.rejection_reason:
        text += f"❌ <b>Причина отклонения:</b> {ad.rejection_reason}\n"
    if ad.description:
        text += f"\n📝 <b>Описание:</b>\n{ad.description}\n"
    
    # Для проданных и снятых с публикации - добавляем информацию в текст
    if ad.status == 'sold':
        text += "\n⚠️ <b>Объявление продано. Редактирование недоступно.</b>\n"
    elif ad.status in ('unpublished', 'removed'):
        text += "\n📴 <b>Объявление снято с публикации. Вы можете редактировать его.</b>\n"
    
    # Первое сообщение: фото + вся информация об объявлении
    ad_info_msg = None
    info_msg_ids = []  # ID всех сообщений с информацией об объявлении (включая все фото медиа-группы)
    if photos:
        # Отправляем все фото как медиа-группу, если их больше одного
        if len(photos) > 1:
            media_group = []
            for i, photo in enumerate(photos):
                photo_union = photo.file_id

                if (not photo.file_id) and photo.storage_path:
                    # Проверяем, существует ли файл физически на диске
                    if os.path.exists(get_full_storage_path(photo.storage_path)):
                        # Безопаснее прочитать файл в память, чтобы aiohttp не падал на отправке body
                        with open(get_full_storage_path(photo.storage_path), "rb") as f:
                            file_bytes = f.read()
                        file_name = os.path.basename(get_full_storage_path(photo.storage_path))
                        photo_union = BufferedInputFile(file_bytes, filename=file_name)
                    else:
                        logger.error(f"Файл не найден по пути: {get_full_storage_path(photo.storage_path)}")
                        continue  # Пропускаем это фото, чтобы не ломать всю отправку

                if not photo_union:
                    continue # Защита на случай, если нет ни file_id, ни файла на диске

                if i == 0 or len(media_group) == 0:
                    # Первое фото (или первое валидное) с подписью (текст объявления)
                    media_group.append(types.InputMediaPhoto(media=photo_union, caption=text, parse_mode='HTML'))
                else:
                    # Остальные фото без подписи
                    media_group.append(types.InputMediaPhoto(media=photo_union))
            
            if media_group:
                # Отправляем медиа-группу
                try:
                    sent_messages = await callback.message.answer_media_group(media_group)
                    # Сохраняем ID всех сообщений группы
                    info_msg_ids = [m.message_id for m in sent_messages] if sent_messages else []
                    ad_info_msg = sent_messages[0] if sent_messages else None
                except Exception as e:
                    logger.exception(f"Ошибка при отправке медиагруппы: {e}")
                    # Тут можно сделать резервный вариант (например, отправить текст обычным сообщением)
            else:
                logger.warning("Медиагруппа оказалась пустой после проверки файлов.")
        else:

            photo_union = photos[0].file_id
            
            if (not photos[0].file_id) and photos[0].storage_path:
                photo_union = FSInputFile(photos[0].storage_path)

            # Если одно фото, отправляем как обычное сообщение
            ad_info_msg = await callback.message.answer_photo(
                photo=photo_union,
                caption=text,
                parse_mode='HTML'
            )
            info_msg_ids = [ad_info_msg.message_id]
    else:
        # Если фото нет, отправляем только текст
        ad_info_msg = await callback.message.answer(text, parse_mode='HTML')
        info_msg_ids = [ad_info_msg.message_id]
    
    # Сохраняем ID всех сообщений в state для последующего удаления
    await state.update_data(
        my_ad_info_msg_id=ad_info_msg.message_id,
        my_ad_info_msg_ids=info_msg_ids,
        my_ad_id=ad_id,
        my_ad_chat_id=callback.message.chat.id,
    )
    
    # Второе сообщение: "Выберите действие" + кнопки
    keyboard = InlineKeyboardBuilder()
    is_pending = ad.status == AdStatus.pending.value or ad.status == "pending"
    has_edit_on_mod = (ad.status == AdStatus.approved.value or ad.status == "approved") and await exists_edit_for_ad(ad_id)
    on_moderation = is_pending or has_edit_on_mod  # на модерации: новое или редактирование

    # На модерации: только "Назад" (без Редактировать, Продано и Снять с публикации)
    if on_moderation:
        pass
    else:
        # Редактировать для одобренных, отклонённых, снятых
        if ad.status == AdStatus.approved.value or ad.status == "approved":
            keyboard.row(
                InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"my_ad_edit:{ad.id}"),
                InlineKeyboardButton(text="🚀 Поднять", callback_data=f"my_ad_boost:{ad.id}")
            )
        elif ad.status == AdStatus.rejected.value:
            keyboard.row(InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"my_ad_edit_rejected:{ad.id}"))
        elif ad.status in ("unpublished", "removed", "paused"):
            keyboard.row(InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"my_ad_edit:{ad.id}"))
            keyboard.row(InlineKeyboardButton(text=SEND_TO_MODERATION_BTN, callback_data=f"my_ad_republish:{ad.id}"))

        # Снять с публикации только для одобренных без редактирования на модерации
        if (ad.status == AdStatus.approved.value or ad.status == "approved"):
            keyboard.row(
                InlineKeyboardButton(text="📴 Снять с публикации", callback_data=f"my_ad_unpublish_confirm:{ad.id}")
            )

    keyboard.row(InlineKeyboardButton(text=BACK_BTN, callback_data="back_from_ad_details"))
    action_msg = "Выберите действие:"
    await callback.message.answer(action_msg, reply_markup=keyboard.as_markup())
    try:
        await callback.message.delete()
    except:
        pass


async def back_from_ad_details_callback(callback: types.CallbackQuery, state: FSMContext):
    """Возврат к списку 'Мои объявления' из деталей объявления"""
    await callback.answer()
    
    # Удаляем первое сообщение с информацией об объявлении
    data = await state.get_data()
    chat_id = data.get('my_ad_chat_id', callback.message.chat.id)
    await delete_my_ad_info_message(state, chat_id)
    
    # Сохраняем ID текущего сообщения для удаления
    current_msg_id = callback.message.message_id
    
    # Очищаем состояние
    await state.clear()
    
    # Возвращаемся к списку "Мои объявления"
    # Получаем все объявления пользователя
    user = await get_user_by_tg_id(callback.from_user.id)
    if not user:
        from src.bot.handlers.start import send_main_menu
        await send_main_menu(callback, state=state)
        try:
            await callback.message.delete()
        except:
            pass
        return
    
    ads = await get_user_ads(user.id)
    
    if not ads:
        text = "📭 У вас пока нет объявлений."
        keyboard = InlineKeyboardBuilder()
        keyboard.row(InlineKeyboardButton(text=BACK_BTN, callback_data="back_to_menu"))
        
        try:
            await callback.message.edit_text(text, reply_markup=keyboard.as_markup())
        except:
            await callback.message.answer(text, reply_markup=keyboard.as_markup())
            try:
                await callback.message.delete()
            except:
                pass
        return
    
    await _show_my_ads_page(callback, ads, page=0, edit=True, state=state)
    
    # Удаляем предыдущие сообщения (фото объявления и т.д.)
    try:
        for i in range(1, 11):
            try:
                msg_id_to_delete = current_msg_id - i
                if msg_id_to_delete > 0:
                    await bot.delete_message(chat_id=chat_id, message_id=msg_id_to_delete)
            except:
                pass
    except:
        pass


async def my_ad_edit_rejected_callback(callback: types.CallbackQuery, state: FSMContext):
    """Редактирование отклоненного объявления - сразу отправляем на модерацию"""
    await callback.answer()
    
    # НЕ удаляем первое сообщение с информацией об объявлении - оно должно оставаться для справки
    # Удалим его только после отправки на модерацию
    
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
    
    # Проверяем статус
    if ad.status != AdStatus.rejected.value:
        await callback.answer("❌ Можно редактировать только отклоненные объявления.", show_alert=True)
        return
    
    # Для отклоненных объявлений сразу переходим к редактированию других параметров
    await state.update_data(editing_ad_id=ad_id, is_rejected_ad=True)
    await state.set_state(MyAdsState.edit_other)
    
    text = f"📝 <b>Редактирование отклоненного объявления #{ad.id}</b>\n\n"
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
    keyboard.row(InlineKeyboardButton(text=BACK_BTN, callback_data=f"my_ad:{ad_id}"))
    
    await callback.message.answer(text, parse_mode='HTML', reply_markup=keyboard.as_markup())
    try:
        await callback.message.delete()
    except:
        pass


