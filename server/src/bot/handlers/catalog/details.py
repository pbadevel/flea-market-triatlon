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

async def ad_details_callback(callback: types.CallbackQuery, state: FSMContext):
    """Показать детальную карточку товара (из списка каталога)."""
    await callback.answer()
    
    ad_id = int(callback.data.split(':')[1])
    # Открыли из каталога — «Назад» должен только закрыть карточку, не показывать профиль продавца
    await state.update_data(last_viewed_ad_id=ad_id, came_from_catalog=True)
    
    # Пытаемся редактировать предыдущее сообщение "Выберите действие:", если есть
    data = await state.get_data()
    prev_details_msg_id = data.get('ad_details_msg_id')
    first_photo_msg_id = data.get('first_photo_msg_id')
    photos_count = data.get('photos_count', 0)
    
    # Если есть предыдущее сообщение, пытаемся его заменить
    if prev_details_msg_id:
        try:
            # Удаляем старые фото, если они были
            if first_photo_msg_id and photos_count > 0:
                for i in range(photos_count):
                    try:
                        await bot.delete_message(chat_id=callback.message.chat.id, message_id=first_photo_msg_id + i)
                    except:
                        pass
            
            # Удаляем старое сообщение с кнопками
            try:
                await bot.delete_message(chat_id=callback.message.chat.id, message_id=prev_details_msg_id)
            except:
                pass
        except:
            pass
    
    await show_ad_details(callback.message, ad_id, state, from_user=callback.from_user)


async def ad_details_command(message: types.Message, state: FSMContext):
    """Показать карточку товара по команде"""
    try:
        ad_id = int(message.text.split('_')[1])
        # Сохраняем ad_id в состоянии для последующего возврата из профиля продавца
        await state.update_data(last_viewed_ad_id=ad_id, ad_details_msg_id=None)
        await show_ad_details(message, ad_id, state)
    except (IndexError, ValueError):
        await message.answer("❌ Неверный формат команды.")


