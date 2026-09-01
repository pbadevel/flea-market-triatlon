"""
Обработчики для поддержки, правил и админских команд
"""

from aiogram import Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from loguru import logger

from src.bot.keyboards.keyboards import *
from src.bot.keyboards.key_text import *
from src.bot.settings.constants import *
from src.bot.settings.settings import SUPPORT_USERNAME


# === ПОДДЕРЖКА ===

async def support_handler(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик кнопки поддержки"""
    try:
        logger.info(f"🔵 support_handler вызван! Data: {callback.data}, User: {callback.from_user.id}")
        await callback.answer()
        await state.clear()
        
        support_text = SUPPORT_MESSAGE
        
        keyboard = InlineKeyboardBuilder()
        
        # Добавляем кнопку с ссылкой на админа, если SUPPORT_USERNAME задан
        if SUPPORT_USERNAME:
            try:
                keyboard.row(InlineKeyboardButton(
                    text=WRITE_SUPPORT_BTN,
                    url=f"https://t.me/{SUPPORT_USERNAME}"
                ))
            except Exception as e:
                logger.error(f"ошибка создания кнопки поддержки: {e}")
        
        keyboard.row(InlineKeyboardButton(
            text=BACK_BTN,
            callback_data="back_to_menu"
        ))
        
        # Заменяем сообщение главного меню на сообщение поддержки
        try:
            await callback.message.edit_text(
                support_text,
                parse_mode='HTML',
                reply_markup=keyboard.as_markup()
            )
        except:
            # Если не удалось отредактировать, отправляем новое
            await callback.message.answer(
                support_text,
                parse_mode='HTML',
                reply_markup=keyboard.as_markup()
            )
        
        logger.info(f"✅ support_handler успешно выполнен для пользователя {callback.from_user.id}")
    except Exception as e:
        logger.error(f"❌ Ошибка в support_handler: {e}", exc_info=True)
        try:
            await callback.answer("❌ Произошла ошибка. Попробуйте позже.", show_alert=True)
        except:
            pass


async def support_message_handler(message: types.Message, state: FSMContext):
    """Обработчик сообщения в поддержку"""
    from src.bot.settings.settings import SUPPORT_USER_ID
    from src.bot.loader import bot
    
    user_text = message.text.strip()
    
    if not user_text:
        await message.answer("❌ Сообщение не может быть пустым. Попробуйте еще раз.")
        return
    
    # Отправляем сообщение админу, если SUPPORT_USER_ID установлен
    if SUPPORT_USER_ID and SUPPORT_USER_ID != 0:
        try:
            support_message = f"📩 <b>Сообщение в поддержку</b>\n\n"
            support_message += f"👤 <b>От:</b> {message.from_user.first_name or 'Пользователь'}"
            if message.from_user.username:
                support_message += f" (@{message.from_user.username})"
            support_message += f"\n🆔 ID: {message.from_user.id}\n\n"
            support_message += f"💬 <b>Сообщение:</b>\n{user_text}"
            
            await bot.send_message(
                chat_id=SUPPORT_USER_ID,
                text=support_message,
                parse_mode='HTML'
            )
            
            await message.answer("✅ Ваше сообщение отправлено в поддержку. Мы ответим вам в ближайшее время.")
            logger.info(f"✅ Сообщение в поддержку отправлено админу {SUPPORT_USER_ID} от пользователя {message.from_user.id}")
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения в поддержку: {e}", exc_info=True)
            await message.answer("❌ Ошибка отправки сообщения. Попробуйте позже.")
    else:
        logger.warning(f"🔴 SUPPORT_USER_ID не установлен, сообщение от пользователя {message.from_user.id} не отправлено")
        await message.answer("❌ Поддержка временно недоступна. Обратитесь к администратору.")
    
    await state.clear()
    
    # Возвращаем в главное меню
    from src.bot.handlers.start import send_main_menu
    await send_main_menu(message, state=state)


# === ПРАВИЛА ===

async def rules_handler(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик кнопки правил"""
    await callback.answer()
    await state.clear()
    
    from src.bot.keyboards.keyboards import InlineKeyboardBuilder, InlineKeyboardButton
    
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(
        text=BACK_BTN,
        callback_data="back_to_menu"
    ))
    
    # Заменяем сообщение главного меню на сообщение с правилами
    try:
        await callback.message.edit_text(
            RULES_MESSAGE,
            reply_markup=keyboard.as_markup()
        )
    except:
        # Если не удалось отредактировать, отправляем новое
        await callback.message.answer(
            RULES_MESSAGE,
            reply_markup=keyboard.as_markup()
        )


