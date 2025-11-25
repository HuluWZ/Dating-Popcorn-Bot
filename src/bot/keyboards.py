"""
Keyboard builders and button helpers for the bot flows.
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, Optional

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from config.settings import SUPPORTED_LANGUAGES
from src.utils.localization import get_message
from src.bot.callbacks import (
    SkipAction,
    SkipCallback,
    MainMenuCallback,
    LocationCallback,
    SearchCallback,
)


class MainMenuAction(str, Enum):
    WRITE_REVIEW = "common.buttons.write_review"
    SEARCH_REVIEWS = "common.buttons.search_reviews"


def _normalize_button_text(text: str) -> str:
    return text.strip().lower()


def _build_main_menu_button_map() -> Dict[str, MainMenuAction]:
    mapping: Dict[str, MainMenuAction] = {}
    for action in MainMenuAction:
        for locale in SUPPORTED_LANGUAGES:
            localized_text = get_message(locale, action.value)
            if localized_text:
                mapping[_normalize_button_text(localized_text)] = action
    return mapping


MAIN_MENU_BUTTON_MAP = _build_main_menu_button_map()


def get_main_menu_action_from_text(text: Optional[str]) -> Optional[MainMenuAction]:
    if not text:
        return None
    return MAIN_MENU_BUTTON_MAP.get(_normalize_button_text(text))


def is_write_review_button_text(text: Optional[str]) -> bool:
    return get_main_menu_action_from_text(text) == MainMenuAction.WRITE_REVIEW


def is_search_review_button_text(text: Optional[str]) -> bool:
    return get_main_menu_action_from_text(text) == MainMenuAction.SEARCH_REVIEWS


def get_main_menu_keyboard(language: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text=get_message(language, MainMenuAction.WRITE_REVIEW.value)
                ),
                KeyboardButton(
                    text=get_message(language, MainMenuAction.SEARCH_REVIEWS.value)
                ),
            ]
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
    )


def get_main_menu_inline_keyboard(language: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=get_message(language, MainMenuAction.WRITE_REVIEW.value),
                    callback_data=MainMenuCallback(
                        action=MainMenuAction.WRITE_REVIEW.value
                    ).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text=get_message(language, MainMenuAction.SEARCH_REVIEWS.value),
                    callback_data=MainMenuCallback(
                        action=MainMenuAction.SEARCH_REVIEWS.value
                    ).pack(),
                )
            ],
        ]
    )


def get_location_keyboard(language: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text=get_message(language, "common.buttons.share_location"),
                    request_location=True,
                )
            ]
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def get_location_inline_keyboard(language: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=get_message(language, "common.buttons.share_location"),
                    callback_data=LocationCallback().pack(),
                )
            ]
        ]
    )


def get_search_type_keyboard(language: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=get_message(language, "search.flow.by_name.button"),
                    callback_data=SearchCallback(search_type="name").pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text=get_message(language, "search.flow.by_image.button"),
                    callback_data=SearchCallback(search_type="image").pack(),
                )
            ],
        ]
    )


def get_cancel_keyboard(language: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=get_message(language, "common.buttons.cancel"))]
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def get_skip_reply_keyboard(language: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=get_message(language, "common.buttons.skip_optional"))]
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def get_skip_inline_keyboard(language: str, action: SkipAction) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=get_message(language, "common.buttons.skip_optional"),
                    callback_data=SkipCallback(action=action.value).pack(),
                )
            ]
        ]
    )

