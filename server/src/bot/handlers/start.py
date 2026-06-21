"""
Handler: /start — главное меню + deeplink авторизация / модерация.
"""

from aiogram import Router
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest
import httpx

from src.config import settings
from src.logging import get_logger
from src.kit.database.service import database_service
from src.services import user_service

from src.bot.keyboards import main_menu_kb, back_kb
from src.bot.texts import START_MESSAGE, RULES_MESSAGE, SUPPORT_MESSAGE
from src.bot.handlers.moderation import proceed_promote_reject

router = Router()
log = get_logger()


# ===========================
#  /start
# ===========================

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, command: CommandObject):
    """Обработка /start — главное меню или deeplink."""
    await state.clear()

    # Deeplink от сайта
    if command.args:
        if command.args.startswith("auth_"):
            await _proceed_auth(command.args, message)
            return
        elif command.args.startswith("promoteReject_"):
            await proceed_promote_reject(command.args, message, state)
            return

    # Обычный /start — создаём/обновляем пользователя, показываем меню
    await _show_main_menu(message)


@router.callback_query(lambda c: c.data == "menu:main")
async def callback_main_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    try:
        await callback.message.edit_text(
            START_MESSAGE,
            reply_markup=await main_menu_kb(callback.from_user.id)
        )
    except TelegramBadRequest:
        await callback.message.answer(
            START_MESSAGE,
            reply_markup=await main_menu_kb(callback.from_user.id)
        )
    await callback.answer()


@router.callback_query(lambda c: c.data == "menu:rules")
async def callback_rules(callback: CallbackQuery):
    try:
        await callback.message.edit_text(RULES_MESSAGE, reply_markup=back_kb("menu:main"))
    except TelegramBadRequest:
        await callback.message.answer(RULES_MESSAGE, reply_markup=back_kb("menu:main"))
    await callback.answer()


@router.callback_query(lambda c: c.data == "menu:support")
async def callback_support(callback: CallbackQuery):
    text = SUPPORT_MESSAGE
    if settings.SUPPORT_USERNAME:
        text += f"\n\n👤 Администратор: @{settings.SUPPORT_USERNAME}"
    try:
        await callback.message.edit_text(text, reply_markup=back_kb("menu:main"))
    except TelegramBadRequest:
        await callback.message.answer(text, reply_markup=back_kb("menu:main"))
    await callback.answer()


@router.callback_query(lambda c: c.data == "noop")
async def callback_noop(callback: CallbackQuery):
    await callback.answer()


# ===========================
#  Создание / обновление пользователя
# ===========================

async def _resolve_user(message: Message):
    """Найти или создать пользователя в БД."""
    tg_user = message.from_user
    if not tg_user:
        return None

    async with database_service.get_session() as session:
        user = await user_service.get_or_create_by_tg(session, tg_user)
        return user


async def _show_main_menu(message: Message):
    """Показать главное меню."""
    user = await _resolve_user(message)

    if user and user.is_banned:
        await message.answer("⛔ Ваш аккаунт заблокирован. Обратитесь к администрации.")
        return

    await message.answer(
        START_MESSAGE,
        reply_markup=await main_menu_kb(message.from_user.id)
    )


# ===========================
#  Deeplink авторизация
# ===========================

async def _proceed_auth(deep_link_param: str, message: Message):
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
        log.error(f"Auth deeplink error: {e}")
        await message.answer("❌ Произошла ошибка. Попробуйте ещё раз.")
