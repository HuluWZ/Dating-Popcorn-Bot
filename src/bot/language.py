"""
Language detection and per-user language preference helpers.
"""

from __future__ import annotations

import logging
from typing import Dict

from aiogram.types import Message  # type: ignore

from config.settings import SUPPORTED_LANGUAGES, DEFAULT_LANGUAGE

logger = logging.getLogger(__name__)

# Simple in-memory store keyed by telegram user id
user_languages: Dict[int, str] = {}


def detect_user_language(message: Message) -> str:
    """
    Detect user's Telegram language and map to supported locale.
    Defaults to English when unsupported.
    """
    user_lang_code = message.from_user.language_code
    logger.info("User %s language_code: %s", message.from_user.id, user_lang_code)

    if user_lang_code and user_lang_code in SUPPORTED_LANGUAGES:
        logger.info("Using user's language: %s", user_lang_code)
        return user_lang_code

    logger.info(
        "User language '%s' not supported, defaulting to %s",
        user_lang_code,
        DEFAULT_LANGUAGE,
    )
    return DEFAULT_LANGUAGE


def get_user_language(user_id: int) -> str:
    """Return persisted language preference or default."""
    return user_languages.get(user_id, DEFAULT_LANGUAGE)


def set_user_language(user_id: int, language: str) -> None:
    """Persist user's preferred language for current session."""
    user_languages[user_id] = language

