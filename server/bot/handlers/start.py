import httpx
from typing import Union, cast
from aiogram import Dispatcher, types, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import ReplyKeyboardRemove
from loguru import logger
from src.bot.logging_config import log_user_action, log_agree

from src.bot.database.methods import create_or_update_user, check_user_agreement, set_user_agreement, count_users, count_approved_ads, check_user_subscription
from src.bot.keyboards.keyboards import main_menu_kb, InlineKeyboardBuilder, InlineKeyboardButton
from src.bot.keyboards.key_text import *
from src.bot.settings.constants import START_MESSAGE, CATEGORIES
from src.bot.loader import bot

from src.kit.database.service import database_service
from src.config import settings
from src.services import user_service, ad_service, email_service, tg_service_notifier


async def get_main_menu_text():
    """получить текст главного меню со статистикой"""
    try:
        users_count = await count_users()
        ads_count = await count_approved_ads()
    except Exception as e:
        logger.error(f"ошибка при получении статистики: {e}")
        users_count = 0
        ads_count = 0
    
    text = """Добро пожаловать в «Триатлонную барахолку» 🏊‍♂️🚴‍♀️🏃‍♂️
Здесь вы можете:
🔍 Найти и купить экипировку для триатлона
💬 Связаться с продавцом напрямую
📝 Разместить объявление о продаже или аренде
📋 Посмотреть свои активные объявления и статус модерации
Следите за новыми лотами и в нашем канале:
👉 t.me/triathlonsale"""
    
    return text


async def send_main_menu(message_or_callback, remove_reply_keyboard=True, state: FSMContext = None):
    """Отправить главное меню с удалением Reply клавиатуры. Пытается редактировать существующее сообщение, если оно есть в state."""
    menu_text = await get_main_menu_text()
    
    # Определяем объект для отправки сообщения
    if hasattr(message_or_callback, 'message'):
        # Это callback
        target = message_or_callback.message
    else:
        # Это message
        target = message_or_callback
    
    # Удаляем Reply клавиатуру, если она была (отправляем отдельным сообщением, которое сразу удаляем)
    if remove_reply_keyboard:
        try:
            remove_msg = await target.answer(
                " ",
                reply_markup=ReplyKeyboardRemove()
            )
            # Удаляем сообщение с ReplyKeyboardRemove через небольшую задержку
            import asyncio
            await asyncio.sleep(0.1)
            try:
                await remove_msg.delete()
            except:
                pass
        except:
            pass
    
    # Пытаемся редактировать существующее сообщение главного меню, если state передан и есть сохраненное сообщение
    if state:
        data = await state.get_data()
        main_menu_msg_id = data.get('main_menu_msg_id')
        
        if main_menu_msg_id:
            try:
                # Пытаемся отредактировать существующее сообщение
                # Получаем user_id для подсчета объявлений
                user_id = None
                if hasattr(message_or_callback, 'from_user'):
                    user_id = message_or_callback.from_user.id
                elif hasattr(message_or_callback, 'message') and hasattr(message_or_callback.message, 'from_user'):
                    user_id = message_or_callback.message.from_user.id
                elif hasattr(message_or_callback, 'from_user'):
                    user_id = message_or_callback.from_user.id
                
                await bot.edit_message_text(
                    chat_id=target.chat.id,
                    message_id=main_menu_msg_id,
                    text=menu_text,
                    parse_mode='HTML',
                    reply_markup=await main_menu_kb(user_id)
                )
                # Сохраняем ID (он тот же)
                await state.update_data(main_menu_msg_id=main_menu_msg_id)
                return
            except Exception as e:
                # Если не удалось отредактировать (сообщение удалено или недоступно), отправляем новое
                logger.debug(f"Не удалось отредактировать главное меню (msg_id={main_menu_msg_id}): {e}")
                pass
    
    # Получаем user_id для подсчета объявлений
    user_id = None
    if hasattr(message_or_callback, 'from_user'):
        user_id = message_or_callback.from_user.id
    elif hasattr(message_or_callback, 'message') and hasattr(message_or_callback.message, 'from_user'):
        user_id = message_or_callback.message.from_user.id
    
    # Отправляем новое сообщение главного меню
    msg = await target.answer(
        menu_text,
        parse_mode='HTML',
        reply_markup=await main_menu_kb(user_id)
    )
    
    # Сохраняем ID сообщения в state, если state передан
    if state:
        await state.update_data(main_menu_msg_id=msg.message_id)


