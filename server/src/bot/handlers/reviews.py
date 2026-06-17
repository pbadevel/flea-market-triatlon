from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from sqlalchemy import select, func, or_
from sqlalchemy.orm import joinedload

from src.logging import get_logger
from src.kit.database.service import database_service
from src.services import user_service
from src.models import Review, Ad, User
from src.bot.states import ReviewState
from src.bot.keyboards import skip_kb, back_kb, main_menu_kb, review_rating_kb
from src.bot.texts import *

router = Router()
log = get_logger()


@router.callback_query(lambda c: c.data.startswith("leave_review:"))
async def start_review(callback: CallbackQuery, state: FSMContext):
    seller_id = int(callback.data.split(":")[1])
    ad_id = int(callback.data.split(":")[2]) if len(callback.data.split(":")) > 2 else None

    tg_user = callback.from_user
    if tg_user.id == seller_id:
        await callback.answer("❌ Нельзя оставить отзыв самому себе", show_alert=True)
        return

    await state.update_data(reviewed_user_id=seller_id, ad_id=ad_id)
    await state.set_state(ReviewState.rating)
    await callback.message.edit_text(
        REVIEW_RATING_MESSAGE,
        reply_markup=review_rating_kb(seller_id, ad_id)
    )
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("rate:"))
async def process_rating(callback: CallbackQuery, state: FSMContext):
    rating = int(callback.data.split(":")[1])
    if rating < 1 or rating > 5:
        await callback.answer("❌ Оценка от 1 до 5", show_alert=True)
        return
    await state.update_data(rating=rating)
    await state.set_state(ReviewState.comment)
    await callback.message.edit_text(REVIEW_COMMENT_MESSAGE, reply_markup=skip_kb("review:skip_comment"))
    await callback.answer()


@router.callback_query(lambda c: c.data == "review:skip_comment")
async def skip_comment(callback: CallbackQuery, state: FSMContext):
    await _save_review(callback.message, state, comment=None)
    await callback.answer()


@router.message(ReviewState.comment)
async def process_comment(message: Message, state: FSMContext):
    comment = message.text.strip()[:500] if message.text else None
    await _save_review(message, state, comment)


async def _save_review(target, state: FSMContext, comment: str | None):
    data = await state.get_data()
    tg_user = getattr(target, "from_user", None) or getattr(target, "chat", None)

    async with database_service.get_session() as session:
        reviewer = await user_service.get_or_create_by_tg(session, tg_user)

        r = Review(
            reviewed_user_id=data["reviewed_user_id"],
            reviewer_user_id=reviewer.id,
            rating=data["rating"],
            comment=comment,
            ad_id=data.get("ad_id"),
        )
        session.add(r)
        await session.commit()

    await state.clear()
    text = REVIEW_THANKS_MESSAGE
    try:
        await target.edit_text(text, reply_markup=back_kb("menu:main"))
    except Exception:
        await target.answer(text, reply_markup=back_kb("menu:main"))
