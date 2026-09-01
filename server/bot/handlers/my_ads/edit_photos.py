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


from ._common import *

# === РЕДАКТИРОВАНИЕ ОБЛОЖКИ ===

async def my_ad_edit_cover_photo_handler(message: types.Message, state: FSMContext):
    """Обработчик загрузки обложки при редактировании"""
    if not message.photo:
        await message.answer(PHOTO_ERROR_MESSAGE)
        return
    
    # Удаляем само фото пользователя
    try:
        await message.delete()
    except:
        pass
    
    # Получаем исходный file_id (берем самое большое фото)
    original_file_id = message.photo[-1].file_id
    logger.debug(f"получено фото обложки с file_id: {original_file_id}")
    
    # Создаем обработанную версию обложки (обрезанную + логотип) для карточек
    processed_cover_file_id = None
    try:
        logger.debug(f"начинаю обработку обложки: сначала обрезка...")
        # Сначала обрезаем изображение по центру
        from src.bot.utils.image_utils import crop_image_center
        cropped_file_id = await crop_image_center(
            file_id=original_file_id,
            chat_id=message.chat.id,
            bot=bot
        )
        logger.debug(f"обложка обрезана, новый file_id: {cropped_file_id}")
        
        # Определяем тип объявления для выбора логотипа
        data = await state.get_data()
        ad_id = data.get('editing_ad_id')
        if ad_id:
            from src.bot.database.methods import get_ad_by_id
            ad = await get_ad_by_id(ad_id)
            if ad:
                ad_type = getattr(ad, 'ad_type', 'Продажа')
                if ad_type == 'Аренда':
                    logo_path = "assets/logo_rent.png"
                    logger.debug("накладываю логотип на обрезанную обложку (assets/logo_rent.png)...")
                else:
                    logo_path = "assets/logo_sale.png"
                    logger.debug("накладываю логотип на обрезанную обложку (assets/logo_sale.png)...")
            else:
                logo_path = "assets/logo_sale.png"
                logger.debug("объявление не найдено, использую logo_sale.png по умолчанию")
        else:
            logo_path = "assets/logo_sale.png"
            logger.debug("ad_id не найден, использую logo_sale.png по умолчанию")
        
        # Добавляем логотип типа объявления (Продажа/Аренда) на обрезанное изображение
        processed_cover_file_id = await add_logo_watermark_to_photo(
            file_id=cropped_file_id,
            chat_id=message.chat.id,
            bot=bot,
            logo_path=logo_path
        )
        logger.debug(f"обложка обработана (обрезана и с логотипом типа), новый file_id: {processed_cover_file_id}")
        
        # Если у продавца объявления статус «Доверенный продавец» — накладываем логотип (18% от ширины)
        # Пока закомментирована вставка второго лого (для доверенного продавца)
        # if ad:
        #     seller = await get_user_by_id(ad.seller_user_id)
        #     if seller and getattr(seller, 'is_trusted_seller', False):
        #         try:
        #             from src.bot.utils.image_utils import add_trusted_seller_logo_to_photo
        #             processed_cover_file_id = await add_trusted_seller_logo_to_photo(
        #                 file_id=processed_cover_file_id,
        #                 chat_id=message.chat.id,
        #                 bot=bot,
        #                 logo_path="assets/logo.png"
        #             )
        #             logger.debug(f"наложен логотип доверенного продавца на обложку при редактировании, file_id: {processed_cover_file_id}")
        #         except Exception as e_trusted:
        #             logger.warning(f"не удалось наложить логотип доверенного продавца: {e_trusted}")
    except Exception as e:
        logger.error(f"ошибка при обработке обложки: {e}", exc_info=True)
        logger.warning(f"будет использоваться оригинал обложки в качестве обработанной версии")
        processed_cover_file_id = original_file_id
    
    # ВАЖНО: сохраняем ОРИГИНАЛЬНОЕ фото в photos (для деталей, модерации, предпросмотра)
    # А обработанную версию (с обоими логами при наличии статуса) — в cover_photo_file_id; при сохранении она попадёт в ad.cover_file_id в БД
    photos = [{'file_id': original_file_id, 'position': 1}]
    await state.update_data(photos=photos, cover_photo_file_id=processed_cover_file_id)
    
    # Получаем ID предыдущего сообщения для редактирования
    data = await state.get_data()
    cover_photo_request_msg_id = data.get('cover_photo_request_msg_id')
    
    # Текст подтверждения
    confirmation_text = "✅ Вот изображение вашей обложки, проверьте.\n"
    confirmation_text += "(_Если хотите изменить изображение, просто отправьте другое изображение и бот подставит его._)"
    
    from src.bot.keyboards.keyboards import cover_photo_kb
    
    # Показываем пользователю ОРИГИНАЛ (без обрезки и лого). Обработанная версия сохранена в cover_photo_file_id для канала/каталога.
    display_file_id = original_file_id
    
    # Редактируем текущее сообщение, добавляя фото
    if cover_photo_request_msg_id:
        try:
            # Пытаемся отредактировать сообщение, добавив фото
            await bot.edit_message_media(
                chat_id=message.chat.id,
                message_id=cover_photo_request_msg_id,
                media=types.InputMediaPhoto(media=display_file_id, caption=confirmation_text, parse_mode='Markdown'),
                reply_markup=cover_photo_kb()
            )
            await state.update_data(cover_photo_msg_id=cover_photo_request_msg_id, last_photo_msg_id=cover_photo_request_msg_id)
            return
        except Exception as e:
            logger.debug(f"Не удалось отредактировать сообщение с фото: {e}")
            # Если не удалось отредактировать (например, сообщение было текстовым), отправляем новое
            try:
                await bot.delete_message(chat_id=message.chat.id, message_id=cover_photo_request_msg_id)
            except:
                pass
    
    # Если не удалось отредактировать - отправляем новое сообщение с фото
    try:
        photo_msg = await bot.send_photo(
            chat_id=message.chat.id,
            photo=display_file_id,
            caption=confirmation_text,
            parse_mode='Markdown',
            reply_markup=cover_photo_kb()
        )
        await state.update_data(cover_photo_msg_id=photo_msg.message_id, last_photo_msg_id=photo_msg.message_id)
    except Exception as e:
        logger.error(f"ошибка при отправке обложки: {e}", exc_info=True)
        # Если не удалось отправить фото, отправляем текстовое сообщение
        msg = await message.answer(
            confirmation_text,
            parse_mode='Markdown',
            reply_markup=cover_photo_kb()
        )
        await state.update_data(cover_photo_msg_id=msg.message_id, last_photo_msg_id=msg.message_id)


