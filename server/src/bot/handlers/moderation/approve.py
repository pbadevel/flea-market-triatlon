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



from src.bot.utils.helpers import get_fsinput_photo, format_file_id_to_storage_path



# === ОДОБРЕНИЕ ===

# === ОДОБРЕНИЕ ===

async def moderation_comment_callback(callback: types.CallbackQuery, state: FSMContext):
    """Начать ввод комментария для модерации"""
    await callback.answer()
    
    # Проверяем права модератора
    user_id = callback.from_user.id
    is_mod = await is_moderator(user_id)
    
    if not is_mod:
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
    
    # Сохраняем ID объявления в состоянии
    await state.update_data(moderating_ad_id=ad_id)
    await state.set_state(ModerationState.comment)
    
    await callback.message.answer(
        "💬 Введите комментарий для модерации (будет добавлен к одобрению или отклонению):"
    )


async def moderation_comment_handler(message: types.Message, state: FSMContext):
    """Обработка ввода комментария модерации"""
    data = await state.get_data()
    ad_id = data.get('moderating_ad_id')
    
    if not ad_id:
        await message.answer("❌ Ошибка: объявление не найдено.")
        await state.clear()
        return
    
    comment = message.text.strip()
    
    if not comment:
        await message.answer("❌ Комментарий не может быть пустым.")
        return
    
    # Сохраняем комментарий
    await state.update_data(moderation_comment=comment)
    
    # Показываем кнопки одобрения/отклонения с комментарием
    keyboard = InlineKeyboardBuilder()
    keyboard.row(
        InlineKeyboardButton(text=APPROVE_BTN, callback_data=f"mod_approve_with_comment:{ad_id}"),
        InlineKeyboardButton(text=REJECT_BTN, callback_data=f"mod_reject_with_comment:{ad_id}")
    )
    
    await message.answer(
        f"💬 Комментарий сохранен: {comment}\n\nВыберите действие:",
        reply_markup=keyboard.as_markup()
    )


