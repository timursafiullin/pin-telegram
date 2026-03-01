from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from apps.config import settings

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