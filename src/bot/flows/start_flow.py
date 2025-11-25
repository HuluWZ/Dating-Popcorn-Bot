"""
Handlers for onboarding flows such as /start and location setup.
"""

from __future__ import annotations

import logging
from typing import Optional

from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from src.bot.callbacks import LocationCallback
from src.bot.language import (
    detect_user_language,
    get_user_language,
    set_user_language,
)
from src.bot.keyboards import get_main_menu_keyboard
from src.bot.menu_utils import (
    send_location_button,
    send_location_request_keyboard,
    send_main_menu_buttons,
)
from src.utils.localization import get_message

logger = logging.getLogger(__name__)


async def handle_start_command(message: Message, state: FSMContext) -> None:
    """Handle /start command - check user existence and request location as needed."""
    user_id = str(message.from_user.id)
    username = message.from_user.username

    detected_language = detect_user_language(message)
    set_user_language(int(user_id), detected_language)

    logger.info("User %s started bot with language %s", user_id, detected_language)

    try:
        from src.database.simple_db import (
            get_user,
            create_or_get_user,
            has_user_location,
        )

        user = await get_user(user_id)

        if user is None:
            logger.info("User %s not found, creating new user...", user_id)
            user = await create_or_get_user(user_id, username)
            logger.info("Created new user: %s", user.id)

            await message.answer(
                get_message(
                    detected_language,
                    "bot.welcome.message",
                    name=message.from_user.first_name or "User",
                )
            )
            await send_location_button(message, detected_language)
            return

        has_location = await has_user_location(user_id)

        if not has_location:
            logger.info("User %s exists but lacks location", user_id)
            await message.answer(
                get_message(
                    detected_language,
                    "bot.welcome.message",
                    name=message.from_user.first_name or "User",
                )
            )
            await send_location_button(message, detected_language)
            return

        await message.answer(
            get_message(
                detected_language,
                "bot.main_menu.welcome_back",
                name=message.from_user.first_name or "User",
            ),
            reply_markup=get_main_menu_keyboard(detected_language),
        )
        await send_main_menu_buttons(message, detected_language)

    except Exception as exc:  # pragma: no cover - defensive fallback
        logger.error("Error in handle_start_command for user %s: %s", user_id, exc)
        await message.answer(
            get_message(
                detected_language,
                "bot.welcome.message",
                name=message.from_user.first_name or "User",
            )
        )
        await send_location_button(message, detected_language)


async def handle_location_callback(
    callback: CallbackQuery, callback_data: LocationCallback, state: FSMContext
) -> None:
    """Handle inline location button presses and prompt for reply keyboard."""
    user_id = callback.from_user.id
    telegram_id = str(user_id)
    language = get_user_language(user_id)

    logger.info(
        "Location callback: user_id=%s, telegram_id=%s", user_id, telegram_id
    )

    await callback.answer()

    try:
        from src.database.simple_db import has_user_location

        has_location = await has_user_location(telegram_id)
        if has_location:
            logger.info("User %s already has location, showing main menu", telegram_id)
            await callback.message.answer(
                get_message(language, "bot.location.already_set"),
                reply_markup=get_main_menu_keyboard(language),
            )
            await send_main_menu_buttons(callback.message, language)
            return
    except Exception as exc:
        logger.error("Error checking location for user %s: %s", telegram_id, exc)

    await send_location_request_keyboard(callback.message, language)


async def handle_location(message: Message, state: FSMContext) -> None:
    """Persist shared location and show main menu when complete."""
    user_id = str(message.from_user.id)
    language = get_user_language(int(user_id))
    location = message.location

    logger.info("handle_location called for user %s", user_id)

    if not location:
        logger.warning("User %s sent location message but no data found", user_id)
        await message.answer(get_message(language, "errors.location_not_received"))
        return

    try:
        from src.database.simple_db import (
            has_user_location,
            set_user_location,
        )

        if await has_user_location(user_id):
            logger.info("User %s already has location set, skipping save", user_id)
            await message.answer(
                get_message(language, "bot.location.already_set"),
                reply_markup=get_main_menu_keyboard(language),
            )
            await send_main_menu_buttons(message, language)
            return

        username = message.from_user.username
        success = await set_user_location(
            user_id, location.latitude, location.longitude, username=username
        )

        reply_key = (
            "bot.location.received" if success else "bot.location.already_set"
        )
        await message.answer(
            get_message(language, reply_key),
            reply_markup=get_main_menu_keyboard(language),
        )
        await send_main_menu_buttons(message, language)

    except Exception as exc:
        logger.error("Error saving location for user %s: %s", user_id, exc)
        await message.answer(get_message(language, "errors.location_save_failed"))
        await send_main_menu_buttons(message, language)

