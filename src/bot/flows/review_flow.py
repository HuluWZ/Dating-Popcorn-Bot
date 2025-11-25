"""
Handlers for the review creation flow.
"""

from __future__ import annotations

import logging
from typing import Optional

from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from src.bot.callbacks import SkipAction, SkipCallback
from src.bot.keyboards import get_cancel_keyboard, get_main_menu_keyboard
from src.bot.language import get_user_language
from src.bot.media import validate_image_content
from src.bot.menu_utils import send_location_button, send_main_menu_buttons, send_skip_hint
from src.bot.states import ReviewStates
from src.utils.localization import get_message

logger = logging.getLogger(__name__)


async def handle_write_review_button(
    message: Message, state: FSMContext, user_id: Optional[int] = None
) -> None:
    """Entry point for Write Review button - ensures location exists."""
    if user_id is None:
        user_id = message.from_user.id

    user_id_str = str(user_id)
    language = get_user_language(user_id)

    logger.info(
        "handle_write_review_button called for user_id=%s (message_user=%s)",
        user_id_str,
        message.from_user.id,
    )

    await state.clear()

    try:
        from src.database.simple_db import get_user_location, has_user_location

        user_location = await get_user_location(user_id_str)
        if user_location or await has_user_location(user_id_str):
            await state.set_state(ReviewStates.waiting_for_name)
            await message.answer(
                get_message(language, "review.flow.enter_name"),
                reply_markup=get_cancel_keyboard(language),
            )
            return

        await message.answer(
            get_message(language, "bot.location.required_for_review")
        )
        await send_location_button(message, language)

    except Exception as exc:
        logger.error("Error checking location for Write Review: %s", exc)
        try:
            from src.database.simple_db import get_user

            user = await get_user(user_id_str)
            if user and user.location is not None:
                await state.set_state(ReviewStates.waiting_for_name)
                await message.answer(
                    get_message(language, "review.flow.enter_name"),
                    reply_markup=get_cancel_keyboard(language),
                )
                return
        except Exception as nested_exc:  # pragma: no cover - logging only
            logger.error(
                "Error verifying user location in exception handler: %s", nested_exc
            )

        await message.answer(
            get_message(language, "bot.location.required_for_review")
        )
        await send_location_button(message, language)


async def handle_review_name(message: Message, state: FSMContext) -> None:
    user_id = message.from_user.id
    language = get_user_language(user_id)

    if message.text == get_message(language, "common.buttons.cancel"):
        logger.info("User %s cancelled review at name step", user_id)
        await state.clear()
        await message.answer(
            get_message(language, "review.flow.cancelled"),
            reply_markup=get_main_menu_keyboard(language),
        )
        await send_main_menu_buttons(message, language)
        return

    if not message.text or len(message.text.strip()) < 2:
        logger.warning(
            "User %s provided invalid name: '%s'", user_id, message.text
        )
        await message.answer(
            get_message(language, "review.flow.validation.name_too_short")
        )
        return

    full_name = message.text.strip()
    logger.info("User %s provided review name: '%s'", user_id, full_name)

    await state.update_data(full_name=full_name)
    await state.set_state(ReviewStates.waiting_for_exact_address)

    await message.answer(
        get_message(language, "review.flow.enter_contact"),
        reply_markup=get_cancel_keyboard(language),
    )
    await send_skip_hint(message, language, SkipAction.REVIEW_CONTACT)


async def handle_review_exact_address(message: Message, state: FSMContext) -> None:
    user_id = message.from_user.id
    language = get_user_language(user_id)
    data = await state.get_data()

    if message.text == get_message(language, "common.buttons.cancel"):
        logger.info("User %s cancelled review at address step", user_id)
        await state.clear()
        await message.answer(
            get_message(language, "review.flow.cancelled"),
            reply_markup=get_main_menu_keyboard(language),
        )
        await send_main_menu_buttons(message, language)
        return

    exact_address = None
    if message.text != get_message(language, "common.buttons.skip_optional"):
        from src.utils.social_utils import normalize_query

        original_input = message.text.strip()
        exact_address = normalize_query(original_input)
        logger.info(
            "User %s provided exact address: '%s' -> '%s'",
            user_id,
            original_input,
            exact_address,
        )
    else:
        logger.info("User %s skipped exact address", user_id)

    await state.update_data(exact_address=exact_address)
    await state.set_state(ReviewStates.waiting_for_content)

    await message.answer(
        get_message(language, "review.flow.enter_content"),
        reply_markup=get_cancel_keyboard(language),
    )


