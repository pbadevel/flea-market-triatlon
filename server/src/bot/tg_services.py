"""src/bot/services.py"""
import aiofiles
import asyncio
from aiogram import Bot
from aiogram.types import BufferedInputFile, InputMediaPhoto
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.enums import ParseMode


from sqlalchemy import select
from sqlalchemy.orm import joinedload

from src.models import Ad
from src.kit.utils import get_bot, get_ru_condition, map_country
from src.kit.database.service import database_service

from src.config import settings
from src.logging import get_logger

log = get_logger()

def get_publish_text_to_channel(ad: Ad):
    country_ru = map_country(ad.country) if ad.country else ""
    location = f"{country_ru} - {ad.city}" if country_ru else ad.city

    return (
        f'🛍 <b>{ad.title}</b>\n\n'
        f'📍 {location}\n'
        f'{f"📏 Размер: {ad.size}\n" if ad.size else ""}'
        f'📦 {get_ru_condition(ad.condition)}\n'
        f'🛒 <b>{ad.price:,} ₽</b>'
    )

def _format_seller(ad: Ad) -> str:
    """Format seller info for moderation message — works for both tg and email users."""
    seller = ad.seller
    if not seller:
        return "👤 Продавец: неизвестен"
    
    # Telegram user with username
    if seller.username:
        name_part = f"@{seller.username}"
        source = "📱 Telegram"
    else:
        # Email/web user — use first/last name or email
        name_parts = []
        if seller.first_name:
            name_parts.append(seller.first_name)
        if seller.last_name:
            name_parts.append(seller.last_name)
        name_part = " ".join(name_parts) if name_parts else "пользователь"
        
        # Try to get email from credentials
        if seller.credentials and seller.credentials.email:
            name_part += f" ({seller.credentials.email})"
        source = "🌐 Сайт"
    
    return f"👤 Продавец: {name_part}\n📬 {source} (ID: {seller.id})"


def get_text_for_moderation(ad: Ad):
    
    return f'🆕 <b>Новое объявление на модерации</b>\n\n' \
    \
    f'📝 <b>{ad.title}</b>\n' \
    f'💰 Цена: {ad.price:,} ₽\n' \
    f'📍 Город: {ad.city}\n' \
    f'🏷 Категория: {ad.category}\n' \
    f'{f"📏 Размер: {ad.size}" if ad.size else ""}\n' \
    f'📦 Состояние: {get_ru_condition(ad.condition)}\n\n'\
    \
    f'{_format_seller(ad)}\n'\
    f'🆔 ID объявления: {ad.id}\n\n'\
    \
    f'{(ad.description[:1000]+"..." if ad.description else None) or ""}'
    