async def check_channel_subscription(user_id: int) -> bool:
    """Проверка подписки на канал"""
    try:
        from src.bot.settings.settings import CHANNEL_USERNAME
        if not CHANNEL_USERNAME:
            # Если канал не настроен, считаем что подписка не требуется
            return False
        
        # Проверяем подписку
        member = await bot.get_chat_member(chat_id=f"@{CHANNEL_USERNAME}", user_id=user_id)
        # Проверяем статус: creator, administrator, member - подписан
        # left, kicked - не подписан
        return member.status in ['creator', 'administrator', 'member']
    except Exception as e:
        logger.error(f"Ошибка проверки подписки на канал: {e}")
        # В случае ошибки считаем что не подписан (чтобы всегда показывать сообщение о подписке)
        return False


async def start_command(message: types.Message, state: FSMContext):
    """команда /start"""
    logger.info(f"start_command called by user {message.from_user.id}")
    # Сохраняем данные, которые нужны для навигации по цепочке
    # (state.clear() ниже сотрёт всё, но deep link может открыть профиль/объявление,
    # и при возврате «Назад» нужно знать, какие сообщения удалять).
    prev_data = await state.get_data()
    await state.clear()
    _keys_to_keep = (
        'first_photo_msg_id', 'photos_count', 'ad_details_msg_id',
        'came_from_catalog', 'came_from_channel', 'channel_message_id', 'channel_username',
        'last_viewed_ad_id', 'last_viewed_seller_id',
        'category_cards_message_ids', 'category_nav_message_id',
        'category_separator_message_id',
        'nav_stack',
        'catalog_msg_id',
    )
    restored = {k: prev_data[k] for k in _keys_to_keep if k in prev_data}
    if restored:
        await state.update_data(**restored)
    
    # создаем юзера
    user = await create_or_update_user(message)
    
    # ПЕРВЫМ ДЕЛОМ проверяем согласие (оферта)
    agreed = await check_user_agreement(message.from_user.id)
    
    if not agreed:
        # показываем соглашение
        agreement_text = """📄 ПУБЛИЧНАЯ ОФЕРТА
о пользовании сервисом «Триатлонная барахолка»

Настоящий текст является публичной офертой. Использование сервиса означает полное и безоговорочное принятие условий ниже.

1. Общие положения

1.1. «Триатлонная барахолка» — информационная площадка для размещения объявлений по теме триатлона.
1.2. Администрация предоставляет техническую возможность размещения объявлений и не участвует в сделках между пользователями.
1.3. Размещение объявления через бота означает акцепт настоящей оферты.

2. Размещение объявлений

2.1. Объявления размещаются исключительно через бота.
2.2. Один товар или услуга — одно объявление.
2.3. Запрещено указывать контактные данные в тексте объявления и на изображениях.
2.4. Название и описание должны соответствовать реальному состоянию товара или услуги.
2.5. Допускаются только товары и услуги, относящиеся к тематике триатлона.

3. Ограничения

3.1. Запрещена коммерческая реклама без согласования с администрацией.
3.2. Запрещено размещение объявлений, не соответствующих тематике сервиса.

4. Персональные данные

4.1. Пользователь соглашается на обработку минимально необходимых данных, включая Telegram ID, имя профиля и данные объявления.
4.2. Контактные данные используются пользователями исключительно для связи между собой.
4.3. Администрация не передаёт персональные данные третьим лицам и не использует их в коммерческих целях.

5. Ответственность

5.1. Все сделки совершаются напрямую между пользователями.
5.2. Администрация не несёт ответственности за качество товаров, оплату, доставку и иные обязательства сторон.
5.3. Администрация не несёт ответственности за технические сбои и перебои в работе сервиса.

6. Модерация

6.1. Администрация вправе удалять объявления и ограничивать доступ к сервису при нарушении условий оферты без объяснения причин.

7. Заключительные положения

7.1. Сервис предоставляется «как есть».
7.2. Администрация вправе изменять условия оферты в одностороннем порядке.
7.3. Актуальная версия оферты размещается в боте или канале.

Продолжая, вы подтверждаете согласие с условиями."""
        
        keyboard = InlineKeyboardBuilder()
        keyboard.row(InlineKeyboardButton(
            text="✅ Принимаю условия",
            callback_data="agree_accept"
        ))
        keyboard.row(InlineKeyboardButton(
            text="❌ Отказаться",
            callback_data="agree_decline"
        ))
        
        await message.answer(
            agreement_text,
            parse_mode='HTML',
            reply_markup=keyboard.as_markup()
        )
        return
    
    # После согласия проверяем статус подписки из БД
    # is_subscribed_in_db = await check_user_subscription(message.from_user.id)
    is_subscribed_in_db = True
    # CHANGE!!!
    
    if not is_subscribed_in_db:
        # Если статус подписки не сохранен в БД - показываем сообщение с просьбой подписаться
        from src.bot.settings.settings import CHANNEL_USERNAME
        subscription_text = """❗ Для использования бота необходимо подписаться на канал

Подпишитесь на наш канал с объявлениями, по кнопке "ПОДПИСАТЬСЯ" ниже, чтобы продолжить:
После подписки нажмите "ПРОВЕРИТЬ ПОДПИСКУ."
"""
        keyboard = InlineKeyboardBuilder()
        keyboard.row(InlineKeyboardButton(
            text="☁️ ПОДПИСАТЬСЯ",
            url=f"https://t.me/{CHANNEL_USERNAME}"
        ))
        keyboard.row(InlineKeyboardButton(
            text="✅ ПРОВЕРИТЬ ПОДПИСКУ",
            callback_data="check_subscription"
        ))
        
        await message.answer(
            subscription_text,
            parse_mode='HTML',
            reply_markup=keyboard.as_markup()
        )
        return
    
    # проверяем deep link параметры
    command_args = message.text.split()
    deep_link_param = command_args[1] if len(command_args) > 1 else None
    
    # если уже согласился - обрабатываем deep link или показываем меню
    username = message.from_user.username or message.from_user.first_name
    log_user_action(message.from_user.id, username, "запустил бота")
    
    # обработка deep link
    if deep_link_param:
        if deep_link_param == "catalog":
            # открываем каталог с выбором категорий
            from src.bot.database.methods import count_ads_by_category
            from src.bot.settings.constants import CATEGORIES
            from src.bot.keyboards.keyboards import catalog_categories_kb
            # удаляем сообщение /start для чистоты чата
            try:
                await message.delete()
            except:
                pass
            
            text = "📂 Выберите категорию товаров:"
            
            # Подсчитываем товары по категориям
            categories_data = {}
            total_ads = 0
            for cat_key, cat_name in CATEGORIES.items():
                count = await count_ads_by_category(cat_key)
                categories_data[cat_key] = (cat_name, count)
                total_ads += count
            
            keyboard = catalog_categories_kb(categories_data, total_ads)
            
            # Отправляем новое сообщение с категориями
            await message.answer(text, reply_markup=keyboard)
            return
        elif deep_link_param.startswith("ad_"):
            # открываем детали объявления (старый формат)
            try:
                ad_id = int(deep_link_param.split("_")[1])
                from src.bot.handlers.catalog import show_ad_details
                # удаляем сообщение /start для чистоты чата
                try:
                    await message.delete()
                except:
                    pass
                await show_ad_details(message, ad_id, state)
                return
            except (ValueError, IndexError):
                pass  # если ошибка - показываем главное меню
        elif deep_link_param.startswith("item_"):
            # открываем детали объявления. item_28 = из канала/прямая ссылка, item_28_p = из профиля продавца
            try:
                parts = deep_link_param.split("_")
                ad_id = int(parts[1])
                from_profile = len(parts) >= 3 and parts[2] == "p"
                logger.info(f"Обработка deep link item_{ad_id} (from_profile={from_profile}) для пользователя {message.from_user.id}")
                from src.bot.handlers.catalog import show_ad_details, get_ad_by_id
                from src.bot.settings.settings import CHANNEL_USERNAME
                data = await state.get_data()
                seller_profile_msg_id = data.get('seller_profile_msg_id')
                ad = await get_ad_by_id(ad_id)
                if ad:
                    if from_profile or seller_profile_msg_id:
                        # Пришли из профиля продавца (ссылка item_X_p или есть сообщение профиля)
                        update_data = {
                            'last_viewed_ad_id': ad_id,
                            'last_viewed_seller_id': ad.seller_user_id,
                            'came_from_seller_profile': True,
                        }
                        if data.get('came_from_channel') and data.get('channel_message_id') is not None:
                            update_data['came_from_channel'] = True
                            update_data['channel_message_id'] = data.get('channel_message_id')
                            update_data['channel_username'] = data.get('channel_username') or CHANNEL_USERNAME or ''
                        await state.update_data(**update_data)
                    else:
                        # Определяем источник: каталог-список или канал/прямая ссылка
                        was_in_catalog = bool(data.get('catalog_msg_id') or data.get('category_nav_message_id') or data.get('came_from_catalog'))
                        if was_in_catalog:
                            update_data = {
                                'last_viewed_ad_id': ad_id,
                                'last_viewed_seller_id': ad.seller_user_id,
                                'came_from_seller_profile': False,
                                'came_from_catalog': True,
                            }
                        else:
                            update_data = {
                                'last_viewed_ad_id': ad_id,
                                'last_viewed_seller_id': ad.seller_user_id,
                                'came_from_seller_profile': False,
                                'came_from_channel': True,
                                'channel_message_id': getattr(ad, 'channel_message_id', None),
                                'channel_username': CHANNEL_USERNAME or '',
                            }
                        await state.update_data(**update_data)
                    logger.info(f"Объявление {ad_id} найдено, статус: {ad.status}")
                else:
                    logger.warning(f"Объявление {ad_id} не найдено в базе данных")
                # удаляем сообщение /start для чистоты чата
                try:
                    await message.delete()
                except:
                    pass
                # Если пришли из профиля продавца — НЕ удаляем сообщение с профилем (цепочка: объявление из профиля — новое звено; «Назад» только закроет объявление)
                if seller_profile_msg_id and not from_profile:
                    try:
                        chat_id = data.get('seller_profile_chat_id') or message.chat.id
                        await bot.delete_message(chat_id=chat_id, message_id=seller_profile_msg_id)
                    except Exception:
                        pass
                    await state.update_data(seller_profile_msg_id=None, seller_profile_chat_id=None)
                await show_ad_details(message, ad_id, state)
                return
            except (ValueError, IndexError) as e:
                logger.error(f"Ошибка при обработке deep link item_: {e}")
                pass  # если ошибка - показываем главное меню
            except Exception as e:
                logger.error(f"Неожиданная ошибка при обработке deep link item_: {e}", exc_info=True)
                pass
        elif deep_link_param.startswith("seller_"):
            # открываем профиль продавца
            try:
                parts = deep_link_param.split("_")
                seller_id = int(parts[1])
                # Если есть ad_id в ссылке (новый формат: seller_{seller_id}_{ad_id})
                ad_id = None
                if len(parts) >= 3:
                    try:
                        ad_id = int(parts[2])
                    except (ValueError, IndexError):
                        pass  # Если не удалось распарсить ad_id, используем None
                
                from src.bot.handlers.catalog import show_seller_profile
                # Сохраняем seller_id и ad_id в состоянии для кнопки "Назад"
                await state.update_data(last_viewed_seller_id=seller_id, last_viewed_ad_id=ad_id)
                # удаляем сообщение /start для чистоты чата
                try:
                    await message.delete()
                except:
                    pass
                await show_seller_profile(message, seller_id, ad_id, state=state)
                return
            except (ValueError, IndexError):
                pass  # если ошибка - показываем главное меню
        elif deep_link_param.startswith("rate_seller_"):
            # открываем страницу оценки продавца
            try:
                seller_id = int(deep_link_param.split("_")[2])
                from src.bot.handlers.catalog import show_rate_seller_page
                # удаляем сообщение /start для чистоты чата
                try:
                    await message.delete()
                except:
                    pass
                await show_rate_seller_page(message, seller_id, state)
                return
            except (ValueError, IndexError):
                pass  # если ошибка - показываем главное меню
        elif deep_link_param.startswith("auth_"):
            await _proceed_auth(deep_link_param, message)
            return
        elif deep_link_param.startswith("promoteReject_"):
            await proceed_promote_reject(deep_link_param, message, state)
            return
    # Чтобы главное меню не оказалось среди удаляемых, сбрасываем main_menu_msg_id —
    # тогда send_main_menu отправит новое сообщение (ID > start_msg_id), а не отредактирует старое.
    await state.update_data(main_menu_msg_id=None)

    # Сохраняем ID сообщения /start для последующего удаления
    start_msg_id = message.message_id
    chat_id = message.chat.id

    # Сначала показываем главное меню (новым сообщением)
    await send_main_menu(message, state=state)

    # === УДАЛЕНИЕ ПРИ /start (без маркеров): сообщение /start и до 30 предыдущих ===
    try:
        await bot.delete_message(chat_id=chat_id, message_id=start_msg_id)
    except Exception as e:
        logger.debug(f"Не удалось удалить сообщение /start: {e}")

    for i in range(1, 31):
        msg_id_to_delete = start_msg_id - i
        if msg_id_to_delete <= 0:
            continue
        try:
            await bot.delete_message(chat_id=chat_id, message_id=msg_id_to_delete)
        except Exception as e:
            # logger.info(f"Не удалось удалить сообщение {msg_id_to_delete} для чата {chat_id}. Причина: {e}")
            pass

