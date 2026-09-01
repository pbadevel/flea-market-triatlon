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

async def reviews_callback(callback: types.CallbackQuery, state: FSMContext):
    """Показать отзывы о продавце"""
    await callback.answer()
    
    # деактивируем кнопки
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except:
        pass
    
    parts = callback.data.split(':')
    seller_id = int(parts[1])
    page = int(parts[2])
    
    # Получаем данные из состояния для последующего возврата
    data = await state.get_data()
    ad_id = data.get('last_viewed_ad_id')
    
    # Сохраняем информацию о том, что мы пришли из профиля продавца
    # Это нужно для правильного возврата при нажатии "Назад"
    await state.update_data(
        last_viewed_seller_id=seller_id, 
        last_viewed_ad_id=ad_id,
        came_from_profile=True  # Флаг, что пришли из профиля продавца
    )
    
    # для пагинации используем edit_text, кнопки обновляются автоматически
    await show_reviews_page(callback.message, seller_id, page, edit=True, state=state)


async def show_reviews_page(message: types.Message, seller_id: int, page: int, edit: bool = False, state: FSMContext = None):
    """Показать страницу отзывов"""
    total_reviews = await count_user_reviews(seller_id)
    
    # Проверяем, есть ли уже отзыв от текущего пользователя
    has_review = False
    if message.from_user:
        buyer = await get_user_by_tg_id(message.from_user.id)
        if buyer and buyer.id != seller_id:
            existing_review = await get_user_review_by_reviewer(seller_id, buyer.id)
            has_review = existing_review is not None
    
    if total_reviews == 0:
        text = "📭 Отзывов пока нет."
        from src.bot.keyboards.keyboards import InlineKeyboardBuilder, InlineKeyboardButton
        from src.bot.keyboards.key_text import BACK_BTN
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
    
    total_pages = ceil(total_reviews / REVIEWS_PER_PAGE)
    reviews = await get_user_reviews(seller_id, limit=REVIEWS_PER_PAGE, offset=page * REVIEWS_PER_PAGE)
    
    text = f"⭐ <b>Отзывы</b>\n"
    text += f"Страница {page + 1} из {total_pages}\n\n"
    
    for review in reviews:
        reviewer = await get_user_by_id(review.reviewer_user_id)
        reviewer_name = f"@{reviewer.username}" if reviewer and reviewer.username else "Пользователь"
        
        text += f"{'⭐' * review.rating} ({review.rating}/5)\n"
        text += f"От: {reviewer_name}\n"
        if review.comment:
            text += f"Комментарий: {review.comment}\n"
        text += f"Дата: {review.created_at.strftime('%d.%m.%Y')}\n\n"
    
    keyboard = reviews_pagination_kb(seller_id, page, total_pages, has_review=has_review)
    
    if edit:
        await message.edit_text(text, parse_mode='HTML', reply_markup=keyboard)
    else:
        await message.answer(text, parse_mode='HTML', reply_markup=keyboard)


