"""src/api/endpoints/bot_test.py - для тестирования бота"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

# from src.bot.tg_services import send_ad_to_moderation_api, publish_ad_to_channel_api
from src.kit.database.service import database_service
from src.services import ad_service
from src.logging import get_logger

router = APIRouter(prefix="/bot-test", tags=["bot-test"])
log = get_logger()


class TestModerationRequest(BaseModel):
    ad_id: int
    action: str  # "approve" or "reject"
    rejection_reason: Optional[str] = None


@router.post("/send-to-moderation/{ad_id}")
async def test_send_to_moderation(ad_id: int):
    """
    Test endpoint: Send ad to moderation chat
    For testing purposes only
    """
    async with database_service.get_session() as session:
        ad = await ad_service.get_ad_for_moderation(session, ad_id)
        
        if not ad:
            raise HTTPException(404, "Ad not found")
        
        # await send_ad_to_moderation_api(ad)
        
        return {"status": "ok", "message": f"Ad {ad_id} sent to moderation"}


@router.post("/publish-to-channel/{ad_id}")
async def test_publish_to_channel(ad_id: int):
    """
    Test endpoint: Publish ad to channel
    For testing purposes only
    """
    async with database_service.get_session() as session:
        ad = await ad_service.get_ad_for_moderation(session, ad_id)
        
        if not ad:
            raise HTTPException(404, "Ad not found")
        
        # message_id = await publish_ad_to_channel_api(ad)
        
        return {
            "status": "ok",
            "message": f"Ad {ad_id} published to channel",
            # "channel_message_id": message_id
        }


@router.post("/moderate")
async def test_moderate(data: TestModerationRequest):
    """
    Test endpoint: Moderate ad and publish/reject
    For testing purposes only
    """
    async with database_service.get_session() as session:
        ad = await ad_service.moderate_ad(
            session=session,
            ad_id=data.ad_id,
            action=data.action,
            rejection_reason=data.rejection_reason,
        )
        
        if not ad:
            raise HTTPException(404, "Ad not found")
        
        # If approved, publish to channel
        if data.action == "approve":
            pass
            # message_id = await publish_ad_to_channel_api(ad)
            # ad.channel_message_id = message_id
        
        await session.commit()
        
        return {
            "status": "ok",
            "message": f"Ad {data.ad_id} {data.action}d",
            "channel_message_id": ad.channel_message_id if data.action == "approve" else None
        }