"""
админские команды
"""

from aiogram import Dispatcher, types, F
from aiogram.filters import Command
from pathlib import Path
from aiogram.types import FSInputFile

from src.bot.settings.settings import DEVELOPER_IDS, ADMIN_IDS
from src.bot.database.methods import is_moderator


async def send_logs_command(message: types.Message):
    """команда /logs - отправка всех логов админам (только для ADMIN_IDS)"""
    # проверка прав (только админы)
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ нет прав")
        return
    
    log_dir = Path("logs")
    if not log_dir.exists():
        await message.answer("❌ папка logs не найдена")
        return
    
    # собираем все .log файлы
    log_files = list(log_dir.glob("*.log"))
    
    if not log_files:
        await message.answer("📭 файлы логов не найдены")
        return
    
    await message.answer(f"📦 отправляю {len(log_files)} файлов...")
    
    # отправляем каждый файл
    sent = 0
    for log_file in log_files:
        try:
            if log_file.stat().st_size > 0:  # только непустые
                document = FSInputFile(str(log_file))
                await message.answer_document(
                    document=document,
                    caption=f"📄 {log_file.name}"
                )
                sent += 1
        except Exception as e:
            await message.answer(f"❌ ошибка с {log_file.name}: {e}")
    
    await message.answer(f"✅ отправлено {sent} файлов")


def register_admin_handlers(dp: Dispatcher):
    """регистрация админских команд"""
    dp.message.register(send_logs_command, Command("logs"))