async def leave_review_callback(callback: types.CallbackQuery, state: FSMContext):
    """Начать процесс оставления отзыва"""
    logger.info(f"🔵 leave_review_callback вызван! User: {callback.from_user.id}, Data: {callback.data}")
    
    # Проверяем наличие сообщения
    if not callback.message:
        logger.error("❌ callback.message is None!")
        await callback.answer("❌ Ошибка: сообщение не найдено.", show_alert=True)
        return
    
    await callback.answer()
    
    # Сохраняем chat_id перед удалением сообщения
    chat_id = callback.message.chat.id
    
    # Парсим seller_id ДО удаления сообщения
    try:
        seller_id = int(callback.data.split(':')[1])
        logger.info(f"🔵 seller_id распарсен: {seller_id}")
    except (ValueError, IndexError) as e:
        logger.error(f"Ошибка парсинга seller_id из callback_data: {callback.data}, ошибка: {e}")
        await callback.answer("❌ Ошибка: неверный формат данных.", show_alert=True)
        return
    
    # Получаем или создаем покупателя ДО удаления сообщения
    logger.info(f"🔵 Получаю покупателя по tg_user_id: {callback.from_user.id}")
    buyer = await get_user_by_tg_id(callback.from_user.id)
    if not buyer:
        logger.info(f"🔵 Покупатель не найден, создаю нового...")
        try:
            buyer = await create_or_update_user(callback.message, from_user=callback.from_user)
            logger.info(f"🔵 Покупатель создан: ID={buyer.id}")
        except Exception as e:
            logger.error(f"Ошибка создания пользователя при оставлении отзыва: {e}", exc_info=True)
            await callback.answer("❌ Ошибка: не удалось создать пользователя.", show_alert=True)
            return
    else:
        logger.info(f"🔵 Покупатель найден: ID={buyer.id}")
    
    # Проверяем, что пользователь не оставляет отзыв самому себе ДО удаления сообщения
    if buyer.id == seller_id:
        logger.info(f"🔵 Пользователь пытается оставить отзыв самому себе. Buyer ID: {buyer.id}, Seller ID: {seller_id}")
        # Вместо удаления сообщения, редактируем его, добавляя предупреждение
        try:
            # Получаем текущий текст сообщения
            current_text = callback.message.text or callback.message.caption or ""
            # Добавляем предупреждение в конец сообщения
            new_text = current_text + "\n\nВЫ НЕ МОЖЕТЕ ОСТАВИТЬ САМОМУ СЕБЕ"
            # Сохраняем текущую клавиатуру, чтобы оставить кнопки
            current_keyboard = callback.message.reply_markup
            # Редактируем сообщение, сохраняя кнопки
            await callback.message.edit_text(
                new_text,
                parse_mode='HTML',
                reply_markup=current_keyboard
            )
        except Exception as e:
            logger.warning(f"Не удалось отредактировать сообщение: {e}")
            # Если не удалось отредактировать, показываем alert
            await callback.answer("❌ Вы не можете оставить отзыв самому себе.", show_alert=True)
        return
    
    # Удаляем предыдущие сообщения (профиль продавца или отзывы) только если это НЕ свой профиль
    try:
        await callback.message.delete()
    except Exception as e:
        logger.warning(f"Не удалось удалить предыдущее сообщение: {e}")
    
    # Проверяем, есть ли уже отзыв (для редактирования)
    existing_review = await get_user_review_by_reviewer(seller_id, buyer.id)
    is_editing = existing_review is not None
    
    logger.info(f"🔵 Обновляю состояние: reviewing_seller_id={seller_id}, устанавливаю ReviewState.comment. Редактирование: {is_editing}")
    await state.update_data(reviewing_seller_id=seller_id, is_editing_review=is_editing)
    await state.set_state(ReviewState.comment)
    logger.info(f"🔵 Состояние обновлено успешно")
    
    try:
        # Формируем сообщение с учетом того, редактируем ли мы отзыв
        if is_editing:
            message_text = f"✏️ <b>Редактирование отзыва</b>\n\n"
            message_text += f"Текущий отзыв:\n"
            message_text += f"Оценка: {'⭐' * existing_review.rating} ({existing_review.rating}/5)\n"
            if existing_review.comment:
                message_text += f"Комментарий: {existing_review.comment}\n\n"
            message_text += REVIEW_COMMENT_MESSAGE
        else:
            message_text = REVIEW_COMMENT_MESSAGE
        
        logger.info(f"🔵 Отправляю сообщение с запросом комментария для отзыва. Seller ID: {seller_id}, Buyer ID: {buyer.id}, Редактирование: {is_editing}")
        # Используем bot.send_message вместо callback.message.answer, так как сообщение уже удалено
        msg = await bot.send_message(
            chat_id=chat_id,
            text=message_text,
            reply_markup=back_and_skip_kb(),
            parse_mode='HTML' if is_editing else None
        )
        # Сохраняем message_id для последующей деактивации кнопок
        await state.update_data(review_comment_msg_id=msg.message_id)
        logger.info(f"🔵 Сообщение отправлено успешно! Message ID: {msg.message_id}")
    except Exception as e:
        logger.error(f"❌ Ошибка при отправке сообщения с запросом комментария: {e}", exc_info=True)
        await callback.answer("❌ Произошла ошибка. Попробуйте позже.", show_alert=True)


