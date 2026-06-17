from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder





def get_moderator_cancel_keyboard():
    return InlineKeyboardBuilder().row(
        InlineKeyboardButton(
            text="Отменить отклонение",
            style='danger',
            callback_data="CancelAdModeration"
        ),
    ).as_markup()

def get_moderator_confirmation_reason_keyboard():
    return InlineKeyboardBuilder().row(
        InlineKeyboardButton(
            text="Подтвердить",
            style='success',
            callback_data=f"moderReason_confirm"
        ),
        InlineKeyboardButton(
            text="Изменить",
            style='primary',
            callback_data=f"moderReason_edit"
        ),
        InlineKeyboardButton(
            text="Отменить отклонение",
            style='danger',
            callback_data="CancelAdModeration"
        ),
        width=2
    ).as_markup()