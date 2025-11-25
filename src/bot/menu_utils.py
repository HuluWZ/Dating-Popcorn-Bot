"""
Shared helpers for sending frequently used bot menus.
"""

from aiogram.types import Message

from src.bot.callbacks import SkipAction
from src.bot.keyboards import (
    get_location_inline_keyboard,
    get_location_keyboard,
    get_main_menu_inline_keyboard,
    get_skip_inline_keyboard,
    get_skip_reply_keyboard,
)
from src.utils.localization import get_message


async def send_location_button(message: Message, language: str) -> None:
    """Send inline button prompting user to share location."""
    await message.answer(
        get_message(language, "bot.welcome.location_request"),
        reply_markup=get_location_inline_keyboard(language),
    )


async def send_main_menu_buttons(message: Message, language: str) -> None:
    """Send inline main menu buttons (reply keyboard already set elsewhere)."""
    await message.answer(
        get_message(language, "bot.main_menu.choose_action"),
        reply_markup=get_main_menu_inline_keyboard(language),
    )


async def send_skip_hint(message: Message, language: str, action: SkipAction) -> None:
    """Send skip hint with both inline button and temporary reply keyboard."""
    await message.answer(
        get_message(language, "common.prompts.skip_hint"),
        reply_markup=get_skip_inline_keyboard(language, action),
    )
    await message.answer(" ", reply_markup=get_skip_reply_keyboard(language))


async def send_location_request_keyboard(message: Message, language: str) -> None:
    """Send reply keyboard that triggers Telegram's location sharing UI."""
    await message.answer(
        get_message(language, "bot.location.share_instructions"),
        reply_markup=get_location_keyboard(language),
    )

