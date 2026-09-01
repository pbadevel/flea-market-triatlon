"""
Обработчик создания объявлений
"""

from typing import Union
from aiogram import Dispatcher, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardRemove
from loguru import logger
from src.bot.logging_config import log_ad_action

from src.bot.database.states import AddAdState
from src.bot.database.methods import (
    create_or_update_user, get_user_by_tg_id, create_ad, add_ad_photos, 
    set_user_phone, is_trusted_seller, count_user_ads_today
)
from src.bot.keyboards.keyboards import *
from src.bot.keyboards.key_text import *
from src.bot.settings.constants import *
from src.bot.settings.settings import MODERATION_CHAT_ID
from src.bot.loader import bot
from src.bot.utils.image_utils import add_logo_watermark_to_photo, crop_image_center
from src.bot.utils.helpers import get_fsinput_photo, format_file_id_to_storage_path, format_contact_for_display




# from src.










# === НАЧАЛО СОЗДАНИЯ ОБЪЯВЛЕНИЯ ===

async def start_add_ad_with_type(callback: types.CallbackQuery, state: FSMContext, ad_type: str):
    """Начало создания объявления с указанным типом (sale/rent)"""
    await callback.answer()
    
    # Очищаем предыдущее состояние
    await state.clear()
    
    # Сохраняем тип объявления
    from src.models import AdType
    ad_type_value = AdType.sale.value if ad_type == 'sale' else AdType.rent.value
    await state.update_data(ad_type=ad_type_value, photos=[])
    
    # Начинаем с выбора категории
    await state.set_state(AddAdState.category)
    
    # Определяем тип объявления для фильтрации категорий
    ad_type_text = AdType.sale.value if ad_type == 'sale' else AdType.rent.value
    
    # Заменяем сообщение главного меню на сообщение с выбором категории
    try:
        await callback.message.edit_text(
            CATEGORY_MESSAGE,
            reply_markup=categories_kb(ad_type=ad_type_text)
        )
        await state.update_data(last_msg_with_keyboard=callback.message.message_id)
    except:
        # Если не удалось отредактировать, отправляем новое
        msg = await callback.message.answer(
            CATEGORY_MESSAGE,
            reply_markup=categories_kb(ad_type=ad_type_text)
        )
        await state.update_data(last_msg_with_keyboard=msg.message_id)


async def start_add_ad(callback: types.CallbackQuery, state: FSMContext):
    """Начало создания объявления (старая функция для совместимости)"""
    # Используем новую функцию с типом "Продажа" по умолчанию
    await start_add_ad_with_type(callback, state, ad_type='sale')


# === ЗАГРУЗКА ФОТО ===

def get_min_photos_count(category: str = None) -> int:
    """Получить минимальное количество фото в зависимости от категории"""
    # Для категории "Слоты" достаточно 1 фото
    if category == "slots":
        return 1
    # Для остальных категорий минимум 2 фото
    return 2

def get_photo_first_message(category: str = None) -> str:
    """Получить сообщение о загрузке фото в зависимости от категории"""
    from src.bot.settings.constants import PHOTO_FIRST_MESSAGE, PHOTO_FIRST_MESSAGE_SLOTS
    # Для категории "Слоты" используем специальное сообщение
    if category == "slots":
        return PHOTO_FIRST_MESSAGE_SLOTS
    # Для остальных категорий стандартное сообщение
    return PHOTO_FIRST_MESSAGE


def get_price_message(ad_type: str = "Продажа") -> str:
    """Текст шага ввода цены с учетом типа объявления."""
    if ad_type == "Аренда":
        return """Укажите цену в рублях за сутки (только число, до 7 знаков).
<i>(Например: 15000)</i>"""
    return PRICE_MESSAGE

# === ОБЛОЖКА ===

async def cover_photo_handler(message: types.Message, state: FSMContext):
    """Обработчик загрузки обложки (первое фото)"""
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
        cropped_file_id = await crop_image_center(
            file_id=original_file_id,
            chat_id=message.chat.id,
            bot=bot
        )
        logger.debug(f"обложка обрезана, новый file_id: {cropped_file_id}")
        
        # Определяем тип объявления для выбора логотипа
        data = await state.get_data()
        ad_type = data.get('ad_type', 'Продажа')
        if ad_type == 'Аренда':
            logo_path = "assets/logo_rent.png"
            logger.debug("накладываю логотип на обрезанную обложку (assets/logo_rent.png)...")
        else:
            logo_path = "assets/logo_sale.png"
            logger.debug("накладываю логотип на обрезанную обложку (assets/logo_sale.png)...")
        
        # Добавляем логотип типа объявления (Продажа/Аренда) на обрезанное изображение
        processed_cover_file_id = await add_logo_watermark_to_photo(
            file_id=cropped_file_id,
            chat_id=message.chat.id,
            bot=bot,
            logo_path=logo_path
        )
        logger.debug(f"обложка обработана (обрезана и с логотипом типа), новый file_id: {processed_cover_file_id}")
        
        # Если у пользователя статус «Доверенный продавец» — накладываем логотип доверенного продавца (18% от ширины)
        # Итоговая обложка с обоими логами сохраняется в state и при создании объявления — в ad.cover_file_id в БД
        # Пока закомментирована вставка второго лого (для доверенного продавца)
        # from src.bot.database.methods import is_trusted_seller
        # from src.bot.utils.image_utils import add_trusted_seller_logo_to_photo
        # if await is_trusted_seller(message.from_user.id):
        #     try:
        #         processed_cover_file_id = await add_trusted_seller_logo_to_photo(
        #             file_id=processed_cover_file_id,
        #             chat_id=message.chat.id,
        #             bot=bot,
        #             logo_path="assets/logo.png"
        #         )
        #         logger.debug(f"наложен логотип доверенного продавца на обложку, file_id: {processed_cover_file_id}")
        #     except Exception as e_trusted:
        #         logger.warning(f"не удалось наложить логотип доверенного продавца: {e_trusted}")
    except Exception as e:
        logger.error(f"ошибка при обработке обложки: {e}", exc_info=True)
        logger.warning(f"будет использоваться оригинал обложки в качестве обработанной версии")
        processed_cover_file_id = original_file_id
    
    # ВАЖНО: сохраняем ОРИГИНАЛЬНОЕ фото в photos (для деталей, модерации, предпросмотра).
    # Обработанную обложку (обрезка + лого типа Продажа/Аренда + при наличии статуса лого «Доверенный продавец»)
    # сохраняем в cover_photo_file_id. При создании объявления (create_ad) это значение попадёт в ad.cover_file_id в БД
    # и будет использоваться в канале и каталоге без повторного наложения логотипов.
    photos = [{'file_id': original_file_id, 'position': 1}]
    await state.update_data(photos=photos, cover_photo_file_id=processed_cover_file_id)
    
    # Получаем ID предыдущего сообщения для редактирования
    data = await state.get_data()
    cover_photo_request_msg_id = data.get('cover_photo_request_msg_id')
    
    # Текст подтверждения
    confirmation_text = "✅ Вот изображение вашей обложки, проверьте.\n"
    confirmation_text += "(_Если хотите изменить изображение, просто отправьте другое изображение и бот подставит его._)"
    
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
            photo=get_fsinput_photo(
                format_file_id_to_storage_path(display_file_id)
            ),
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


async def cover_photo_confirm_callback(callback: types.CallbackQuery, state: FSMContext):
    """Подтверждение обложки - переход к добавлению остальных фото"""
    await callback.answer()
    
    data = await state.get_data()
    photos = data.get('photos', [])
    
    if not photos:
        await callback.answer("❌ Ошибка: обложка не найдена.", show_alert=True)
        return
    
    # Переходим к этапу добавления остальных фото
    await state.set_state(AddAdState.photos)
    
    # Получаем категорию для определения минимального количества фото
    category = data.get('category')
    min_photos = get_min_photos_count(category)
    
    # Проверяем, есть ли кнопка "Продолжить" (когда достаточно фото для продолжения)
    has_continue_button = (category == "slots" and len(photos) >= 1) or (category != "slots" and len(photos) > 1)
    
    # Формируем сообщение
    additional_photos_text = "📸 Отправьте остальные изображения объявления\n"
    additional_photos_text += "(_Общее кол-во изображений с обложкой должно быть не более 8._)"
    # Показываем текст о минимуме только если нет кнопки "Продолжить"
    if not has_continue_button:
        additional_photos_text += "\n(_Для продолжения нужно минимум 1 изображение._)"
    
    # Пытаемся отредактировать текущее сообщение (даже если оно с фото, edit_text может заменить его на текст)
    try:
        await callback.message.edit_text(
            additional_photos_text,
            parse_mode='Markdown',
            reply_markup=additional_photos_kb(len(photos), category)
        )
        await state.update_data(last_photo_msg_id=callback.message.message_id, photo_request_msg_id=callback.message.message_id)
    except Exception as e:
        logger.debug(f"Не удалось отредактировать сообщение: {e}")
        # Сначала отправляем новое сообщение, потом удаляем предыдущее
        msg = await callback.message.answer(
            additional_photos_text,
            parse_mode='Markdown',
            reply_markup=additional_photos_kb(len(photos), category)
        )
        await state.update_data(last_photo_msg_id=msg.message_id, photo_request_msg_id=msg.message_id)
        try:
            await bot.delete_message(chat_id=callback.message.chat.id, message_id=callback.message.message_id)
        except Exception:
            pass


async def cover_photo_retry_callback(callback: types.CallbackQuery, state: FSMContext):
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


async def photo_handler(message: types.Message, state: FSMContext):
    """Обработчик загрузки остальных фото (после обложки)"""
    if not message.photo:
        await message.answer(PHOTO_ERROR_MESSAGE)
        return
    
    data = await state.get_data()
    photos = data.get('photos', [])
    
    # Проверяем, что обложка уже добавлена
    if not photos or len(photos) == 0:
        await message.answer("❌ Сначала добавьте обложку.")
        return
    
    # Удаляем само фото пользователя
    try:
        await message.delete()
    except:
        pass
    
    # Проверяем максимум (8 фото всего, включая обложку)
    if len(photos) >= 8:
        data = await state.get_data()
        category = data.get('category')
        last_photo_msg_id = data.get('last_photo_msg_id')
        photo_request_msg_id = data.get('photo_request_msg_id')
        msg_id_to_edit = last_photo_msg_id or photo_request_msg_id
        
        if msg_id_to_edit:
            try:
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
    
    # Получаем категорию и ID сообщений для редактирования
    data = await state.get_data()
    category = data.get('category')
    last_photo_msg_id = data.get('last_photo_msg_id')
    photo_request_msg_id = data.get('photo_request_msg_id')
    
    # Формируем сообщение с количеством фото
    total_photos = len(photos)
    # Проверяем, есть ли кнопка "Продолжить"
    has_continue_button = (category == "slots" and total_photos >= 1) or (category != "slots" and total_photos > 1)
    
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


async def photo_done_callback(callback: types.CallbackQuery, state: FSMContext):
    """Завершение загрузки фото"""
    await callback.answer()
    
    data = await state.get_data()
    photos = data.get('photos', [])
    category = data.get('category')
    min_photos = get_min_photos_count(category)
    
    # Проверяем, что есть хотя бы обложка
    if len(photos) < 1:
        await callback.answer("❌ Необходимо добавить обложку.", show_alert=True)
        return
    
    # Для категории "slots" достаточно только обложки
    if category == "slots" and len(photos) >= 1:
        pass  # OK
    elif len(photos) < min_photos:
        await callback.answer(PHOTO_MIN_ERROR.format(min=min_photos, count=len(photos)), show_alert=True)
        return
    
    # Переходим к выбору способа связи
    await state.set_state(AddAdState.contact_method)
    
    # Редактируем сообщение на выбор способа связи
    try:
        await callback.message.edit_text(
            CONTACT_METHOD_MESSAGE,
            reply_markup=contact_method_kb()
        )
        await state.update_data(last_msg_with_keyboard=callback.message.message_id)
    except:
        msg = await callback.message.answer(
            CONTACT_METHOD_MESSAGE,
            reply_markup=contact_method_kb()
        )
        await state.update_data(last_msg_with_keyboard=msg.message_id)


async def photo_delete_last_callback(callback: types.CallbackQuery, state: FSMContext):
    """Удаление последнего фото (из дополнительных)"""
    await callback.answer()
    
    data = await state.get_data()
    photos = data.get('photos', [])
    category = data.get('category')
    
    if len(photos) > 1:
        # Удаляем последнее фото (обложка с position=1 всегда остается)
        photos.pop()
        await state.update_data(photos=photos)
    
    # Если осталась только обложка, возвращаемся к пункту А
    if len(photos) == 1:
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


# === НАЗВАНИЕ ===

