from fastapi import APIRouter, Request, HTTPException, Depends
from aiogram.types import Update

from src.bot.main import get_bot, get_dispatcher
from src.config import settings
from src.logging import get_logger

router = APIRouter(tags=["telegram"])
log = get_logger()


@router.post(settings.WEBHOOK_PATH)
async def telegram_webhook(request: Request):
    """Handle Telegram webhook updates"""
    # Verify secret token
    secret_header = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    if secret_header != settings.webhook_secret_token:
        raise HTTPException(status_code=403, detail="Invalid secret token")
    
    # Parse update
    update_data = await request.json()
    update = Update(**update_data)
    
    # Process update
    try:
        await get_dispatcher().feed_update(get_bot(), update)
    except Exception as e:
        log.error(f"Error processing update: {e}", exc_info=True)
    
    return {"ok": True}