async def agreement_accept(callback: types.CallbackQuery, state: FSMContext):
    """принятие соглашения"""
    await callback.answer("✅ Согласие принято")
    
    # сохраняем согласие
    await set_user_agreement(callback.from_user.id)
    
    # логируем
    username = callback.from_user.username or callback.from_user.first_name
    log_agree(callback.from_user.id, username)
    
    # Удаляем сообщение с офертой
    try:
        await callback.message.delete()
    except:
        pass
    
    # Проверяем статус подписки из БД
    # is_subscribed_in_db = await check_user_subscription(callback.from_user.id)
    is_subscribed_in_db = True
    # CHANGE!!!
    
    if not is_subscribed_in_db:
        # Если статус подписки не сохранен в БД - показываем сообщение с просьбой подписаться
        from src.bot.settings.settings import CHANNEL_USERNAME
        subscription_text = """❗ Для использования бота необходимо подписаться на канал

Подпишитесь на наш канал с объявлениями, по кнопке "ПОДПИСАТЬСЯ" ниже, чтобы продолжить:
После подписки нажмите "ПРОВЕРИТЬ ПОДПИСКУ."
"""
        keyboard = InlineKeyboardBuilder()
        keyboard.row(InlineKeyboardButton(
            text="☁️ ПОДПИСАТЬСЯ",
            url=f"https://t.me/{CHANNEL_USERNAME}"
        ))
        keyboard.row(InlineKeyboardButton(
            text="✅ ПРОВЕРИТЬ ПОДПИСКУ",
            callback_data="check_subscription"
        ))
        
        await callback.message.answer(
            subscription_text,
            parse_mode='HTML',
            reply_markup=keyboard.as_markup()
        )
        return
    
    # Если уже подписан (статус сохранен в БД) - показываем главное меню
    await send_main_menu(callback, state=state)