async def title_handler(message: types.Message, state: FSMContext):
    """Обработчик ввода названия"""
    title = message.text.strip()
    
    if not title or len(title) > 150:
        # Удаляем сообщение пользователя с неверными данными
        try:
            await message.delete()
        except:
            pass
        
        # Редактируем сообщение с просьбой ввести название на сообщение об ошибке
        data = await state.get_data()
        last_msg_id = data.get('last_msg_with_keyboard')
        if last_msg_id:
            try:
                await bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=last_msg_id,
                    text="❌ Название должно быть от 1 до 150 символов.\n\n" + TITLE_MESSAGE,
                    reply_markup=back_kb()
                )
                return
            except:
                pass
        
        # Если не удалось отредактировать - отправляем новое сообщение
        await message.answer("❌ Название должно быть от 1 до 150 символов.\n\n" + TITLE_MESSAGE, reply_markup=back_kb())
        return
    
    # Сохраняем ID сообщения для редактирования
    data = await state.get_data()
    last_msg_id = data.get('last_msg_with_keyboard')
    
    await state.update_data(title=title)
    
    # Удаляем сообщение пользователя (его нельзя редактировать)
    try:
        await message.delete()
    except:
        pass
    
    # Проверяем, нужен ли размер для этой подкатегории
    subcategory = data.get('subcategory')
    category = data.get('category')
    
    # Для категорий "swim", "bike" и "run" размер обязателен всегда
    needs_size = category in ['swim', 'bike', 'run'] or subcategory in SIZE_REQUIRED_SUBCATEGORIES
    
    if needs_size:
        # Переходим к размеру
        await state.set_state(AddAdState.size)
        
        # Заменяем предыдущее сообщение вместо удаления
        if last_msg_id:
            try:
                await bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=last_msg_id,
                    text=SIZE_MESSAGE,
                    reply_markup=sizes_kb()
                )
                await state.update_data(last_msg_with_keyboard=last_msg_id)
            except:
                msg = await message.answer(
                    SIZE_MESSAGE,
                    reply_markup=sizes_kb()
                )
                await state.update_data(last_msg_with_keyboard=msg.message_id)
        else:
            msg = await message.answer(
                SIZE_MESSAGE,
                reply_markup=sizes_kb()
            )
            await state.update_data(last_msg_with_keyboard=msg.message_id)
    else:
        # Переходим к описанию (размер не нужен)
        await state.set_state(AddAdState.description)
        
        # Заменяем предыдущее сообщение вместо удаления
        if last_msg_id:
                try:
                    await bot.edit_message_text(
                        chat_id=message.chat.id,
                        message_id=last_msg_id,
                        text=DESCRIPTION_MESSAGE,
                        parse_mode='HTML',
                        reply_markup=back_kb()
                    )
                    await state.update_data(last_msg_with_keyboard=last_msg_id)
                except:
                    msg = await message.answer(
                        DESCRIPTION_MESSAGE,
                        parse_mode='HTML',
                        reply_markup=back_kb()
                    )
                    await state.update_data(last_msg_with_keyboard=msg.message_id)
        else:
            msg = await message.answer(
                DESCRIPTION_MESSAGE,
                parse_mode='HTML',
                reply_markup=back_kb()
            )
            await state.update_data(last_msg_with_keyboard=msg.message_id)


# === ЦЕНА ===

async def price_handler(message: types.Message, state: FSMContext):
    """Обработчик ввода цены"""
    logger.debug(f"price_handler вызван, текст: {message.text}")
    
    price_text = message.text.strip().replace(' ', '').replace(',', '')
    
    try:
        price = int(price_text)
        if price <= 0 or len(price_text) > 7:
            raise ValueError
    except ValueError:
        # Удаляем сообщение пользователя с неверными данными
        try:
            await message.delete()
        except:
            pass
        
        # Редактируем существующее сообщение с ошибкой
        data = await state.get_data()
        last_msg_id = data.get('last_msg_with_keyboard')
        
        ad_type = data.get('ad_type', 'Продажа')
        error_text = f"{PRICE_ERROR_MESSAGE}\n\n{get_price_message(ad_type)}"
        
        # Всегда пытаемся отредактировать существующее сообщение
        if last_msg_id:
            try:
                await bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=last_msg_id,
                    text=error_text,
                    parse_mode='HTML',
                    reply_markup=back_kb()
                )
                # Сохраняем ID сообщения для последующего редактирования
                await state.update_data(last_msg_with_keyboard=last_msg_id)
                logger.debug(f"Сообщение {last_msg_id} успешно отредактировано с ошибкой цены")
                return
            except Exception as e:
                error_str = str(e).lower()
                # Если сообщение не изменилось (такой же текст), просто игнорируем ошибку
                if "message is not modified" in error_str or "message_not_modified" in error_str:
                    logger.debug(f"Сообщение {last_msg_id} не изменилось (такой же текст ошибки), это нормально")
                    # Сохраняем ID сообщения для последующего редактирования
                    await state.update_data(last_msg_with_keyboard=last_msg_id)
                    return
                
                logger.debug(f"Не удалось отредактировать сообщение {last_msg_id}: {e}")
                # Если не удалось отредактировать (например, сообщение было удалено), отправляем новое
                try:
                    msg = await message.answer(error_text, parse_mode='HTML', reply_markup=back_kb())
                    await state.update_data(last_msg_with_keyboard=msg.message_id)
                    logger.debug(f"Отправлено новое сообщение об ошибке цены, message_id: {msg.message_id}")
                    return
                except Exception as e2:
                    logger.error(f"Ошибка при отправке сообщения об ошибке цены: {e2}")
                    return
        else:
            # Если нет ID сообщения для редактирования, отправляем новое
            try:
                msg = await message.answer(error_text, parse_mode='HTML', reply_markup=back_kb())
                await state.update_data(last_msg_with_keyboard=msg.message_id)
                logger.debug(f"Отправлено новое сообщение об ошибке цены (нет last_msg_id), message_id: {msg.message_id}")
                return
            except Exception as e:
                logger.error(f"Ошибка при отправке сообщения об ошибке цены: {e}")
                return
    
    # Сохраняем ID сообщения для редактирования
    data = await state.get_data()
    last_msg_id = data.get('last_msg_with_keyboard')
    
    await state.update_data(price=price)
    
    # Удаляем сообщение пользователя (его нельзя редактировать)
    try:
        await message.delete()
    except:
        pass
    
    # Проверяем тип объявления
    ad_type = data.get('ad_type', 'Продажа')
    
    # Переходим к выбору города
    await state.set_state(AddAdState.location_select)
    
    # Заменяем предыдущее сообщение вместо удаления
    if last_msg_id:
        try:
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=last_msg_id,
                text=LOCATION_MESSAGE,
                reply_markup=cities_kb()
            )
            await state.update_data(last_msg_with_keyboard=last_msg_id)
            logger.debug(f"price_handler успешно обработал цену {price}, сообщение заменено на выбор города")
        except Exception as e:
            logger.debug(f"не удалось отредактировать сообщение в price_handler: {e}")
            # Если не удалось отредактировать, отправляем новое
            try:
                msg = await message.answer(
                    LOCATION_MESSAGE,
                    reply_markup=cities_kb()
                )
                await state.update_data(last_msg_with_keyboard=msg.message_id)
            except Exception as e2:
                logger.error(f"ошибка в price_handler при отправке сообщения: {e2}", exc_info=True)
                await message.answer("❌ Произошла ошибка. Попробуйте еще раз.")
                return
    else:
        # Если нет предыдущего сообщения, отправляем новое
        try:
            msg = await message.answer(
                LOCATION_MESSAGE,
                reply_markup=cities_kb()
            )
            await state.update_data(last_msg_with_keyboard=msg.message_id)
        except Exception as e:
            logger.error(f"ошибка в price_handler при отправке сообщения: {e}", exc_info=True)
            await message.answer("❌ Произошла ошибка. Попробуйте еще раз.")
            return


# === ТИП ОБЪЯВЛЕНИЯ ===

