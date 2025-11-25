"""
Handlers for main menu interactions and keyword shortcuts.
"""

from __future__ import annotations

import logging
from typing import Optional

from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from src.bot.callbacks import MainMenuCallback
from src.bot.keyboards import MainMenuAction, is_search_review_button_text, is_write_review_button_text
from src.bot.language import get_user_language
from src.bot.menu_utils import send_location_button, send_main_menu_buttons
from src.utils.localization import get_message
from src.bot.states import SearchStates

logger = logging.getLogger(__name__)


def detect_main_menu_keyword(text: Optional[str]) -> Optional[str]:
    if not text:
        return None

    text_lower = text.strip().lower()
    if text_lower in ["search", "buscar"]:
        return "search"
    if text_lower in ["write", "escribir"]:
        return "write"
    if text_lower in ["name", "nombre"]:
        return "name"
    if text_lower in ["image", "imagen"]:
        return "image"
    return None


async def handle_main_menu_callback(
    callback: CallbackQuery, callback_data: MainMenuCallback, state: FSMContext
) -> None:
    user_id = callback.from_user.id
    language = get_user_language(user_id)
    await state.clear()
    await callback.answer()

    if callback_data.action == MainMenuAction.WRITE_REVIEW.value:
        from src.bot.flows.review_flow import handle_write_review_button

        await handle_write_review_button(callback.message, state, user_id=user_id)
    elif callback_data.action == MainMenuAction.SEARCH_REVIEWS.value:
        from src.bot.flows.search_flow import handle_search_someone_button

        await handle_search_someone_button(callback.message, state, user_id=user_id)
    else:
        await callback.answer(
            get_message(language, "errors.invalid_button"), show_alert=True
        )


async def handle_main_menu_keyword(message: Message, state: FSMContext) -> bool:
    user_id = message.from_user.id
    language = get_user_language(user_id)

    current_state = await state.get_state()
    if current_state is not None:
        return False

    if is_write_review_button_text(message.text) or is_search_review_button_text(
        message.text
    ):
        return False

    keyword_action = detect_main_menu_keyword(message.text)
    if keyword_action is None:
        return False

    if keyword_action == "search":
        from src.bot.flows.search_flow import handle_search_someone_button

        await handle_search_someone_button(message, state, user_id=user_id)
        return True

    if keyword_action == "write":
        from src.bot.flows.review_flow import handle_write_review_button

        await handle_write_review_button(message, state, user_id=user_id)
        return True

    if keyword_action in ("name", "image"):
        from src.database.simple_db import (
            get_user_location,
            has_user_location,
        )

        telegram_id = str(user_id)
        user_location = await get_user_location(telegram_id)
        if not user_location and not await has_user_location(telegram_id):
            await message.answer(
                get_message(language, "bot.location.required_for_search")
            )
            await send_location_button(message, language)
            return True

        if keyword_action == "name":
            await state.set_state(SearchStates.waiting_for_name)
            await message.answer(get_message(language, "search.flow.by_name.prompt"))
        else:
            await state.set_state(SearchStates.waiting_for_image)
            await message.answer(get_message(language, "search.flow.by_image.prompt"))
        return True

    return False


async def handle_unknown_message(message: Message, state: FSMContext) -> None:
    user_id = message.from_user.id
    language = get_user_language(user_id)

    handled = await handle_main_menu_keyword(message, state)
    if handled:
        return

    await message.answer(get_message(language, "errors.invalid_button"))
    await send_main_menu_buttons(message, language)

