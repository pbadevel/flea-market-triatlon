"""src/bot/services.py"""
from aiogram import Bot
from aiogram.types import BufferedInputFile, InputMediaPhoto
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.enums import ParseMode

from src.models import Ad
from src.config import settings
from src.logging import get_logger
import aiofiles

log = get_logger()


async def send_ad_to_channel(bot: Bot, ad: Ad) -> int | None:
    """
    Send approved ad to Telegram channel
    Returns channel message ID
    """
    try:
        # Build message for channel
        text = f"""
🛍 <b>{ad.title}</b>

💰 <b>{ad.price:,} ₽</b>
📍 {ad.city}
🏷 {ad.category}
{f'📏 Размер: {ad.size}' if ad.size else ''}
📦 {ad.condition}

{ad.description or ''}

👤 Продавец: @{ad.seller.username or 'не указан'}
"""
        
        # Contact button
        builder = InlineKeyboardBuilder()
        if ad.contact_method == "telegram":
            builder.button(
                text="📩 Написать продавцу",
                url=f"https://t.me/{ad.seller.username or ad.seller.tg_user_id}"
            )
        elif ad.contact_method == "phone" and ad.seller.phone:
            builder.button(
                text="📞 Позвонить",
                url=f"tel:{ad.seller.phone}"
            )
        
        # Send to channel
        channel_id = settings.TELEGRAM_CHANNEL_ID
        
        if ad.photos:
            # Send as media group if multiple photos
            if len(ad.photos) > 1:
                media = []
                
                for i, photo in enumerate(ad.photos[:10]):  # Max 10 photos
                    if photo.file_id:
                        if i == 0:
                            media.append(InputMediaPhoto(media=photo.file_id, caption=text, parse_mode=ParseMode.HTML))
                        else:
                            media.append(InputMediaPhoto(media=photo.file_id))
                    elif photo.storage_path:
                        async with aiofiles.open(f"uploads/{photo.storage_path}", 'rb') as f:
                            photo_bytes = await f.read()
                        
                        if i == 0:
                            media.append(InputMediaPhoto(
                                media=BufferedInputFile(photo_bytes, filename="photo.jpg"),
                                caption=text,
                                parse_mode=ParseMode.HTML
                            ))
                        else:
                            media.append(InputMediaPhoto(
                                media=BufferedInputFile(photo_bytes, filename="photo.jpg")
                            ))
                
                messages = await bot.send_media_group(channel_id, media)
                message_id = messages[0].message_id
                
                # Send contact button separately
                if builder.as_markup().inline_keyboard:
                    await bot.send_message(
                        channel_id,
                        "👆 Нажмите для связи с продавцом",
                        reply_markup=builder.as_markup(),
                        reply_to_message_id=message_id,
                    )
                
                return message_id
            
            else:
                # Single photo
                photo = ad.photos[0]
                if photo.file_id:
                    msg = await bot.send_photo(
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
                    
                    msg = await bot.send_photo(
                        channel_id,
                        photo=BufferedInputFile(photo_bytes, filename="photo.jpg"),
                        caption=text,
                        reply_markup=builder.as_markup(),
                        parse_mode=ParseMode.HTML,
                    )
                    return msg.message_id
        
        # No photos - send as text
        msg = await bot.send_message(
            channel_id,
            text,
            reply_markup=builder.as_markup(),
            parse_mode=ParseMode.HTML,
        )
        return msg.message_id
        
    except Exception as e:
        log.error(f"Failed to send ad to channel: {e}", exc_info=True)
        return None


async def notify_user_ad_approved(bot: Bot, ad: Ad):
    """Notify user that their ad was approved"""
    try:
        text = f"""
✅ <b>Ваше объявление одобрено!</b>

📝 {ad.title}
💰 {ad.price:,} ₽

Объявление опубликовано в канале и доступно на сайте.
"""
        
        await bot.send_message(
            ad.seller.tg_user_id,
            text,
            parse_mode=ParseMode.HTML,
        )
    except Exception as e:
        log.error(f"Failed to notify user about approval: {e}", exc_info=True)


async def notify_user_ad_rejected(bot: Bot, ad: Ad, reason: str):
    """Notify user that their ad was rejected"""
    try:
        text = f"""
❌ <b>Ваше объявление отклонено</b>

📝 {ad.title}
💰 {ad.price:,} ₽

Причина: {reason}

Вы можете исправить объявление и отправить на повторную модерацию.
"""
        
        await bot.send_message(
            ad.seller.tg_user_id,
            text,
            parse_mode=ParseMode.HTML,
        )
    except Exception as e:
        log.error(f"Failed to notify user about rejection: {e}", exc_info=True)


async def send_ad_for_moderation(bot: Bot, chat_id: int, ad: Ad):
    """Send new ad to moderator chat for review"""
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    
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


# Функции для прямых вызовов API (для тестов)
async def send_ad_to_moderation_api(ad: Ad):
    """
    Send ad to moderation via direct API call (for testing)
    This can be called from the create_ad endpoint
    """
    from src.bot.main import bot
    
    if settings.MODERATOR_CHAT_ID:
        await send_ad_for_moderation(bot, settings.MODERATOR_CHAT_ID, ad)
        log.info(f"Ad {ad.id} sent to moderation chat")


async def publish_ad_to_channel_api(ad: Ad):
    """
    Publish ad to channel via direct API call (for testing)
    This can be called from the moderate_ad endpoint
    """
    from src.bot.main import bot
    
    channel_message_id = await send_ad_to_channel(bot, ad)
    if channel_message_id:
        log.info(f"Ad {ad.id} published to channel, message_id: {channel_message_id}")
        return channel_message_id
    return None



# from aiogram import Bot
# from aiogram.types import BufferedInputFile
# from aiogram.utils.keyboard import InlineKeyboardBuilder
# from aiogram.enums import ParseMode

# from src.models import Ad
# from src.config import settings
# from src.logging import get_logger

# log = get_logger()


# async def send_ad_to_channel(bot: Bot, ad: Ad) -> int | None:
#     """
#     Send approved ad to Telegram channel
#     Returns channel message ID
#     """
#     try:
#         # Build message for channel
#         text = f"""
# 🛍 <b>{ad.title}</b>

# 💰 <b>{ad.price:,} ₽</b>
# 📍 {ad.city}
# 🏷 {ad.category}
# {f'📏 Размер: {ad.size}' if ad.size else ''}
# 📦 {ad.condition}

# {ad.description or ''}

# 👤 Продавец: @{ad.seller.username or 'не указан'}
# """
        
#         # Contact button
#         builder = InlineKeyboardBuilder()
#         if ad.contact_method == "telegram":
#             builder.button(
#                 text="📩 Написать продавцу",
#                 url=f"https://t.me/{ad.seller.username or ad.seller.tg_user_id}"
#             )
#         elif ad.contact_method == "phone" and ad.seller.phone:
#             builder.button(
#                 text="📞 Позвонить",
#                 url=f"tel:{ad.seller.phone}"
#             )
        
#         # Send to channel
#         channel_id = settings.TELEGRAM_CHANNEL_ID
        
#         if ad.photos:
#             # Send as media group if multiple photos
#             if len(ad.photos) > 1:
#                 from aiogram.types import InputMediaPhoto
#                 media = []
                
#                 for i, photo in enumerate(ad.photos[:10]):  # Max 10 photos
#                     if photo.file_id:
#                         if i == 0:
#                             media.append(InputMediaPhoto(media=photo.file_id, caption=text, parse_mode=ParseMode.HTML))
#                         else:
#                             media.append(InputMediaPhoto(media=photo.file_id))
#                     elif photo.storage_path:
#                         import aiofiles
#                         async with aiofiles.open(f"uploads/{photo.storage_path}", 'rb') as f:
#                             photo_bytes = await f.read()
                        
#                         if i == 0:
#                             media.append(InputMediaPhoto(
#                                 media=BufferedInputFile(photo_bytes, filename="photo.jpg"),
#                                 caption=text,
#                                 parse_mode=ParseMode.HTML
#                             ))
#                         else:
#                             media.append(InputMediaPhoto(
#                                 media=BufferedInputFile(photo_bytes, filename="photo.jpg")
#                             ))
                
#                 messages = await bot.send_media_group(channel_id, media)
#                 message_id = messages[0].message_id
                
#                 # Send contact button separately
#                 if builder.as_markup().inline_keyboard:
#                     await bot.send_message(
#                         channel_id,
#                         "👆 Нажмите для связи с продавцом",
#                         reply_markup=builder.as_markup(),
#                         reply_to_message_id=message_id,
#                     )
                
#                 return message_id
            
#             else:
#                 # Single photo
#                 photo = ad.photos[0]
#                 if photo.file_id:
#                     msg = await bot.send_photo(
#                         channel_id,
#                         photo=photo.file_id,
#                         caption=text,
#                         reply_markup=builder.as_markup(),
#                         parse_mode=ParseMode.HTML,
#                     )
#                     return msg.message_id
#                 elif photo.storage_path:
#                     import aiofiles
#                     async with aiofiles.open(f"uploads/{photo.storage_path}", 'rb') as f:
#                         photo_bytes = await f.read()
                    
#                     msg = await bot.send_photo(
#                         channel_id,
#                         photo=BufferedInputFile(photo_bytes, filename="photo.jpg"),
#                         caption=text,
#                         reply_markup=builder.as_markup(),
#                         parse_mode=ParseMode.HTML,
#                     )
#                     return msg.message_id
        
#         # No photos - send as text
#         msg = await bot.send_message(
#             channel_id,
#             text,
#             reply_markup=builder.as_markup(),
#             parse_mode=ParseMode.HTML,
#         )
#         return msg.message_id
        
#     except Exception as e:
#         log.error(f"Failed to send ad to channel: {e}", exc_info=True)
#         return None


# async def notify_user_ad_approved(bot: Bot, ad: Ad):
#     """Notify user that their ad was approved"""
#     try:
#         text = f"""
# ✅ <b>Ваше объявление одобрено!</b>

# 📝 {ad.title}
# 💰 {ad.price:,} ₽

# Объявление опубликовано в канале и доступно на сайте.
# """
        
#         await bot.send_message(
#             ad.seller.tg_user_id,
#             text,
#             parse_mode=ParseMode.HTML,
#         )
#     except Exception as e:
#         log.error(f"Failed to notify user about approval: {e}", exc_info=True)


# async def notify_user_ad_rejected(bot: Bot, ad: Ad, reason: str):
#     """Notify user that their ad was rejected"""
#     try:
#         text = f"""
# ❌ <b>Ваше объявление отклонено</b>

# 📝 {ad.title}
# 💰 {ad.price:,} ₽

# Причина: {reason}

# Вы можете исправить объявление и отправить на повторную модерацию.
# """
        
#         await bot.send_message(
#             ad.seller.tg_user_id,
#             text,
#             parse_mode=ParseMode.HTML,
#         )
#     except Exception as e:
#         log.error(f"Failed to notify user about rejection: {e}", exc_info=True)


# async def send_ad_to_moderation(bot: Bot, ad: Ad, moderator_chat_id: int):
#     """Send new ad to moderator chat for review"""
#     from src.bot.handlers.moderation import send_ad_for_moderation
#     await send_ad_for_moderation(bot, moderator_chat_id, ad)