async def my_ad_edit_cover_photo_confirm_callback(callback: types.CallbackQuery, state: FSMContext):
    """Подтверждение обложки - переход к добавлению остальных фото"""
    await callback.answer()
    
    data = await state.get_data()
    photos = data.get('photos', [])
    ad_id = data.get('editing_ad_id')
    
    if not photos:
        await callback.answer("❌ Ошибка: обложка не найдена.", show_alert=True)
        return
    
    # Получаем категорию для определения минимального количества фото
    ad = await get_ad_by_id(ad_id)
    if not ad:
        await callback.answer("❌ Объявление не найдено.", show_alert=True)
        await state.clear()
        return
    
    category = ad.category
    
    # Переходим к этапу добавления остальных фото
    await state.set_state(MyAdsState.edit_additional_photos)
    
    # Проверяем, есть ли кнопка "Продолжить" (когда достаточно фото для продолжения)
    has_continue_button = (category == "slots" and len(photos) >= 1) or (category != "slots" and len(photos) > 1)
    
    # Формируем сообщение
    from src.bot.keyboards.keyboards import additional_photos_kb
    additional_photos_text = "📸 Отправьте остальные изображения объявления\n"
    additional_photos_text += "(_Общее кол-во изображений с обложкой должно быть не более 8._)"
    # Показываем текст о минимуме только если нет кнопки "Продолжить"
    if not has_continue_button:
        additional_photos_text += "\n(_Для продолжения нужно минимум 1 изображение._)"
    
    # Пытаемся отредактировать текущее сообщение
    try:
        await callback.message.edit_text(
            additional_photos_text,
            parse_mode='Markdown',
            reply_markup=additional_photos_kb(len(photos), category)
        )
        await state.update_data(last_photo_msg_id=callback.message.message_id, photo_request_msg_id=callback.message.message_id)
    except Exception as e:
        logger.debug(f"Не удалось отредактировать сообщение: {e}")
        # Если не удалось отредактировать (например, сообщение с фото), пробуем удалить и отправить новое
        try:
            await bot.delete_message(chat_id=callback.message.chat.id, message_id=callback.message.message_id)
            msg = await callback.message.answer(
                additional_photos_text,
                parse_mode='Markdown',
                reply_markup=additional_photos_kb(len(photos), category)
            )
            await state.update_data(last_photo_msg_id=msg.message_id, photo_request_msg_id=msg.message_id)
        except:
            # Если и это не получилось, отправляем новое сообщение
            msg = await callback.message.answer(
                additional_photos_text,
                parse_mode='Markdown',
                reply_markup=additional_photos_kb(len(photos), category)
            )
            await state.update_data(last_photo_msg_id=msg.message_id, photo_request_msg_id=msg.message_id)