async def ad_type_callback(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик выбора типа объявления"""
    await callback.answer()
    
    ad_type_value = callback.data.split(':')[1]  # 'sale' или 'rent'
    
    # Сохраняем тип объявления
    from src.models import AdType
    if ad_type_value == 'sale':
        ad_type = AdType.sale.value
    else:
        ad_type = AdType.rent.value
    
    await state.update_data(ad_type=ad_type)
    await state.set_state(AddAdState.location_select)
    
    try:
        await callback.message.edit_text(
            LOCATION_MESSAGE,
            reply_markup=cities_kb()
        )
    except:
        msg = await callback.message.answer(
            LOCATION_MESSAGE,
            reply_markup=cities_kb()
        )
        await state.update_data(last_msg_with_keyboard=msg.message_id)
        return
    await state.update_data(last_msg_with_keyboard=callback.message.message_id)


# === МЕСТОПОЛОЖЕНИЕ ===

async def city_callback(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик выбора города"""
    await callback.answer()
    
    city_key = callback.data.split(':')[1]
    
    # Сохраняем ID сообщения для последующего удаления
    menu_msg_id = callback.message.message_id
    
    if city_key == 'other':
        await state.set_state(AddAdState.location_city_custom)
        
        # Заменяем сообщение вместо удаления
        try:
            await callback.message.edit_text(
                CITY_CUSTOM_MESSAGE,
                reply_markup=back_kb()
            )
            await state.update_data(last_msg_with_keyboard=callback.message.message_id)
        except:
            msg = await callback.message.answer(
                CITY_CUSTOM_MESSAGE,
                reply_markup=back_kb()
            )
            await state.update_data(last_msg_with_keyboard=msg.message_id)
    elif city_key == 'other_country':
        # Заменяем сообщение вместо удаления
        country_message = "⚠️ Раздел пока в разработке.\nОбъявления сохраняются и видны в каталоге, но не публикуются в общем канале (он работает только для РФ).\n<b>Для других стран появятся свои каналы, если будет спрос</b>"
        try:
            await callback.message.edit_text(
                country_message,
                reply_markup=countries_kb(),
                parse_mode='HTML'
            )
            await state.update_data(last_msg_with_keyboard=callback.message.message_id)
        except:
            msg = await callback.message.answer(
                country_message,
                reply_markup=countries_kb(),
                parse_mode='HTML'
            )
            await state.update_data(last_msg_with_keyboard=msg.message_id)
    else:
        city = DEFAULT_CITIES[city_key]
        await state.update_data(city=city, country=None)
        
        # Проверяем тип объявления
        data = await state.get_data()
        ad_type = data.get('ad_type', 'Продажа')
        category = data.get('category')
        
        # Если это АРЕНДА или категория "slots", пропускаем доставку и сразу к обложке
        if ad_type == 'Аренда' or category == 'slots':
            # Устанавливаем delivery_method = None для аренды и слотов
            await state.update_data(delivery_method=None)
            await state.set_state(AddAdState.cover_photo)
            
            # Сообщение для запроса обложки
            cover_photo_text = "📲 Отправьте обложку для вашего объявления\n"
            cover_photo_text += "(_Одно изображение._)"
            
            # Заменяем сообщение вместо удаления
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
        else:
            # Переходим к выбору способа доставки (для продажи, кроме "slots")
            await state.set_state(AddAdState.delivery_method)
            
            # Заменяем сообщение вместо удаления
            try:
                await callback.message.edit_text(
                    DELIVERY_METHOD_MESSAGE,
                    reply_markup=delivery_method_kb()
                )
                await state.update_data(last_msg_with_keyboard=callback.message.message_id)
            except:
                msg = await callback.message.answer(
                    DELIVERY_METHOD_MESSAGE,
                    reply_markup=delivery_method_kb()
                )
                await state.update_data(last_msg_with_keyboard=msg.message_id)


async def country_callback(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик выбора страны"""
    await callback.answer()
    
    # Проверяем, что мы не в состоянии редактирования
    current_state = await state.get_state()
    from src.bot.database.states import MyAdsState
    if current_state in [MyAdsState.edit_city_select, MyAdsState.edit_city_custom, MyAdsState.edit_city_after_country]:
        # Это редактирование, пропускаем этот обработчик
        return
    
    country_key = callback.data.split(':')[1]
    
    if country_key == 'other':
        # Ввод собственной страны
        await state.set_state(AddAdState.location_country_custom)
        try:
            await callback.message.edit_text(
                COUNTRY_CUSTOM_MESSAGE,
                reply_markup=back_kb()
            )
        except:
            msg = await callback.message.answer(
                COUNTRY_CUSTOM_MESSAGE,
                reply_markup=back_kb()
            )
            await state.update_data(last_msg_with_keyboard=msg.message_id)
            return
        await state.update_data(last_msg_with_keyboard=callback.message.message_id)
    else:
        # Предустановленная страна - показываем список городов
        country = CIS_COUNTRIES[country_key]['name']
        await state.update_data(country=country, selected_country_key=country_key)
        await state.set_state(AddAdState.location_city_after_country)
        
        # Показываем список городов страны
        try:
            await callback.message.edit_text(
                "📍 Выберите город:",
                reply_markup=country_cities_kb(country_key)
            )
            await state.update_data(last_msg_with_keyboard=callback.message.message_id)
        except:
            msg = await callback.message.answer(
                "📍 Выберите город:",
                reply_markup=country_cities_kb(country_key)
            )
            await state.update_data(last_msg_with_keyboard=msg.message_id)


async def city_custom_handler(message: types.Message, state: FSMContext):
    """Обработчик ввода собственного города"""
    city = message.text.strip()
    
    if not city or len(city) > 100:
        await message.answer("❌ Название города должно быть от 1 до 100 символов.")
        return
    
    # Сохраняем ID сообщения для редактирования
    data = await state.get_data()
    last_msg_id = data.get('last_msg_with_keyboard')
    
    await state.update_data(city=city, country=None)
    
    # Удаляем сообщение пользователя (его нельзя редактировать)
    try:
        await message.delete()
    except:
        pass
    
    # Проверяем тип объявления и категорию
    ad_type = data.get('ad_type', 'Продажа')
    category = data.get('category')
    
    # Если это АРЕНДА или категория "slots", пропускаем доставку и сразу к обложке
    if ad_type == 'Аренда' or category == 'slots':
        # Устанавливаем delivery_method = None для аренды и слотов
        await state.update_data(delivery_method=None)
        await state.set_state(AddAdState.cover_photo)
        
        # Переходим к загрузке обложки
        cover_photo_text = "📲 Отправьте обложку для вашего объявления\n"
        cover_photo_text += "(_Одно изображение._)"
        
        # Заменяем предыдущее сообщение вместо удаления
        if last_msg_id:
            try:
                await bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=last_msg_id,
                    text=cover_photo_text,
                    parse_mode='Markdown',
                    reply_markup=cover_photo_request_kb()
                )
                await state.update_data(cover_photo_request_msg_id=last_msg_id, last_msg_with_keyboard=last_msg_id)
            except:
                msg = await message.answer(
                    cover_photo_text,
                    parse_mode='Markdown',
                    reply_markup=cover_photo_request_kb()
                )
                await state.update_data(cover_photo_request_msg_id=msg.message_id, last_msg_with_keyboard=msg.message_id)
        else:
            msg = await message.answer(
                cover_photo_text,
                parse_mode='Markdown',
                reply_markup=cover_photo_request_kb()
            )
            await state.update_data(cover_photo_request_msg_id=msg.message_id, last_msg_with_keyboard=msg.message_id)
    else:
        # Переходим к выбору способа доставки (для продажи)
        await state.set_state(AddAdState.delivery_method)
        
        # Заменяем предыдущее сообщение вместо удаления
        if last_msg_id:
            try:
                await bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=last_msg_id,
                    text=DELIVERY_METHOD_MESSAGE,
                    reply_markup=delivery_method_kb()
                )
                await state.update_data(last_msg_with_keyboard=last_msg_id)
            except:
                msg = await message.answer(
                    DELIVERY_METHOD_MESSAGE,
                    reply_markup=delivery_method_kb()
                )
                await state.update_data(last_msg_with_keyboard=msg.message_id)
        else:
            msg = await message.answer(
                DELIVERY_METHOD_MESSAGE,
                reply_markup=delivery_method_kb()
            )
            await state.update_data(last_msg_with_keyboard=msg.message_id)


async def country_custom_handler(message: types.Message, state: FSMContext):
    """Обработчик ввода собственной страны"""
    country = message.text.strip()
    
    if not country or len(country) > 100:
        await message.answer("❌ Название страны должно быть от 1 до 100 символов.")
        return
    
    # Сохраняем ID сообщения для редактирования
    data = await state.get_data()
    last_msg_id = data.get('last_msg_with_keyboard')
    
    # Удаляем сообщение пользователя (его нельзя редактировать)
    try:
        await message.delete()
    except:
        pass
    
    await state.update_data(country=country)
    await state.set_state(AddAdState.location_city_after_country)
    
    # Заменяем предыдущее сообщение вместо удаления
    if last_msg_id:
        try:
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=last_msg_id,
                text=CITY_CUSTOM_MESSAGE,
                reply_markup=back_kb()
            )
            await state.update_data(last_msg_with_keyboard=last_msg_id)
        except:
            msg = await message.answer(
                CITY_CUSTOM_MESSAGE,
                reply_markup=back_kb()
            )
            await state.update_data(last_msg_with_keyboard=msg.message_id)
    else:
        msg = await message.answer(
            CITY_CUSTOM_MESSAGE,
            reply_markup=back_kb()
        )
        await state.update_data(last_msg_with_keyboard=msg.message_id)


async def city_from_country_callback(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик выбора города из списка стран"""
    await callback.answer()
    
    # Получаем данные из callback_data: city_from_country:country_key:city_index
    parts = callback.data.split(':')
    if len(parts) < 3:
        await callback.answer("❌ Ошибка выбора города.", show_alert=True)
        return
    
    country_key = parts[1]
    try:
        city_index = int(parts[2])
    except (ValueError, IndexError):
        await callback.answer("❌ Ошибка выбора города.", show_alert=True)
        return
    
    # Получаем название города по индексу
    if country_key not in CIS_COUNTRIES or 'cities' not in CIS_COUNTRIES[country_key]:
        await callback.answer("❌ Ошибка выбора города.", show_alert=True)
        return
    
    cities = CIS_COUNTRIES[country_key]['cities']
    if city_index < 0 or city_index >= len(cities):
        await callback.answer("❌ Ошибка выбора города.", show_alert=True)
        return
    
    city = cities[city_index]
    
    # Сохраняем город и страну
    data = await state.get_data()
    country = data.get('country', CIS_COUNTRIES.get(country_key, {}).get('name', ''))
    await state.update_data(city=city, country=country)
    
    # Проверяем тип объявления и категорию
    ad_type = data.get('ad_type', 'Продажа')
    category = data.get('category')
    
    # Если это АРЕНДА или категория "slots", пропускаем доставку и сразу к обложке
    if ad_type == 'Аренда' or category == 'slots':
        # Устанавливаем delivery_method = None для аренды и слотов
        await state.update_data(delivery_method=None)
        await state.set_state(AddAdState.cover_photo)
        
        # Переходим к загрузке обложки
        cover_photo_text = "📲 Отправьте обложку для вашего объявления\n"
        cover_photo_text += "(_Одно изображение._)"
        
        # Редактируем сообщение на запрос обложки
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
    else:
        # Переходим к выбору способа доставки (для продажи, кроме "slots")
        await state.set_state(AddAdState.delivery_method)
        
        # Редактируем сообщение на выбор доставки
        try:
            await callback.message.edit_text(
                DELIVERY_METHOD_MESSAGE,
                reply_markup=delivery_method_kb()
            )
            await state.update_data(last_msg_with_keyboard=callback.message.message_id)
        except:
            msg = await callback.message.answer(
                DELIVERY_METHOD_MESSAGE,
                reply_markup=delivery_method_kb()
            )
            await state.update_data(last_msg_with_keyboard=msg.message_id)


async def city_after_country_handler(message: types.Message, state: FSMContext):
    """Обработчик ввода города после выбора страны (для ввода вручную, если нужно)"""
    city = message.text.strip()
    
    if not city or len(city) > 100:
        # Просто удаляем сообщение пользователя
        try:
            await message.delete()
        except:
            pass
        return
    
    # Сохраняем ID сообщения для редактирования
    data = await state.get_data()
    last_msg_id = data.get('last_msg_with_keyboard')
    
    await state.update_data(city=city)
    
    # Удаляем сообщение пользователя (его нельзя редактировать)
    try:
        await message.delete()
    except:
        pass
    
    # Проверяем тип объявления и категорию
    ad_type = data.get('ad_type', 'Продажа')
    category = data.get('category')
    
    # Если это АРЕНДА или категория "slots", пропускаем доставку и сразу к обложке
    if ad_type == 'Аренда' or category == 'slots':
        # Устанавливаем delivery_method = None для аренды и слотов
        await state.update_data(delivery_method=None)
        await state.set_state(AddAdState.cover_photo)
        
        # Переходим к загрузке обложки
        cover_photo_text = "📲 Отправьте обложку для вашего объявления\n"
        cover_photo_text += "(_Одно изображение._)"
        
        # Заменяем предыдущее сообщение вместо удаления
        if last_msg_id:
            try:
                await bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=last_msg_id,
                    text=cover_photo_text,
                    parse_mode='Markdown',
                    reply_markup=cover_photo_request_kb()
                )
                await state.update_data(cover_photo_request_msg_id=last_msg_id, last_msg_with_keyboard=last_msg_id)
            except:
                msg = await message.answer(
                    cover_photo_text,
                    parse_mode='Markdown',
                    reply_markup=cover_photo_request_kb()
                )
                await state.update_data(cover_photo_request_msg_id=msg.message_id, last_msg_with_keyboard=msg.message_id)
        else:
            msg = await message.answer(
                cover_photo_text,
                parse_mode='Markdown',
                reply_markup=cover_photo_request_kb()
            )
            await state.update_data(cover_photo_request_msg_id=msg.message_id, last_msg_with_keyboard=msg.message_id)
    else:
        # Переходим к выбору способа доставки (для продажи)
        await state.set_state(AddAdState.delivery_method)
        
        # Заменяем предыдущее сообщение вместо удаления
        if last_msg_id:
            try:
                await bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=last_msg_id,
                    text=DELIVERY_METHOD_MESSAGE,
                    reply_markup=delivery_method_kb()
                )
                await state.update_data(last_msg_with_keyboard=last_msg_id)
            except:
                msg = await message.answer(
                    DELIVERY_METHOD_MESSAGE,
                    reply_markup=delivery_method_kb()
                )
                await state.update_data(last_msg_with_keyboard=msg.message_id)
        else:
            msg = await message.answer(
                DELIVERY_METHOD_MESSAGE,
                reply_markup=delivery_method_kb()
            )
            await state.update_data(last_msg_with_keyboard=msg.message_id)


# === КАТЕГОРИЯ И ПОДКАТЕГОРИЯ ===

