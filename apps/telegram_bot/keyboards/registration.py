from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)


def get_registration_type_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.add(
        InlineKeyboardButton(
            text="👥 I have an invite code",
            callback_data="have_invite_code"
        ),
        InlineKeyboardButton(
            text="🙋 Request access",
            callback_data="request_access"
        )
    )

    return builder.as_markup()


def back_to_choose_reg_type_button() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.add(
        InlineKeyboardButton(
            text="🔙 Go back",
            callback_data="back_to_choose_reg_type"
        )
    )

    return builder.as_markup()


def request_confirmation() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.add(
        InlineKeyboardButton(
            text="👌 Confirm",
            callback_data="confirm_request_access"
        ),
        InlineKeyboardButton(
            text="🔙 Go back",
            callback_data="back_to_choose_reg_type"
        )
    )

    return builder.as_markup()


def get_timezone_keyboard_reply(default_timezone: str) -> ReplyKeyboardMarkup:
    """
    Reply keyboard for timezone selection.

    - Share location button triggers Telegram native location permission popup.
    - Use default button sends text, backend resolves/validates default timezone safely.
    """

    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="📍 Share location", request_location=True),
        KeyboardButton(text=f"Use default ({default_timezone})"),
        width=1,
    )

    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True, selective=True)