async def handle_review_content(message: Message, state: FSMContext) -> None:
    user_id = message.from_user.id
    language = get_user_language(user_id)

    if message.text == get_message(language, "common.buttons.cancel"):
        logger.info("User %s cancelled review at content step", user_id)
        await state.clear()
        await message.answer(
            get_message(language, "review.flow.cancelled"),
            reply_markup=get_main_menu_keyboard(language),
        )
        await send_main_menu_buttons(message, language)
        return

    if not message.text or len(message.text.strip()) < 10:
        logger.warning(
            "User %s provided invalid content (length %s)",
            user_id,
            len(message.text) if message.text else 0,
        )
        await message.answer(
            get_message(language, "review.flow.validation.content_too_short")
        )
        return

    content = message.text.strip()
    await state.update_data(content=content)
    await state.set_state(ReviewStates.waiting_for_photo)

    data = await state.get_data()
    full_name = data.get("full_name", "this person")

    await message.answer(
        get_message(language, "review.flow.upload_image", name=full_name),
        reply_markup=get_cancel_keyboard(language),
    )
    await send_skip_hint(message, language, SkipAction.REVIEW_PHOTO)


async def _finalize_review_submission(
    message: Message,
    state: FSMContext,
    language: str,
    user_id: str,
    image_url: Optional[str],
) -> None:
    data = await state.get_data()
    full_name = data.get("full_name")
    content = data.get("content")
    exact_address = data.get("exact_address")

    logger.info(
        "Processing review submission for user %s: name='%s', address='%s'",
        user_id,
        full_name,
        exact_address,
    )

    try:
        from src.database.simple_db import create_review

        review = await create_review(
            reviewer_id=user_id,
            full_name=full_name,
            content=content,
            exact_address=exact_address,
            image_url=image_url,
        )

        if not review:
            raise RuntimeError("Failed to create review - database returned None")

        await state.clear()
        await message.answer(
            get_message(language, "review.flow.saved"),
            reply_markup=get_main_menu_keyboard(language),
        )
        await send_main_menu_buttons(message, language)

    except Exception as exc:
        logger.error("Error saving review for user %s: %s", user_id, exc)
        await message.answer(
            get_message(language, "errors.review_save_failed"),
            reply_markup=get_main_menu_keyboard(language),
        )
        await send_main_menu_buttons(message, language)


async def handle_review_photo(message: Message, state: FSMContext) -> None:
    user_id = str(message.from_user.id)
    language = get_user_language(int(user_id))

    if message.text == get_message(language, "common.buttons.cancel"):
        logger.info("User %s cancelled review at photo step", user_id)
        await state.clear()
        await message.answer(
            get_message(language, "review.flow.cancelled"),
            reply_markup=get_main_menu_keyboard(language),
        )
        await send_main_menu_buttons(message, language)
        return

    image_url = None
    if message.text == get_message(language, "common.buttons.skip_optional"):
        logger.info("User %s skipped photo upload", user_id)
        await _finalize_review_submission(message, state, language, user_id, image_url)
        return

    if not message.photo:
        logger.warning("User %s sent message without photo", user_id)
        await message.answer(
            get_message(language, "review.flow.validation.photo_required")
        )
        return

    try:
        from io import BytesIO

        from src.bot.bot_instance import get_bot_instance
        from src.utils.s3_utils import upload_to_s3

        photo = message.photo[-1]
        if photo.file_size and photo.file_size > 5 * 1024 * 1024:
            await message.answer(
                get_message(language, "review.flow.validation.photo_too_large")
            )
            return

        bot = get_bot_instance()
        file = await bot.get_file(photo.file_id)
        file_data = await bot.download_file(file.file_path)
        file_content = file_data.read()

        file_type = validate_image_content(file_content)
        if not file_type or file_type not in ["jpg", "png"]:
            await message.answer(
                get_message(language, "review.flow.validation.invalid_photo_format")
            )
            return

        file_buffer = BytesIO(file_content)
        image_url = await upload_to_s3(file_buffer, file_type)

    except Exception as exc:
        logger.error("Error uploading photo for user %s: %s", user_id, exc)
        await message.answer(
            get_message(language, "review.flow.errors.photo_upload_failed")
        )
        return

    await _finalize_review_submission(message, state, language, user_id, image_url)


async def handle_skip_callback(
    callback: CallbackQuery, callback_data: SkipCallback, state: FSMContext
) -> None:
    user_id = callback.from_user.id
    telegram_id = str(user_id)
    language = get_user_language(user_id)
    current_state = await state.get_state()

    if callback_data.action == SkipAction.REVIEW_CONTACT.value:
        if current_state != ReviewStates.waiting_for_exact_address.state:
            await callback.answer(
                get_message(language, "errors.invalid_button"), show_alert=True
            )
            return

        await state.update_data(exact_address=None)
        await state.set_state(ReviewStates.waiting_for_content)
        await callback.message.answer(
            get_message(language, "review.flow.enter_content"),
            reply_markup=get_cancel_keyboard(language),
        )
        await callback.answer()
        return

    if callback_data.action == SkipAction.REVIEW_PHOTO.value:
        if current_state != ReviewStates.waiting_for_photo.state:
            await callback.answer(
                get_message(language, "errors.invalid_button"), show_alert=True
            )
            return

        await _finalize_review_submission(
            callback.message,
            state,
            language,
            telegram_id,
            image_url=None,
        )
        await callback.answer()
        return

    await callback.answer(
        get_message(language, "errors.invalid_button"), show_alert=True
    )

