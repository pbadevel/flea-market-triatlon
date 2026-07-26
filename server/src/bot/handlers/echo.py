from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command

from src.logging import get_logger
from src.bot.keyboards import main_menu_kb
from src.bot.texts import START_MESSAGE, RULES_MESSAGE

router = Router()
log = get_logger()

OFERTA_MESSAGE = """<b>ОФЕРТА</b>

1. Настоящее соглашение является публичной офертой.

2. Размещая объявление через бота, Пользователь подтверждает согласие на обработку персональных данных в соответствии с 152-ФЗ.

3. Администрация не несёт ответственности за сделки между пользователями.

4. Запрещается размещение объявлений, нарушающих законодательство РФ.

5. Администрация оставляет за собой право удалять объявления без объяснения причин."""


@router.message(Command("help"))
async def cmd_help(message: Message):
    text = (
        "/start — главное меню\n"
        "/cancel — отменить текущее действие\n"
        "/help — эта справка\n"
        "/rules — правила барахолки\n"
        "/oferta — оферта\n"
        "/stats — статистика (админы)\n"
        "/admin — админ-панель (админы/модераторы)\n"
        "/ban /unban — управление баном (админы)\n"
        "/moderator — назначить модератора (админы)\n"
        "/logs — логи (админы)\n"
    )
    await message.answer(text, reply_markup=await main_menu_kb(message.from_user.id))


@router.message(Command("rules"))
async def cmd_rules(message: Message):
    await message.answer(RULES_MESSAGE, reply_markup=await main_menu_kb(message.from_user.id))


@router.message(Command("oferta"))
async def cmd_oferta(message: Message):
    await message.answer(OFERTA_MESSAGE, reply_markup=await main_menu_kb(message.from_user.id), parse_mode="html")


@router.message()
async def echo_fallback(message: Message):
    """Catches everything not handled by other handlers."""
    await message.answer(
        "Используй кнопки меню",
        reply_markup=await main_menu_kb(message.from_user.id)
    )