class TgService:

    def __init__(self):
        self.bot = get_bot()
        

    async def send_ad_to_channel(self, ad: Ad, from_site: bool = True) -> int | None:
        """
        Send approved ad to Telegram channel
        Returns channel message ID
        """
        try:
            water_text = ''
            if from_site:
                water_text = f"Наш сайт || {settings.API_DOMAIN_URL}"
            # Build message for channel
            text=get_publish_text_to_channel(ad) + water_text
            
            # Build keyboard
            builder = InlineKeyboardBuilder()
            builder.button(
                text="🔍 Подробнее",
                callback_data=f"detail:{ad.id}"
            )
            
            # Send to channel
            channel_id = settings.TELEGRAM_CHANNEL_ID
            
            if ad.photos:
                # Send as media group if multiple photos
                if len(ad.photos) > 1:
                    pass

                    # media = []
                    
                    # for i, photo in enumerate(ad.photos[:10]):  # Max 10 photos
                    #     if photo.storage_path:
                    #         async with aiofiles.open(f"uploads/{photo.storage_path}", 'rb') as f:
                    #             photo_bytes = await f.read()
                            
                    #         if i == 0:
                    #             media.append(InputMediaPhoto(
                    #                 media=BufferedInputFile(photo_bytes, filename="photo.jpg"),
                    #                 caption=text,
                    #                 parse_mode=ParseMode.HTML
                    #             ))
                    #         else:
                    #             media.append(InputMediaPhoto(
                    #                 media=BufferedInputFile(photo_bytes, filename="photo.jpg")
                    #             ))
                    
                    # messages = await self.bot.send_media_group(channel_id, media)
                    # message_id = messages[0].message_id
                    
                    # # Send contact button separately
                    # if builder.as_markup().inline_keyboard:
                    #     await self.bot.send_message(
                    #         channel_id,
                    #         "👆 Нажмите для связи с продавцом",
                    #         reply_markup=builder.as_markup(),
                    #         reply_to_message_id=message_id,
                    #     )
                    
                    # return message_id
                # else:
                
                # Single photo
                photo = ad.photos[0]
                if photo.file_id:
                    msg = await self.bot.send_photo(
                        channel_id,
                        photo=photo.file_id,
                        caption=text,
                        reply_markup=builder.as_markup(),
                        parse_mode=ParseMode.HTML,
                    )
                    return msg.message_id
                elif photo.storage_path:
                    async with aiofiles.open(f"uploads/{photo.storage_path}", 'rb') as f:
                        photo_bytes = await f.read()
                    
                    msg = await self.bot.send_photo(
                        channel_id,
                        photo=BufferedInputFile(photo_bytes, filename="photo.jpg"),
                        caption=text,
                        reply_markup=builder.as_markup(),
                        parse_mode=ParseMode.HTML,
                    )
                    return msg.message_id
            
            # No photos - send as text
            msg = await self.bot.send_message(
                channel_id,
                text,
                reply_markup=builder.as_markup(),
                parse_mode=ParseMode.HTML,
            )
            return msg.message_id
            
        except Exception as e:
            log.error(f"Failed to send ad to channel: {e}", exc_info=True)
            return None


    async def notify_user_ad_approved(self, ad: Ad):
        """Notify user that their ad was approved"""
        try:
            text = f"""
✅ <b>Ваше объявление одобрено!</b>

📝 {ad.title}
💰 {ad.price:,} ₽

Объявление опубликовано в канале и доступно на сайте.
    """
            
            await self.bot.send_message(
                ad.seller.tg_user_id,
                text,
                parse_mode=ParseMode.HTML,
            )
        except Exception as e:
            log.error(f"Failed to notify user about approval: {e}", exc_info=True)


    async def notify_user_ad_rejected(self, ad: Ad, reason: str):
        """Notify user that their ad was rejected"""
        try:
            text = f"""
❌ <b>Ваше объявление отклонено</b>

📝 {ad.title}
💰 {ad.price:,} ₽

Причина: {reason}

Вы можете исправить объявление и отправить на повторную модерацию.
    """
            
            await self.bot.send_message(
                ad.seller.tg_user_id,
                text,
                parse_mode=ParseMode.HTML,
            )
        except Exception as e:
            log.error(f"Failed to notify user about rejection: {e}", exc_info=True)


    async def send_ad_for_moderation(self, ad: Ad):
        """Send new ad to moderator's chat for review"""
        
        # Build message
        text = get_text_for_moderation(ad)

        # Build keyboard
        builder = InlineKeyboardBuilder()

        # Callbacks
        builder.button(text="✅ Одобрить", callback_data=f"moderate:approve:{ad.id}")
        builder.button(text="❌ Отклонить", url=f"https://t.me/{settings.BOT_USERNAME}?start=promoteReject_{ad.id}")

        # builder.button(text="Открыть Web", url=f"{settings.SITE_URL}/admin/ads/{ad.id}")

        builder.adjust(2)
        
        # Send with photo if available
        if ad.photos:
            media = []
            for i, photo in enumerate(ad.photos[:10]):  # Max 10 photos
                if photo.storage_path:
                    async with aiofiles.open(f"uploads/{photo.storage_path}", 'rb') as f:
                        photo_bytes = await f.read()
                    
                    if i == 0:
                        media.append(InputMediaPhoto(
                            media=BufferedInputFile(photo_bytes, filename=f"photo{i}.jpg"),
                            parse_mode=ParseMode.HTML
                        ))
                    else:
                        media.append(InputMediaPhoto(
                            media=BufferedInputFile(photo_bytes, filename=f"photo{i}.jpg")
                        ))
            
            await self.bot.send_media_group(
                chat_id=settings.MODERATORS_CHAT_ID, 
                media=media
            )
            await self.bot.send_message(
                chat_id=settings.MODERATORS_CHAT_ID,
                text=text,
                reply_markup=builder.as_markup() 
            )
        else:
            await self.bot.send_message(
                chat_id=settings.MODERATORS_CHAT_ID,
                text=text,
                reply_markup=builder.as_markup(),
            )

    async def delete_ad_from_channel(self, ad: Ad):
        
        if not ad.channel_message_id:
            log.error("CANNOT DELETE MESSAGE FROM CHANNEL: NO MESSAGE ID", ad=ad)
            return
        
        try:
            await self.bot.delete_message(
                chat_id=settings.TELEGRAM_CHANNEL_ID,
                message_id=ad.channel_message_id
            )
        except Exception as e:
            log.error(f"cannot delete message from telegram channel: {e}")

    async def send_ad_for_moderation_by_id(self, ad_id: int):
        """Загрузить объявление по ID и отправить на модерацию (для фоновых задач)."""
        async with database_service.get_session() as session:
            stmt = (
                select(Ad)
                .where(Ad.id == ad_id)
                .options(
                    joinedload(Ad.photos),
                    joinedload(Ad.seller),
                )
            )
            result = await session.execute(stmt)
            ad = result.scalars().first()
        if not ad:
            log.error(f"send_ad_for_moderation_by_id: ad {ad_id} not found")
            return
        await self.send_ad_for_moderation(ad)

    async def delete_ad_from_channel_by_id(self, ad_id: int):
        """Загрузить объявление по ID и удалить из канала (для фоновых задач)."""
        async with database_service.get_session() as session:
            result = await session.execute(
                select(Ad).where(Ad.id == ad_id)
            )
            ad = result.scalars().first()
            if not ad:
                log.error(f"delete_ad_from_channel_by_id: ad {ad_id} not found")
                return
        await self.delete_ad_from_channel(ad)


tg_service_notifier = TgService()