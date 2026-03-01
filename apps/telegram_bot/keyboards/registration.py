from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from apps.config import settings


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

def get_timezone_keyboard(default_timezone: str = settings.DEFAULT_TIMEZONE) -> InlineKeyboardMarkup:
    """
    Keyboard for timezone choose (registration part).
    
    Includes:
        - `Share geolocation` button (automatically send query to share location)
        - `Use default` button (uses timezone from apps config)
    """
    
    builder = InlineKeyboardBuilder()
    
    builder.add(
        InlineKeyboardButton(
            text="📍 Share geolocation",
            callback_data="choose_own_timezone"
        ),
        InlineKeyboardButton(
            text=f"Use default ({default_timezone})",
            callback_data="choose_default_timezone"
        )
    )
    
    return builder.as_markup()