async def back_to_menu_callback(callback: types.CallbackQuery, state: FSMContext):
    """возврат в главное меню"""
    await callback.answer()
    
    # Удаляем первое сообщение с информацией об объявлении, если оно есть (из "Мои объявления")
    data = await state.get_data()
    info_msg_id = data.get('my_ad_info_msg_id')
    chat_id = data.get('my_ad_chat_id', callback.message.chat.id)
    if info_msg_id:
        try:
            from src.bot.loader import bot
            await bot.delete_message(chat_id=chat_id, message_id=info_msg_id)
        except:
            pass
    
    await state.clear()
    
    # Редактируем текущее сообщение на главное меню
    from src.bot.handlers.start import get_main_menu_text
    from src.bot.keyboards.keyboards import main_menu_kb
    menu_text = await get_main_menu_text()
    try:
        await callback.message.edit_text(
            menu_text,
            parse_mode='HTML',
            reply_markup=await main_menu_kb(callback.from_user.id if hasattr(callback, 'from_user') else None)
        )
        await state.update_data(main_menu_msg_id=callback.message.message_id)
    except:
        # Если не удалось отредактировать, отправляем новое
        from src.bot.handlers.start import send_main_menu
        await send_main_menu(callback, state=state)
    
    # Удаляем предыдущие сообщения для чистоты чата (до 20 последних)
    try:
        from src.bot.loader import bot
        current_msg_id = callback.message.message_id
        for i in range(1, 21):
            try:
                msg_id_to_delete = current_msg_id - i
                if msg_id_to_delete > 0:
                    # Пытаемся удалить сообщение
                    await bot.delete_message(chat_id=callback.message.chat.id, message_id=msg_id_to_delete)
            except:
                # Если не удалось удалить (сообщение уже удалено или не существует) - продолжаем
                pass
    except:
        pass


# === АДМИНСКИЕ КОМАНДЫ ===

# Старые команды удалены - используйте /admin для доступа к админ-панели


# === КОМАНДЫ ===

async def help_command(message: types.Message, state: FSMContext):
    """Обработчик команды /help"""
    # Проверяем согласие и подписку
    from src.bot.database.methods import check_user_agreement
    from src.bot.handlers.start import check_channel_subscription
    
    agreed = await check_user_agreement(message.from_user.id)
    # is_subscribed = await check_channel_subscription(message.from_user.id)
    is_subscribed = True
    # CHANGE!!!
    
    # Если не пройдены оба этапа - удаляем сообщение
    if not agreed or not is_subscribed:
        try:
            await message.delete()
        except:
            pass
        return
    
    await state.clear()
    
    support_text = SUPPORT_MESSAGE
    
    # создаем клавиатуру
    keyboard = InlineKeyboardBuilder()
    
    # проверяем что SUPPORT_USERNAME задан
    if SUPPORT_USERNAME:
        try:
            keyboard.row(InlineKeyboardButton(
                text=WRITE_SUPPORT_BTN,
                url=f"https://t.me/{SUPPORT_USERNAME}"
            ))
        except Exception as e:
            logger.error(f"ошибка создания кнопки поддержки: {e}")
            # если ошибка - просто не добавляем кнопку
    
    keyboard.row(InlineKeyboardButton(
        text=BACK_BTN,
        callback_data="back_to_menu"
    ))
    
    # Отправляем сообщение
    await message.answer(
        support_text,
        parse_mode='HTML',
        reply_markup=keyboard.as_markup()
    )