async def review_comment_handler(message: types.Message, state: FSMContext):
    """Обработка комментария отзыва"""
    comment = message.text.strip()
    
    if len(comment) > 500:
        await message.answer("❌ Комментарий должен быть не более 500 символов.")
        return
    
    # Деактивируем кнопки в предыдущем сообщении
    data = await state.get_data()
    prev_msg_id = data.get('review_comment_msg_id')
    if prev_msg_id:
        try:
            await bot.edit_message_reply_markup(
                chat_id=message.chat.id,
                message_id=prev_msg_id,
                reply_markup=None
            )
        except Exception as e:
            logger.warning(f"Не удалось деактивировать кнопки в сообщении {prev_msg_id}: {e}")
    
    await state.update_data(review_comment=comment)
    await state.set_state(ReviewState.rating)
    
    seller_id = data.get('reviewing_seller_id')
    is_editing = data.get('is_editing_review', False)
    
    # Если редактируем, показываем текущую оценку
    rating_message = REVIEW_RATING_MESSAGE
    if is_editing:
        buyer = await get_user_by_tg_id(message.from_user.id)
        if buyer:
            existing_review = await get_user_review_by_reviewer(seller_id, buyer.id)
            if existing_review:
                rating_message = f"✏️ <b>Редактирование отзыва</b>\n\nТекущая оценка: {'⭐' * existing_review.rating} ({existing_review.rating}/5)\n\n{REVIEW_RATING_MESSAGE}"
    
    await message.answer(
        rating_message,
        reply_markup=review_rating_kb(seller_id),
        parse_mode='HTML' if is_editing else None
    )


async def review_back_callback(callback: types.CallbackQuery, state: FSMContext):
    """Вернуться назад из процесса оставления отзыва"""
    await callback.answer()
    
    # деактивируем кнопки
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except:
        pass
    
    # Очищаем состояние и возвращаемся к профилю продавца
    data = await state.get_data()
    seller_id = data.get('reviewing_seller_id')
    ad_id = data.get('last_viewed_ad_id')  # Для корректного отображения контакта
    
    await state.clear()
    
    if seller_id:
        await show_seller_profile(callback.message, seller_id, ad_id, from_user=callback.from_user, state=state)
    else:
        await callback.message.answer("❌ Ошибка: не найден ID продавца.")


async def review_skip_callback(callback: types.CallbackQuery, state: FSMContext):
    """Пропустить комментарий"""
    await callback.answer()
    
    # деактивируем кнопки в текущем сообщении
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except:
        pass
    
    await state.update_data(review_comment=None)
    await state.set_state(ReviewState.rating)
    
    data = await state.get_data()
    seller_id = data.get('reviewing_seller_id')
    is_editing = data.get('is_editing_review', False)
    
    # Если редактируем, показываем текущую оценку
    rating_message = REVIEW_RATING_MESSAGE
    if is_editing:
        buyer = await get_user_by_tg_id(callback.from_user.id)
        if buyer:
            existing_review = await get_user_review_by_reviewer(seller_id, buyer.id)
            if existing_review:
                rating_message = f"✏️ <b>Редактирование отзыва</b>\n\nТекущая оценка: {'⭐' * existing_review.rating} ({existing_review.rating}/5)\n\n{REVIEW_RATING_MESSAGE}"
    
    await callback.message.answer(
        rating_message,
        reply_markup=review_rating_kb(seller_id),
        parse_mode='HTML' if is_editing else None
    )


