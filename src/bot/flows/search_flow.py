"""
Handlers for search flows (by name or image).
"""

from __future__ import annotations

import logging
import math
from typing import Optional

from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from src.bot.callbacks import SearchCallback
from src.bot.keyboards import get_search_type_keyboard
from src.bot.language import get_user_language
from src.bot.media import validate_image_content
from src.bot.menu_utils import send_location_button, send_main_menu_buttons
from src.bot.states import SearchStates
from src.utils.localization import get_message
from src.utils.review_display import ReviewDisplay
from src.bot.bot_instance import get_bot_instance

logger = logging.getLogger(__name__)


async def handle_search_someone_button(
    message: Message, state: FSMContext, user_id: Optional[int] = None
) -> None:
    if user_id is None:
        user_id = message.from_user.id

    user_id_str = str(user_id)
    language = get_user_language(user_id)

    try:
        from src.database.simple_db import (
            get_user,
            get_user_location,
            has_user_location,
        )

        user = await get_user(user_id_str)
        if user and user.location is not None:
            await state.set_state(SearchStates.choosing_search_type)
            await message.answer(
                get_message(language, "search.flow.choose_method"),
                reply_markup=get_search_type_keyboard(language),
            )
            return

        user_location = await get_user_location(user_id_str)
        if user_location or await has_user_location(user_id_str):
            await state.set_state(SearchStates.choosing_search_type)
            await message.answer(
                get_message(language, "search.flow.choose_method"),
                reply_markup=get_search_type_keyboard(language),
            )
            return

        await message.answer(
            get_message(language, "bot.location.required_for_search")
        )
        await send_location_button(message, language)

    except Exception as exc:
        logger.error("Error checking location for Search Reviews: %s", exc)
        try:
            from src.database.simple_db import get_user

            user = await get_user(user_id_str)
            if user and user.location is not None:
                await state.set_state(SearchStates.choosing_search_type)
                await message.answer(
                    get_message(language, "search.flow.choose_method"),
                    reply_markup=get_search_type_keyboard(language),
                )
                return
        except Exception as nested_exc:  # pragma: no cover - logging only
            logger.error("Error verifying user location fallback: %s", nested_exc)

        await message.answer(
            get_message(language, "bot.location.required_for_search")
        )
        await send_location_button(message, language)


async def handle_search_callback(
    callback: CallbackQuery, callback_data: SearchCallback, state: FSMContext
) -> None:
    user_id = callback.from_user.id
    language = get_user_language(user_id)

    if callback_data.search_type == "name":
        await state.set_state(SearchStates.waiting_for_name)
        await callback.message.edit_text(
            get_message(language, "search.flow.by_name.prompt")
        )
    elif callback_data.search_type == "image":
        await state.set_state(SearchStates.waiting_for_image)
        await callback.message.edit_text(
            get_message(language, "search.flow.by_image.prompt")
        )

    await callback.answer()


async def handle_search_type_selection_text(
    message: Message, state: FSMContext
) -> None:
    user_id = message.from_user.id
    language = get_user_language(user_id)

    await message.answer(get_message(language, "errors.invalid_button"))
    await message.answer(
        get_message(language, "search.flow.choose_method"),
        reply_markup=get_search_type_keyboard(language),
    )


async def handle_search_name(message: Message, state: FSMContext) -> None:
    user_id = message.from_user.id
    telegram_id = str(user_id)
    language = get_user_language(user_id)

    if not message.text or len(message.text.strip()) < 2:
        await message.answer(get_message(language, "common.validation.name_required"))
        return

    search_query = message.text.strip()
    await message.answer(
        get_message(language, "search.results.searching", name=search_query)
    )

    try:
        from src.database.services import SearchService

        search_results = await SearchService.advanced_search_by_name_and_location(
            searcher_telegram_id=telegram_id,
            query=search_query,
            radius_km=50,
        )

        if not search_results:
            await message.answer(get_message(language, "search.results.none_found"))
            await send_main_menu_buttons(message, language)
            await state.clear()
            return

        reviews = []
        for review_obj, match_count, distance_km in search_results:
            rounded_distance = math.ceil(distance_km) if distance_km > 0 else 1

            reviewer_username = None
            reviewer = getattr(review_obj, "reviewer", None)
            if reviewer and reviewer.username:
                reviewer_username = reviewer.username

            reviews.append(
                {
                    "name": review_obj.full_name,
                    "content": review_obj.content,
                    "distance": rounded_distance,
                    "image": review_obj.image_url,
                    "reviewer_username": reviewer_username,
                }
            )

        bot = get_bot_instance()
        review_display = ReviewDisplay(bot)
        await review_display.display_reviews(message, reviews, language)

    except Exception as exc:
        logger.error("Error in name search for user %s: %s", user_id, exc)
        await message.answer("Sorry, there was an error searching. Please try again.")

    await send_main_menu_buttons(message, language)
    await state.clear()


