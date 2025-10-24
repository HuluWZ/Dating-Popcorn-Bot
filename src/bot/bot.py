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
    handle_review_contact, handle_review_text, handle_review_image, 
    handle_search_name, handle_search_image, handle_unknown_message,
    SearchCallback, ReviewStates, SearchStates
)

# Configure logging
logging.basicConfig(level=getattr(logging, LOG_LEVEL), format=LOG_FORMAT)
logger = logging.getLogger(__name__)

# Initialize bot and dispatcher
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Make bot instance available globally for review display
def get_bot_instance():
    """Get the global bot instance"""
    return bot

# Register command handlers
dp.message.register(handle_start_command, Command("start"))

# Register location handler
dp.message.register(handle_location, lambda message: message.location is not None)

# Register callback query handlers
dp.callback_query.register(handle_search_callback, SearchCallback.filter())

# Register button handlers (using dynamic text matching)
dp.message.register(handle_write_review_button, lambda message: message.text and "write" in message.text.lower() and "review" in message.text.lower())
dp.message.register(handle_search_someone_button, lambda message: message.text and "search" in message.text.lower() and "review" in message.text.lower())

# Register FSM handlers
dp.message.register(handle_review_name, ReviewStates.waiting_for_name)
dp.message.register(handle_review_contact, ReviewStates.waiting_for_contact)
dp.message.register(handle_review_text, ReviewStates.waiting_for_text)
dp.message.register(handle_review_image, ReviewStates.waiting_for_image)

dp.message.register(handle_search_name, SearchStates.waiting_for_name)
dp.message.register(handle_search_image, SearchStates.waiting_for_image)

# Register fallback handler
dp.message.register(handle_unknown_message)

async def main():
    """Main function to run the bot"""
    logger.info("Starting Dating Popcorn Bot...")
    
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