async def my_ad_edit_cover_photo_retry_callback(callback: types.CallbackQuery, state: FSMContext):
    """Повторная отправка обложки"""
    await callback.answer()
    
    # Очищаем обложку
    await state.update_data(photos=[], cover_photo_file_id=None)
    
    # Удаляем предыдущее сообщение с обложкой
    data = await state.get_data()
    cover_photo_msg_id = data.get('cover_photo_msg_id')
    if cover_photo_msg_id:
        try:
            await bot.delete_message(chat_id=callback.message.chat.id, message_id=cover_photo_msg_id)
        except:
            pass
    
    # Возвращаемся к запросу обложки
    from src.bot.keyboards.keyboards import cover_photo_request_kb
    cover_photo_text = "📲 Отправьте обложку для вашего объявления\n"
    cover_photo_text += "(_Одно изображение._)"
    
    try:
        await callback.message.edit_text(
            cover_photo_text,
            parse_mode='Markdown',
            reply_markup=cover_photo_request_kb()
        )
        await state.update_data(cover_photo_request_msg_id=callback.message.message_id)
    except:
        msg = await callback.message.answer(
            cover_photo_text,
            parse_mode='Markdown',
            reply_markup=cover_photo_request_kb()
        )
        await state.update_data(cover_photo_request_msg_id=msg.message_id)


# === РЕДАКТИРОВАНИЕ ДОПОЛНИТЕЛЬНЫХ ФОТО ===

