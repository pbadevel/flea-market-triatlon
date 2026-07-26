"""
Handler: полноценная админ-панель в боте.
/poRT из barakholka/handlers/admin_panel.py.
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest
from sqlalchemy import select, func

from src.config import settings
from src.logging import get_logger
from src.kit.database.service import database_service
from src.models import Ad, AdStatus, User, Review, Blacklist
from src.enums import UserRole
from src.bot.states import AdminPanelState

router = Router()
log = get_logger()


def _is_admin(user_id: int) -> bool:
    return user_id in settings.ADMIN_IDS


async def _is_moderator_or_admin(user_id: int) -> bool:
    if user_id in settings.ADMIN_IDS:
        return True
    async with database_service.get_session() as session:
        result = await session.execute(select(User).where(User.tg_user_id == user_id))
        user = result.scalar_one_or_none()
        return user is not None and user.role in (UserRole.MODERATOR, UserRole.ADMIN)


# ===========================
#  /admin — главное меню
# ===========================

@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    if not await _is_moderator_or_admin(message.from_user.id):
        return
    await state.clear()
    text, kb = await _admin_menu()
    await message.answer(text, parse_mode="html", reply_markup=kb.as_markup())
    try:
        await message.delete()
    except Exception:
        pass


async def _admin_menu():
    async with database_service.get_session() as session:
        users_count = await session.scalar(select(func.count(User.id))) or 0
        active_ads = await session.scalar(
            select(func.count(Ad.id)).where(Ad.status == AdStatus.approved)
        ) or 0
        pending_ads = await session.scalar(
            select(func.count(Ad.id)).where(Ad.status == AdStatus.pending)
        ) or 0
        mod_count = await session.scalar(
            select(func.count(User.id)).where(User.role == UserRole.MODERATOR)
        ) or 0

    text = (
        f"<b>АДМИН-ПАНЕЛЬ</b>\n\n"
        f"Пользователей: {users_count}\n"
        f"Активных объявлений: {active_ads}\n"
        f"На модерации: {pending_ads}\n"
        f"Модераторов: {mod_count}\n\n"
        "Выберите раздел:"
    )
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="Пользователи", callback_data="adm:users"))
    kb.row(InlineKeyboardButton(text="Доверенный продавец", callback_data="adm:trusted"))
    kb.row(InlineKeyboardButton(text="Статистика", callback_data="adm:stats"))
    kb.row(InlineKeyboardButton(text="Логи", callback_data="adm:logs"))
    return text, kb


@router.callback_query(lambda c: c.data == "adm:back")
async def admin_back(callback: CallbackQuery, state: FSMContext):
    if not await _is_moderator_or_admin(callback.from_user.id):
        return
    await state.clear()
    text, kb = await _admin_menu()
    try:
        await callback.message.edit_text(text, parse_mode="html", reply_markup=kb.as_markup())
    except TelegramBadRequest:
        await callback.message.answer(text, parse_mode="html", reply_markup=kb.as_markup())
    await callback.answer()


# ===========================
#  Управление пользователями
# ===========================

@router.callback_query(lambda c: c.data == "adm:users")
async def admin_users(callback: CallbackQuery):
    if not await _is_moderator_or_admin(callback.from_user.id):
        return
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="Найти по ID", callback_data="adm:user_find_id"))
    kb.row(InlineKeyboardButton(text="Найти по username", callback_data="adm:user_find_name"))
    kb.row(InlineKeyboardButton(text="Забаненные", callback_data="adm:user_banned"))
    kb.row(InlineKeyboardButton(text="Назначить модератора", callback_data="adm:set_mod"))
    kb.row(InlineKeyboardButton(text="Назначить админа", callback_data="adm:set_admin"))
    kb.row(InlineKeyboardButton(text="Назад", callback_data="adm:back"))
    try:
        await callback.message.edit_text("Управление пользователями:", reply_markup=kb.as_markup())
    except TelegramBadRequest:
        await callback.message.answer("Управление пользователями:", reply_markup=kb.as_markup())
    await callback.answer()


@router.callback_query(lambda c: c.data == "adm:user_find_id")
async def admin_user_find_id(callback: CallbackQuery, state: FSMContext):
    if not await _is_moderator_or_admin(callback.from_user.id):
        return
    await state.set_state(AdminPanelState.wait_user_id)
    try:
        await callback.message.edit_text("Введите Telegram ID пользователя:")
    except TelegramBadRequest:
        pass
    await callback.answer()


@router.message(AdminPanelState.wait_user_id)
async def process_user_id(message: Message, state: FSMContext):
    if not await _is_moderator_or_admin(message.from_user.id):
        return
    try:
        tg_id = int(message.text.strip())
    except ValueError:
        await message.answer("Введите числовой ID.")
        return

    async with database_service.get_session() as session:
        result = await session.execute(select(User).where(User.tg_user_id == tg_id))
        user = result.scalar_one_or_none()

    if not user:
        await message.answer(f"Пользователь {tg_id} не найден.")
        await state.clear()
        return

    text = _format_user(user)
    kb = _user_action_kb(user)
    await message.answer(text, parse_mode="html", reply_markup=kb.as_markup())
    await state.clear()


@router.callback_query(lambda c: c.data == "adm:user_find_name")
async def admin_user_find_name(callback: CallbackQuery, state: FSMContext):
    if not await _is_moderator_or_admin(callback.from_user.id):
        return
    await state.set_state(AdminPanelState.wait_username)
    try:
        await callback.message.edit_text("Введите username (без @):")
    except TelegramBadRequest:
        pass
    await callback.answer()


@router.message(AdminPanelState.wait_username)
async def process_username(message: Message, state: FSMContext):
    if not await _is_moderator_or_admin(message.from_user.id):
        return
    username = message.text.strip().lstrip("@")

    async with database_service.get_session() as session:
        result = await session.execute(
            select(User).where(func.lower(User.username) == username.lower())
        )
        user = result.scalar_one_or_none()

    if not user:
        await message.answer(f"@{username} не найден.")
        await state.clear()
        return

    text = _format_user(user)
    kb = _user_action_kb(user)
    await message.answer(text, parse_mode="html", reply_markup=kb.as_markup())
    await state.clear()


@router.callback_query(lambda c: c.data == "adm:user_banned")
async def admin_user_banned(callback: CallbackQuery):
    if not await _is_moderator_or_admin(callback.from_user.id):
        return
    async with database_service.get_session() as session:
        result = await session.execute(
            select(Blacklist).order_by(Blacklist.created_at.desc()).limit(20)
        )
        bans = result.scalars().all()

    if not bans:
        await callback.answer("Нет забаненных пользователей", show_alert=True)
        return

    text = "Забаненные пользователи:\n\n"
    for b in bans:
        text += f"ID: {b.tg_user_id}\n"

    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="Назад", callback_data="adm:users"))
    try:
        await callback.message.edit_text(text, reply_markup=kb.as_markup())
    except TelegramBadRequest:
        await callback.message.answer(text, reply_markup=kb.as_markup())
    await callback.answer()


@router.callback_query(lambda c: c.data == "adm:set_mod")
async def admin_set_mod(callback: CallbackQuery, state: FSMContext):
    if not await _is_admin(callback.from_user.id):
        await callback.answer("Только администраторы", show_alert=True)
        return
    await state.set_state(AdminPanelState.wait_mod_id)
    try:
        await callback.message.edit_text("Введите TG ID для назначения модератором:")
    except TelegramBadRequest:
        pass
    await callback.answer()


@router.message(AdminPanelState.wait_mod_id)
async def process_set_mod(message: Message, state: FSMContext):
    if not await _is_admin(message.from_user.id):
        return
    try:
        tg_id = int(message.text.strip())
    except ValueError:
        await message.answer("Введите числовой ID.")
        return

    async with database_service.get_session() as session:
        result = await session.execute(select(User).where(User.tg_user_id == tg_id))
        user = result.scalar_one_or_none()
        if not user:
            await message.answer(f"Пользователь {tg_id} не найден.")
            await state.clear()
            return
        user.role = UserRole.MODERATOR
        await session.commit()

    await message.answer(f"Пользователь {tg_id} назначен модератором.")
    await state.clear()


@router.callback_query(lambda c: c.data == "adm:set_admin")
async def admin_set_admin(callback: CallbackQuery, state: FSMContext):
    if not await _is_admin(callback.from_user.id):
        await callback.answer("Только администраторы", show_alert=True)
        return
    await state.set_state(AdminPanelState.wait_admin_id)
    try:
        await callback.message.edit_text("Введите TG ID для назначения администратором:")
    except TelegramBadRequest:
        pass
    await callback.answer()


@router.message(AdminPanelState.wait_admin_id)
async def process_set_admin(message: Message, state: FSMContext):
    if not await _is_admin(message.from_user.id):
        return
    try:
        tg_id = int(message.text.strip())
    except ValueError:
        await message.answer("Введите числовой ID.")
        return

    async with database_service.get_session() as session:
        result = await session.execute(select(User).where(User.tg_user_id == tg_id))
        user = result.scalar_one_or_none()
        if not user:
            await message.answer(f"Пользователь {tg_id} не найден.")
            await state.clear()
            return
        user.role = UserRole.ADMIN
        await session.commit()

    await message.answer(f"Пользователь {tg_id} назначен администратором.")
    await state.clear()


# ===========================
#  Доверенный продавец
# ===========================

@router.callback_query(lambda c: c.data == "adm:trusted")
async def admin_trusted(callback: CallbackQuery, state: FSMContext):
    if not await _is_admin(callback.from_user.id):
        return
    await state.set_state(AdminPanelState.wait_trusted_id)
    try:
        await callback.message.edit_text(
            "Введите TG ID пользователя:\n"
            "(повторный ввод снимет статус)"
        )
    except TelegramBadRequest:
        pass
    await callback.answer()


@router.message(AdminPanelState.wait_trusted_id)
async def process_trusted(message: Message, state: FSMContext):
    if not await _is_admin(message.from_user.id):
        return
    try:
        tg_id = int(message.text.strip())
    except ValueError:
        await message.answer("Введите числовой ID.")
        return

    async with database_service.get_session() as session:
        result = await session.execute(select(User).where(User.tg_user_id == tg_id))
        user = result.scalar_one_or_none()
        if not user:
            await message.answer(f"Пользователь {tg_id} не найден.")
            await state.clear()
            return
        user.is_trusted_seller = not user.is_trusted_seller
        await session.commit()

    status = "установлен" if user.is_trusted_seller else "снят"
    await message.answer(f"Статус 'Доверенный продавец' {status} для пользователя {tg_id}.")
    await state.clear()


# ===========================
#  Статистика
# ===========================

@router.callback_query(lambda c: c.data == "adm:stats")
async def admin_stats(callback: CallbackQuery):
    if not await _is_moderator_or_admin(callback.from_user.id):
        return

    async with database_service.get_session() as session:
        users_count = await session.scalar(select(func.count(User.id))) or 0
        total_ads = await session.scalar(select(func.count(Ad.id))) or 0
        pending = await session.scalar(select(func.count(Ad.id)).where(Ad.status == AdStatus.pending)) or 0
        approved = await session.scalar(select(func.count(Ad.id)).where(Ad.status == AdStatus.approved)) or 0
        rejected = await session.scalar(select(func.count(Ad.id)).where(Ad.status == AdStatus.rejected)) or 0
        sold = await session.scalar(select(func.count(Ad.id)).where(Ad.status == AdStatus.sold)) or 0
        avg_rating = await session.scalar(select(func.avg(Review.rating))) or 0
        reviews_count = await session.scalar(select(func.count(Review.id))) or 0
        banned = await session.scalar(select(func.count(Blacklist.id))) or 0
        trusted = await session.scalar(select(func.count(User.id)).where(User.is_trusted_seller == True)) or 0

    text = (
        f"<b>Статистика</b>\n\n"
        f"Пользователей: {users_count}\n"
        f"Забанено: {banned}\n"
        f"Доверенных: {trusted}\n\n"
        f"Всего объявлений: {total_ads}\n"
        f"  На модерации: {pending}\n"
        f"  Одобрено: {approved}\n"
        f"  Отклонено: {rejected}\n"
        f"  Продано: {sold}\n\n"
        f"Отзывов: {reviews_count}\n"
        f"Средняя оценка: {round(float(avg_rating), 1) if avg_rating else '-'}\n"
    )
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="Назад", callback_data="adm:back"))
    try:
        await callback.message.edit_text(text, parse_mode="html", reply_markup=kb.as_markup())
    except TelegramBadRequest:
        await callback.message.answer(text, parse_mode="html", reply_markup=kb.as_markup())
    await callback.answer()


# ===========================
#  Логи
# ===========================

@router.callback_query(lambda c: c.data == "adm:logs")
async def admin_logs(callback: CallbackQuery):
    if not await _is_admin(callback.from_user.id):
        return

    from pathlib import Path
    log_dir = Path("logs")
    if not log_dir.exists():
        await callback.answer("Папка logs не найдена", show_alert=True)
        return

    log_files = sorted(log_dir.glob("*.log"))
    if not log_files:
        await callback.answer("Логи не найдены", show_alert=True)
        return

    sent = 0
    for f in log_files:
        try:
            if f.stat().st_size > 0:
                from aiogram.types import FSInputFile
                document = FSInputFile(str(f))
                await callback.message.answer_document(document=document, caption=f"{f.name}")
                sent += 1
        except Exception as e:
            await callback.message.answer(f"Ошибка с {f.name}: {e}")

    await callback.message.answer(f"Отправлено {sent} файлов логов.")
    await callback.answer()


# ===========================
#  Helpers
# ===========================

def _format_user(user: User) -> str:
    text = f"<b>Пользователь</b>\n\n"
    text += f"ID: {user.id}\n"
    text += f"TG ID: {user.tg_user_id or '-'}\n"
    text += f"Username: @{user.username or '-'}\n"
    text += f"Имя: {user.first_name or '-'} {user.last_name or ''}\n"
    text += f"Роль: {user.role.value}\n"
    text += f"Забанен: {'Да' if user.is_banned else 'Нет'}\n"
    text += f"Доверенный: {'Да' if user.is_trusted_seller else 'Нет'}\n"
    text += f"Согласие 152-ФЗ: {'Да' if user.agreed_to_terms else 'Нет'}\n"
    text += f"Дата регистрации: {user.created_at.strftime('%d.%m.%Y') if user.created_at else '-'}\n"
    return text


def _user_action_kb(user: User) -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()

    # Ban / Unban
    if user.is_banned:
        kb.row(InlineKeyboardButton(text="Разбанить", callback_data=f"adm:unban:{user.tg_user_id}"))
    else:
        kb.row(InlineKeyboardButton(text="Забанить", callback_data=f"adm:ban:{user.tg_user_id}"))

    # Trusted seller toggle
    if user.is_trusted_seller:
        kb.row(InlineKeyboardButton(text="Снять доверенного", callback_data=f"adm:trust_toggle:{user.tg_user_id}"))
    else:
        kb.row(InlineKeyboardButton(text="Сделать доверенным", callback_data=f"adm:trust_toggle:{user.tg_user_id}"))

    kb.row(InlineKeyboardButton(text="Назад", callback_data="adm:users"))
    return kb


@router.callback_query(lambda c: c.data.startswith("adm:ban:"))
async def admin_ban(callback: CallbackQuery):
    if not await _is_moderator_or_admin(callback.from_user.id):
        return
    tg_id = int(callback.data.split(":")[2])
    async with database_service.get_session() as session:
        existing = await session.execute(select(Blacklist).where(Blacklist.tg_user_id == tg_id))
        if not existing.scalar_one_or_none():
            session.add(Blacklist(tg_user_id=tg_id))
            await session.commit()
    from src.bot.middlewares.ban import invalidate_banned_cache
    invalidate_banned_cache()
    await callback.answer(f"Пользователь {tg_id} забанен.", show_alert=True)


@router.callback_query(lambda c: c.data.startswith("adm:unban:"))
async def admin_unban(callback: CallbackQuery):
    if not await _is_moderator_or_admin(callback.from_user.id):
        return
    tg_id = int(callback.data.split(":")[2])
    async with database_service.get_session() as session:
        result = await session.execute(select(Blacklist).where(Blacklist.tg_user_id == tg_id))
        entry = result.scalar_one_or_none()
        if entry:
            await session.delete(entry)
            await session.commit()
    from src.bot.middlewares.ban import invalidate_banned_cache
    invalidate_banned_cache()
    await callback.answer(f"Пользователь {tg_id} разбанен.", show_alert=True)


@router.callback_query(lambda c: c.data.startswith("adm:trust_toggle:"))
async def admin_trust_toggle(callback: CallbackQuery):
    if not await _is_admin(callback.from_user.id):
        await callback.answer("Только администраторы", show_alert=True)
        return
    tg_id = int(callback.data.split(":")[2])
    async with database_service.get_session() as session:
        result = await session.execute(select(User).where(User.tg_user_id == tg_id))
        user = result.scalar_one_or_none()
        if not user:
            await callback.answer("Пользователь не найден", show_alert=True)
            return
        user.is_trusted_seller = not user.is_trusted_seller
        await session.commit()
    status = "установлен" if user.is_trusted_seller else "снят"
    await callback.answer(f"Статус доверенного {status}", show_alert=True)
