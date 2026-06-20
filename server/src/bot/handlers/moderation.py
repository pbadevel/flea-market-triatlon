from aiogram import Router, F, Bot
from aiogram.types import User as TGUser, CallbackQuery, Message, MaybeInaccessibleMessageUnion

from aiogram.fsm.context import FSMContext

from src.models import AdStatus
from src.services import ad_service
from src.services.email import email_service
from src.kit.database.service import database_service
from src.bot.tg_services import tg_service_notifier

from src.bot.handlers.kb import get_moderator_cancel_keyboard, get_moderator_confirmation_reason_keyboard
from src.bot.states import ModeratorRejectionState

from src.logging import get_logger
from src.enums import UserRole
from src.config import settings
from typing import cast

router = Router()
log = get_logger()


@router.callback_query(F.data.startswith("moderate:"))
async def handle_moderation_callback(callback: CallbackQuery, bot: Bot):

    log.info("MODERATION STARTED", callback=callback.data)
    """Handle moderation buttons (approve/reject)"""
    if not callback.message:
        return
    
    # Parse callback data: moderate:approve:123 or moderate:reject:123
    data = cast(str, callback.data)
    parts = data.split(":")

    if len(parts) != 3:
        await callback.answer("❌ Ошибка формата данных", show_alert=True)
        return
    
    _, action, ad_id_str = parts
    
    try:
        ad_id = int(ad_id_str)
    except ValueError:
        await callback.answer("❌ Неверный ID объявления", show_alert=True)
        return
    
    log.info("MODERATION CONTINUED")
    try:
        # Check if user is moderator
        async with database_service.get_session() as session:
            tg_user = callback.from_user
            
            # Find user in DB
            from src.repositories.users import UserRepository
            user_repo = UserRepository(session)
            user = await user_repo.get_by_tg_id(tg_user.id)
            log.info(f"User: {user}")
            
            if not user or (user.role == UserRole.USER):
                await callback.answer("⛔ У вас нет прав модератора", show_alert=True)

                return
            
            # Get ad
            ad = await ad_service.get_ad_for_moderation(session, ad_id)
            log.info(f"ad: {ad}")
            
            if not ad:
                await callback.answer("❌ Объявление не найдено", show_alert=True)
                return
            
            if ad.status != AdStatus.pending.value:
                await callback.answer(f"ℹ️ Объявление уже обработано\n(статус: {ad.status})", show_alert=True)
                return
            
            # Moderate
            if action == "approve":
                channel_message_id = await tg_service_notifier.send_ad_to_channel(ad, from_site=False)
                
                await ad_service.moderate_ad(
                    session=session,
                    ad_id=ad_id,
                    action="approve",
                    channel_message_id=channel_message_id,
                )
                await session.commit()

                await edit_message(
                    message=callback.message, 
                    new_text=f"\n\n✅ Одобрено и опубликовано в канале модератором {
                        ('@'+callback.from_user.username if callback.from_user.username else None)
                        or callback.from_user.full_name}"
                )
                
                await callback.answer(
                    f"✅ Объявление #{ad_id} одобрено и опубликовано в канале", show_alert=True
                )
                
                # Notify user
                await tg_service_notifier.notify_user_ad_approved(ad)
                
                # Email notification for email-registered users
                if not ad.seller.username and ad.seller.credentials and ad.seller.credentials.email:
                    await email_service.notify_user_ad_approved_email(
                        email=ad.seller.credentials.email,
                        title=ad.title,
                        price=ad.price,
                        ad_id=ad.id,
                    )


            # NEED REASON  
            # elif action == "reject":
            #     await ad_service.moderate_ad(
            #         session=session,
            #         ad_id=ad_id,
            #         action="reject",
            #         rejection_reason="Отклонено модератором",
            #     )
            #     await session.commit()
                
            #     await edit_message(
            #         message=callback.message, 
            #         new_text=f"\n\n❌ Отклонено модератором {
            #             ('@'+callback.from_user.username if callback.from_user.username else None)
            #             or callback.from_user.full_name}"
            #     )
                
            #     await callback.answer(
            #         f"❌ Объявление #{ad_id} отклонено", show_alert=True
            #     )
                
            #     # Notify user
            #     await tg_service_notifier.notify_user_ad_rejected(ad, "Отклонено модератором")
            

        await callback.answer()

    except Exception as e:
        log.error(f"ERROR IN MODERATION:{e}")


