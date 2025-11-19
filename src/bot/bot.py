"""
Main bot implementation for Dating Popcorn Bot
"""

import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.filters import Command, StateFilter
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, CallbackQuery

from config.settings import BOT_TOKEN, LOG_LEVEL, LOG_FORMAT
from src.bot.user_flow import (
    handle_start_command, handle_location, 
    handle_search_callback, handle_write_review_button, 
    handle_search_someone_button, handle_review_name, 
    handle_review_content, handle_review_exact_address, handle_review_photo, 
    handle_search_name, handle_search_image, handle_unknown_message,
    SearchCallback, ReviewStates, SearchStates,
    is_write_review_button_text, is_search_review_button_text
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

# Register button handlers (localized text matching)
dp.message.register(handle_write_review_button, lambda message: is_write_review_button_text(message.text))
dp.message.register(handle_search_someone_button, lambda message: is_search_review_button_text(message.text))

# Register FSM handlers
dp.message.register(handle_review_name, ReviewStates.waiting_for_name)
dp.message.register(handle_review_content, ReviewStates.waiting_for_content)
dp.message.register(handle_review_exact_address, ReviewStates.waiting_for_exact_address)
dp.message.register(handle_review_photo, ReviewStates.waiting_for_photo)

dp.message.register(handle_search_name, SearchStates.waiting_for_name)
dp.message.register(handle_search_image, SearchStates.waiting_for_image)

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