async def approve_ad_callback(callback: types.CallbackQuery, state: FSMContext):
    """Одобрить объявление"""
    logger.info(f"🔵 CALLBACK APPROVE ПОЛУЧЕН! User: {callback.from_user.id}, Data: {callback.data}")
    
    await callback.answer()
    
    # деактивируем кнопки сразу
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except:
        pass
    
    # Проверяем права модератора
    from src.bot.settings.settings import ADMIN_IDS
    user_id = callback.from_user.id
    logger.info(f"🔵 Проверка прав для user {user_id}")
    logger.info(f"🔵 ADMIN_IDS: {ADMIN_IDS}, user в списке: {user_id in ADMIN_IDS}")
    
    is_mod = await is_moderator(user_id)
    logger.info(f"🔵 Результат is_moderator({user_id}): {is_mod}")
    
    if not is_mod:
        logger.warning(f"🔴 User {user_id} не является модератором! ADMIN_IDS={ADMIN_IDS}, user в списке={user_id in ADMIN_IDS}")
        await callback.answer("❌ У вас нет прав модератора.", show_alert=True)
        return
    
    ad_id = int(callback.data.split(':')[1])
    comment = None
    
    # Получаем объявление
    ad = await get_ad_by_id(ad_id)
    if not ad:
        await callback.answer("❌ Объявление не найдено.", show_alert=True)
        return
    
    if ad.status != 'pending':
        await callback.answer("❌ Объявление уже обработано.", show_alert=True)
        return
    
    # Получаем фото
    photos = await get_ad_photos(ad_id)
    logger.debug(f"получено {len(photos)} фото для объявления #{ad_id}")
    
    if not photos:
        logger.error(f"объявление #{ad_id} не имеет фото, не могу опубликовать")
        await callback.answer("❌ Объявление не имеет фото.", show_alert=True)
        return
    
    # Проверяем, что объявление с российским городом (публикуем только российские города)
    def is_russian_city(city: str, country: str = None) -> bool:
        """Проверяет, является ли город российским"""
        from src.bot.settings.constants import DEFAULT_CITIES, CIS_COUNTRIES
        
        # Если страна указана и это не Россия, то город не российский
        if country:
            country_lower = country.lower().strip()
            russia_variants = ['россия', 'российская федерация', 'рф', 'russia', 'russian federation']
            if country_lower not in russia_variants:
                # Проверяем, не является ли это страной из CIS_COUNTRIES
                for key, data in CIS_COUNTRIES.items():
                    if data['name'].lower() == country_lower:
                        return False  # Это не российский город
                # Если страна не распознана, считаем что это не Россия
                return False
        
        # Проверяем, является ли город российским (из списка DEFAULT_CITIES)
        if not city:
            return False
        
        city_lower = city.lower().strip()
        # Проверяем список российских городов
        for city_name in DEFAULT_CITIES.values():
            if city_name.lower() == city_lower:
                return True
        
        # Если город не в списке, но страна не указана или Россия - считаем российским
        # (пользователь мог ввести свой город)
        if not country:
            return True
        
        country_lower = country.lower().strip()
        russia_variants = ['россия', 'российская федерация', 'рф', 'russia', 'russian federation']
        if country_lower in russia_variants:
            return True
        
        return False
    
    # Проверяем город перед публикацией
    is_russian = is_russian_city(ad.city, ad.country)
    if not is_russian:
        logger.warning(f"объявление #{ad_id} не может быть опубликовано: город '{ad.city}' не является российским (страна: '{ad.country}')")
        
        # Одобряем объявление, но не публикуем в канал
        await approve_ad(ad_id, channel_message_id=None)
        logger.info(f"объявление #{ad_id} одобрено, но не опубликовано в канал (не российский город)")
        
        # Обновляем сообщение модератору
        country_display = ad.country if ad.country else "Не указана"
        confirm_text = f"Объявление #{ad_id} одобрено, но не опубликовано в канал. (Страна: {country_display})"
        try:
            if callback.message.photo:
                await callback.message.edit_caption(caption=confirm_text, reply_markup=None)
            else:
                await callback.message.edit_text(confirm_text, reply_markup=None)
        except Exception as e:
            logger.error(f"не удалось обновить сообщение модератору: {e}")
            await callback.message.answer(confirm_text)
        
        # Уведомляем продавца (без ссылки на канал)
        seller = await get_user_by_id(ad.seller_user_id)
        if seller:
            try:
                title = ad.title
                if len(title) > 10:
                    title_formatted = f"<i>{title[:10]}</i>{title[10:]}"
                else:
                    title_formatted = f"<i>{title}</i>"
                
                notification_text = f"✅ Готово! 📍Ваше📍Объявление с названием \"{title_formatted}\" одобрено.\n\n"
                notification_text += "‼️Отредактировать объявление можно в разделе «Мои объявления»\n"
                notification_text += "Цену можно поменять без модерации!!!"
                
                keyboard = InlineKeyboardBuilder()
                keyboard.row(InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu"))
                
                await bot.send_message(
                    chat_id=seller.tg_user_id,
                    text=notification_text,
                    parse_mode='HTML',
                    reply_markup=keyboard.as_markup()
                )
            except Exception as e:
                logger.error(f"ошибка уведомления продавца: {e}")
        
        # логируем
        mod_username = callback.from_user.username or callback.from_user.first_name
        log_moderation(callback.from_user.id, mod_username, ad_id, "одобрил (не опубликовано - не российский город)")
        
        return
    
    # Публикуем в канал
    # Определяем флаг страны
    def get_country_flag(country_name):
        """Получить флаг страны по названию"""
        if not country_name:
            return "🇷🇺"  # По умолчанию Россия
        
        country_lower = country_name.lower().strip()
        
        # Варианты названий России
        russia_variants = ['россия', 'российская федерация', 'рф', 'russia', 'russian federation']
        if country_lower in russia_variants:
            return "🇷🇺"
        
        # Проверяем страны из CIS_COUNTRIES
        from src.bot.settings.constants import CIS_COUNTRIES
        for key, data in CIS_COUNTRIES.items():
            if data['name'].lower() == country_lower:
                return data['flag']
        
        return "🇷🇺"  # По умолчанию
    
    country_flag = get_country_flag(ad.country)
    
    # Формируем caption для канала (новый формат)
    seller = await get_user_by_id(ad.seller_user_id)
    is_trusted = seller.is_trusted_seller if seller else False

    from src.bot.utils.channel_utils import format_active_caption
    caption = format_active_caption(ad, is_trusted)
    
    logger.info(f"публикую объявление #{ad_id} в канал {CHANNEL_ID} (тип: {type(CHANNEL_ID)}, @{CHANNEL_USERNAME}) с {len(photos)} фото")
    channel_msg = None
    
    try:
        # Используем обработанную обложку (обрезанную с логотипом) из cover_file_id
        # Если её нет, накладываем логотип на лету для старых объявлений
        if ad.cover_file_id:
            logger.debug(f"использую обработанную обложку для публикации (обрезана и с логотипом)")
            first_photo_file_id = ad.cover_file_id
        else:
            # Для старых объявлений без cover_file_id накладываем логотип на лету
            logger.debug(f"cover_file_id отсутствует, накладываю логотип на первое фото на лету")
            try:
                from src.bot.utils.image_utils import add_logo_watermark_to_photo
                # Определяем тип объявления для выбора логотипа
                ad_type_text = getattr(ad, 'ad_type', 'Продажа')
                if ad_type_text == 'Аренда':
                    logo_path = "assets/logo_rent.png"
                else:
                    logo_path = "assets/logo_sale.png"
                # Накладываем логотип на первое фото
                first_photo_file_id = await add_logo_watermark_to_photo(
                    file_id=photos[0].file_id,
                    chat_id=MODERATION_CHAT_ID,  # Используем чат модерации как временный
                    bot=bot,
                    logo_path=logo_path
                )
                logger.debug(f"логотип наложен на лету, новый file_id: {first_photo_file_id}")
            except Exception as e:
                logger.error(f"ошибка при наложении логотипа на лету: {e}, использую первое фото без логотипа")
                # В случае ошибки используем первое фото без логотипа
                first_photo_file_id = photos[0].file_id
        
        # Логотип «Доверенный продавец» уже на обложке: он накладывается при подтверждении обложки
        # пользователем (add_ad) и сохраняется в ad.cover_file_id. Здесь используем обложку как есть.
        
        # Используем username канала вместо ID для большей надежности
        channel_target = f"@{CHANNEL_USERNAME}" if CHANNEL_USERNAME else CHANNEL_ID
        logger.info(f"отправляю в канал: {channel_target}")
        
        # Проверяем, есть ли уже сообщение в канале (редактирование или повторная публикация)
        if ad.channel_message_id:
            # Редактируем существующее сообщение в канале (фото + caption + кнопки)
            logger.info(f"это редактирование/повторная публикация, редактирую сообщение #{ad.channel_message_id} в канале")
            old_message_id = ad.channel_message_id
            try:
                # Редактируем фото и caption
                media = InputMediaPhoto(media=first_photo_file_id, caption=caption, parse_mode="HTML")
                await bot.edit_message_media(
                    chat_id=channel_target,
                    message_id=old_message_id,
                    media=media,
                )
                # Редактируем кнопки
                await bot.edit_message_reply_markup(
                    chat_id=channel_target,
                    message_id=old_message_id,
                    reply_markup=ad_in_channel_kb(ad_id, BOT_USERNAME),
                )
                logger.info(f"сообщение #{old_message_id} отредактировано в канале")
                # Используем старый message_id (сообщение не менялось)
                channel_msg_id = old_message_id
            except Exception as edit_e:
                # Если редактирование не удалось — удаляем и отправляем новое (fallback)
                logger.warning(f"не удалось отредактировать сообщение #{old_message_id}: {edit_e}, удаляю и отправляю новое")
                try:
                    await bot.delete_message(chat_id=channel_target, message_id=old_message_id)
                except Exception as del_e:
                    logger.warning(f"не удалось удалить сообщение #{old_message_id}: {del_e}")

                # if photos[0].storage_path:
                #     channel_msg = await bot.send_photo(
                #         chat_id=channel_target,
                #         photo=first_photo_file_id,
                #         caption=caption,
                #         parse_mode='HTML',
                #         reply_markup=ad_in_channel_kb(ad_id, BOT_USERNAME)
                #     )
                # else:
                try:
                    channel_msg = await bot.send_photo(
                        chat_id=channel_target,
                        photo=first_photo_file_id,
                        caption=caption,
                        parse_mode='HTML',
                        reply_markup=ad_in_channel_kb(ad_id, BOT_USERNAME)
                    )
                    channel_msg_id = channel_msg.message_id
                    logger.info(f"новое сообщение отправлено, message_id: {channel_msg_id}")
                except:
                    pass
                    # CHANGE!!!
        else:
            # Отправляем только обложку (первое фото) с текстом и кнопками
            # Остальные фото не публикуем в канале
            logger.info(f"отправляю обложку (первое фото) с кнопками в {channel_target}")
            try:
                channel_msg = await bot.send_photo(
                    chat_id=channel_target,
                    photo=first_photo_file_id,
                    caption=caption,
                    parse_mode='HTML',
                    reply_markup=ad_in_channel_kb(ad_id, BOT_USERNAME)
                )
            except:
                pass
                # CHANGE!!! 
            # logger.info(f"обложка отправлена с кнопками, message_id: {channel_msg.message_id}")
            # channel_msg_id = channel_msg.message_id
        
        channel_msg_id = 0
        # CHANGE!!!
        
        # одобряем объявление
        logger.debug(f"одобряю объявление #{ad_id} с channel_message_id={channel_msg_id}")
        await approve_ad(ad_id, channel_msg_id)
        logger.info(f"объявление #{ad_id} успешно одобрено и опубликовано")

        # Устанавливаем next_boost_at только если ещё не задан (первичная публикация).
        # При повторном одобрении (после снятия с публикации) сохраняем уже имеющийся
        # next_boost_at — таймер продолжает отсчёт, пока объявление было неактивно.
        try:
            from src.bot.database.methods import get_boost_settings, update_ad, get_ad_by_id as _get_ad
            from datetime import timedelta, datetime as _dt
            from src.bot.settings.settings import TEST_MODE as _ENV_TEST_MODE
            current_ad = await _get_ad(ad_id)
            if current_ad and current_ad.next_boost_at is None:
                boost_settings = await get_boost_settings()
                is_trusted_seller = seller.is_trusted_seller if seller else False
                if _ENV_TEST_MODE:
                    from src.bot.services.scheduler import _TEST_REGULAR_INTERVAL, _TEST_TRUSTED_INTERVAL
                    delta = _TEST_TRUSTED_INTERVAL if is_trusted_seller else _TEST_REGULAR_INTERVAL
                else:
                    interval_days = (
                        boost_settings.trusted_boost_interval_days
                        if is_trusted_seller
                        else boost_settings.regular_boost_interval_days
                    )
                    delta = timedelta(days=interval_days)
                await update_ad(ad_id, next_boost_at=_dt.utcnow() + delta)
        except Exception as boost_e:
            logger.warning(f"Не удалось установить next_boost_at для #{ad_id}: {boost_e}")
        
        # обновляем сообщение модератору
        confirm_text = f"✅ Объявление #{ad_id} одобрено и опубликовано в канал."
        try:
            if callback.message.photo:
                await callback.message.edit_caption(caption=confirm_text, reply_markup=None)
            else:
                await callback.message.edit_text(confirm_text, reply_markup=None)
        except Exception as e:
            logger.error(f"не удалось обновить сообщение модератору: {e}")
            await callback.message.answer(confirm_text)
        
        # уведомляем продавца
        seller = await get_user_by_id(ad.seller_user_id)
        if seller:
            try:
                # Формируем сообщение с названием объявления
                title = ad.title
                # Первые 10 символов - курсивом, остальное - обычным текстом
                if len(title) > 10:
                    title_formatted = f"<i>{title[:10]}</i>{title[10:]}"
                else:
                    title_formatted = f"<i>{title}</i>"
                
                notification_text = f"✅ Готово! 📍Ваше📍Объявление с названием \"{title_formatted}\" опубликовано в канале.\n\n"
                notification_text += "‼️Отредактировать объявление можно в разделе «Мои объявления»\n"
                notification_text += "Цену можно поменять без модерации!!!"
                
                # Создаем клавиатуру с кнопкой "Главное меню" и ссылкой на объявление в канале
                keyboard = InlineKeyboardBuilder()
                
                # Кнопка со ссылкой на объявление в канале (channel_msg_id всегда задан после успешной публикации/редактирования)
                if CHANNEL_USERNAME and channel_msg_id is not None:
                    channel_link = f"https://t.me/{CHANNEL_USERNAME}/{channel_msg_id}"
                    keyboard.row(InlineKeyboardButton(text="📍 Посмотреть в канале", url=channel_link))
                
                # Кнопка "Главное меню"
                keyboard.row(InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu"))
                
                await bot.send_message(
                    chat_id=seller.tg_user_id,
                    text=notification_text,
                    parse_mode='HTML',
                    reply_markup=keyboard.as_markup()
                )
            except Exception as e:
                logger.error(f"ошибка уведомления продавца: {e}")
        
        # логируем
        mod_username = callback.from_user.username or callback.from_user.first_name
        log_moderation(callback.from_user.id, mod_username, ad_id, "одобрил")
    
    except Exception as e:
        logger.error(f"Ошибка при публикации объявления в канал: {e}", exc_info=True)
        await callback.answer("❌ Ошибка при публикации в канал.", show_alert=True)


async def approve_edit_callback(callback: types.CallbackQuery, state: FSMContext):
    """Одобрить редактирование: применить копию к оригиналу, обновить канал."""
    await callback.answer()
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

    user_id = callback.from_user.id
    if not await is_moderator(user_id):
        await callback.answer("❌ У вас нет прав модератора.", show_alert=True)
        return

    edit_id = int(callback.data.split(":")[1])
    edit = await get_ad_edit(edit_id)
    if not edit:
        await callback.answer("❌ Копия объявления не найдена.", show_alert=True)
        return

    ad_id = await apply_ad_edit(edit_id)
    if not ad_id:
        await callback.answer("❌ Ошибка применения редактирования.", show_alert=True)
        return

    ad = await get_ad_by_id(ad_id)
    photos = await get_ad_photos(ad_id)
    if not ad or not photos:
        await callback.answer("❌ Объявление или фото не найдены.", show_alert=True)
        return

    def is_russian_city(city: str, country: str = None) -> bool:
        from src.bot.settings.constants import DEFAULT_CITIES, CIS_COUNTRIES
        if country:
            cl = country.lower().strip()
            rv = ['россия', 'российская федерация', 'рф', 'russia', 'russian federation']
            if cl not in rv:
                for _, d in CIS_COUNTRIES.items():
                    if d['name'].lower() == cl:
                        return False
                return False
        if not city:
            return False
        cl = city.lower().strip()
        for v in DEFAULT_CITIES.values():
            if v.lower() == cl:
                return True
        if not country:
            return True
        cl = (country or "").lower().strip()
        return cl in ['россия', 'российская федерация', 'рф', 'russia', 'russian federation']

    channel_target = f"@{CHANNEL_USERNAME}" if CHANNEL_USERNAME else CHANNEL_ID
    old_msg_id = ad.channel_message_id

    if not is_russian_city(ad.city, ad.country):
        if old_msg_id:
            try:
                await bot.delete_message(chat_id=channel_target, message_id=old_msg_id)
            except Exception as e:
                logger.warning(f"не удалось удалить сообщение #{old_msg_id}: {e}")
        await approve_ad(ad_id, None)
        try:
            if callback.message.photo:
                await callback.message.edit_caption(
                    caption=f"✅ Редактирование (оригинал #{ad_id}) применено, в канал не публиковалось.",
                    reply_markup=None,
                    parse_mode="HTML",
                )
            else:
                await callback.message.edit_text(f"✅ Редактирование (оригинал #{ad_id}) применено, в канал не публиковалось.", reply_markup=None)
        except Exception as e:
            logger.error(f"обновление сообщения модератору: {e}")
        seller = await get_user_by_id(ad.seller_user_id)
        if seller:
            try:
                t = ad.title
                tf = f"<i>{t[:10]}</i>{t[10:]}" if len(t) > 10 else f"<i>{t}</i>"
                await bot.send_message(
                    seller.tg_user_id,
                    f"✅ Редактирование объявления «{tf}» применено.\n\n‼️Отредактировать объявление можно в разделе «Мои объявления»\nЦену можно поменять без модерации!!!",
                    parse_mode="HTML",
                    reply_markup=InlineKeyboardBuilder().row(InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")).as_markup(),
                )
            except Exception as e:
                logger.error(f"уведомление продавца: {e}")
        log_moderation(user_id, callback.from_user.username or callback.from_user.first_name, ad_id, "одобрил редактирование (не в канал)")
        return

    seller = await get_user_by_id(ad.seller_user_id)
    is_trusted = getattr(seller, 'is_trusted_seller', False) if seller else False
    from src.bot.utils.channel_utils import format_active_caption
    cap = format_active_caption(ad, is_trusted)

    first_file_id = getattr(ad, 'cover_file_id', None) or photos[0].file_id
    if old_msg_id:
        # Редактируем карточку в канале (фото + подпись + кнопки), не удаляя сообщение
        try:
            media = InputMediaPhoto(media=first_file_id, caption=cap, parse_mode="HTML")
            await bot.edit_message_media(
                chat_id=channel_target,
                message_id=old_msg_id,
                media=media,
            )
            await bot.edit_message_reply_markup(
                chat_id=channel_target,
                message_id=old_msg_id,
                reply_markup=ad_in_channel_kb(ad_id, BOT_USERNAME),
            )
            await approve_ad(ad_id, old_msg_id)
            logger.info(f"карточка объявления #{ad_id} в канале отредактирована (message_id={old_msg_id})")
        except Exception as e:
            # Если редактирование не удалось (например, сообщение от канала), удаляем и отправляем новое
            logger.warning(f"не удалось отредактировать сообщение #{old_msg_id} в канале: {e}, удаляю и отправляю новое")
            try:
                await bot.delete_message(chat_id=channel_target, message_id=old_msg_id)
            except Exception as del_e:
                logger.warning(f"не удалось удалить сообщение #{old_msg_id}: {del_e}")


            # channel_msg = await bot.send_photo(
            #     chat_id=channel_target,
            #     photo=first_file_id,
            #     caption=cap,
            #     parse_mode="HTML",
            #     reply_markup=ad_in_channel_kb(ad_id, BOT_USERNAME),
            # )
            # CHANGE!!!
            message_id = 0
            await approve_ad(ad_id, message_id)
    else:
        # Нет старого message_id (на случай сбоя) — отправляем новую карточку
        # channel_msg = await bot.send_photo(
        #     chat_id=channel_target,
        #     photo=first_file_id,
        #     caption=cap,
        #     parse_mode="HTML",
        #     reply_markup=ad_in_channel_kb(ad_id, BOT_USERNAME),
        # )
        # CHANGE!!!
        message_id = 0
        
        await approve_ad(ad_id, message_id)

    try:
        if callback.message.photo:
            await callback.message.edit_caption(caption=f"✅ Редактирование (оригинал #{ad_id}) одобрено.", reply_markup=None, parse_mode="HTML")
        else:
            await callback.message.edit_text(f"✅ Редактирование (оригинал #{ad_id}) одобрено.", reply_markup=None)
    except Exception as e:
        logger.error(f"обновление сообщения модератору: {e}")

    seller = await get_user_by_id(ad.seller_user_id)
    if seller:
        try:
            t = ad.title
            tf = f"<i>{t[:10]}</i>{t[10:]}" if len(t) > 10 else f"<i>{t}</i>"
            channel_link = f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}" if CHANNEL_USERNAME else None
            txt = f"✅ Готово! 📍Ваше📍Объявление с названием \"{tf}\" обновлено в канале.\n\n‼️Отредактировать объявление можно в разделе «Мои объявления»\nЦену можно поменять без модерации!!!"
            kb = InlineKeyboardBuilder()
            kb.row(InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu"))
            if channel_link:
                kb.row(InlineKeyboardButton(text="📍 Посмотреть в канале", url=channel_link))
            await bot.send_message(seller.tg_user_id, txt, parse_mode="HTML", reply_markup=kb.as_markup())
        except Exception as e:
            logger.error(f"уведомление продавца: {e}")
    log_moderation(user_id, callback.from_user.username or callback.from_user.first_name, ad_id, "одобрил редактирование")


# === РЕГИСТРАЦИЯ ОБРАБОТЧИКОВ ===

async def approve_with_comment_callback(callback: types.CallbackQuery, state: FSMContext):
    """Одобрить объявление с комментарием"""
    data = await state.get_data()
    comment = data.get('moderation_comment')
    
    # Вызываем обычный обработчик одобрения
    await approve_ad_callback(callback, state)
    
    # Если был комментарий, добавляем его в логирование
    if comment:
        ad_id = int(callback.data.split(':')[1])
        mod_username = callback.from_user.username or callback.from_user.first_name
        log_moderation(callback.from_user.id, mod_username, ad_id, "одобрил", comment=comment)
    
    await state.clear()


async def reject_with_comment_callback(callback: types.CallbackQuery, state: FSMContext):
    """Отклонить объявление с комментарием"""
    data = await state.get_data()
    comment = data.get('moderation_comment')
    
    # Сохраняем комментарий для использования в процессе отклонения
    if comment:
        await state.update_data(moderation_comment=comment)
    
    # Вызываем обычный обработчик отклонения
    await reject_ad_callback(callback, state)