async def show_rate_seller_page(message: types.Message, seller_id: int, state: FSMContext = None):
    """Показать страницу оценки продавца (из deep link)"""
    seller = await get_user_by_id(seller_id)
    if not seller:
        await message.answer("❌ Продавец не найден.")
        return
    
    # Проверяем, не пытается ли пользователь оставить отзыв самому себе
    buyer = await get_user_by_tg_id(message.from_user.id)
    if buyer and buyer.id == seller_id:
        text = "❌ Вы не можете оставить отзыв самому себе."
        keyboard = InlineKeyboardBuilder()
        keyboard.row(InlineKeyboardButton(text=BACK_BTN, callback_data="back_from_rate"))
        msg = await message.answer(
            text,
            reply_markup=keyboard.as_markup()
        )
        if state:
            await state.update_data(rate_seller_msg_id=msg.message_id, came_from_deep_link=True)
        return
    
    # Сохраняем seller_id в state для обработки оценки
    if state:
        await state.update_data(reviewing_seller_id=seller_id, came_from_deep_link=True)
    
    # Проверяем, есть ли уже отзыв от текущего пользователя
    is_editing = False
    if buyer and buyer.id != seller_id:
        existing_review = await get_user_review_by_reviewer(seller_id, buyer.id)
        is_editing = existing_review is not None
    
    text = "⭐ <b>Оцените продавца</b>\n\n"
    text += "Выберите количество звезд или оставьте жалобу:"
    
    # Если редактируем, показываем текущую оценку
    if is_editing and buyer:
        existing_review = await get_user_review_by_reviewer(seller_id, buyer.id)
        if existing_review:
            text = f"✏️ <b>Редактирование отзыва</b>\n\n"
            text += f"Текущая оценка: {'⭐' * existing_review.rating} ({existing_review.rating}/5)\n\n"
            text += "Выберите количество звезд или оставьте жалобу:"
    
    keyboard = review_rating_kb(seller_id, include_complaint=True)
    
    msg = await message.answer(
        text,
        parse_mode='HTML',
        reply_markup=keyboard
    )
    
    # Сохраняем ID сообщения для последующего удаления при нажатии "Назад"
    if state:
        await state.update_data(rate_seller_msg_id=msg.message_id, came_from_deep_link=True)


async def review_rating_callback(callback: types.CallbackQuery, state: FSMContext):
    """Обработка оценки"""
    await callback.answer()
    
    parts = callback.data.split(':')
    seller_id = int(parts[1])
    rating = int(parts[2])
    
    data = await state.get_data()
    comment = data.get('review_comment')
    came_from_deep_link = data.get('came_from_deep_link', False)
    
    # Получаем покупателя
    buyer = await get_user_by_tg_id(callback.from_user.id)
    if not buyer:
        buyer = await create_or_update_user(callback.message, from_user=callback.from_user)
    
    # Проверяем, не пытается ли пользователь оставить отзыв самому себе
    if buyer.id == seller_id:
        error_text = "❌ Вы не можете оставить отзыв самому себе."
        keyboard = InlineKeyboardBuilder()
        keyboard.row(InlineKeyboardButton(text=BACK_BTN, callback_data="back_from_rate"))
        
        try:
            await callback.message.edit_text(
                error_text,
                reply_markup=keyboard.as_markup()
            )
            if state:
                await state.update_data(rate_seller_msg_id=callback.message.message_id, came_from_deep_link=True)
        except:
            msg = await callback.message.answer(
                error_text,
                reply_markup=keyboard.as_markup()
            )
            if state:
                await state.update_data(rate_seller_msg_id=msg.message_id, came_from_deep_link=True)
        return
    
    # Создаем или обновляем отзыв
    existing_review = await get_user_review_by_reviewer(seller_id, buyer.id)
    if existing_review:
        await create_review(seller_id, buyer.id, rating, comment)
        thanks_text = "✅ Отзыв обновлен! ⭐"
        logger.info(f"Пользователь {buyer.tg_user_id} обновил отзыв продавцу {seller_id}, оценка: {rating}")
    else:
        await create_review(seller_id, buyer.id, rating, comment)
        thanks_text = "Спасибо за оценку. Чтобы закрыть это сообщение, нажмите кнопку ниже."
        logger.info(f"Пользователь {buyer.tg_user_id} оставил отзыв продавцу {seller_id}, оценка: {rating}")
    
    # Заменяем сообщение на "Спасибо за оценку"
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text=BACK_BTN, callback_data="back_from_rate"))
    
    try:
        await callback.message.edit_text(
            thanks_text,
            reply_markup=keyboard.as_markup()
        )
        # Сохраняем ID сообщения для удаления при нажатии "Назад"
        if state:
            await state.update_data(rate_seller_msg_id=callback.message.message_id, came_from_deep_link=True)
    except:
        # Если не удалось отредактировать, отправляем новое
        msg = await callback.message.answer(
            thanks_text,
            reply_markup=keyboard.as_markup()
        )
        if state:
            await state.update_data(rate_seller_msg_id=msg.message_id, came_from_deep_link=True)
    
    # НЕ очищаем state, чтобы можно было удалить сообщение при нажатии "Назад"