async def agreement_decline(callback: types.CallbackQuery, state: FSMContext):
    """отказ от соглашения"""
    await callback.answer()
    
    # Изменяем сообщение на текст с кнопкой "Вернуться к оферте"
    decline_text = "Без согласия вы не сможете получить доступ к основному функционалу бота. Если передумаете, нажмите кнопку ниже:"
    
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(
        text="Вернуться к оферте",
        callback_data="return_to_oferta"
    ))
    
    try:
        await callback.message.edit_text(
            decline_text,
            reply_markup=keyboard.as_markup()
        )
    except Exception as e:
        # Игнорируем ошибку "message is not modified" - если сообщение уже имеет тот же текст
        if "message is not modified" not in str(e).lower():
            logger.error(f"Ошибка при редактировании сообщения в agreement_decline: {e}")


async def check_subscription_callback(callback: types.CallbackQuery, state: FSMContext):
    """Проверка подписки после нажатия кнопки"""
    await callback.answer()
    
    # is_subscribed = await check_channel_subscription(callback.from_user.id)
    is_subscribed = True
    # CHANGE!!!
    
    if not is_subscribed:
        # Редактируем сообщение на текст о том, что пользователь не подписан
        from src.bot.settings.settings import CHANNEL_USERNAME
        error_text = "❌ Вы не подписаны на канал. Проверьте подписку на канал и нажмите на кнопку снова!"
        keyboard = InlineKeyboardBuilder()
        keyboard.row(InlineKeyboardButton(
            text="☁️ ПОДПИСАТЬСЯ",
            url=f"https://t.me/{CHANNEL_USERNAME}"
        ))
        keyboard.row(InlineKeyboardButton(
            text="✅ ПРОВЕРИТЬ ПОДПИСКУ",
            callback_data="check_subscription"
        ))
        
        try:
            await callback.message.edit_text(
                error_text,
                parse_mode='HTML',
                reply_markup=keyboard.as_markup()
            )
        except:
            # Если не удалось отредактировать, отправляем новое сообщение
            await callback.message.answer(
                error_text,
                parse_mode='HTML',
                reply_markup=keyboard.as_markup()
            )
        return
    
    # Подписка подтверждена - сохраняем в БД
    from src.bot.database.methods import set_user_subscription
    await set_user_subscription(callback.from_user.id)
    
    # Удаляем сообщение о подписке
    try:
        await callback.message.delete()
    except:
        pass
    
    # Показываем главное меню
    await send_main_menu(callback, state=state)