async def show_ad_details(message: types.Message, ad_id: int, state: FSMContext = None, from_user=None):
    """Показать детальную информацию об объявлении.
    from_user: при вызове с callback.message передавать callback.from_user, иначе в лог «Подробнее» попадёт бот (message.from_user — автор сообщения с кнопкой, т.е. бот)."""
    # Если пришли из профиля продавца — НЕ удаляем профиль, а текущую карточку
    # (её фото/кнопки) сохраняем в nav_stack, чтобы при возврате восстановить.
    if state:
        data = await state.get_data()
        came_from_seller_profile = data.get('came_from_seller_profile', False)
        if came_from_seller_profile:
            nav_stack = list(data.get('nav_stack', []))
            entry = {
                'first_photo_msg_id': data.get('first_photo_msg_id'),
                'photos_count': data.get('photos_count', 0),
                'ad_details_msg_id': data.get('ad_details_msg_id'),
                'last_viewed_ad_id': data.get('last_viewed_ad_id'),
                'came_from_catalog': data.get('came_from_catalog', False),
                'came_from_channel': data.get('came_from_channel', False),
                'channel_message_id': data.get('channel_message_id'),
                'channel_username': data.get('channel_username'),
            }
            nav_stack.append(entry)
            await state.update_data(nav_stack=nav_stack)
        else:
            seller_profile_msg_id = data.get('seller_profile_msg_id')
            seller_profile_chat_id = data.get('seller_profile_chat_id') or (message.chat.id if message else None)
            if seller_profile_msg_id and seller_profile_chat_id:
                try:
                    await bot.delete_message(chat_id=seller_profile_chat_id, message_id=seller_profile_msg_id)
                except Exception:
                    pass
                await state.update_data(seller_profile_msg_id=None, seller_profile_chat_id=None)

    viewer = from_user if from_user is not None else getattr(message, "from_user", None)
    try:
        ad = await get_ad_by_id(ad_id)
        
        # Логируем для отладки
        logger.info(f"show_ad_details: ad_id={ad_id}, ad={ad}, status={ad.status if ad else 'None'}")
        
        # Разрешаем просмотр объявлений со статусом 'approved' и 'sold'
        if not ad:
            logger.warning(f"Объявление с id={ad_id} не найдено в базе данных")
            try:
                await message.answer("❌ Объявление не найдено или еще не опубликовано.")
            except Exception as e:
                logger.error(f"Ошибка при отправке сообщения об ошибке: {e}")
            return
        
        if ad.status not in ['approved', 'sold']:
            logger.warning(f"Объявление с id={ad_id} имеет статус '{ad.status}', а не 'approved' или 'sold'")
            try:
                await message.answer(f"❌ Объявление не найдено или еще не опубликовано. (Статус: {ad.status})")
            except Exception as e:
                logger.error(f"Ошибка при отправке сообщения об ошибке: {e}")
            return
    except Exception as e:
        logger.error(f"Ошибка в начале show_ad_details для ad_id={ad_id}: {e}", exc_info=True)
        try:
            await message.answer("❌ Произошла ошибка при загрузке объявления. Попробуйте позже.")
        except:
            pass
        return
    
    # логируем просмотр (файл + БД для статистики админки). viewer — кто смотрит; при callback.message это callback.from_user, иначе в лог попадёт бот
    if viewer:
        viewer_username = viewer.username or viewer.first_name
        log_ad_view(viewer.id, viewer_username, ad_id, ad.title)
        await log_details_view(viewer.id, viewer.username, ad_id, ad.seller_user_id)

    # Получаем фото
    photos = await get_ad_photos(ad_id)
    
    # Формируем текст в новом формате для детального просмотра
    # Форматируем цену с пробелами (77 000 вместо 77000)
    price_formatted = f"{ad.price:,}".replace(",", " ")
    
    ad_type_text = getattr(ad, 'ad_type', 'Продажа')
    condition_text = CONDITIONS.get(ad.condition, ad.condition)
    
    # Получаем информацию о продавце для статуса доверенного продавца
    from src.bot.database.methods import get_user_by_id
    seller = await get_user_by_id(ad.seller_user_id)
    is_trusted = seller.is_trusted_seller if seller else False

    # Пометка "ПРОДАНО" должна быть первой строкой
    sold_prefix = "💰 <b>ПРОДАНО</b>\n" if ad.status == 'sold' else ""

    # Название товара (жирным)
    text = f"{sold_prefix}<b>{ad.title}</b>\n"
    
    # Статус доверенного продавца — сразу под названием
    if is_trusted:
        text += "✅ Доверенный продавец\n"
    
    # Размер (если есть)
    if ad.size:
        text += f"Размер: {ad.size}\n\n"
    
    # Тип объявления и состояние
    if ad_type_text == "Аренда":
        text += f"♻️ Аренда\n"
    else:
        text += f"🛒 Продажа • {condition_text}\n"
    
    # Цена и город/страна
    def get_country_flag(country_name: str | None) -> str:
        """Получить флаг страны по названию (fallback: 🇷🇺)."""
        if not country_name:
            return "🇷🇺"
        country_lower = country_name.lower().strip()
        russia_variants = ['россия', 'российская федерация', 'рф', 'russia', 'russian federation']
        if country_lower in russia_variants:
            return "🇷🇺"
        from src.bot.settings.constants import CIS_COUNTRIES
        for _, data in CIS_COUNTRIES.items():
            if data['name'].lower() == country_lower:
                return data['flag']
        return "🇷🇺"

    country_name = (ad.country or "Россия").strip()
    country_flag = get_country_flag(country_name)
    location = f"{ad.city}, {country_flag} {country_name}"
    is_russia = country_name.lower() in ("россия", "российская федерация", "рф", "russia", "russian federation")
    if is_russia:
        text += f"💰 Цена: {price_formatted} ₽\n📍 {location}\n"
    else:
        text += f"💰 Цена: {price_formatted} ₽ 📍 {location}\n"
    
    # Доставка (если есть)
    if ad.delivery_method:
        # Преобразуем "Отправка" в "Доставка и самовывоз"
        if ad.delivery_method == "Отправка":
            delivery_display = "Доставка и самовывоз"
        elif ad.delivery_method == "Доставка / Самовывоз":
            delivery_display = "Доставка и самовывоз"
        else:
            delivery_display = ad.delivery_method
        text += f"🚚 {delivery_display}\n"
    
    # Описание (если есть) - с заголовком жирным
    if ad.description:
        text += f"\n<b>📝 Описание</b>\n{ad.description}\n"
    
    # Формируем ссылку на профиль продавца с ad_id для правильного отображения контакта
    from src.bot.settings.settings import BOT_USERNAME
    if BOT_USERNAME:
        profile_link = f"https://t.me/{BOT_USERNAME}?start=seller_{ad.seller_user_id}_{ad.id}"
    else:
        profile_link = f"seller_{ad.seller_user_id}_{ad.id}"
    
    text += f"\n📩 Связь: 👤 <a href=\"{profile_link}\">Контакты и профиль</a>\n"
    
    # ID объявления и дата создания
    if hasattr(ad, 'created_at') and ad.created_at:
        from datetime import datetime
        # Форматируем дату в формат DD.MM.YYYY
        if isinstance(ad.created_at, str):
            # Если это строка, пытаемся распарсить
            try:
                date_obj = datetime.fromisoformat(ad.created_at.replace('Z', '+00:00'))
                date_formatted = date_obj.strftime('%d.%m.%Y')
            except:
                date_formatted = ad.created_at[:10] if len(ad.created_at) >= 10 else ad.created_at
        else:
            # Если это datetime объект
            date_formatted = ad.created_at.strftime('%d.%m.%Y')
        text += f"\n№{ad.id} Создано: {date_formatted}"
    else:
        text += f"\n№{ad.id}"
    
    # Проверяем, есть ли уже отправленные сообщения для замены.
    # Если открываем из профиля продавца — предыдущее объявление остаётся в чате, не трогаем его.
    prev_details_msg_id = None
    prev_first_photo_msg_id = None
    prev_photos_count = 0
    if state:
        data = await state.get_data()
        came_from_seller_profile_now = data.get('came_from_seller_profile', False)
        if not came_from_seller_profile_now:
            prev_details_msg_id = data.get('ad_details_msg_id')
            prev_first_photo_msg_id = data.get('first_photo_msg_id')
            prev_photos_count = data.get('photos_count', 0)
    
    # Удаляем старые фото, если они были (медиа-группу нельзя редактировать)
    if prev_first_photo_msg_id and prev_photos_count > 0:
        for i in range(prev_photos_count):
            try:
                await bot.delete_message(chat_id=message.chat.id, message_id=prev_first_photo_msg_id + i)
            except:
                pass
    
    # Отправляем фото альбомом
    if photos:
        try:
            media_group = []
            for i, photo in enumerate(photos):
                if i == 0:
                    media_group.append(types.InputMediaPhoto(media=photo.file_id, caption=text, parse_mode='HTML'))
                else:
                    media_group.append(types.InputMediaPhoto(media=photo.file_id))
            
            sent_messages = await message.answer_media_group(media_group)
            # Сохраняем ID первого сообщения с фото для последующего удаления
            first_photo_msg_id = sent_messages[0].message_id if sent_messages else None
        except Exception as e:
            logger.error(f"Ошибка при отправке медиа-группы для ad_id={ad_id}: {e}", exc_info=True)
            # Если не удалось отправить медиа-группу, отправляем текст без фото
            try:
                await message.answer(text, parse_mode='HTML')
                first_photo_msg_id = None
            except Exception as e2:
                logger.error(f"Ошибка при отправке текста объявления: {e2}", exc_info=True)
                await message.answer("❌ Произошла ошибка при загрузке объявления. Попробуйте позже.")
                return
        
        # Пытаемся редактировать сообщение "Выберите действие:", если оно есть
        if prev_details_msg_id:
            try:
                await bot.edit_message_reply_markup(
                    chat_id=message.chat.id,
                    message_id=prev_details_msg_id,
                    reply_markup=ad_details_kb(ad_id, ad.seller_user_id, first_photo_msg_id or 0, len(photos))
                )
                if state:
                    await state.update_data(
                        ad_details_msg_id=prev_details_msg_id,
                        first_photo_msg_id=first_photo_msg_id,
                        photos_count=len(photos)
                    )
            except:
                msg = await message.answer(
                    "Вернуться в предыдущее меню.",
                    parse_mode='HTML',
                    reply_markup=ad_details_kb(ad_id, ad.seller_user_id, first_photo_msg_id or 0, len(photos))
                )
                # Удаляем старое сообщение, если оно есть
                if prev_details_msg_id:
                    try:
                        await bot.delete_message(chat_id=message.chat.id, message_id=prev_details_msg_id)
                    except:
                        pass
                # Сохраняем ID нового сообщения
                if state:
                    await state.update_data(
                        ad_details_msg_id=msg.message_id,
                        first_photo_msg_id=first_photo_msg_id,
                        photos_count=len(photos)
                    )
        else:
            # Отправляем кнопки отдельным сообщением (всегда, даже если state=None)
            # ВАЖНО: отправляем с текстом, чтобы кнопки точно отобразились
            msg = await message.answer(
                "Вернуться в предыдущее меню.",
                parse_mode='HTML',
                reply_markup=ad_details_kb(ad_id, ad.seller_user_id, first_photo_msg_id or 0, len(photos))
            )
            if state:
                await state.update_data(
                    ad_details_msg_id=msg.message_id,
                    first_photo_msg_id=first_photo_msg_id,
                    photos_count=len(photos)
                )
    else:
        # Если фото нет, пытаемся редактировать сообщение, если оно есть
        if prev_details_msg_id:
            try:
                await bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=prev_details_msg_id,
                    text=text,
                    parse_mode='HTML',
                    reply_markup=ad_details_kb(ad_id, ad.seller_user_id, 0, 0)
                )
                # Сохраняем тот же ID сообщения
                if state:
                    await state.update_data(
                        ad_details_msg_id=prev_details_msg_id,
                        first_photo_msg_id=None,
                        photos_count=0
                    )
            except:
                # Если не удалось отредактировать, отправляем новое
                msg = await message.answer(
                    text,
                    parse_mode='HTML',
                    reply_markup=ad_details_kb(ad_id, ad.seller_user_id, 0, 0)
                )
                if prev_details_msg_id:
                    try:
                        await bot.delete_message(chat_id=message.chat.id, message_id=prev_details_msg_id)
                    except:
                        pass
                # Сохраняем ID нового сообщения
                if state:
                    await state.update_data(
                        ad_details_msg_id=msg.message_id,
                        first_photo_msg_id=None,
                        photos_count=0
                    )
        else:
            # Если фото нет, отправляем текст с кнопками (всегда, даже если state=None)
            msg = await message.answer(
                text,
                parse_mode='HTML',
                reply_markup=ad_details_kb(ad_id, ad.seller_user_id, 0, 0)
            )
            if state:
                await state.update_data(
                    ad_details_msg_id=msg.message_id,
                    first_photo_msg_id=None,
                    photos_count=0
                )