async def handle_search_image(message: Message, state: FSMContext) -> None:
    user_id = message.from_user.id
    telegram_id = str(user_id)
    language = get_user_language(user_id)

    from src.utils.rate_limiter import check_rate_limit

    is_allowed, rate_limit_error = check_rate_limit(telegram_id)
    if not is_allowed:
        await message.answer(rate_limit_error or get_message(language, "errors.rate_limit"))
        await state.clear()
        return

    if not message.photo:
        await message.answer(get_message(language, "search.flow.by_image.upload_required"))
        await state.clear()
        return

    from src.database.simple_db import get_user_location

    user_location = await get_user_location(telegram_id)
    if not user_location:
        await message.answer(get_message(language, "bot.location.required_for_search"))
        await send_location_button(message, language)
        await state.clear()
        return

    user_latitude, user_longitude = user_location
    await message.answer(get_message(language, "search.flow.by_image.received"))
    await message.answer(get_message(language, "search.flow.by_image.processing"))

    from src.utils.image_comparison import search_by_image
    from src.utils.face_embedding import FaceDetectionError

    uploaded_image_bytes = None

    try:
        bot = get_bot_instance()
        photo = message.photo[-1]

        file = await bot.get_file(photo.file_id)
        file_data = await bot.download_file(file.file_path)
        uploaded_image_bytes = file_data.read()

        file_type = validate_image_content(uploaded_image_bytes)
        if not file_type or file_type not in ["jpg", "png"]:
            await message.answer(
                get_message(language, "review.flow.validation.invalid_photo_format")
            )
            await state.clear()
            return

        matches = await search_by_image(
            uploaded_image_bytes=uploaded_image_bytes,
            user_latitude=user_latitude,
            user_longitude=user_longitude,
            radius_km=50,
        )

        if matches:
            review_dicts = []
            for match in matches:
                review = match.review
                reviewer_username = None
                reviewer = getattr(review, "reviewer", None)
                if reviewer and reviewer.username:
                    reviewer_username = reviewer.username

                review_dicts.append(
                    {
                        "name": review.full_name,
                        "content": review.content,
                        "distance": match.distance_km or 0,
                        "exact_address": review.exact_address,
                        "image": review.image_url,
                        "similarity": match.similarity,
                        "reviewer_username": reviewer_username,
                    }
                )

            review_dicts.sort(key=lambda x: x.get("similarity", 0), reverse=True)
            review_dicts = review_dicts[:3]

            bot = get_bot_instance()
            review_display = ReviewDisplay(bot)
            await review_display.display_reviews(message, review_dicts, language)
        else:
            await message.answer(get_message(language, "search.results.none_found"))

        await send_main_menu_buttons(message, language)

    except FaceDetectionError as exc:
        error_code = getattr(exc, "error_code", "UNKNOWN")
        code_map = {
            "NO_FACE": "search.flow.by_image.errors.no_face_detected",
            "FACE_TOO_SMALL_OR_LOW_QUALITY": "search.flow.by_image.errors.face_too_small_or_low_quality",
            "INVALID_IMAGE": "search.flow.by_image.errors.invalid_image",
            "IMAGE_TOO_LARGE": "search.flow.by_image.errors.image_too_large",
        }
        await message.answer(
            get_message(language, code_map.get(error_code, "search.flow.by_image.errors.detection_failed"))
        )
        await send_main_menu_buttons(message, language)
    except Exception as exc:  # pragma: no cover - unexpected errors
        logger.error("Unexpected error in image search: %s", exc)
        await message.answer(get_message(language, "errors.general"))
        await send_main_menu_buttons(message, language)

    await state.clear()