async def my_ad_edit_additional_photos_handler(message: types.Message, state: FSMContext):
    """Обработчик загрузки остальных фото (после обложки) при редактировании"""
    if not message.photo:
        await message.answer(PHOTO_ERROR_MESSAGE)
        return
    
    data = await state.get_data()
    photos = data.get('photos', [])
    ad_id = data.get('editing_ad_id')
    
    # Проверяем, что обложка уже добавлена
    if not photos or len(photos) == 0:
        await message.answer("❌ Сначала добавьте обложку.")
        return
    
    # Удаляем само фото пользователя
    try:
        await message.delete()
    except:
        pass
    
    # Получаем категорию объявления
    ad = await get_ad_by_id(ad_id)
    if not ad:
        await message.answer("❌ Объявление не найдено.")
        await state.clear()
        return
    
    category = ad.category
    
    # Проверяем максимум (8 фото всего, включая обложку)
    if len(photos) >= 8:
        last_photo_msg_id = data.get('last_photo_msg_id')
        photo_request_msg_id = data.get('photo_request_msg_id')
        msg_id_to_edit = last_photo_msg_id or photo_request_msg_id
        
        if msg_id_to_edit:
            try:
                from src.bot.keyboards.keyboards import additional_photos_kb
                await bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=msg_id_to_edit,
                    text=PHOTO_MAX_ERROR.format(count=len(photos)),
                    reply_markup=additional_photos_kb(len(photos), category)
                )
            except:
                pass
        return
    
    # Получаем исходный file_id
    original_file_id = message.photo[-1].file_id
    logger.debug(f"получено дополнительное фото #{len(photos) + 1} с file_id: {original_file_id}")
    
    # Дополнительные фото сохраняем без логотипа
    photo_file_id = original_file_id
    
    # Добавляем фото (position начинается с 2, так как position=1 - обложка)
    photos.append({'file_id': photo_file_id, 'position': len(photos) + 1})
    await state.update_data(photos=photos)
    
    # Получаем ID сообщений для редактирования
    last_photo_msg_id = data.get('last_photo_msg_id')
    photo_request_msg_id = data.get('photo_request_msg_id')
    
    # Формируем сообщение с количеством фото
    total_photos = len(photos)
    # Проверяем, есть ли кнопка "Продолжить"
    has_continue_button = (category == "slots" and total_photos >= 1) or (category != "slots" and total_photos > 1)
    
    from src.bot.keyboards.keyboards import additional_photos_kb
    additional_photos_text = "📸 Отправьте остальные изображения объявления\n"
    additional_photos_text += f"(_Общее кол-во изображений {total_photos} / 8._)"
    # Показываем текст о минимуме только если нет кнопки "Продолжить"
    if not has_continue_button:
        additional_photos_text += "\n(_Для продолжения нужно минимум 1 изображение._)"
    
    # Пытаемся отредактировать предыдущее сообщение
    msg_id_to_edit = last_photo_msg_id or photo_request_msg_id
    if msg_id_to_edit:
        try:
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=msg_id_to_edit,
                text=additional_photos_text,
                parse_mode='Markdown',
                reply_markup=additional_photos_kb(total_photos, category)
            )
            await state.update_data(last_photo_msg_id=msg_id_to_edit, photo_request_msg_id=msg_id_to_edit)
            logger.debug(f"Сообщение {msg_id_to_edit} успешно отредактировано, фото: {total_photos}, категория: {category}")
            return
        except Exception as e:
            logger.debug(f"Не удалось отредактировать сообщение {msg_id_to_edit}: {e}")
            # Если не удалось отредактировать, отправляем новое сообщение
            msg = await message.answer(
                additional_photos_text,
                parse_mode='Markdown',
                reply_markup=additional_photos_kb(total_photos, category)
            )
            # сохраняем ID нового сообщения
            await state.update_data(last_photo_msg_id=msg.message_id, photo_request_msg_id=msg.message_id)
            return
    
    # Если нет ID сообщения для редактирования - отправляем новое сообщение
    msg = await message.answer(
        additional_photos_text,
        parse_mode='Markdown',
        reply_markup=additional_photos_kb(total_photos, category)
    )
    
    # сохраняем ID нового сообщения
    await state.update_data(last_photo_msg_id=msg.message_id, photo_request_msg_id=msg.message_id)