async def unpublished_ad_callback(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик кнопки "Подробнее" под объявлением, снятым с публикации (в канале)"""
    await callback.answer("📴 Объявление снято с публикации.", show_alert=True)


async def sold_ad_callback(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик кнопки "Подробнее" под проданным объявлением (в канале)"""
    await callback.answer("💰 Объявление продано.", show_alert=True)


async def contact_seller_callback(callback: types.CallbackQuery, state: FSMContext):
    """Связаться с продавцом"""
    await callback.answer()
    
    # Парсим callback_data: contact_seller:ad_id:seller_id
    parts = callback.data.split(':')
    if len(parts) < 3:
        await callback.answer("❌ Ошибка: неверный формат данных.", show_alert=True)
        return
    
    try:
        ad_id = int(parts[1])
        seller_id = int(parts[2])
    except (ValueError, IndexError):
        await callback.answer("❌ Ошибка: неверный формат данных.", show_alert=True)
        return
    
    # Сохраняем ad_id в состоянии для возврата
    await state.update_data(last_viewed_ad_id=ad_id)
    
    # НЕ удаляем сообщение "Выберите действие:", а просто деактивируем кнопки
    # Это позволит вернуться назад без переотправки объявления
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except:
        pass
    
    # логируем в БД (используем callback.from_user, иначе create_or_update_user получит бота из callback.message)
    buyer = await get_user_by_tg_id(callback.from_user.id)
    if not buyer:
        buyer = await create_or_update_user(callback.message, from_user=callback.from_user)
    await log_contact_request(buyer.id, seller_id, ad_id)
    
    # получаем инфо
    seller = await get_user_by_id(seller_id)
    ad = await get_ad_by_id(ad_id)
    
    if not seller or not ad:
        await callback.answer("❌ ошибка получения информации", show_alert=True)
        return
    
    # Создаем клавиатуру с кнопкой "Назад"
    from src.bot.keyboards.keyboards import InlineKeyboardBuilder, InlineKeyboardButton
    from src.bot.keyboards.key_text import BACK_BTN
    keyboard = InlineKeyboardBuilder()
    
    # формируем контакт
    logger.debug(f"Показ контакта для объявления #{ad_id}: ad.contact_method = {ad.contact_method}")
    contact_method = ad.contact_method or ''
    
    # Определяем тип контакта по значению contact_method
    if contact_method.replace('+', '').replace(' ', '').isdigit():
        phone_display = format_phone_for_display(contact_method)
        contact_text = f"📞 <b>Контакт продавца:</b>\n\n"
        contact_text += f"Телефон: {phone_display}\n"
        contact_text += f"Товар: {ad.title}"
    elif contact_method.startswith('@'):
        # Это Telegram username
        contact_text = f"💬 <b>Контакт продавца:</b>\n\n"
        contact_text += f"Telegram: {contact_method}\n"
        contact_text += f"Товар: {ad.title}"
    elif contact_method.startswith('tg://'):
        # Это ссылка на Telegram профиль
        contact_text = f"💬 <b>Контакт продавца:</b>\n\n"
        contact_text += f"<a href=\"{contact_method}\">Профиль продавца</a>\n"
        contact_text += f"Товар: {ad.title}"
    elif contact_method == 'phone' and seller.phone:
        phone_display = format_phone_for_display(seller.phone)
        contact_text = f"📞 <b>Контакт продавца:</b>\n\n"
        contact_text += f"Телефон: {phone_display}\n"
        contact_text += f"Товар: {ad.title}"
    else:
        # Обратная совместимость: старый формат с telegram или по умолчанию
        if seller.username:
            contact_text = f"💬 <b>Контакт продавца:</b>\n\n"
            contact_text += f"Telegram: @{seller.username}\n"
            contact_text += f"Товар: {ad.title}"
        else:
            # Создаем ссылку на профиль через tg://user?id=
            profile_link = f"tg://user?id={seller.tg_user_id}"
            contact_text = f"💬 <b>Контакт продавца:</b>\n\n"
            contact_text += f"<a href=\"{profile_link}\">Профиль продавца</a>\n"
            contact_text += f"Товар: {ad.title}"
    
    keyboard.row(InlineKeyboardButton(text=BACK_BTN, callback_data="back"))
    await callback.message.answer(contact_text, parse_mode='HTML', reply_markup=keyboard.as_markup())
    
    # логируем запрос контакта
    buyer_username = callback.from_user.username or callback.from_user.first_name
    seller_username = seller.username or seller.first_name
    log_contact_request(
        callback.from_user.id, buyer_username,
        seller.tg_user_id, seller_username,
        ad_id, ad.title
    )


async def noop_callback(callback: types.CallbackQuery):
    """Пустой обработчик для кнопки с номером страницы"""
    await callback.answer()


async def close_ad_details_callback(callback: types.CallbackQuery, state: FSMContext):
    """Закрыть детали объявления — удалить фото + сообщение «Вернуться в предыдущее меню.».
    ID фото и их количество закодированы в callback_data: close_ad:{first_photo_msg_id}:{photos_count},
    поэтому удаление работает даже если state потерялся (рестарт бота и т.п.)."""
    await callback.answer()

    # Парсим фото из callback_data (первоисточник, надёжнее state)
    parts = callback.data.split(':')
    cb_photo_id = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
    cb_photo_cnt = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 0

    data = await state.get_data()
    first_photo_msg_id = cb_photo_id or data.get('first_photo_msg_id') or 0
    photos_count = cb_photo_cnt or data.get('photos_count', 0)
    seller_id = data.get('last_viewed_seller_id')
    ad_id = data.get('last_viewed_ad_id')
    came_from_seller_profile = data.get('came_from_seller_profile', False)
    came_from_catalog = data.get('came_from_catalog', False)
    came_from_channel = data.get('came_from_channel', False)

    # Удаляем фото объявления
    if first_photo_msg_id and photos_count > 0:
        for i in range(photos_count):
            try:
                await bot.delete_message(
                    chat_id=callback.message.chat.id,
                    message_id=first_photo_msg_id + i,
                )
            except Exception:
                pass

    # Удаляем текущее сообщение с кнопкой
    try:
        await callback.message.delete()
    except Exception:
        pass

    # Восстанавливаем предыдущий уровень из nav_stack (если есть)
    nav_stack = list(data.get('nav_stack', []))

    if came_from_seller_profile:
        # Открыли объявление из профиля продавца — «Назад» удаляет только это звено.
        # Восстанавливаем данные предыдущей карточки из стека.
        if nav_stack:
            prev = nav_stack.pop()
            await state.update_data(
                nav_stack=nav_stack,
                ad_details_msg_id=prev.get('ad_details_msg_id'),
                first_photo_msg_id=prev.get('first_photo_msg_id'),
                photos_count=prev.get('photos_count', 0),
                last_viewed_ad_id=prev.get('last_viewed_ad_id'),
                came_from_catalog=prev.get('came_from_catalog', False),
                came_from_channel=prev.get('came_from_channel', False),
                channel_message_id=prev.get('channel_message_id'),
                channel_username=prev.get('channel_username'),
                came_from_seller_profile=False,
            )
        else:
            await state.update_data(
                ad_details_msg_id=None,
                first_photo_msg_id=None,
                photos_count=0,
                came_from_seller_profile=False,
            )
    elif came_from_catalog:
        # Открыли из каталога — «Назад» удаляет только сообщения объявления;
        # карточки каталога остаются в чате.
        await state.update_data(
            ad_details_msg_id=None,
            first_photo_msg_id=None,
            photos_count=0,
            came_from_catalog=False,
        )
    elif seller_id and (data.get('came_from_profile', False) or data.get('came_from_seller_ads', False)):
        await state.update_data(came_from_profile=False, came_from_seller_ads=False)
        from src.bot.handlers.catalog.seller import show_seller_profile
        await show_seller_profile(
            callback.message, seller_id, ad_id, from_user=callback.from_user, state=state
        )
    elif came_from_channel:
        # Открыли из канала — единственный случай, когда по «Назад» показываем главное меню.
        await state.clear()
        from src.bot.handlers.start import send_main_menu
        await send_main_menu(callback, state=state)
    else:
        # Всё остальное (поиск, /details_, deep link) — просто удаляем объявление.
        await state.update_data(
            ad_details_msg_id=None,
            first_photo_msg_id=None,
            photos_count=0,
        )


async def main_menu_callback(callback: types.CallbackQuery, state: FSMContext):
    """Вернуться в главное меню"""
    await callback.answer()
    
