"""
Main bot implementation for Dating Popcorn Bot
"""

import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.filters import Command, StateFilter
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, CallbackQuery
from aiogram.filters.callback_data import CallbackData

from config.settings import BOT_TOKEN, LOG_LEVEL, LOG_FORMAT
from src.bot.handlers import (
    handle_start_command, handle_search_command, handle_write_command,
    handle_location, handle_action_callback, handle_language_callback,
    handle_search_callback, handle_write_review_button, handle_search_reviews_button,
    handle_language_button, handle_review_name, handle_review_contact,
    handle_review_text, handle_review_image, handle_search_name,
    handle_search_image, handle_unknown_message,
    ActionCallback, LanguageCallback, SearchCallback
)
from src.bot.handlers import ReviewStates, SearchStates

# Configure logging
logging.basicConfig(level=getattr(logging, LOG_LEVEL), format=LOG_FORMAT)
logger = logging.getLogger(__name__)

# Initialize bot and dispatcher
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Register command handlers
dp.message.register(handle_start_command, Command("start"))
dp.message.register(handle_search_command, Command("search"))
dp.message.register(handle_write_command, Command("write"))

# Register location handler
dp.message.register(handle_location, lambda message: message.location is not None)

# Register callback query handlers
dp.callback_query.register(handle_action_callback, ActionCallback.filter())
dp.callback_query.register(handle_language_callback, LanguageCallback.filter())
dp.callback_query.register(handle_search_callback, SearchCallback.filter())

# Register button handlers
dp.message.register(handle_write_review_button, lambda message: message.text in ["Write a Review", "Escribir una Reseña"])
dp.message.register(handle_search_reviews_button, lambda message: message.text in ["Search Reviews", "Buscar Reseñas"])
dp.message.register(handle_language_button, lambda message: message.text == "🌐 Language / Idioma")

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
