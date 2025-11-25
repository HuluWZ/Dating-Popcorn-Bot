"""
CallbackData helpers and enums shared across flows.
"""

from enum import Enum

from aiogram.filters.callback_data import CallbackData


class SkipAction(str, Enum):
    REVIEW_CONTACT = "review_contact"
    REVIEW_PHOTO = "review_photo"


class SearchCallback(CallbackData, prefix="search"):
    search_type: str


class SkipCallback(CallbackData, prefix="skip"):
    action: str


class MainMenuCallback(CallbackData, prefix="menu"):
    action: str


class LocationCallback(CallbackData, prefix="location"):
    action: str = "share"

