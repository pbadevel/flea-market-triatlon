from aiogram import Router, F, Bot
from aiogram.types import User as TGUser, CallbackQuery, Message
from aiogram.filters import Command
from aiogram.enums import ChatAction

from src.kit.database.postgres import AsyncSessionMaker

from src.models import Ad, AdStatus, User
from src.repositories.ads import AdRepository
from src.services import ad_service
from src.kit.database.service import database_service
from src.bot.services import send_ad_to_channel, notify_user_ad_approved, notify_user_ad_rejected
from src.logging import get_logger
from src.enums import UserRole
from typing import cast

router = Router()
log = get_logger()


@router.callback_query(F.data.startswith("moderate:"))
async def handle_moderation_callback(callback: CallbackQuery, bot: Bot):
    """Handle moderation buttons (approve/reject)"""
    await callback.answer()
    
    # Parse callback data: moderate:approve:123 or moderate:reject:123
    data = cast(str, callback.data)
    parts = data.split(":")
    msg = cast(Message, callback.message)
    if len(parts) != 3:
        await msg.edit_text("❌ Ошибка формата данных")
        return
    
    _, action, ad_id_str = parts
    
    try:
        ad_id = int(ad_id_str)
    except ValueError:
        await msg.edit_text("❌ Неверный ID объявления")
        return
    
    # Check if user is moderator
    async with database_service.get_session() as session:
        tg_user = callback.from_user
        
        # Find user in DB
        from src.repositories.users import UserRepository
        user_repo = UserRepository(session)
        user = await user_repo.get_by_tg_id(tg_user.id)
        
        if not user or not user.role == UserRole.USER:
            await callback.answer("⛔ У вас нет прав модератора", show_alert=True)
            return
        
        # Get ad
        ad = await ad_service.get_ad_for_moderation(session, ad_id)
        
        if not ad:
            await msg.edit_text("❌ Объявление не найдено")
            return
        
        if ad.status != AdStatus.pending.value:
            await msg.edit_text(f"ℹ️ Объявление уже обработано (статус: {ad.status})")
            return
        
        # Moderate
        if action == "approve":
            # Send to channel
            channel_message_id = await send_ad_to_channel(bot, ad)
            
            await ad_service.moderate_ad(
                session=session,
                ad_id=ad_id,
                action="approve",
                channel_message_id=channel_message_id,
            )
            
            await msg.edit_text(
                f"✅ Объявление #{ad_id} одобрено и опубликовано в канале"
            )
            
            # Notify user
            await notify_user_ad_approved(bot, ad)
            
        elif action == "reject":
            await ad_service.moderate_ad(
                session=session,
                ad_id=ad_id,
                action="reject",
                rejection_reason="Отклонено модератором",
            )
            
            await msg.edit_text(
                f"❌ Объявление #{ad_id} отклонено"
            )
            
            # Notify user
            await notify_user_ad_rejected(bot, ad, "Отклонено модератором")
        
        await session.commit()


@router.message(Command("pending"))
async def cmd_pending(message: Message, bot: Bot):
    """Show pending ads for moderation (admin command)"""
    async with database_service.get_session() as session:
        # Check if user is moderator
        from src.repositories.users import UserRepository
        user_repo = UserRepository(session)
        tg_user = cast(TGUser, message.from_user)
        user = await user_repo.get_by_tg_id(tg_user.id)
        
        if not user or not user.role == UserRole.USER:
            await message.answer("⛔ У вас нет прав модератора")
            return
        
        # Get pending ads
        repository = AdRepository(session)
        ads, total = await repository.get_pending_ads(limit=5, page=1)
        
        if not ads:
            await message.answer("✅ Нет объявлений на модерации")
            return
        
        await message.answer(f"📋 Объявлений на модерации: {total}")
        
        for ad in ads:
            await send_ad_for_moderation(bot, message.chat.id, ad)


async def send_ad_for_moderation(bot: Bot, chat_id: int, ad: Ad):
    """Send ad to moderator chat with approve/reject buttons"""
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import BufferedInputFile
    
    # Build message
    text = f"""
🆕 <b>Новое объявление на модерации</b>

📝 <b>{ad.title}</b>
💰 Цена: {ad.price:,} ₽
📍 Город: {ad.city}
🏷 Категория: {ad.category}
{f'📏 Размер: {ad.size}' if ad.size else ''}
📦 Состояние: {ad.condition}

{ad.description or ''}

👤 Продавец: @{ad.seller.username or 'не указан'} (ID: {ad.seller.id})
🆔 ID объявления: {ad.id}
"""
    
    # Build keyboard
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Одобрить", callback_data=f"moderate:approve:{ad.id}")
    builder.button(text="❌ Отклонить", callback_data=f"moderate:reject:{ad.id}")
    builder.adjust(2)
    
    # Send with photo if available
    if ad.photos:
        photo = ad.photos[0]
        if photo.file_id:
            await bot.send_photo(
                chat_id=chat_id,
                photo=photo.file_id,
                caption=text,
                reply_markup=builder.as_markup(),
            )
        elif photo.storage_path:
            # Load from storage
            import aiofiles
            async with aiofiles.open(f"uploads/{photo.storage_path}", 'rb') as f:
                photo_bytes = await f.read()
            
            await bot.send_photo(
                chat_id=chat_id,
                photo=BufferedInputFile(photo_bytes, filename="photo.jpg"),
                caption=text,
                reply_markup=builder.as_markup(),
            )
    else:
        await bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=builder.as_markup(),
        )