async def category_callback(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик выбора категории"""
    await callback.answer()
    
    category = callback.data.split(':')[1]
    await state.update_data(category=category)
    
    # Проверяем, есть ли подкатегории для этой категории
    from src.bot.settings.constants import SUBCATEGORIES
    subcats = SUBCATEGORIES.get(category, {})
    
    if not subcats:
        # Если подкатегорий нет (например, для "swim"), пропускаем этот шаг
        await state.update_data(subcategory=None)
        
        # Проверяем тип объявления
        data = await state.get_data()
        ad_type = data.get('ad_type', 'Продажа')
        
        # Если это АРЕНДА или категория "slots", пропускаем состояние и сразу переходим к названию
        if ad_type == 'Аренда' or category == 'slots':
            # Для категории "slots" устанавливаем состояние в None
            if category == 'slots':
                await state.update_data(condition=None)
            await state.set_state(AddAdState.title)
            try:
                await callback.message.edit_text(
                    TITLE_MESSAGE,
                    reply_markup=back_kb()
                )
                await state.update_data(last_msg_with_keyboard=callback.message.message_id)
            except:
                msg = await callback.message.answer(
                    TITLE_MESSAGE,
                    reply_markup=back_kb()
                )
                await state.update_data(last_msg_with_keyboard=msg.message_id)
        else:
            # Переходим к состоянию (для продажи, кроме "slots")
            await state.set_state(AddAdState.condition)
            try:
                await callback.message.edit_text(
                    CONDITION_MESSAGE,
                    reply_markup=conditions_kb()
                )
                await state.update_data(last_msg_with_keyboard=callback.message.message_id)
            except:
                msg = await callback.message.answer(
                    CONDITION_MESSAGE,
                    reply_markup=conditions_kb()
                )
                await state.update_data(last_msg_with_keyboard=msg.message_id)
    else:
        # Есть подкатегории - показываем их выбор
        await state.set_state(AddAdState.subcategory)
        
        # Для категории "bike" используем специальное сообщение
        message_text = BIKE_SUBCATEGORY_MESSAGE if category == "bike" else SUBCATEGORY_MESSAGE
        
        # Заменяем сообщение вместо удаления
        try:
            await callback.message.edit_text(
                message_text,
                reply_markup=subcategories_kb(category)
            )
            await state.update_data(last_msg_with_keyboard=callback.message.message_id)
        except:
            # Если не удалось отредактировать, отправляем новое
            msg = await callback.message.answer(
                message_text,
                reply_markup=subcategories_kb(category)
            )
            await state.update_data(last_msg_with_keyboard=msg.message_id)


async def bike_group_callback(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик выбора группы подкатегорий велоспорта"""
    await callback.answer()
    
    group_key = callback.data.split(':')[1]
    
    # Убеждаемся, что состояние установлено в subcategory
    await state.set_state(AddAdState.subcategory)
    
    # Сохраняем информацию о том, что мы в группе
    await state.update_data(current_bike_group=group_key)
    
    # Выбираем текст сообщения в зависимости от группы
    # Для группы "bicycles" используем специальное сообщение
    if group_key == "bicycles":
        message_text = BIKE_BICYCLES_SUBCATEGORY_MESSAGE
    elif group_key == "equipment":
        message_text = BIKE_EQUIPMENT_SUBCATEGORY_MESSAGE
    else:
        message_text = SUBCATEGORY_MESSAGE
    
    # Показываем подкатегории внутри группы
    from src.bot.keyboards.keyboards import bike_group_subcategories_kb
    try:
        await callback.message.edit_text(
            message_text,
            reply_markup=bike_group_subcategories_kb(group_key),
            parse_mode="HTML"
        )
        await state.update_data(last_msg_with_keyboard=callback.message.message_id)
    except:
        msg = await callback.message.answer(
            message_text,
            reply_markup=bike_group_subcategories_kb(group_key),
            parse_mode="HTML"
        )
        await state.update_data(last_msg_with_keyboard=msg.message_id)


async def subcategory_callback(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик выбора подкатегории"""
    await callback.answer()
    
    subcategory = callback.data.split(':')[1]
    # Очищаем информацию о группе, так как выбрана конкретная подкатегория
    await state.update_data(subcategory=subcategory, current_bike_group=None)
    
    # Сохраняем ID сообщения для последующего удаления
    menu_msg_id = callback.message.message_id
    
    # Проверяем тип объявления и категорию
    data = await state.get_data()
    ad_type = data.get('ad_type', 'Продажа')
    category = data.get('category')
    
    # Если это АРЕНДА или категория "slots", пропускаем состояние и сразу переходим к названию
    if ad_type == 'Аренда' or category == 'slots':
        # Не запрашиваем состояние для аренды или слотов, сразу к названию
        # Для категории "slots" устанавливаем состояние в None
        if category == 'slots':
            await state.update_data(condition=None)
        await state.set_state(AddAdState.title)
        
        # Заменяем сообщение вместо удаления
        try:
            await callback.message.edit_text(
                TITLE_MESSAGE,
                reply_markup=back_kb()
            )
            await state.update_data(last_msg_with_keyboard=callback.message.message_id)
        except:
            msg = await callback.message.answer(
                TITLE_MESSAGE,
                reply_markup=back_kb()
            )
            await state.update_data(last_msg_with_keyboard=msg.message_id)
    else:
        # Переходим к состоянию (для продажи, кроме "slots")
        await state.set_state(AddAdState.condition)
        
        # Заменяем сообщение вместо удаления
        try:
            await callback.message.edit_text(
                CONDITION_MESSAGE,
                reply_markup=conditions_kb()
            )
            await state.update_data(last_msg_with_keyboard=callback.message.message_id)
        except:
            msg = await callback.message.answer(
                CONDITION_MESSAGE,
                reply_markup=conditions_kb()
            )
            await state.update_data(last_msg_with_keyboard=msg.message_id)


# === РАЗМЕР ===

async def size_callback(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик выбора размера"""
    await callback.answer()
    
    size_data = callback.data.split(':')[1]
    
    if size_data == 'manual':
        # Ввод размера вручную
        await state.set_state(AddAdState.size)
        try:
            await callback.message.edit_text(
                SIZE_CUSTOM_MESSAGE,
                reply_markup=back_kb()
            )
        except:
            msg = await callback.message.answer(
                SIZE_CUSTOM_MESSAGE,
                reply_markup=back_kb()
            )
            await state.update_data(last_msg_with_keyboard=msg.message_id)
            return
        await state.update_data(last_msg_with_keyboard=callback.message.message_id)
    elif size_data == 'none':
        # Без размера
        await state.update_data(size=None)
        
        # Переходим к описанию
        await state.set_state(AddAdState.description)
        
        # Заменяем сообщение вместо удаления
        try:
            await callback.message.edit_text(
                DESCRIPTION_MESSAGE,
                parse_mode='HTML',
                reply_markup=back_kb()
            )
            await state.update_data(last_msg_with_keyboard=callback.message.message_id)
        except:
            msg = await callback.message.answer(
                DESCRIPTION_MESSAGE,
                parse_mode='HTML',
                reply_markup=back_kb()
            )
            await state.update_data(last_msg_with_keyboard=msg.message_id)
    else:
        # Предустановленный размер
        await state.update_data(size=size_data)
        
        # Переходим к описанию
        await state.set_state(AddAdState.description)
        
        # Заменяем сообщение вместо удаления
        try:
            await callback.message.edit_text(
                DESCRIPTION_MESSAGE,
                parse_mode='HTML',
                reply_markup=back_kb()
            )
            await state.update_data(last_msg_with_keyboard=callback.message.message_id)
        except:
            msg = await callback.message.answer(
                DESCRIPTION_MESSAGE,
                parse_mode='HTML',
                reply_markup=back_kb()
            )
            await state.update_data(last_msg_with_keyboard=msg.message_id)


async def size_manual_handler(message: types.Message, state: FSMContext):
    """Обработчик ввода размера вручную"""
    size = message.text.strip()
    
    if not size or len(size) > 6:
        # Просто удаляем сообщение пользователя без отправки сообщения об ошибке
        try:
            await message.delete()
        except:
            pass
        return
    
    # Сохраняем ID сообщения для редактирования
    data = await state.get_data()
    last_msg_id = data.get('last_msg_with_keyboard')
    
    # Удаляем сообщение пользователя (его нельзя редактировать)
    try:
        await message.delete()
    except:
        pass
    
    await state.update_data(size=size)
    
    # Переходим к описанию
    await state.set_state(AddAdState.description)
    
    # Заменяем предыдущее сообщение вместо удаления
    if last_msg_id:
        try:
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=last_msg_id,
                text=DESCRIPTION_MESSAGE,
                parse_mode='HTML',
                reply_markup=back_kb()
            )
            await state.update_data(last_msg_with_keyboard=last_msg_id)
        except:
            msg = await message.answer(
                DESCRIPTION_MESSAGE,
                parse_mode='HTML',
                reply_markup=back_kb()
            )
            await state.update_data(last_msg_with_keyboard=msg.message_id)
    else:
        msg = await message.answer(
            DESCRIPTION_MESSAGE,
            parse_mode='HTML',
            reply_markup=back_kb()
        )
        await state.update_data(last_msg_with_keyboard=msg.message_id)
    
    # Удаляем только сообщение пользователя с введенным размером
    try:
        await message.delete()
    except:
        pass


# === СОСТОЯНИЕ ===

async def condition_callback(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик выбора состояния"""
    await callback.answer()
    
    condition = callback.data.split(':')[1]
    await state.update_data(condition=condition)
    
    # Переходим к названию (после состояния)
    await state.set_state(AddAdState.title)
    
    # Заменяем сообщение вместо удаления
    try:
        await callback.message.edit_text(
            TITLE_MESSAGE,
            reply_markup=back_kb()
        )
        await state.update_data(last_msg_with_keyboard=callback.message.message_id)
    except:
        msg = await callback.message.answer(
            TITLE_MESSAGE,
            reply_markup=back_kb()
        )
        await state.update_data(last_msg_with_keyboard=msg.message_id)


# === ОПИСАНИЕ ===

async def description_handler(message: types.Message, state: FSMContext):
    """Обработчик ввода описания"""
    description = message.text.strip()
    
    if not description:
        # Удаляем сообщение пользователя с пустыми данными
        try:
            await message.delete()
        except:
            pass
        
        # Редактируем сообщение с просьбой ввести описание на сообщение об ошибке
        data = await state.get_data()
        last_msg_id = data.get('last_msg_with_keyboard')
        if last_msg_id:
            try:
                await bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=last_msg_id,
                    text="❌ Описание не может быть пустым.\n\n" + DESCRIPTION_MESSAGE,
                    parse_mode='HTML',
                    reply_markup=back_kb()
                )
                return
            except:
                pass
        
        # Если не удалось отредактировать - отправляем новое сообщение
        await message.answer("❌ Описание не может быть пустым.\n\n" + DESCRIPTION_MESSAGE, parse_mode='HTML', reply_markup=back_kb())
        return
    
    # Обрезаем описание до 650 символов без ошибки
    if len(description) > 650:
        description = description[:650]
    
    # Сохраняем ID сообщения для редактирования
    data = await state.get_data()
    last_msg_id = data.get('last_msg_with_keyboard')
    
    # Удаляем сообщение пользователя (его нельзя редактировать)
    try:
        await message.delete()
    except:
        pass
    
    await state.update_data(description=description if description else None)
    
    # Переходим к цене
    await state.set_state(AddAdState.price)
    
    # Заменяем предыдущее сообщение вместо удаления
    if last_msg_id:
        try:
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=last_msg_id,
                text=get_price_message(data.get('ad_type', 'Продажа')),
                parse_mode='HTML',
                reply_markup=back_kb()
            )
            await state.update_data(last_msg_with_keyboard=last_msg_id)
        except:
            msg = await message.answer(
                get_price_message(data.get('ad_type', 'Продажа')),
                parse_mode='HTML',
                reply_markup=back_kb()
            )
            await state.update_data(last_msg_with_keyboard=msg.message_id)
    else:
        msg = await message.answer(
            get_price_message(data.get('ad_type', 'Продажа')),
            parse_mode='HTML',
            reply_markup=back_kb()
        )
        await state.update_data(last_msg_with_keyboard=msg.message_id)




# === СПОСОБ ДОСТАВКИ ===

async def delivery_method_callback(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик выбора способа доставки"""
    await callback.answer()
    
    delivery_data = callback.data.split(':')[1]
    if delivery_data == 'both':
        delivery_method = "Доставка / Самовывоз"
    elif delivery_data == 'pickup':
        delivery_method = "Самовывоз"
    else:
        delivery_method = "Отправка"
    await state.update_data(delivery_method=delivery_method)
    
    # Переходим к загрузке обложки
    await state.set_state(AddAdState.cover_photo)
    
    # Сообщение для запроса обложки
    cover_photo_text = "📲 Отправьте обложку для вашего объявления\n"
    cover_photo_text += "(_Одно изображение._)"
    
    # Заменяем сообщение вместо удаления
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


# === СПОСОБ СВЯЗИ ===

async def contact_method_callback(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик выбора способа связи"""
    await callback.answer()
    
    method = callback.data.split(':')[1]
    logger.debug(f"Выбран способ связи: {method}")
    await state.update_data(contact_method=method)
    
    if method == 'phone':
        # Переходим к вводу телефона
        await state.set_state(AddAdState.phone_input)
        try:
            await callback.message.edit_text(
                PHONE_INPUT_MESSAGE,
                parse_mode='HTML',
                reply_markup=back_kb()
            )
            await state.update_data(last_msg_with_keyboard=callback.message.message_id)
        except:
            msg = await callback.message.answer(
                PHONE_INPUT_MESSAGE,
                parse_mode='HTML',
                reply_markup=back_kb()
            )
            await state.update_data(last_msg_with_keyboard=msg.message_id)
    else:
        # Выбран Telegram - сохраняем Telegram контакт в contact_method
        user = await get_user_by_tg_id(callback.from_user.id)
        if user:
            # Если есть username, сохраняем его, иначе сохраняем ссылку через tg_id
            if user.username:
                contact_value = f"@{user.username}"
            else:
                contact_value = f"tg://user?id={user.tg_user_id}"
            await state.update_data(contact_method=contact_value)
            logger.debug(f"Установлен contact_method='{contact_value}' для объявления")
        else:
            # Если пользователь не найден, создаем или получаем его
            user = await create_or_update_user(callback.message, from_user=callback.from_user)
            if user.username:
                contact_value = f"@{user.username}"
            else:
                contact_value = f"tg://user?id={user.tg_user_id}"
            await state.update_data(contact_method=contact_value)
            logger.debug(f"Установлен contact_method='{contact_value}' для объявления")
        # Переходим к предпросмотру
        await state.set_state(AddAdState.confirm)
        await show_confirmation(callback.message, state)


async def phone_input_handler(message: types.Message, state: FSMContext):
    """Обработчик ввода номера телефона"""
    phone = message.text.strip().replace(' ', '').replace('-', '').replace('+', '')
    
    # Валидация: только цифры, ровно 11 символов
    if not phone or not phone.isdigit() or len(phone) != 11:
        # Удаляем сообщение пользователя
        try:
            await message.delete()
        except:
            pass
        
        # Редактируем существующее сообщение с ошибкой
        data = await state.get_data()
        last_msg_id = data.get('last_msg_with_keyboard')
        
        # Формируем текст ошибки с введенным номером
        error_text = f"❌ Номер телефона должен содержать ровно 11 цифр (без \"+\").\nНомер \"{phone}\" не валидный, введите еще раз."
        
        if last_msg_id:
            try:
                await bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=last_msg_id,
                    text=error_text,
                    reply_markup=back_kb()
                )
                # Сохраняем ID сообщения для последующего редактирования
                await state.update_data(last_msg_with_keyboard=last_msg_id)
                return
            except Exception as e:
                logger.debug(f"Не удалось отредактировать сообщение {last_msg_id}: {e}")
                # Если не удалось отредактировать, отправляем новое сообщение
                msg = await message.answer(
                    error_text,
                    reply_markup=back_kb()
                )
                await state.update_data(last_msg_with_keyboard=msg.message_id)
                return
        else:
            # Если нет ID сообщения для редактирования, отправляем новое
            msg = await message.answer(
                error_text,
                reply_markup=back_kb()
            )
            await state.update_data(last_msg_with_keyboard=msg.message_id)
            return
    
    # Удаляем сообщение пользователя с телефоном
    try:
        await message.delete()
    except:
        pass
    
    # Сохраняем номер телефона в профиль пользователя (для обратной совместимости)
    user = await get_user_by_tg_id(message.from_user.id)
    if user:
        await set_user_phone(user.tg_user_id, phone)
    
    # Сохраняем номер телефона в contact_method для этого объявления
    await state.update_data(phone=phone, contact_method=phone)
    
    # Переход к подтверждению
    await state.set_state(AddAdState.confirm)
    await show_confirmation(message, state)


# === ПОДТВЕРЖДЕНИЕ ===

async def show_confirmation(message: types.Message, state: FSMContext):
    """Показать превью объявления для подтверждения"""
    data = await state.get_data()
    
    # Проверяем наличие обязательных полей
    if 'city' not in data:
        logger.error(f"Ошибка: отсутствует 'city' в данных состояния. Данные: {data}")
        await message.answer("❌ Ошибка: не указан город. Пожалуйста, начните создание объявления заново.")
        await state.clear()
        return
    
    # Удаляем предыдущее сообщение (просьбу ввести телефон или сообщение о способе связи)
    last_msg_id = data.get('last_msg_with_keyboard')
    if last_msg_id:
        try:
            await bot.delete_message(chat_id=message.chat.id, message_id=last_msg_id)
        except:
            pass
    
    # Удаляем сообщение пользователя с телефоном (если было)
    # Проверяем, что это сообщение от пользователя (не callback)
    if hasattr(message, 'text') and message.text and not hasattr(message, 'callback_query'):
        try:
            await message.delete()
        except:
            pass
    
    # Формируем текст превью в новом формате
    city = data.get('city', 'Не указан')
    country_name = (data.get('country') or "Россия").strip()
    
    # Форматируем цену с пробелами
    price_formatted = f"{data['price']:,}".replace(",", " ")
    
    ad_type_text = data.get('ad_type', 'Продажа')
    category = data.get('category', '')
    condition_text = CONDITIONS.get(data.get('condition', ''), data.get('condition', 'Не указано'))
    
    def _get_country_flag(country: str) -> str:
        """Получить флаг страны по названию (fallback: 🇷🇺)."""
        if not country:
            return "🇷🇺"
        country_lower = country.lower().strip()
        russia_variants = ['россия', 'российская федерация', 'рф', 'russia', 'russian federation']
        if country_lower in russia_variants:
            return "🇷🇺"
        from src.bot.settings.constants import CIS_COUNTRIES
        for _, data_item in CIS_COUNTRIES.items():
            if data_item['name'].lower() == country_lower:
                return data_item['flag']
        return "🇷🇺"

    # Название товара (жирным)
    preview_text = f"<b>{data['title']}</b>\n"
    
    # Размер (для всех категорий кроме слотов и электроники)
    if category not in ['slots', 'electronics'] and data.get('size'):
        preview_text += f"Размер: {data['size']}\n"
    
    # Категория и подкатегория
    category_name = CATEGORIES.get(data['category'], data['category'])
    if data.get('subcategory'):
        subcats = SUBCATEGORIES.get(data['category'], {})
        # Проверяем, есть ли подкатегория в группах велоспорта
        subcategory_name = None
        group_name = None
        if data['category'] == 'bike':
            # Проверяем группы велоспорта
            from src.bot.settings.constants import BIKE_SUBCATEGORY_GROUPS
            for group_key, group_data in BIKE_SUBCATEGORY_GROUPS.items():
                if data['subcategory'] in group_data['subcategories']:
                    group_name = group_data['name']
                    subcategory_name = group_data['subcategories'][data['subcategory']]
                    break
            # Если не нашли в группах, ищем в обычных подкатегориях
            if not subcategory_name:
                subcategory_name = subcats.get(data['subcategory'], data['subcategory'])
        else:
            subcategory_name = subcats.get(data['subcategory'], data['subcategory'])
        
        if group_name and subcategory_name:
            # Если есть группа: Категория → Группа → Подкатегория
            preview_text += f"Категория: {category_name} → {group_name} → {subcategory_name}\n"
        elif subcategory_name:
            # Если нет группы: Категория → Подкатегория
            preview_text += f"Категория: {category_name} → {subcategory_name}\n"
        else:
            preview_text += f"Категория: {category_name}\n"
    else:
        preview_text += f"Категория: {category_name}\n"
    
    # Пустая строка перед типом объявления
    preview_text += "\n"
    
    # Тип объявления и состояние
    if ad_type_text == "Аренда":
        preview_text += f"♻️ Аренда\n"
    else:
        preview_text += f"🛒 Продажа • {condition_text}\n"
    
    # Цена и город/страна (с флагом). Если Россия — город и страна на отдельной строке
    country_flag = _get_country_flag(country_name)
    location = f"{city}, {country_flag} {country_name}"
    _is_russia = (country_name or "").lower().strip() in ("россия", "российская федерация", "рф", "russia", "russian federation")
    price_label = f"{price_formatted} ₽/сутки" if ad_type_text == "Аренда" else f"{price_formatted} ₽"
    if _is_russia:
        preview_text += f"💰 Цена: {price_label}\n📍 {location}\n"
    else:
        preview_text += f"💰 Цена: {price_label} 📍 {location}\n"
    
    # Доставка (для аренды и категории "slots" не показываем)
    if ad_type_text != 'Аренда' and category != 'slots':
        delivery_method = data.get('delivery_method', 'Не указан')
        # Преобразуем "Отправка" в "Доставка и самовывоз", "Доставка / Самовывоз" тоже в "Доставка и самовывоз"
        if delivery_method == "Отправка":
            delivery_display = "Доставка и самовывоз"
        elif delivery_method == "Доставка / Самовывоз":
            delivery_display = "Доставка и самовывоз"
        else:
            delivery_display = delivery_method
        preview_text += f"🚚 : {delivery_display}\n"
    
    # Описание (если есть) - с заголовком жирным
    if data.get('description'):
        # Экранируем HTML-символы в описании пользователя
        from html import escape
        escaped_description = escape(data['description'])
        preview_text += f"\n📝 <b>Описание</b>:\n{escaped_description}"

    # Контактные данные (внизу): телефон, @username или ссылка «Ссылка» для tg://
    contact_value = format_contact_for_display(data.get('contact_method'))
    if contact_value:
        preview_text += f"\n\n<b>Контактные данные:</b> {contact_value}"
    
    # Отправляем все фото с превью
    photos = data.get('photos', [])
    if photos:
        # Если несколько фото, отправляем как медиа-группу
        if len(photos) > 1:
            media_group = []
            for i, photo in enumerate(photos):
                if i == 0:
                    # Первое фото с подписью
                    media_group.append(types.InputMediaPhoto(media=photo['file_id'], caption=preview_text, parse_mode='HTML'))
                else:
                    # Остальные фото без подписи
                    media_group.append(types.InputMediaPhoto(media=photo['file_id']))
            
            await message.answer_media_group(media_group)
        else:
            # Одно фото
            await message.answer_photo(
                photo=photos[0]['file_id'],
                caption=preview_text,
                parse_mode='HTML'
            )
    else:
        # Если фото нет, отправляем только текст
        await message.answer(
            preview_text,
            parse_mode='HTML'
        )
    
    await state.set_state(AddAdState.confirm)
    
    msg = await message.answer(
        CONFIRM_MESSAGE,
        reply_markup=confirm_kb()
    )
    await state.update_data(confirm_msg_id=msg.message_id)


async def confirm_send_callback(callback: types.CallbackQuery, state: FSMContext):
    """Отправка объявления на модерацию"""
    data = await state.get_data()
    
    # Удаляем сообщение "Проверьте объявление..."
    confirm_msg_id = data.get('confirm_msg_id')
    if confirm_msg_id:
        try:
            await bot.delete_message(chat_id=callback.message.chat.id, message_id=confirm_msg_id)
        except:
            pass
    
    # Удаляем сообщение с фото превью (если есть)
    try:
        # Пытаемся удалить предыдущее сообщение (фото с превью)
        photo_msg_id = confirm_msg_id - 1 if confirm_msg_id else None
        if photo_msg_id and photo_msg_id > 0:
            try:
                await bot.delete_message(chat_id=callback.message.chat.id, message_id=photo_msg_id)
            except:
                pass
    except:
        pass
    
    # получаем юзера
    user = await get_user_by_tg_id(callback.from_user.id)
    if not user:
        user = await create_or_update_user(callback.message, from_user=callback.from_user)
    
    # Проверяем лимит размещений
    from src.bot.database.methods import is_trusted_seller, count_user_ads_today
    is_trusted = await is_trusted_seller(callback.from_user.id)
    daily_limit = 6 if is_trusted else 3
    ads_today = await count_user_ads_today(user.id)
    
    if ads_today >= daily_limit:
        await callback.answer("Достигнут лимит размещений на сегодня. Попробуйте завтра.", show_alert=True)
        return

    await callback.answer()
    
    # Проверяем и логируем contact_method перед созданием объявления
    contact_method = data.get('contact_method')
    logger.debug(f"Создание объявления: contact_method из state = {contact_method}")
    
    # Убеждаемся, что contact_method установлен
    if not contact_method:
        # Если не установлен, используем Telegram контакт по умолчанию
        if user.username:
            contact_method = f"@{user.username}"
        else:
            contact_method = f"tg://user?id={user.tg_user_id}"
        data['contact_method'] = contact_method
        logger.warning(f"contact_method не найден в state, устанавливаю Telegram контакт по умолчанию: {contact_method}")
    
    # создаем объявление
    ad = await create_ad(user.id, data)
    logger.debug(f"Объявление #{ad.id} создано с contact_method = {ad.contact_method}")
    
    # добавляем фото
    await add_ad_photos(ad.id, data['photos'])
    
    # логируем
    from src.bot.logging_config import log_ad_action
    username = callback.from_user.username or callback.from_user.first_name
    log_ad_action(callback.from_user.id, username, ad.id, "создал")
    
    # Отправляем сообщение с кнопкой "В главное меню"
    from src.bot.keyboards.keyboards import main_menu_from_moderation_kb
    msg = await callback.message.answer(
        SENT_TO_MODERATION_MESSAGE,
        reply_markup=main_menu_from_moderation_kb()
    )
    
    # Сохраняем ID сообщения о модерации для последующего удаления
    await state.update_data(moderation_msg_id=msg.message_id)
    
    # на модерацию
    await send_to_moderation(ad.id, data)
    
    await state.clear()


# === ОТПРАВКА НА МОДЕРАЦИЮ ===

async def send_to_moderation(ad_id: int, data: dict, edited_fields: list = None):
    """Отправить объявление на модерацию
    
    Args:
        ad_id: ID объявления
        data: Данные объявления
        edited_fields: Список измененных полей (для редактирования)
    """
    from src.bot.settings.settings import MODERATION_CHAT_ID
    
    logger.info(f"отправляю объявление #{ad_id} на модерацию в чат {MODERATION_CHAT_ID}")
    
    # Город/страна
    city = data.get('city', 'Не указан')
    country_name = (data.get('country') or "Россия").strip()
    
    # Форматируем цену с пробелами
    price_formatted = f"{data['price']:,}".replace(",", " ")
    
    ad_type_text = data.get('ad_type', 'Продажа')
    category = data.get('category', '')
    condition_text = CONDITIONS.get(data.get('condition', ''), data.get('condition', 'Не указано'))
    
    def _get_country_flag(country: str) -> str:
        """Получить флаг страны по названию (fallback: 🇷🇺)."""
        if not country:
            return "🇷🇺"
        country_lower = country.lower().strip()
        russia_variants = ['россия', 'российская федерация', 'рф', 'russia', 'russian federation']
        if country_lower in russia_variants:
            return "🇷🇺"
        from src.bot.settings.constants import CIS_COUNTRIES
        for _, data_item in CIS_COUNTRIES.items():
            if data_item['name'].lower() == country_lower:
                return data_item['flag']
        return "🇷🇺"

    # Формируем текст в новом формате для модерации
    mod_text = ""
    
    # Если это редактирование, показываем измененные поля в начале
    if edited_fields:
        field_names = {
            'title': 'Название',
            'description': 'Описание',
            'category': 'Категория',
            'subcategory': 'Подкатегория',
            'size': 'Размер',
            'city': 'Город',
            'country': 'Страна',
            'contact': 'Контакт',
            'photos': 'Фото',
            'price': 'Цена',
            'condition': 'Состояние',
            'delivery_method': 'Способ доставки'
        }
        mod_text += "✏️ <b>Изменено:</b>\n"
        for field in edited_fields:
            field_name = field_names.get(field, field)
            mod_text += f"  • {field_name}\n"
        mod_text += "\n"
    
    # Название товара (без тегов, просто текст)
    mod_text += f"{data['title']}\n"
    
    # Размер (для всех категорий кроме слотов и электроники)
    if category not in ['slots', 'electronics'] and data.get('size'):
        mod_text += f"Размер: {data['size']}\n"
    
    # Категория и подкатегория
    category_name = CATEGORIES.get(data['category'], data['category'])
    if data.get('subcategory'):
        subcats = SUBCATEGORIES.get(data['category'], {})
        # Проверяем, есть ли подкатегория в группах велоспорта
        subcategory_name = None
        if data['category'] == 'bike':
            # Проверяем группы велоспорта
            from src.bot.settings.constants import BIKE_SUBCATEGORY_GROUPS
            for group_key, group_data in BIKE_SUBCATEGORY_GROUPS.items():
                if data['subcategory'] in group_data['subcategories']:
                    subcategory_name = group_data['subcategories'][data['subcategory']]
                    break
            # Если не нашли в группах, ищем в обычных подкатегориях
            if not subcategory_name:
                subcategory_name = subcats.get(data['subcategory'], data['subcategory'])
        else:
            subcategory_name = subcats.get(data['subcategory'], data['subcategory'])
        
        if subcategory_name:
            mod_text += f"Категория: {category_name} → {subcategory_name}\n"
        else:
            mod_text += f"Категория: {category_name}\n"
    else:
        mod_text += f"Категория: {category_name}\n"
    
    # Пустая строка перед типом объявления
    mod_text += "\n"
    
    # Тип объявления и состояние
    if ad_type_text == "Аренда":
        mod_text += f"♻️ Аренда\n"
    else:
        mod_text += f"🛒 Продажа • {condition_text}\n"
    
    # Цена и город/страна (с флагом). Если Россия — город и страна на отдельной строке
    country_flag = _get_country_flag(country_name)
    location = f"{city}, {country_flag} {country_name}"
    _is_russia = (country_name or "").lower().strip() in ("россия", "российская федерация", "рф", "russia", "russian federation")
    price_label = f"{price_formatted} ₽/сутки" if ad_type_text == "Аренда" else f"{price_formatted} ₽"
    if _is_russia:
        mod_text += f"💰 Цена: {price_label}\n📍 {location}\n"
    else:
        mod_text += f"💰 Цена: {price_label} 📍 {location}\n"
    
    # Доставка
    if data.get('delivery_method'):
        # Преобразуем "Отправка" в "Доставка и самовывоз", "Доставка / Самовывоз" тоже в "Доставка и самовывоз"
        if data['delivery_method'] == "Отправка":
            delivery_display = "Доставка и самовывоз"
        elif data['delivery_method'] == "Доставка / Самовывоз":
            delivery_display = "Доставка и самовывоз"
        else:
            delivery_display = data['delivery_method']
        mod_text += f"🚚 : {delivery_display}\n"
    
    # Описание (если есть) - с заголовком жирным
    if data.get('description'):
        mod_text += f"\n📝 <b>Описание</b>:\n{data['description']}"

    # Контактные данные (внизу) - всегда показываем при редактировании или если есть контакт
    contact_value = format_contact_for_display(data.get('contact_method'))
    if edited_fields or contact_value:
        # При редактировании всегда показываем контакт (даже если он не изменился)
        if contact_value:
            mod_text += f"\n\n<b>Контактные данные:</b> {contact_value}"
        else:
            # Если контакт не указан, все равно показываем заголовок при редактировании
            mod_text += f"\n\n<b>Контактные данные:</b> не указаны"
    
    photos = data.get('photos', [])
    if photos:
        try:
            logger.info(f"отправляю {len(photos)} фото объявления #{ad_id} с кнопками модерации")
            
            # Отправляем все фото как медиа-группу (альбом)
            if len(photos) == 1:
                # Если одно фото, отправляем как обычное сообщение
                sent_msg = await bot.send_photo(
                    chat_id=MODERATION_CHAT_ID,
                    photo=get_fsinput_photo(
                        format_file_id_to_storage_path(photos[0]['file_id'])
                    ),
                    caption=mod_text,
                    parse_mode='HTML',
                    reply_markup=moderation_kb(ad_id)
                )
                logger.info(f"объявление #{ad_id} с 1 фото успешно отправлено на модерацию, message_id: {sent_msg.message_id}")
            else:
                # Если несколько фото, отправляем как альбом
                media_group = []
                for i, photo in enumerate(photos):
                    if i == 0:
                        # Первое фото с подписью
                        media_group.append(types.InputMediaPhoto(media=photo['file_id'], caption=mod_text, parse_mode='HTML'))
                    else:
                        # Остальные фото без подписи
                        media_group.append(types.InputMediaPhoto(media=photo['file_id']))
                
                # Отправляем альбом
                sent_messages = await bot.send_media_group(
                    chat_id=MODERATION_CHAT_ID,
                    media=media_group
                )
                logger.info(f"объявление #{ad_id} с {len(photos)} фото успешно отправлено на модерацию как альбом")
                
                # Отправляем кнопки модерации отдельным сообщением после альбома
                await bot.send_message(
                    chat_id=MODERATION_CHAT_ID,
                    text=f"Модерация объявления #{ad_id}:",
                    reply_markup=moderation_kb(ad_id)
                )
        except Exception as e:
            logger.error(f"ошибка при отправке объявления #{ad_id} на модерацию: {e}", exc_info=True)
    else:
        logger.error(f"объявление #{ad_id} не имеет фото, не могу отправить на модерацию")


async def send_edit_to_moderation(edit_id: int, original_ad_id: int, data: dict, edited_fields: list):
    """Отправить копию объявления (редактирование) на модерацию. Оригинал не трогаем."""
    from src.bot.settings.settings import MODERATION_CHAT_ID
    from src.bot.keyboards.keyboards import moderation_edit_kb

    logger.info(f"отправляю редактирование #{edit_id} (оригинал #{original_ad_id}) на модерацию")
    city = data.get('city', 'Не указан')
    country_name = (data.get('country') or "Россия").strip()
    price_formatted = f"{data['price']:,}".replace(",", " ")
    ad_type_text = data.get('ad_type', 'Продажа')
    category = data.get('category', '')
    condition_text = CONDITIONS.get(data.get('condition', ''), data.get('condition', 'Не указано'))

    def _get_country_flag(c):
        if not c:
            return "🇷🇺"
        cl = c.lower().strip()
        for x in ['россия', 'российская федерация', 'рф', 'russia', 'russian federation']:
            if cl == x:
                return "🇷🇺"
        from src.bot.settings.constants import CIS_COUNTRIES
        for _, d in CIS_COUNTRIES.items():
            if d['name'].lower() == cl:
                return d['flag']
        return "🇷🇺"

    mod_text = ""
    field_names = {
        'title': 'Название', 'description': 'Описание', 'category': 'Категория',
        'subcategory': 'Подкатегория', 'size': 'Размер', 'city': 'Город',
        'country': 'Страна', 'contact': 'Контакт', 'photos': 'Фото', 'price': 'Цена',
        'condition': 'Состояние', 'delivery_method': 'Способ доставки'
    }
    mod_text += "✏️ <b>Изменено:</b>\n"
    for f in edited_fields:
        mod_text += f"  • {field_names.get(f, f)}\n"
    mod_text += "\n"
    mod_text += f"{data['title']}\n"
    if category not in ['slots', 'electronics'] and data.get('size'):
        mod_text += f"Размер: {data['size']}\n"
    category_name = CATEGORIES.get(data['category'], data['category'])
    if data.get('subcategory'):
        subcats = SUBCATEGORIES.get(data['category'], {})
        subcategory_name = None
        if data['category'] == 'bike':
            from src.bot.settings.constants import BIKE_SUBCATEGORY_GROUPS
            for _, gd in BIKE_SUBCATEGORY_GROUPS.items():
                if data['subcategory'] in gd['subcategories']:
                    subcategory_name = gd['subcategories'][data['subcategory']]
                    break
            if not subcategory_name:
                subcategory_name = subcats.get(data['subcategory'], data['subcategory'])
        else:
            subcategory_name = subcats.get(data['subcategory'], data['subcategory'])
        mod_text += f"Категория: {category_name} → {subcategory_name}\n" if subcategory_name else f"Категория: {category_name}\n"
    else:
        mod_text += f"Категория: {category_name}\n"
    mod_text += "\n"
    if ad_type_text == "Аренда":
        mod_text += "♻️ Аренда\n"
    else:
        mod_text += f"🛒 Продажа • {condition_text}\n"
    location = f"{city}, {_get_country_flag(country_name)} {country_name}"
    _is_russia = (country_name or "").lower().strip() in ("россия", "российская федерация", "рф", "russia", "russian federation")
    price_label = f"{price_formatted} ₽/сутки" if ad_type_text == "Аренда" else f"{price_formatted} ₽"
    if _is_russia:
        mod_text += f"💰 Цена: {price_label}\n📍 {location}\n"
    else:
        mod_text += f"💰 Цена: {price_label} 📍 {location}\n"
    if data.get('delivery_method'):
        dm = data['delivery_method']
        display = "Доставка и самовывоз" if dm in ("Отправка", "Доставка / Самовывоз") else dm
        mod_text += f"🚚 : {display}\n"
    if data.get('description'):
        mod_text += f"\n📝 <b>Описание</b>:\n{data['description']}"
    cv = format_contact_for_display(data.get('contact_method'))
    mod_text += f"\n\n<b>Контактные данные:</b> {cv}" if cv else "\n\n<b>Контактные данные:</b> не указаны"

    photos = data.get('photos', [])
    if not photos:
        logger.error(f"редактирование #{edit_id} без фото, не отправляю на модерацию")
        return
    try:
        if len(photos) == 1:
            await bot.send_photo(
                chat_id=MODERATION_CHAT_ID,
                photo=get_fsinput_photo(format_file_id_to_storage_path(photos[0]['file_id'])),
                caption=mod_text,
                parse_mode='HTML',
                reply_markup=moderation_edit_kb(edit_id)
            )
        else:
            media_group = []
            for i, p in enumerate(photos):
                if i == 0:
                    media_group.append(types.InputMediaPhoto(media=p['file_id'], caption=mod_text, parse_mode='HTML'))
                else:
                    media_group.append(types.InputMediaPhoto(media=p['file_id']))
            await bot.send_media_group(chat_id=MODERATION_CHAT_ID, media=media_group)
            await bot.send_message(
                chat_id=MODERATION_CHAT_ID,
                text=f"Модерация редактирования (оригинал #{original_ad_id}):",
                reply_markup=moderation_edit_kb(edit_id)
            )
        logger.info(f"редактирование #{edit_id} отправлено на модерацию")
    except Exception as e:
        logger.error(f"ошибка отправки редактирования #{edit_id} на модерацию: {e}", exc_info=True)


# === ОТМЕНА ===

async def back_callback(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'Назад'"""
    await callback.answer()
    
    current_state = await state.get_state()
    data = await state.get_data()
    
    # НЕ деактивируем кнопки для состояния confirm, так как будем редактировать сообщение
    if current_state != AddAdState.confirm:
        # деактивируем кнопки для остальных состояний
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except:
            pass
    
    # определяем предыдущий шаг в зависимости от текущего состояния
    if current_state == AddAdState.category:
        # возврат к выбору типа объявления - редактируем текущее сообщение
        from src.bot.keyboards.keyboards import ad_type_selection_kb
        text = "📝 <b>Выберите тип объявления:</b>"
        try:
            await callback.message.edit_text(
                text,
                parse_mode='HTML',
                reply_markup=ad_type_selection_kb()
            )
        except:
            # Если не удалось отредактировать, отправляем новое сообщение
            await callback.message.answer(
                text,
                parse_mode='HTML',
                reply_markup=ad_type_selection_kb()
            )
        
    elif current_state == AddAdState.subcategory:
        # возврат к категории или к списку подкатегорий велоспорта
        data = await state.get_data()
        category = data.get('category')
        current_bike_group = data.get('current_bike_group')
        
        # Проверяем, находимся ли мы внутри группы велоспорта
        # Если current_bike_group установлен, значит мы внутри группы
        if category == "bike" and current_bike_group:
            # Возвращаемся к списку подкатегорий велоспорта (из группы)
            await state.update_data(current_bike_group=None)  # Очищаем информацию о группе
            try:
                await callback.message.edit_text(
                    BIKE_SUBCATEGORY_MESSAGE,
                    reply_markup=subcategories_kb(category)
                )
                await state.update_data(last_msg_with_keyboard=callback.message.message_id)
            except:
                msg = await callback.message.answer(
                    BIKE_SUBCATEGORY_MESSAGE,
                    reply_markup=subcategories_kb(category)
                )
                await state.update_data(last_msg_with_keyboard=msg.message_id)
        else:
            # Возврат к категории (из списка подкатегорий)
            await state.set_state(AddAdState.category)
            await state.update_data(current_bike_group=None)  # Очищаем информацию о группе
            ad_type = data.get('ad_type', 'Продажа')
            try:
                await callback.message.edit_text(
                    CATEGORY_MESSAGE,
                    reply_markup=categories_kb(ad_type=ad_type)
                )
                await state.update_data(last_msg_with_keyboard=callback.message.message_id)
            except:
                msg = await callback.message.answer(
                    CATEGORY_MESSAGE,
                    reply_markup=categories_kb(ad_type=ad_type)
                )
                await state.update_data(last_msg_with_keyboard=msg.message_id)
        
    elif current_state == AddAdState.condition:
        # возврат к подкатегории или категории - редактируем текущее сообщение
        data = await state.get_data()
        category = data.get('category')
        subcategory = data.get('subcategory')
        
        # Проверяем, есть ли подкатегории у категории
        from src.bot.settings.constants import SUBCATEGORIES
        subcats = SUBCATEGORIES.get(category, {}) if category else {}
        
        # Если есть подкатегории и выбрана подкатегория, возвращаемся к выбору подкатегории
        # Если подкатегорий нет или они не были выбраны, возвращаемся к выбору категории
        if category and subcats and subcategory:
            # Проверяем, является ли подкатегория частью группы велоспорта
            from src.bot.settings.constants import BIKE_SUBCATEGORY_GROUPS
            is_from_group = False
            group_key = None
            if category == "bike":
                for g_key, g_data in BIKE_SUBCATEGORY_GROUPS.items():
                    if subcategory in g_data["subcategories"]:
                        is_from_group = True
                        group_key = g_key
                        break
            
            if is_from_group and group_key:
                # Если подкатегория из группы, возвращаемся к группе
                from src.bot.keyboards.keyboards import bike_group_subcategories_kb
                await state.set_state(AddAdState.subcategory)
                # Сохраняем информацию о том, что мы в группе
                await state.update_data(current_bike_group=group_key)
                # Выбираем текст сообщения в зависимости от группы
                # Для группы "bicycles" используем специальное сообщение
                if group_key == "bicycles":
                    message_text = BIKE_BICYCLES_SUBCATEGORY_MESSAGE
                elif group_key == "equipment":
                    message_text = BIKE_EQUIPMENT_SUBCATEGORY_MESSAGE
                else:
                    message_text = SUBCATEGORY_MESSAGE
                try:
                    await callback.message.edit_text(
                        message_text,
                        parse_mode="HTML",
                        reply_markup=bike_group_subcategories_kb(group_key)
                    )
                    await state.update_data(last_msg_with_keyboard=callback.message.message_id)
                except:
                    msg = await callback.message.answer(
                        message_text,
                        parse_mode="HTML",
                        reply_markup=bike_group_subcategories_kb(group_key)
                    )
                    await state.update_data(last_msg_with_keyboard=msg.message_id)
            else:
                # Возврат к списку подкатегорий
                await state.set_state(AddAdState.subcategory)
                # Для категории "bike" используем специальное сообщение
                message_text = BIKE_SUBCATEGORY_MESSAGE if category == "bike" else SUBCATEGORY_MESSAGE
                try:
                    await callback.message.edit_text(
                        message_text,
                        reply_markup=subcategories_kb(category)
                    )
                    await state.update_data(last_msg_with_keyboard=callback.message.message_id)
                except:
                    msg = await callback.message.answer(
                        message_text,
                        reply_markup=subcategories_kb(category)
                    )
                    await state.update_data(last_msg_with_keyboard=msg.message_id)
        else:
            # Возврат к категории (если подкатегорий нет или они не были выбраны)
            await state.set_state(AddAdState.category)
            ad_type = data.get('ad_type', 'Продажа')
            try:
                await callback.message.edit_text(
                    CATEGORY_MESSAGE,
                    reply_markup=categories_kb(ad_type=ad_type)
                )
                await state.update_data(last_msg_with_keyboard=callback.message.message_id)
            except:
                msg = await callback.message.answer(
                    CATEGORY_MESSAGE,
                    reply_markup=categories_kb(ad_type=ad_type)
                )
                await state.update_data(last_msg_with_keyboard=msg.message_id)
            
    elif current_state == AddAdState.title:
        # Проверяем тип объявления и категорию
        data = await state.get_data()
        ad_type = data.get('ad_type', 'Продажа')
        category = data.get('category')
        subcategory = data.get('subcategory')
        
        # Проверяем, есть ли подкатегории у категории
        from src.bot.settings.constants import SUBCATEGORIES
        subcats = SUBCATEGORIES.get(category, {}) if category else {}
        
        # Если это АРЕНДА или категория "slots", возвращаемся к подкатегории или категории (пропускаем состояние)
        if ad_type == 'Аренда' or category == 'slots':
            # Если есть подкатегории и выбрана подкатегория, возвращаемся к выбору подкатегории
            # Если подкатегорий нет или они не были выбраны, возвращаемся к выбору категории
            if category and subcats and subcategory:
                # Проверяем, является ли подкатегория частью группы велоспорта
                from src.bot.settings.constants import BIKE_SUBCATEGORY_GROUPS
                is_from_group = False
                group_key = None
                if category == "bike":
                    for g_key, g_data in BIKE_SUBCATEGORY_GROUPS.items():
                        if subcategory in g_data["subcategories"]:
                            is_from_group = True
                            group_key = g_key
                            break
                
                if is_from_group and group_key:
                    # Если подкатегория из группы, возвращаемся к группе
                    from src.bot.keyboards.keyboards import bike_group_subcategories_kb
                    await state.set_state(AddAdState.subcategory)
                    # Сохраняем информацию о том, что мы в группе
                    await state.update_data(current_bike_group=group_key)
                    # Выбираем текст сообщения в зависимости от группы
                    # Для группы "bicycles" используем специальное сообщение
                    if group_key == "bicycles":
                        message_text = BIKE_BICYCLES_SUBCATEGORY_MESSAGE
                    elif group_key == "equipment":
                        message_text = BIKE_EQUIPMENT_SUBCATEGORY_MESSAGE
                    else:
                        message_text = SUBCATEGORY_MESSAGE
                    try:
                        await callback.message.edit_text(
                            message_text,
                            parse_mode="HTML",
                            reply_markup=bike_group_subcategories_kb(group_key)
                        )
                        await state.update_data(last_msg_with_keyboard=callback.message.message_id)
                    except:
                        msg = await callback.message.answer(
                            message_text,
                            parse_mode="HTML",
                            reply_markup=bike_group_subcategories_kb(group_key)
                        )
                        await state.update_data(last_msg_with_keyboard=msg.message_id)
                else:
                    # Возврат к списку подкатегорий
                    await state.set_state(AddAdState.subcategory)
                    # Для категории "bike" используем специальное сообщение
                    message_text = BIKE_SUBCATEGORY_MESSAGE if category == "bike" else SUBCATEGORY_MESSAGE
                    try:
                        await callback.message.edit_text(
                            message_text,
                            reply_markup=subcategories_kb(category)
                        )
                        await state.update_data(last_msg_with_keyboard=callback.message.message_id)
                    except:
                        msg = await callback.message.answer(
                            message_text,
                            reply_markup=subcategories_kb(category)
                        )
                        await state.update_data(last_msg_with_keyboard=msg.message_id)
            else:
                # Возврат к категории (если подкатегорий нет или они не были выбраны)
                await state.set_state(AddAdState.category)
                ad_type = data.get('ad_type', 'Продажа')
                try:
                    await callback.message.edit_text(
                        CATEGORY_MESSAGE,
                        reply_markup=categories_kb(ad_type=ad_type)
                    )
                    await state.update_data(last_msg_with_keyboard=callback.message.message_id)
                except:
                    msg = await callback.message.answer(
                        CATEGORY_MESSAGE,
                        reply_markup=categories_kb(ad_type=ad_type)
                    )
                    await state.update_data(last_msg_with_keyboard=msg.message_id)
        else:
            # Для продажи (кроме "slots") возвращаемся к состоянию - редактируем текущее сообщение
            await state.set_state(AddAdState.condition)
            try:
                await callback.message.edit_text(
                    CONDITION_MESSAGE,
                    reply_markup=conditions_kb()
                )
                await state.update_data(last_msg_with_keyboard=callback.message.message_id)
            except:
                msg = await callback.message.answer(
                    CONDITION_MESSAGE,
                    reply_markup=conditions_kb()
                )
                await state.update_data(last_msg_with_keyboard=msg.message_id)
        
    elif current_state == AddAdState.size:
        # Проверяем, находимся ли мы в состоянии ввода ручного размера
        # Если да, возвращаемся к выбору размера, иначе к названию
        if callback.message.text and "Введите размер вручную" in callback.message.text:
            # Возврат к выбору размера
            try:
                await callback.message.edit_text(
                    SIZE_MESSAGE,
                    reply_markup=sizes_kb()
                )
                await state.update_data(last_msg_with_keyboard=callback.message.message_id)
            except:
                msg = await callback.message.answer(
                    SIZE_MESSAGE,
                    reply_markup=sizes_kb()
                )
                await state.update_data(last_msg_with_keyboard=msg.message_id)
        else:
            # возврат к названию - редактируем текущее сообщение
            await state.set_state(AddAdState.title)
            try:
                await callback.message.edit_text(
                    TITLE_MESSAGE,
                    reply_markup=back_kb()
                )
                await state.update_data(last_msg_with_keyboard=callback.message.message_id)
            except:
                msg = await callback.message.answer(
                    TITLE_MESSAGE,
                    reply_markup=back_kb()
                )
                await state.update_data(last_msg_with_keyboard=msg.message_id)
        
    elif current_state == AddAdState.description:
        # возврат к размеру или названию - редактируем текущее сообщение
        data = await state.get_data()
        subcategory = data.get('subcategory')
        category = data.get('category')
        # Для категорий "swim", "bike" и "run" размер обязателен всегда
        needs_size = category in ['swim', 'bike', 'run'] or subcategory in SIZE_REQUIRED_SUBCATEGORIES
        if needs_size:
            await state.set_state(AddAdState.size)
            try:
                await callback.message.edit_text(
                    SIZE_MESSAGE,
                    reply_markup=sizes_kb()
                )
                await state.update_data(last_msg_with_keyboard=callback.message.message_id)
            except:
                msg = await callback.message.answer(
                    SIZE_MESSAGE,
                    reply_markup=sizes_kb()
                )
                await state.update_data(last_msg_with_keyboard=msg.message_id)
        else:
            await state.set_state(AddAdState.title)
            try:
                await callback.message.edit_text(
                    TITLE_MESSAGE,
                    reply_markup=back_kb()
                )
                await state.update_data(last_msg_with_keyboard=callback.message.message_id)
            except:
                msg = await callback.message.answer(
                    TITLE_MESSAGE,
                    reply_markup=back_kb()
                )
                await state.update_data(last_msg_with_keyboard=msg.message_id)
        
    elif current_state == AddAdState.price:
        # возврат к описанию - редактируем текущее сообщение
        await state.set_state(AddAdState.description)
        try:
            await callback.message.edit_text(
                DESCRIPTION_MESSAGE,
                parse_mode='HTML',
                reply_markup=back_kb()
            )
            await state.update_data(last_msg_with_keyboard=callback.message.message_id)
        except:
            msg = await callback.message.answer(
                DESCRIPTION_MESSAGE,
                parse_mode='HTML',
                reply_markup=back_kb()
            )
            await state.update_data(last_msg_with_keyboard=msg.message_id)
        
    elif current_state == AddAdState.location_select:
        # Проверяем, находимся ли мы на шаге выбора страны
        if callback.message.text and ("Выберите страну:" in callback.message.text or "⚠️ Раздел пока в разработке" in callback.message.text):
            # Возврат к выбору города - редактируем текущее сообщение
            try:
                await callback.message.edit_text(
                    LOCATION_MESSAGE,
                    reply_markup=cities_kb()
                )
                await state.update_data(last_msg_with_keyboard=callback.message.message_id)
            except:
                msg = await callback.message.answer(
                    LOCATION_MESSAGE,
                    reply_markup=cities_kb()
                )
                await state.update_data(last_msg_with_keyboard=msg.message_id)
        else:
            # возврат к вводу цены - редактируем текущее сообщение
            await state.set_state(AddAdState.price)
            try:
                await callback.message.edit_text(
                    get_price_message(data.get('ad_type', 'Продажа')),
                    parse_mode='HTML',
                    reply_markup=back_kb()
                )
                await state.update_data(last_msg_with_keyboard=callback.message.message_id)
            except:
                msg = await callback.message.answer(
                    get_price_message(data.get('ad_type', 'Продажа')),
                    parse_mode='HTML',
                    reply_markup=back_kb()
                )
                await state.update_data(last_msg_with_keyboard=msg.message_id)
        
    elif current_state == AddAdState.location_city_custom:
        # возврат к выбору города - редактируем текущее сообщение
        await state.set_state(AddAdState.location_select)
        try:
            await callback.message.edit_text(
                LOCATION_MESSAGE,
                reply_markup=cities_kb()
            )
            await state.update_data(last_msg_with_keyboard=callback.message.message_id)
        except:
            msg = await callback.message.answer(
                LOCATION_MESSAGE,
                reply_markup=cities_kb()
            )
            await state.update_data(last_msg_with_keyboard=msg.message_id)
        
    elif current_state == AddAdState.location_country_custom:
        # возврат к выбору города - редактируем текущее сообщение
        await state.set_state(AddAdState.location_select)
        try:
            await callback.message.edit_text(
                LOCATION_MESSAGE,
                reply_markup=cities_kb()
            )
            await state.update_data(last_msg_with_keyboard=callback.message.message_id)
        except:
            msg = await callback.message.answer(
                LOCATION_MESSAGE,
                reply_markup=cities_kb()
            )
            await state.update_data(last_msg_with_keyboard=msg.message_id)
        
    elif current_state == AddAdState.location_city_after_country:
        # возврат к выбору страны - редактируем текущее сообщение
        # Проверяем, есть ли выбранная страна - если есть, значит мы на странице списка городов
        data = await state.get_data()
        selected_country_key = data.get('selected_country_key')
        
        # Если есть выбранная страна - значит мы на странице списка городов страны
        # Возвращаемся к выбору страны
        if selected_country_key and selected_country_key in CIS_COUNTRIES:
            await state.set_state(AddAdState.location_select)
            # Удаляем selected_country_key, чтобы очистить состояние
            await state.update_data(selected_country_key=None)
            country_message = "⚠️ Раздел пока в разработке.\nОбъявления сохраняются и видны в каталоге, но не публикуются в общем канале (он работает только для РФ).\n<b>Для других стран появятся свои каналы, если будет спрос</b>"
            try:
                await callback.message.edit_text(
                    country_message,
                    reply_markup=countries_kb(),
                    parse_mode='HTML'
                )
                await state.update_data(last_msg_with_keyboard=callback.message.message_id)
            except:
                msg = await callback.message.answer(
                    country_message,
                    reply_markup=countries_kb(),
                    parse_mode='HTML'
                )
                await state.update_data(last_msg_with_keyboard=msg.message_id)
        else:
            # Если это был ввод города вручную - возвращаемся к выбору города из списка или страны
            # Возвращаемся к выбору страны
            await state.set_state(AddAdState.location_select)
            try:
                await callback.message.edit_text(
                    "Выберите страну:",
                    reply_markup=countries_kb()
                )
                await state.update_data(last_msg_with_keyboard=callback.message.message_id)
            except:
                msg = await callback.message.answer(
                    "Выберите страну:",
                    reply_markup=countries_kb()
                )
                await state.update_data(last_msg_with_keyboard=msg.message_id)
        
    elif current_state == AddAdState.delivery_method:
        # возврат к выбору города
        await state.set_state(AddAdState.location_select)
        try:
            await callback.message.edit_text(
                LOCATION_MESSAGE,
                reply_markup=cities_kb()
            )
            await state.update_data(last_msg_with_keyboard=callback.message.message_id)
        except:
            msg = await callback.message.answer(
                LOCATION_MESSAGE,
                reply_markup=cities_kb()
            )
            await state.update_data(last_msg_with_keyboard=msg.message_id)
        
    elif current_state == AddAdState.cover_photo:
        # Возврат к предыдущему этапу (доставка или город)
        data = await state.get_data()
        ad_type = data.get('ad_type', 'Продажа')
        category = data.get('category')
        
        # Проверяем, является ли текущее сообщение сообщением с фото
        is_photo_message = callback.message.photo is not None
        
        if ad_type == 'Аренда' or category == 'slots':
            # Для аренды и категории "slots" возвращаемся к выбору города (доставка не нужна)
            await state.set_state(AddAdState.location_select)
            if is_photo_message:
                # Если сообщение с фото, удаляем его и отправляем новое текстовое сообщение
                try:
                    await bot.delete_message(chat_id=callback.message.chat.id, message_id=callback.message.message_id)
                except:
                    pass
                # Отправляем новое текстовое сообщение
                msg = await callback.message.answer(
                    LOCATION_MESSAGE,
                    reply_markup=cities_kb()
                )
                await state.update_data(last_msg_with_keyboard=msg.message_id)
            else:
                # Если сообщение текстовое, редактируем как обычно
                try:
                    await callback.message.edit_text(
                        LOCATION_MESSAGE,
                        reply_markup=cities_kb()
                    )
                    await state.update_data(last_msg_with_keyboard=callback.message.message_id)
                except:
                    msg = await callback.message.answer(
                        LOCATION_MESSAGE,
                        reply_markup=cities_kb()
                    )
                    await state.update_data(last_msg_with_keyboard=msg.message_id)
        else:
            # Для продажи (кроме "slots") возвращаемся к способу доставки
            await state.set_state(AddAdState.delivery_method)
            if is_photo_message:
                # Если сообщение с фото, удаляем его и отправляем новое текстовое сообщение
                try:
                    await bot.delete_message(chat_id=callback.message.chat.id, message_id=callback.message.message_id)
                except:
                    pass
                # Отправляем новое текстовое сообщение
                msg = await callback.message.answer(
                    DELIVERY_METHOD_MESSAGE,
                    reply_markup=delivery_method_kb()
                )
                await state.update_data(last_msg_with_keyboard=msg.message_id)
            else:
                # Если сообщение текстовое, редактируем как обычно
                try:
                    await callback.message.edit_text(
                        DELIVERY_METHOD_MESSAGE,
                        reply_markup=delivery_method_kb()
                    )
                    await state.update_data(last_msg_with_keyboard=callback.message.message_id)
                except:
                    msg = await callback.message.answer(
                        DELIVERY_METHOD_MESSAGE,
                        reply_markup=delivery_method_kb()
                    )
                    await state.update_data(last_msg_with_keyboard=msg.message_id)
        
        # Очищаем обложку при возврате назад
        await state.update_data(photos=[], cover_photo_file_id=None)
        
    elif current_state == AddAdState.photos:
        # Возврат к этапу обложки
        await state.set_state(AddAdState.cover_photo)
        
        # Получаем обложку из сохраненных фото
        data = await state.get_data()
        photos = data.get('photos', [])
        cover_photo_file_id = None
        
        if photos and len(photos) > 0:
            # Берем первое фото как обложку
            cover_photo_file_id = photos[0]['file_id']
            # Оставляем только обложку
            photos = [photos[0]]
            await state.update_data(photos=photos, cover_photo_file_id=cover_photo_file_id)
        
        # Сообщение для запроса обложки
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
        
    elif current_state == AddAdState.phone_input:
        # Возврат к выбору способа связи
        await state.set_state(AddAdState.contact_method)
        try:
            await callback.message.edit_text(
                CONTACT_METHOD_MESSAGE,
                reply_markup=contact_method_kb()
            )
            await state.update_data(last_msg_with_keyboard=callback.message.message_id)
        except:
            msg = await callback.message.answer(
                CONTACT_METHOD_MESSAGE,
                reply_markup=contact_method_kb()
            )
            await state.update_data(last_msg_with_keyboard=msg.message_id)
    
    elif current_state == AddAdState.contact_method:
        # Возврат к остальным фото
        await state.set_state(AddAdState.photos)
        data = await state.get_data()
        photos = data.get('photos', [])
        
        if not photos or len(photos) == 0:
            # Если нет фото, возвращаемся к обложке
            await state.set_state(AddAdState.cover_photo)
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
        else:
            # Показываем этап остальных фото
            total_photos = len(photos)
            category = data.get('category')
            # Проверяем, есть ли кнопка "Продолжить"
            has_continue_button = (category == "slots" and total_photos >= 1) or (category != "slots" and total_photos > 1)
            
            additional_photos_text = "📸 Отправьте остальные изображения объявления\n"
            additional_photos_text += f"(_Общее кол-во изображений {total_photos} / 8._)"
            # Показываем текст о минимуме только если нет кнопки "Продолжить"
            if not has_continue_button:
                additional_photos_text += "\n(_Для продолжения нужно минимум 1 изображение._)"
            
            try:
                await callback.message.edit_text(
                    text=additional_photos_text,
                    parse_mode='Markdown',
                    reply_markup=additional_photos_kb(total_photos, category)
                )
                await state.update_data(last_photo_msg_id=callback.message.message_id, last_msg_with_keyboard=callback.message.message_id)
            except:
                msg = await callback.message.answer(
                    additional_photos_text,
                    parse_mode='Markdown',
                    reply_markup=additional_photos_kb(total_photos, category)
                )
                await state.update_data(last_photo_msg_id=msg.message_id, last_msg_with_keyboard=msg.message_id)
    
    elif current_state == AddAdState.confirm:
        # возврат к выбору способа связи
        await state.set_state(AddAdState.contact_method)
        try:
            await callback.message.edit_text(
                CONTACT_METHOD_MESSAGE,
                reply_markup=contact_method_kb()
            )
            await state.update_data(last_msg_with_keyboard=callback.message.message_id)
        except:
            msg = await callback.message.answer(
                CONTACT_METHOD_MESSAGE,
                reply_markup=contact_method_kb()
            )
            await state.update_data(last_msg_with_keyboard=msg.message_id)
        
        # Удаляем сообщения с превью (фото/текст)
        try:
            # Удаляем несколько предыдущих сообщений (превью могло быть медиа-группой)
            for i in range(1, 10):  # Удаляем до 9 сообщений назад
                try:
                    await bot.delete_message(chat_id=callback.message.chat.id, message_id=callback.message.message_id - i)
                except:
                    pass
        except:
            pass
        
    else:
        # если не знаем куда возвращаться - просто отменяем
        await cancel_callback(callback, state)


async def cancel_callback(callback: types.CallbackQuery, state: FSMContext):
    """Отмена создания объявления"""
    await callback.answer()
    
    # Получаем данные из состояния перед очисткой
    data = await state.get_data()
    last_photo_msg_id = data.get('last_photo_msg_id')
    photo_request_msg_id = data.get('photo_request_msg_id')
    current_msg_id = callback.message.message_id
    
    # Сохраняем флаг, удалось ли отредактировать сообщение на главное меню
    edited_to_menu = False
    
    # Пытаемся отредактировать сообщение с просьбой отправить фото на главное меню
    if photo_request_msg_id:
        try:
            # Пытаемся изменить сообщение на возврат в главное меню
            from src.bot.handlers.start import get_main_menu_text
            from src.bot.keyboards.keyboards import main_menu_kb
            menu_text = await get_main_menu_text()
            await bot.edit_message_text(
                chat_id=callback.message.chat.id,
                message_id=photo_request_msg_id,
                text=menu_text,
                parse_mode='HTML',
                reply_markup=await main_menu_kb(callback.from_user.id if hasattr(callback, 'from_user') else None)
            )
            edited_to_menu = True
            # Удаляем Reply клавиатуру отдельным сообщением
            try:
                await bot.send_message(
                    chat_id=callback.message.chat.id,
                    text=" ",
                    reply_markup=ReplyKeyboardRemove()
                )
            except:
                pass
        except:
            pass
    elif last_photo_msg_id:
        # Если есть сообщение о количестве фото - тоже пытаемся отредактировать
        try:
            from src.bot.handlers.start import get_main_menu_text
            from src.bot.keyboards.keyboards import main_menu_kb
            menu_text = await get_main_menu_text()
            await bot.edit_message_text(
                chat_id=callback.message.chat.id,
                message_id=last_photo_msg_id,
                text=menu_text,
                parse_mode='HTML',
                disable_web_page_preview=True,
                reply_markup=await main_menu_kb(callback.from_user.id if hasattr(callback, 'from_user') else None)
            )
            edited_to_menu = True
            # Удаляем Reply клавиатуру отдельным сообщением
            try:
                await bot.send_message(
                    chat_id=callback.message.chat.id,
                    text=" ",
                    reply_markup=ReplyKeyboardRemove()
                )
            except:
                pass
        except:
            pass
    
    # Если не удалось отредактировать сообщение - отправляем новое главное меню
    main_menu_msg_id = None
    if not edited_to_menu:
        from src.bot.handlers.start import send_main_menu
        await send_main_menu(callback, state=state)
        # Получаем ID только что отправленного сообщения главного меню
        data_after = await state.get_data()
        main_menu_msg_id = data_after.get('main_menu_msg_id')
    
    # Очищаем состояние
    await state.clear()
    
    # Определяем ID сообщения, от которого будем удалять предыдущие сообщения
    # Если главное меню было отредактировано, используем его ID, иначе используем current_msg_id или main_menu_msg_id
    if edited_to_menu:
        base_msg_id = photo_request_msg_id if photo_request_msg_id else last_photo_msg_id
    else:
        base_msg_id = main_menu_msg_id if main_menu_msg_id else current_msg_id
    
    # Удаляем предыдущие 20 сообщений (используя универсальную функцию)
    from src.bot.handlers.catalog import delete_previous_messages
    await delete_previous_messages(callback.message.chat.id, base_msg_id, 20)
    
    # Удаляем текущее сообщение (если есть и это не главное меню)
    if not edited_to_menu and callback.message.message_id != main_menu_msg_id:
        try:
            await callback.message.delete()
        except:
            pass
    elif edited_to_menu:
        # Если главное меню было отредактировано, удаляем текущее сообщение только если это не главное меню
        if callback.message.message_id != photo_request_msg_id and callback.message.message_id != last_photo_msg_id:
            try:
                await callback.message.delete()
            except:
                pass


async def main_menu_from_moderation_callback(callback: types.CallbackQuery, state: FSMContext):
    """Возврат в главное меню после отправки на модерацию"""
    await callback.answer()
    
    # Сохраняем ID сообщения для последующего удаления
    current_msg_id = callback.message.message_id
    
    # Очищаем состояние
    await state.clear()
    
    # Сначала отправляем главное меню
    from src.bot.handlers.start import send_main_menu
    await send_main_menu(callback, state=state)
    
    # Потом удаляем сообщение "🕒 Объявление отправлено на модерацию..."
    try:
        await callback.message.delete()
    except:
        pass
    
    # Удаляем предыдущие сообщения (до 20 последних)
    try:
        for i in range(1, 21):
            try:
                msg_id_to_delete = current_msg_id - i
                if msg_id_to_delete > 0:
                    await bot.delete_message(chat_id=callback.message.chat.id, message_id=msg_id_to_delete)
            except:
                pass
    except:
        pass


# === РЕГИСТРАЦИЯ ОБРАБОТЧИКОВ ===

def register_add_ad_handlers(dp: Dispatcher):
    """Регистрация обработчиков создания объявления"""
    
    # Начало
    dp.callback_query.register(start_add_ad, F.data == "add_ad")
    
    # Обложка
    dp.message.register(cover_photo_handler, StateFilter(AddAdState.cover_photo), F.photo)
    dp.callback_query.register(cover_photo_confirm_callback, StateFilter(AddAdState.cover_photo), F.data == "cover_photo_confirm")
    dp.callback_query.register(cover_photo_retry_callback, StateFilter(AddAdState.cover_photo), F.data == "cover_photo_retry")
    
    # Остальные фото
    dp.message.register(photo_handler, StateFilter(AddAdState.photos), F.photo)
    dp.callback_query.register(photo_done_callback, StateFilter(AddAdState.photos), F.data == "photo_done")
    dp.callback_query.register(photo_delete_last_callback, StateFilter(AddAdState.photos), F.data == "photo_delete_last")
    
    # Способ связи
    dp.callback_query.register(contact_method_callback, StateFilter(AddAdState.contact_method), F.data.startswith("contact:"))
    dp.message.register(phone_input_handler, StateFilter(AddAdState.phone_input), F.text)
    
    # Название
    dp.message.register(title_handler, StateFilter(AddAdState.title), F.text)
    
    # Цена
    dp.message.register(price_handler, StateFilter(AddAdState.price), F.text)
    
    # Способ доставки
    dp.callback_query.register(delivery_method_callback, StateFilter(AddAdState.delivery_method), F.data.startswith("delivery:"))
    
    # Местоположение
    dp.callback_query.register(city_callback, StateFilter(AddAdState.location_select), F.data.startswith("city:"))
    dp.callback_query.register(country_callback, StateFilter(AddAdState.location_select), F.data.startswith("country:"))
    dp.callback_query.register(city_from_country_callback, StateFilter(AddAdState.location_city_after_country), F.data.startswith("city_from_country:"))
    dp.message.register(city_custom_handler, StateFilter(AddAdState.location_city_custom), F.text)
    dp.message.register(country_custom_handler, StateFilter(AddAdState.location_country_custom), F.text)
    dp.message.register(city_after_country_handler, StateFilter(AddAdState.location_city_after_country), F.text)
    
    # Категория и подкатегория
    dp.callback_query.register(category_callback, F.data.startswith("cat:"))
    dp.callback_query.register(bike_group_callback, F.data.startswith("bike_group:"))
    dp.callback_query.register(subcategory_callback, F.data.startswith("subcat:"))
    
    # Размер
    dp.callback_query.register(size_callback, StateFilter(AddAdState.size), F.data.startswith("size:"))
    dp.message.register(size_manual_handler, StateFilter(AddAdState.size), F.text)
    
    # Состояние
    dp.callback_query.register(condition_callback, F.data.startswith("cond:"))
    
    # Описание
    dp.message.register(description_handler, StateFilter(AddAdState.description), F.text)
    
    # Подтверждение
    dp.callback_query.register(confirm_send_callback, StateFilter(AddAdState.confirm), F.data == "confirm_send")
    
    # Возврат в главное меню после модерации
    dp.callback_query.register(main_menu_from_moderation_callback, F.data == "main_menu_from_moderation")
    
    # Кнопка "Назад" - только в состояниях создания объявления
    dp.callback_query.register(back_callback, StateFilter(AddAdState), F.data == "back")
    
    # Отмена
    dp.callback_query.register(cancel_callback, F.data == "cancel")
