"""
Handler: админские команды (/stats, /logs, /ban, /unban, /moderator).
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.filters import Command
from sqlalchemy import select, func
from pathlib import Path

from src.logging import get_logger
from src.config import settings
from src.kit.database.service import database_service
from src.models import Ad, AdStatus, User, Blacklist
from src.enums import UserRole
from src.bot.keyboards import back_kb

router = Router()
log = get_logger()


def _is_admin(tg_user_id: int) -> bool:
    """Проверить, является ли пользователь администратором"""
    return tg_user_id in settings.ADMIN_IDS


def _is_developer(tg_user_id: int) -> bool:
    """Проверить, является ли пользователь разработчиком"""
    return tg_user_id in settings.DEVELOPER_IDS


# ===========================
#  Статистика
# ===========================

@router.message(Command("stats"))
async def cmd_stats(message: Message):
    if not _is_admin(message.from_user.id):
        await message.answer("❌ Нет прав")
        return

    async with database_service.get_session() as session:
        result = await session.execute(select(Ad.status, func.count(Ad.id)).group_by(Ad.status))
        ads_by_status = {row[0]: row[1] for row in result.all()}

        users_count = await session.scalar(select(func.count(User.id))) or 0
        banned_count = await session.scalar(select(func.count(Blacklist.id))) or 0
        pending = ads_by_status.get(AdStatus.pending.value, 0)
        approved = ads_by_status.get(AdStatus.approved.value, 0)
        rejected = ads_by_status.get(AdStatus.rejected.value, 0)
        total = sum(ads_by_status.values())

    text = (
        f"📊 <b>Статистика</b>\n\n"
        f"👤 Пользователей: {users_count}\n"
        f"🚫 Забанено: {banned_count}\n"
        f"📦 Всего объявлений: {total}\n"
        f"   🕒 На модерации: {pending}\n"
        f"   ✅ Одобрено: {approved}\n"
        f"   ❌ Отклонено: {rejected}\n"
    )

    await message.answer(text, parse_mode="html")


# ===========================
#  Бан / разбан
# ===========================

@router.message(Command("ban"))
async def cmd_ban(message: Message):
    if not _is_admin(message.from_user.id):
        await message.answer("❌ Нет прав")
        return

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Использование: /ban <tg_user_id или @username>")
        return

    target = args[1].strip()
    try:
        tg_id = int(target)
    except ValueError:
        # Поиск по username
        username = target.lstrip("@")
        async with database_service.get_session() as session:
            result = await session.execute(
                select(User).where(func.lower(User.username) == username.lower())
            )
            user = result.scalar_one_or_none()
            if not user:
                await message.answer(f"❌ Пользователь @{username} не найден")
                return
            tg_id = user.tg_user_id

    async with database_service.get_session() as session:
        existing = await session.execute(
            select(Blacklist).where(Blacklist.tg_user_id == tg_id)
        )
        if not existing.scalar_one_or_none():
            session.add(Blacklist(tg_user_id=tg_id))
            await session.commit()
            log.info(f"User {tg_id} banned by admin {message.from_user.id}")

    await message.answer(f"✅ Пользователь {tg_id} забанен.")


@router.message(Command("unban"))
async def cmd_unban(message: Message):
    if not _is_admin(message.from_user.id):
        await message.answer("❌ Нет прав")
        return

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Использование: /unban <tg_user_id>")
        return

    tg_id = args[1].strip()
    try:
        tg_id = int(tg_id)
    except ValueError:
        await message.answer("❌ Укажите числовой ID")
        return

    async with database_service.get_session() as session:
        result = await session.execute(
            select(Blacklist).where(Blacklist.tg_user_id == tg_id)
        )
        entry = result.scalar_one_or_none()
        if entry:
            await session.delete(entry)
            await session.commit()
            log.info(f"User {tg_id} unbanned by admin {message.from_user.id}")
            await message.answer(f"✅ Пользователь {tg_id} разбанен.")
        else:
            await message.answer(f"❌ Пользователь {tg_id} не найден в чёрном списке.")


# ===========================
#  Назначить модератора
# ===========================

@router.message(Command("moderator"))
async def cmd_moderator(message: Message):
    if not _is_admin(message.from_user.id):
        await message.answer("❌ Нет прав")
        return

    args = message.text.split(maxsplit=2)
    if len(args) < 2:
        await message.answer("Использование: /moderator <tg_user_id> [on|off]")
        return

    try:
        tg_id = int(args[1])
    except ValueError:
        await message.answer("❌ Укажите числовой ID")
        return

    set_role = True
    if len(args) > 2:
        set_role = args[2].lower() == "on"

    async with database_service.get_session() as session:
        result = await session.execute(select(User).where(User.tg_user_id == tg_id))
        user = result.scalar_one_or_none()
        if not user:
            await message.answer(f"❌ Пользователь с TG ID {tg_id} не найден")
            return

        user.role = UserRole.MODERATOR if set_role else UserRole.USER
        await session.commit()
        log.info(f"User {tg_id} moderator={set_role} by admin {message.from_user.id}")

    await message.answer(f"✅ Пользователь {tg_id}: модератор={'вкл' if set_role else 'выкл'}")


# ===========================
#  Логи
# ===========================

@router.message(Command("logs"))
async def cmd_logs(message: Message):
    if not _is_admin(message.from_user.id):
        await message.answer("❌ Нет прав")
        return

    log_dir = Path("logs")
    if not log_dir.exists():
        await message.answer("❌ Папка logs не найдена")
        return

    log_files = sorted(log_dir.glob("*.log"))
    if not log_files:
        await message.answer("📭 Логи не найдены")
        return

    await message.answer(f"📦 Отправляю {len(log_files)} файлов...")
    sent = 0
    for f in log_files:
        try:
            if f.stat().st_size > 0:
                document = FSInputFile(str(f))
                await message.answer_document(document=document, caption=f"📄 {f.name}")
                sent += 1
        except Exception as e:
            await message.answer(f"❌ Ошибка с {f.name}: {e}")

    await message.answer(f"✅ Отправлено {sent} файлов")