async def create_ad_button_handler(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'Создать объявление'"""
    # Проверяем лимит размещений до показа выбора типа
    from src.bot.database.methods import get_user_by_tg_id, create_or_update_user, is_trusted_seller, count_user_ads_today
    user = await get_user_by_tg_id(callback.from_user.id)
    if not user:
        user = await create_or_update_user(callback.message, from_user=callback.from_user)
    is_trusted = await is_trusted_seller(callback.from_user.id)
    daily_limit = 6 if is_trusted else 3
    ads_today = await count_user_ads_today(user.id)
    if ads_today >= daily_limit:
        await callback.answer("Достигнут лимит размещений на сегодня. Попробуйте завтра.", show_alert=True)
        return

    await callback.answer()
    
    # Редактируем сообщение главного меню на выбор типа объявления
    from src.bot.keyboards.keyboards import ad_type_selection_kb
    text = "📝 <b>Выберите тип объявления:</b>"
    
    try:
        await callback.message.edit_text(
            text,
            parse_mode='HTML',
            reply_markup=ad_type_selection_kb()
        )
    except:
        await callback.message.answer(
            text,
            parse_mode='HTML',
            reply_markup=ad_type_selection_kb()
        )


async def ad_type_selection_back_handler(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'Назад' из выбора типа объявления"""
    await callback.answer()
    
    # Редактируем сообщение обратно в главное меню
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
        await state.update_data(main_menu_msg_id=callback.message.message_id)
    except:
        from src.bot.handlers.start import send_main_menu
        await send_main_menu(callback, state=state)


async def ad_type_selection_sale_handler(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик выбора 'Продажа' из меню выбора типа"""
    await callback.answer()
    
    # Проверяем подписку на канал
    # is_subscribed = await check_channel_subscription(callback.from_user.id)
    is_subscribed = True
    # CHANGE!!!
    
    if not is_subscribed:
        from src.bot.settings.settings import CHANNEL_USERNAME
        subscription_text = """
❗ <b>Для использования бота необходимо подписаться на канал</b>

Подпишитесь на наш канал с объявлениями, чтобы продолжить:

👉 @{channel}

После подписки нажмите кнопку "✅ Я подписался"
"""
        keyboard = InlineKeyboardBuilder()
        keyboard.row(InlineKeyboardButton(
            text="📢 Перейти в канал",
            url=f"https://t.me/{CHANNEL_USERNAME}"
        ))
        keyboard.row(InlineKeyboardButton(
            text="✅ Я подписался",
            callback_data="check_subscription"
        ))
        
        try:
            await callback.message.edit_text(
                subscription_text.format(channel=CHANNEL_USERNAME),
                parse_mode='HTML',
                reply_markup=keyboard.as_markup()
            )
        except:
            await callback.message.answer(
                subscription_text.format(channel=CHANNEL_USERNAME),
                parse_mode='HTML',
                reply_markup=keyboard.as_markup()
            )
        return
    
    # Запускаем процесс создания объявления с типом "Продажа"
    from src.bot.handlers.add_ad import start_add_ad_with_type
    await start_add_ad_with_type(callback, state, ad_type='sale')


async def ad_type_selection_rent_handler(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик выбора 'Аренда' из меню выбора типа"""
    await callback.answer()
    
    # Проверяем подписку на канал
    # is_subscribed = await check_channel_subscription(callback.from_user.id)
    is_subscribed = True
    # CHANGE!!!
    
    if not is_subscribed:
        from src.bot.settings.settings import CHANNEL_USERNAME
        subscription_text = """
❗ <b>Для использования бота необходимо подписаться на канал</b>

Подпишитесь на наш канал с объявлениями, чтобы продолжить:

👉 @{channel}

После подписки нажмите кнопку "✅ Я подписался"
"""
        keyboard = InlineKeyboardBuilder()
        keyboard.row(InlineKeyboardButton(
            text="📢 Перейти в канал",
            url=f"https://t.me/{CHANNEL_USERNAME}"
        ))
        keyboard.row(InlineKeyboardButton(
            text="✅ Я подписался",
            callback_data="check_subscription"
        ))
        
        try:
            await callback.message.edit_text(
                subscription_text.format(channel=CHANNEL_USERNAME),
                parse_mode='HTML',
                reply_markup=keyboard.as_markup()
            )
        except:
            await callback.message.answer(
                subscription_text.format(channel=CHANNEL_USERNAME),
                parse_mode='HTML',
                reply_markup=keyboard.as_markup()
            )
        return
    
    # Запускаем процесс создания объявления с типом "Аренда"
    from src.bot.handlers.add_ad import start_add_ad_with_type
    await start_add_ad_with_type(callback, state, ad_type='rent')


async def catalog_button_handler(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'Каталог'"""
    await callback.answer()
    
    # Открываем каталог (показываем категории)
    from src.bot.database.methods import count_ads_by_category
    from src.bot.settings.constants import CATEGORIES
    from src.bot.keyboards.keyboards import catalog_categories_kb
    
    text = "📂 Выберите категорию товаров:"
    
    # Подсчитываем товары по категориям
    categories_data = {}
    total_ads = 0
    for cat_key, cat_name in CATEGORIES.items():
        count = await count_ads_by_category(cat_key)
        categories_data[cat_key] = (cat_name, count)
        total_ads += count
    
    keyboard = catalog_categories_kb(categories_data, total_ads)
    
    # Заменяем сообщение главного меню на сообщение с категориями
    try:
        await callback.message.edit_text(text, reply_markup=keyboard)
    except:
        # Если не удалось отредактировать, отправляем новое
        await callback.message.answer(text, reply_markup=keyboard)


async def return_to_oferta_callback(callback: types.CallbackQuery, state: FSMContext):
    """Возврат к оферте после отказа"""
    await callback.answer()
    
    # Показываем оферту снова
    agreement_text = """📄 ПУБЛИЧНАЯ ОФЕРТА
о пользовании сервисом «Триатлонная барахолка»

Настоящий текст является публичной офертой. Использование сервиса означает полное и безоговорочное принятие условий ниже.

1. Общие положения

1.1. «Триатлонная барахолка» — информационная площадка для размещения объявлений по теме триатлона.
1.2. Администрация предоставляет техническую возможность размещения объявлений и не участвует в сделках между пользователями.
1.3. Размещение объявления через бота означает акцепт настоящей оферты.

2. Размещение объявлений

2.1. Объявления размещаются исключительно через бота.
2.2. Один товар или услуга — одно объявление.
2.3. Запрещено указывать контактные данные в тексте объявления и на изображениях.
2.4. Название и описание должны соответствовать реальному состоянию товара или услуги.
2.5. Допускаются только товары и услуги, относящиеся к тематике триатлона.

3. Ограничения

3.1. Запрещена коммерческая реклама без согласования с администрацией.
3.2. Запрещено размещение объявлений, не соответствующих тематике сервиса.

4. Персональные данные

4.1. Пользователь соглашается на обработку минимально необходимых данных, включая Telegram ID, имя профиля и данные объявления.
4.2. Контактные данные используются пользователями исключительно для связи между собой.
4.3. Администрация не передаёт персональные данные третьим лицам и не использует их в коммерческих целях.

5. Ответственность

5.1. Все сделки совершаются напрямую между пользователями.
5.2. Администрация не несёт ответственности за качество товаров, оплату, доставку и иные обязательства сторон.
5.3. Администрация не несёт ответственности за технические сбои и перебои в работе сервиса.

6. Модерация

6.1. Администрация вправе удалять объявления и ограничивать доступ к сервису при нарушении условий оферты без объяснения причин.

7. Заключительные положения

7.1. Сервис предоставляется «как есть».
7.2. Администрация вправе изменять условия оферты в одностороннем порядке.
7.3. Актуальная версия оферты размещается в боте или канале.

Продолжая, вы подтверждаете согласие с условиями."""
    
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(
        text="✅ Принимаю условия",
        callback_data="agree_accept"
    ))
    keyboard.row(InlineKeyboardButton(
        text="❌ Отказаться",
        callback_data="agree_decline"
    ))
    
    await callback.message.edit_text(
        agreement_text,
        parse_mode='HTML',
        reply_markup=keyboard.as_markup()
    )


def register_start_handlers(dp: Dispatcher):
    """регистрация обработчиков /start и главного меню"""
    dp.message.register(start_command, Command("start"))
    dp.callback_query.register(agreement_accept, F.data == "agree_accept")
    dp.callback_query.register(agreement_decline, F.data == "agree_decline")
    dp.callback_query.register(return_to_oferta_callback, F.data == "return_to_oferta")
    dp.callback_query.register(check_subscription_callback, F.data == "check_subscription")
    dp.callback_query.register(create_ad_button_handler, F.data == "main_menu:create_ad")
    dp.callback_query.register(ad_type_selection_back_handler, F.data == "ad_type_selection:back")
    dp.callback_query.register(ad_type_selection_sale_handler, F.data == "ad_type_selection:sale")
    dp.callback_query.register(ad_type_selection_rent_handler, F.data == "ad_type_selection:rent")
    dp.callback_query.register(catalog_button_handler, F.data == "main_menu:catalog")

    # INTEGRATION:
    dp.message.register(continue_rejection, ModeratorRejectionState.wait_for_reason)
    dp.callback_query.register(continue_confirmation_rejection, F.data.startswith("moderReason_"))
    dp.callback_query.register(cancel_ad_moderation, F.data == "CancelAdModeration")














# INTEGRATION:

class ModeratorRejectionState(StatesGroup):
    wait_for_reason = State()




def get_moderator_cancel_keyboard():
    return InlineKeyboardBuilder().row(
        InlineKeyboardButton(
            text="Отменить отклонение",
            style='danger',
            callback_data="CancelAdModeration"
        ),
    ).as_markup()

def get_moderator_confirmation_reason_keyboard():
    return InlineKeyboardBuilder().row(
        InlineKeyboardButton(
            text="Подтвердить",
            style='success',
            callback_data=f"moderReason_confirm"
        ),
        InlineKeyboardButton(
            text="Изменить",
            style='primary',
            callback_data=f"moderReason_edit"
        ),
        InlineKeyboardButton(
            text="Отменить отклонение",
            style='danger',
            callback_data="CancelAdModeration"
        ),
        width=2
    ).as_markup()




async def _proceed_auth(deep_link_param: str, message: types.Message):
    """Авторизация через Telegram (deeplink с сайта)."""
    if not message.from_user:
        return

    # Проверяем бан
    async with database_service.get_session() as session:
        user = await user_service.get_or_create_by_tg(session, message.from_user)
        if user and user.is_banned:
            await message.answer("⛔ Ваш аккаунт заблокирован. Обратитесь к администрации.")
            return

    session_token = deep_link_param.replace("auth_", "")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.API_DOMAIN_URL}/v1/auth/telegram/callback",
                json={
                    "session_token": session_token,
                    "tg_user_id": message.from_user.id,
                    "username": message.from_user.username,
                    "first_name": message.from_user.first_name,
                    "last_name": message.from_user.last_name,
                },
            )

        if response.status_code == 200:
            await message.answer(
                "✅ Авторизация успешна!\n\nТеперь вы можете вернуться на сайт.",
                reply_markup=await main_menu_kb(message.from_user.id)
            )
        else:
            await message.answer("❌ Ошибка авторизации. Попробуйте ещё раз.")
    except Exception as e:
        logger.error(f"Auth deeplink error: {e}")
        await message.answer("❌ Произошла ошибка. Попробуйте ещё раз.")



async def proceed_promote_reject(deeplink: str, message: types.Message, state: FSMContext):
    ad_id = deeplink.replace("promoteReject_", "")

    try:
        ad_id = int(ad_id)
    except:
        logger.error("Ad_id isn't a number")
        return
    
    await state.update_data(ad_id=ad_id)
    
    await message.answer(
        text='Введите причину:',
        reply_markup=get_moderator_cancel_keyboard()
    )
    await state.set_state(ModeratorRejectionState.wait_for_reason)

async def continue_rejection(message: types.Message, state: FSMContext):
    rejection_reason = message.text
    if not rejection_reason:
        await message.answer(
            text='Пожалуйста отправьте ТЕКСТ - причину отказа',
            reply_markup=get_moderator_cancel_keyboard()
        )
        return
        
    await message.answer(
        text='Подтвердите причину:\n\n' \
        f'Причина: <b>{rejection_reason}</b>',
        reply_markup=get_moderator_confirmation_reason_keyboard()
    )

    await state.update_data(rejection_reason=rejection_reason)


async def continue_confirmation_rejection(cb: types.CallbackQuery, state: FSMContext):
    msg = cast(types.Message, cb.message)
    data = await state.get_data()
    ad_id = data["ad_id"]
    rejection_reason = data["rejection_reason"]

    if cb.data.replace("moderReason_", "") == 'confirm': # pyright: ignore

        try:
            async with database_service.get_session() as session:
                ad = await ad_service.moderate_ad(
                    session=session,
                    ad_id=ad_id,
                    action="reject",
                    rejection_reason=rejection_reason,
                )
                await session.commit()

                if not ad:
                    await cb.answer(
                        text='Объявления больше не существует',
                        show_alert=True
                    )
                    return
                
                username = "@" + cb.from_user.username if cb.from_user and cb.from_user.username else None
                full_name = cb.from_user.full_name if cb.from_user else None
                
                bot = cast(Bot, cb.bot)

                await cb.message.delete() # pyright: ignore

                msg = await bot.send_message(
                    chat_id=settings.MODERATORS_CHAT_ID,
                    text=f"❌ Объявление #{ad_id}\n"\
                            f"Отклонено модератором {username or full_name}\n"\
                            f"Причина: <b>{rejection_reason}</b>"
                )

                
                await cb.answer(
                    f"❌ Объявление #{ad_id} успешно отклонено", show_alert=True
                )

                await state.clear()
                
                # Notify user
                await tg_service_notifier.notify_user_ad_rejected(ad, rejection_reason)
                
                # Email notification for email-registered users
                if not ad.seller.username and ad.seller.credentials and ad.seller.credentials.email:
                    await email_service.notify_user_ad_rejected_email(
                        email=ad.seller.credentials.email,
                        title=ad.title,
                        price=ad.price,
                        reason=rejection_reason,
                    )
                
                # In-app notification
                from src.models import Notification
                session.add(Notification(
                    user_id=ad.seller_user_id,
                    title="Объявление отклонено",
                    message=f"Ваше объявление «{ad.title}» отклонено. Причина: {rejection_reason}",
                    type="error",
                    ad_id=ad.id,
                ))
                await session.commit()
                return
        except Exception as e:
            await msg.answer(
                text='Пожалуйста отправьте причину отказа ЕЩЕ РАЗ:',
                reply_markup=get_moderator_cancel_keyboard()
            )
            logger.error(f"ERROR WHILE CONFIRMATING REJECTION: {e}")
    else:
        await msg.answer(
            text='Пожалуйста отправьте причину отказа ЕЩЕ РАЗ:',
            reply_markup=get_moderator_cancel_keyboard()
        )
        await state.set_state(ModeratorRejectionState.wait_for_reason)
        return


async def cancel_ad_moderation(cb: types.CallbackQuery, state: FSMContext):
    await cast(types.Message, cb.message).edit_text('Отменено. Хорошего дня!')
    await state.clear()




async def edit_message(
        message: types.MaybeInaccessibleMessageUnion, 
        new_text: str,
    ):

    if isinstance(message, types.Message):
        
        if message.photo or message.media_group_id:
            await message.edit_caption(
                caption=new_text
            )
            return
        await message.edit_text(
            text=new_text
        )
        return