async def my_ad_edit_additional_photos_done_callback(callback: types.CallbackQuery, state: FSMContext):
    """Завершение загрузки фото при редактировании"""
    await callback.answer()
    
    data = await state.get_data()
    photos = data.get('photos', [])
    ad_id = data.get('editing_ad_id')
    
    if not ad_id:
        await callback.answer("❌ Ошибка: объявление не найдено.", show_alert=True)
        await state.clear()
        return
    
    # Получаем категорию объявления для определения минимального количества фото
    ad = await get_ad_by_id(ad_id)
    if not ad:
        await callback.answer("❌ Объявление не найдено.", show_alert=True)
        await state.clear()
        return
    
    min_photos = 1 if ad.category == "slots" else 2
    
    if len(photos) < min_photos:
        await callback.answer(PHOTO_MIN_ERROR.format(count=len(photos)), show_alert=True)
        return
    
    # Проверяем, что это объявление пользователя
    user = await get_user_by_tg_id(callback.from_user.id)
    
    if not user or ad.seller_user_id != user.id:
        await callback.answer("❌ Это не ваше объявление.", show_alert=True)
        await state.clear()
        return
    
    # Одобренное объявление: фото не пишем в БД, храним только в state (копия пойдёт в ad_edits при подтверждении)
    if ad.status != AdStatus.approved.value and ad.status != 'approved':
        # Удаляем старые фото из БД
        async with async_session() as session:
            await session.execute(
                delete(AdPhoto).where(AdPhoto.ad_id == ad_id)
            )
            await session.commit()
        await add_ad_photos(ad_id, photos)
        cover_file_id = data.get('cover_photo_file_id')
        if cover_file_id:
            await update_ad(ad_id, cover_file_id=cover_file_id)
            logger.info(f"Обновлена обложка объявления #{ad_id} с file_id: {cover_file_id}")
    
    data = await state.get_data()
    edited_fields = data.get('edited_fields', [])
    if 'photos' not in edited_fields:
        edited_fields.append('photos')
    
    await state.update_data(edited_fields=edited_fields)
    
    try:
        await callback.message.delete()
    except:
        pass
    
    # Возвращаемся в меню редактирования
    await return_to_edit_menu(callback, state, ad_id)


async def my_ad_edit_additional_photos_delete_last_callback(callback: types.CallbackQuery, state: FSMContext):
    """Удаление последнего фото (из дополнительных) при редактировании"""
    await callback.answer()
    
    data = await state.get_data()
    photos = data.get('photos', [])
    ad_id = data.get('editing_ad_id')
    
    # Получаем категорию объявления
    ad = await get_ad_by_id(ad_id)
    if not ad:
        await callback.answer("❌ Объявление не найдено.", show_alert=True)
        await state.clear()
        return
    
    category = ad.category
    
    if len(photos) > 1:
        # Удаляем последнее фото (обложка с position=1 всегда остается)
        photos.pop()
        await state.update_data(photos=photos)
    
    # Если осталась только обложка, возвращаемся к пункту А
    if len(photos) == 1:
        from src.bot.keyboards.keyboards import additional_photos_kb
        additional_photos_text = "📸 Отправьте остальные изображения объявления\n"
        additional_photos_text += "(_Общее кол-во изображений с обложкой должно быть не более 8._)\n"
        additional_photos_text += "(_Для продолжения нужно минимум 1 изображение._)"
        
        try:
            await callback.message.edit_text(
                additional_photos_text,
                parse_mode='Markdown',
                reply_markup=additional_photos_kb(len(photos), category)
            )
        except:
            await callback.message.edit_reply_markup(reply_markup=additional_photos_kb(len(photos), category))
    else:
        # Обновляем текст с количеством фото
        total_photos = len(photos)
        # Проверяем, есть ли кнопка "Продолжить"
        has_continue_button = (category == "slots" and total_photos >= 1) or (category != "slots" and total_photos > 1)
        
        from src.bot.keyboards.keyboards import additional_photos_kb
        additional_photos_text = "📸 Отправьте остальные изображения объявления\n"
        additional_photos_text += f"(_Общее кол-во изображений {total_photos} / 8._)"
        # Показываем текст о минимуме только если нет кнопки "Продолжить"
        if not has_continue_button:
            additional_photos_text += "\n(_Для продолжения нужно минимум 1 изображение._)"
        
        try:
            await callback.message.edit_text(
                additional_photos_text,
                parse_mode='Markdown',
                reply_markup=additional_photos_kb(total_photos, category)
            )
        except:
            await callback.message.edit_reply_markup(reply_markup=additional_photos_kb(total_photos, category))


