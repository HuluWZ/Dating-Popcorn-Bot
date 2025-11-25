"""
Backward compatibility facade for legacy imports.
"""

from src.bot.callbacks import (
    SearchCallback,
    SkipCallback,
    MainMenuCallback,
    LocationCallback,
    SkipAction,
)
from src.bot.language import (
    detect_user_language,
    get_user_language,
    set_user_language,
)
from src.bot.media import validate_image_content
from src.bot.states import ReviewStates, SearchStates
from src.bot.keyboards import (
    MainMenuAction,
    get_main_menu_keyboard,
    get_main_menu_inline_keyboard,
    get_location_keyboard,
    get_location_inline_keyboard,
    get_search_type_keyboard,
    get_cancel_keyboard,
    get_skip_reply_keyboard,
    get_skip_inline_keyboard,
    is_write_review_button_text,
    is_search_review_button_text,
)
from src.bot.menu_utils import (
    send_location_button,
    send_location_request_keyboard,
    send_main_menu_buttons,
    send_skip_hint,
)
from src.bot.flows.start_flow import (
    handle_start_command,
    handle_location,
    handle_location_callback,
)
from src.bot.flows.review_flow import (
    handle_write_review_button,
    handle_review_name,
    handle_review_content,
    handle_review_exact_address,
    handle_review_photo,
    handle_skip_callback,
)
from src.bot.flows.search_flow import (
    handle_search_someone_button,
    handle_search_callback,
    handle_search_type_selection_text,
    handle_search_name,
    handle_search_image,
)
from src.bot.flows.main_menu_flow import (
    handle_main_menu_callback,
    handle_main_menu_keyword,
    handle_unknown_message,
    detect_main_menu_keyword,
)

__all__ = [
    # helpers
    "detect_user_language",
    "get_user_language",
    "set_user_language",
    "validate_image_content",
    "MainMenuAction",
    "get_main_menu_keyboard",
    "get_main_menu_inline_keyboard",
    "get_location_keyboard",
    "get_location_inline_keyboard",
    "get_search_type_keyboard",
    "get_cancel_keyboard",
    "get_skip_reply_keyboard",
    "get_skip_inline_keyboard",
    "is_write_review_button_text",
    "is_search_review_button_text",
    "send_location_button",
    "send_location_request_keyboard",
    "send_main_menu_buttons",
    "send_skip_hint",
    # states
    "ReviewStates",
    "SearchStates",
    # callbacks
    "SearchCallback",
    "SkipCallback",
    "MainMenuCallback",
    "LocationCallback",
    "SkipAction",
    # handlers
    "handle_start_command",
    "handle_location",
    "handle_location_callback",
    "handle_write_review_button",
    "handle_review_name",
    "handle_review_content",
    "handle_review_exact_address",
    "handle_review_photo",
    "handle_skip_callback",
    "handle_search_someone_button",
    "handle_search_callback",
    "handle_search_type_selection_text",
    "handle_search_name",
    "handle_search_image",
    "handle_main_menu_callback",
    "handle_main_menu_keyword",
    "handle_unknown_message",
    "detect_main_menu_keyword",
]

