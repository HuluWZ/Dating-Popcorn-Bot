"""
Main bot implementation for Dating Popcorn Bot
"""

import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, CallbackQuery

from config.settings import BOT_TOKEN, LOG_LEVEL, LOG_FORMAT
from src.bot.callbacks import (
    SearchCallback,
    SkipCallback,
    MainMenuCallback,
    LocationCallback,
)
from src.bot.states import ReviewStates, SearchStates
from src.bot.keyboards import (
    is_write_review_button_text,
    is_search_review_button_text,
)
from src.bot.flows import (
    handle_start_command,
    handle_location,
    handle_location_callback,
    handle_write_review_button,
    handle_review_name,
    handle_review_content,
    handle_review_exact_address,
    handle_review_photo,
    handle_skip_callback,
    handle_search_someone_button,
    handle_search_callback,
    handle_search_type_selection_text,
    handle_search_name,
    handle_search_image,
    handle_main_menu_callback,
    handle_main_menu_keyword,
    handle_unknown_message,
    detect_main_menu_keyword,
)
from src.database.init_db import initialize_database
from src.bot.bot_instance import bot, get_bot_instance

# Configure logging
logging.basicConfig(level=getattr(logging, LOG_LEVEL), format=LOG_FORMAT)
logger = logging.getLogger(__name__)

# Initialize dispatcher
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Register command handlers
dp.message.register(handle_start_command, Command("start"))

# Register location handler
dp.message.register(handle_location, lambda message: message.location is not None)

# Register callback query handlers
dp.callback_query.register(handle_search_callback, SearchCallback.filter())
dp.callback_query.register(handle_skip_callback, SkipCallback.filter())
dp.callback_query.register(handle_main_menu_callback, MainMenuCallback.filter())
dp.callback_query.register(handle_location_callback, LocationCallback.filter())

# Register FSM handlers (these have higher priority due to state filters)
dp.message.register(handle_review_name, ReviewStates.waiting_for_name)
dp.message.register(handle_review_content, ReviewStates.waiting_for_content)
dp.message.register(handle_review_exact_address, ReviewStates.waiting_for_exact_address)
dp.message.register(handle_review_photo, ReviewStates.waiting_for_photo)

dp.message.register(handle_search_name, SearchStates.waiting_for_name)
dp.message.register(handle_search_image, SearchStates.waiting_for_image)
dp.message.register(handle_search_type_selection_text, SearchStates.choosing_search_type)

# Register keyword handler for main menu (only when state is None and inline keyboard is shown)
# This must be registered BEFORE button text handlers to check keywords first
async def keyword_filter(message: Message, state) -> bool:
    """Filter to check if message should be handled by keyword handler.
    Only works when state is None (main menu with inline keyboard shown)"""
    if not message.text:
        return False
    current_state = await state.get_state()
    if current_state is not None:
        return False
    # Check if text matches a keyword (not button text)
    return detect_main_menu_keyword(message.text) is not None

dp.message.register(handle_main_menu_keyword, keyword_filter)

# Register button handlers (localized text matching) - registered AFTER keyword handler
# These handle actual button text from ReplyKeyboard buttons
dp.message.register(handle_write_review_button, lambda message: is_write_review_button_text(message.text))
dp.message.register(handle_search_someone_button, lambda message: is_search_review_button_text(message.text))

# Register fallback handler
dp.message.register(handle_unknown_message)

async def main():
    """Main function to run the bot"""
    logger.info("Starting Dating Popcorn Bot...")
    
    try:
        # Initialize database
        logger.info("Initializing database...")
        await initialize_database()
        logger.info("Database initialized successfully")
        
        # Start bot polling
        logger.info("Starting bot polling...")
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