async def proceed_promote_reject(deeplink: str, message: Message, state: FSMContext):
    ad_id = deeplink.replace("promoteReject_", "")

    try:
        ad_id = int(ad_id)
    except:
        log.error("Ad_id isn't a number")
        return
    
    await state.update_data(ad_id=ad_id)
    
    await message.answer(
        text='Введите причину:',
        reply_markup=get_moderator_cancel_keyboard()
    )
    await state.set_state(ModeratorRejectionState.wait_for_reason)

@router.message(ModeratorRejectionState.wait_for_reason)
async def continue_rejection(message: Message, state: FSMContext):
    rejection_reason = message.text
    if not rejection_reason:
        await message.answer(
            text='Пожалуйста отправьте ТЕКСТ - причину отказа',
            reply_markup=get_moderator_cancel_keyboard()
        )
        return
        
    await message.answer(
        text='Подтвердите причину:\n\n' \
        f'Причина: <b>{rejection_reason}</b>',
        reply_markup=get_moderator_confirmation_reason_keyboard()
    )

    await state.update_data(rejection_reason=rejection_reason)


@router.callback_query(F.data.startswith("moderReason_"))
async def continue_confirmation_rejection(cb: CallbackQuery, state: FSMContext):
    msg = cast(Message, cb.message)
    data = await state.get_data()
    ad_id = data["ad_id"]
    rejection_reason = data["rejection_reason"]

    if cb.data.replace("moderReason_", "") == 'confirm': # pyright: ignore

        try:
            async with database_service.get_session() as session:
                ad = await ad_service.moderate_ad(
                    session=session,
                    ad_id=ad_id,
                    action="reject",
                    rejection_reason=rejection_reason,
                )
                await session.commit()

                if not ad:
                    await cb.answer(
                        text='Объявления больше не существует',
                        show_alert=True
                    )
                    return
                
                username = "@" + cb.from_user.username if cb.from_user and cb.from_user.username else None
                full_name = cb.from_user.full_name if cb.from_user else None
                
                bot = cast(Bot, cb.bot)

                await cb.message.delete() # pyright: ignore

                msg = await bot.send_message(
                    chat_id=settings.MODERATORS_CHAT_ID,
                    text=f"❌ Объявление #{ad_id}\n"\
                            f"Отклонено модератором {username or full_name}\n"\
                            f"Причина: <b>{rejection_reason}</b>"
                )

                
                await cb.answer(
                    f"❌ Объявление #{ad_id} успешно отклонено", show_alert=True
                )

                await state.clear()
                
                # Notify user
                await tg_service_notifier.notify_user_ad_rejected(ad, rejection_reason)
                
                # Email notification for email-registered users
                if not ad.seller.username and ad.seller.credentials and ad.seller.credentials.email:
                    await email_service.notify_user_ad_rejected_email(
                        email=ad.seller.credentials.email,
                        title=ad.title,
                        price=ad.price,
                        reason=rejection_reason,
                    )
                return
        except Exception as e:
            await msg.answer(
                text='Пожалуйста отправьте причину отказа ЕЩЕ РАЗ:',
                reply_markup=get_moderator_cancel_keyboard()
            )
            log.error(f"ERROR WHILE CONFIRMATING REJECTION: {e}")
    else:
        await msg.answer(
            text='Пожалуйста отправьте причину отказа ЕЩЕ РАЗ:',
            reply_markup=get_moderator_cancel_keyboard()
        )
        await state.set_state(ModeratorRejectionState.wait_for_reason)
        return



@router.callback_query(F.data == "CancelAdModeration")
async def cancel_ad_moderation(cb: CallbackQuery, state: FSMContext):
    await cast(Message, cb.message).edit_text('Отменено. Хорошего дня!')
    await state.clear()




async def edit_message(
        message: MaybeInaccessibleMessageUnion, 
        new_text: str,
    ):

    if isinstance(message, Message):
        
        if message.photo or message.media_group_id:
            await message.edit_caption(
                caption=new_text
            )
            return
        await message.edit_text(
            text=new_text
        )
        return