async def my_ad_edit_additional_photos_back_callback(callback: types.CallbackQuery, state: FSMContext):
    """Возврат к редактированию обложки из этапа дополнительных фото"""
    await callback.answer()
    
    # Возвращаемся к состоянию редактирования обложки
    await state.set_state(MyAdsState.edit_cover_photo)
    
    # Получаем текущую обложку
    data = await state.get_data()
    photos = data.get('photos', [])
    cover_photo_file_id = None
    
    # Сохраняем обложку, если она есть
    if photos:
        cover_photo_file_id = photos[0]['file_id']
        # Оставляем только обложку
        photos = [photos[0]]
        await state.update_data(photos=photos, cover_photo_file_id=cover_photo_file_id)
    else:
        await state.update_data(photos=[], cover_photo_file_id=None)
    
    # Показываем обложку или запрос на её загрузку
    from src.bot.keyboards.keyboards import cover_photo_request_kb
    cover_photo_text = "📲 Отправьте обложку для вашего объявления\n"
    cover_photo_text += "(_Одно изображение._)"
    
    try:
        await callback.message.edit_text(
            cover_photo_text,
            parse_mode='Markdown',
            reply_markup=cover_photo_request_kb()
        )
        await state.update_data(cover_photo_request_msg_id=callback.message.message_id, last_msg_with_keyboard=callback.message.message_id)
    except:
        msg = await callback.message.answer(
            cover_photo_text,
            parse_mode='Markdown',
            reply_markup=cover_photo_request_kb()
        )
        await state.update_data(cover_photo_request_msg_id=msg.message_id, last_msg_with_keyboard=msg.message_id)


async def my_ad_edit_cover_photo_back_callback(callback: types.CallbackQuery, state: FSMContext):
    """Возврат в меню редактирования из этапа редактирования обложки"""
    await callback.answer()
    
    data = await state.get_data()
    ad_id = data.get('editing_ad_id')
    
    if not ad_id:
        await callback.answer("❌ Ошибка: объявление не найдено.", show_alert=True)
        await state.clear()
        return
    
    # Получаем объявление для проверки статуса
    ad = await get_ad_by_id(ad_id)
    if not ad:
        await callback.answer("❌ Объявление не найдено.", show_alert=True)
        await state.clear()
        return
    
    # Определяем, является ли это отклоненным объявлением
    is_rejected = ad.status == AdStatus.rejected.value
    
    # Очищаем состояние редактирования фото
    await state.set_state(MyAdsState.edit_other)
    
    # Удаляем текущее сообщение
    try:
        await callback.message.delete()
    except:
        pass
    
    await state.update_data(editing_ad_id=ad_id)
    
    # Возвращаемся в меню редактирования
    if is_rejected:
        # Возвращаемся в меню редактирования отклоненного объявления
        text = f"📝 <b>Редактирование отклоненного объявления #{ad.id}</b>\n\n"
        text += "Выберите, что хотите изменить:\n\n"
        text += "⚠️ <b>Внимание:</b> Изменения будут отправлены на модерацию."
    else:
        # Возвращаемся в меню редактирования других параметров
        text = f"📝 <b>Редактирование других параметров</b>\n\n"
        text += "Выберите, что хотите изменить:\n\n"
        text += "⚠️ <b>Внимание:</b> Изменения будут отправлены на модерацию."
    
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    from src.bot.keyboards.key_text import BACK_BTN
    
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
    
    if is_rejected:
        keyboard.row(InlineKeyboardButton(text=BACK_BTN, callback_data=f"my_ad:{ad_id}"))
    else:
        keyboard.row(InlineKeyboardButton(text=BACK_BTN, callback_data=f"my_ad_edit:{ad_id}"))
    
    await callback.message.answer(text, parse_mode='HTML', reply_markup=keyboard.as_markup())