async def rules_command(message: types.Message, state: FSMContext):
    """Обработчик команды /rules"""
    # Проверяем согласие и подписку
    from src.bot.database.methods import check_user_agreement
    from src.bot.handlers.start import check_channel_subscription
    
    agreed = await check_user_agreement(message.from_user.id)
    # is_subscribed = await check_channel_subscription(message.from_user.id)
    is_subscribed = True
    # CHANGE !!!
    
    # Если не пройдены оба этапа - удаляем сообщение
    if not agreed or not is_subscribed:
        try:
            await message.delete()
        except:
            pass
        return
    
    await state.clear()
    
    from src.bot.keyboards.keyboards import InlineKeyboardBuilder, InlineKeyboardButton
    
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(
        text=BACK_BTN,
        callback_data="back_to_menu"
    ))
    
    # Отправляем сообщение
    await message.answer(
        RULES_MESSAGE,
        reply_markup=keyboard.as_markup()
    )


async def cancel_command(message: types.Message, state: FSMContext):
    """Обработчик команды /cancel"""
    # Проверяем согласие и подписку
    from src.bot.database.methods import check_user_agreement
    from src.bot.handlers.start import check_channel_subscription, send_main_menu
    
    agreed = await check_user_agreement(message.from_user.id)
    # is_subscribed = await check_channel_subscription(message.from_user.id)
    is_subscribed = True
    # CHANGE!!!
    
    # Если не пройдены оба этапа - удаляем сообщение
    if not agreed or not is_subscribed:
        try:
            await message.delete()
        except:
            pass
        return
    
    # Очищаем состояние
    await state.clear()
    
    # Отправляем главное меню
    await send_main_menu(message, state=state)


async def oferta_command(message: types.Message, state: FSMContext):
    """Обработчик команды /oferta"""
    # Проверяем согласие и подписку
    from src.bot.database.methods import check_user_agreement
    from src.bot.handlers.start import check_channel_subscription
    
    agreed = await check_user_agreement(message.from_user.id)
    # is_subscribed = await check_channel_subscription(message.from_user.id)
    is_subscribed = True
    # CHANGE!!!
    
    # Если не пройдены оба этапа - удаляем сообщение
    if not agreed or not is_subscribed:
        try:
            await message.delete()
        except:
            pass
        return
    
    oferta_text = """📄 ПУБЛИЧНАЯ ОФЕРТА
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
7.3. Актуальная версия оферты размещается в боте или канале."""
    
    from src.bot.keyboards.keyboards import InlineKeyboardBuilder, InlineKeyboardButton
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(
        text=BACK_BTN,
        callback_data="back_to_menu"
    ))
    
    await message.answer(
        oferta_text,
        parse_mode='HTML',
        reply_markup=keyboard.as_markup()
    )


# === РЕГИСТРАЦИЯ ОБРАБОТЧИКОВ ===

def register_support_handlers(dp: Dispatcher):
    """Регистрация обработчиков поддержки и админских команд"""
    from src.bot.database.states import SupportState
    from aiogram.filters import StateFilter
    
    # Команды
    dp.message.register(help_command, Command("help"))
    dp.message.register(rules_command, Command("rules"))
    dp.message.register(cancel_command, Command("cancel"))
    dp.message.register(oferta_command, Command("oferta"))
    
    # Поддержка и правила (callback)
    dp.callback_query.register(support_handler, F.data == "main_menu:support")
    dp.callback_query.register(rules_handler, F.data == "main_menu:rules")
    
    # Обработка сообщений в поддержку
    dp.message.register(support_message_handler, StateFilter(SupportState.message), F.text)
    
    # Возврат в меню
    dp.callback_query.register(back_to_menu_callback, F.data == "back_to_menu")
    
    # Админские команды перенесены в админ-панель (/admin)
