from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command

from src.logging import get_logger
from src.bot.keyboards import main_menu_kb
from src.bot.texts import START_MESSAGE

router = Router()
log = get_logger()


@router.message(Command("help"))
async def cmd_help(message: Message):
    text = (
        "/start — главное меню\n"
        "/cancel — отменить текущее действие\n"
        "/help — эта справка\n"
        "/rules — правила барахолки\n"
        "/stats — статистика (админы)\n"
        "/ban /unban — управление баном (админы)\n"
        "/moderator — назначить модератора (админы)\n"
        "/logs — логи (админы)\n"
    )
    await message.answer(text, reply_markup=await main_menu_kb(message.from_user.id))


@router.message(Command("rules"))
async def cmd_rules(message: Message):
    from src.bot.texts import RULES_MESSAGE
    await message.answer(RULES_MESSAGE, reply_markup=await main_menu_kb(message.from_user.id))


@router.message()
async def echo_fallback(message: Message):
    """Ловит всё, что не обработали другие хендлеры."""
    from src.bot.texts import RULES_MESSAGE

    await message.answer(
        "Используй кнопки меню 👇",
        reply_markup=await main_menu_kb(message.from_user.id)
    )