async def complaint_callback(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'Пожаловаться'"""
    await callback.answer()
    
    seller_id = int(callback.data.split(':')[1])
    
    # Пока просто показываем сообщение (можно расширить функционал)
    text = "⚠️ <b>Пожаловаться на продавца</b>\n\n"
    text += "Если у вас есть жалоба на продавца, пожалуйста, напишите в поддержку."
    
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text=BACK_BTN, callback_data="back_from_rate"))
    
    try:
        await callback.message.edit_text(
            text,
            parse_mode='HTML',
            reply_markup=keyboard.as_markup()
        )
    except:
        msg = await callback.message.answer(
            text,
            parse_mode='HTML',
            reply_markup=keyboard.as_markup()
        )
        # Сохраняем ID сообщения для удаления при нажатии "Назад"
        if state:
            await state.update_data(rate_seller_msg_id=msg.message_id, came_from_deep_link=True)
            return
    
    # Сохраняем ID сообщения для удаления при нажатии "Назад"
    if state:
        await state.update_data(rate_seller_msg_id=callback.message.message_id, came_from_deep_link=True)


# === УНИВЕРСАЛЬНАЯ ФУНКЦИЯ УДАЛЕНИЯ СООБЩЕНИЙ ===

async def delete_previous_messages(chat_id: int, current_msg_id: int, count: int = 20):
    """Удаляет предыдущие сообщения (до 20)
    Если можно удалить только 4, а указано 20, то можно прерваться (чат чист)"""
    deleted_count = 0
    for i in range(1, count + 1):
        try:
            msg_id_to_delete = current_msg_id - i
            if msg_id_to_delete > 0:
                await bot.delete_message(chat_id=chat_id, message_id=msg_id_to_delete)
                deleted_count += 1
        except Exception:
            # Если сообщение не найдено или уже удалено, это нормально - продолжаем
            # Если ошибка другого типа, тоже продолжаем (не критично)
            pass
    return deleted_count


# === ПОИСК ===

async def search_back_to_menu_callback(callback: types.CallbackQuery, state: FSMContext):
    """Возврат в главное меню из результатов поиска"""
    await callback.answer()
    
    # Сохраняем ID текущего сообщения
    current_msg_id = callback.message.message_id
    
    # Проверяем, является ли текущее сообщение сообщением с результатами поиска или об отсутствии результатов
    is_search_result_msg = False
    if callback.message.text:
        # Проверяем ключевые слова, которые указывают на результаты поиска
        search_keywords = [
            "🔍",
            "Результаты поиска",
            "По вашему запросу ничего не найдено",
            "ничего не найдено"
        ]
        # Проверяем, содержит ли текст сообщения один из ключевых слов
        is_search_result_msg = any(keyword in callback.message.text for keyword in search_keywords)
    
    # Очищаем состояние
    await state.clear()
    
    # Если это сообщение с результатами поиска, редактируем его на главное меню
    if is_search_result_msg:
        from src.bot.handlers.start import get_main_menu_text
        from src.bot.keyboards.keyboards import main_menu_kb
        menu_text = await get_main_menu_text()
        
        try:
            await callback.message.edit_text(
                text=menu_text,
                parse_mode='HTML',
                reply_markup=await main_menu_kb(callback.from_user.id if hasattr(callback, 'from_user') else None)
            )
            # Сохраняем ID сообщения главного меню
            await state.update_data(main_menu_msg_id=current_msg_id)
            return
        except Exception as e:
            logger.error(f"Ошибка при редактировании сообщения результатов поиска на главное меню: {e}")
            # Если не удалось отредактировать, отправляем новое сообщение
            from src.bot.handlers.start import send_main_menu
            await send_main_menu(callback, state=state)
            # Удаляем предыдущие 20 сообщений
            await delete_previous_messages(callback.message.chat.id, current_msg_id, 20)
            # Удаляем старое сообщение
            try:
                await callback.message.delete()
            except:
                pass
            return
    
    # Если это не сообщение с результатами поиска, используем обычную логику
    from src.bot.handlers.start import send_main_menu
    await send_main_menu(callback, state=state)
    
    # Удаляем предыдущие 20 сообщений
    await delete_previous_messages(callback.message.chat.id, current_msg_id, 20)
    
    # Удаляем текущее сообщение
    try:
        await callback.message.delete()
    except:
        pass


