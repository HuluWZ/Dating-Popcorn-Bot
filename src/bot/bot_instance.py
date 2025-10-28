"""
Bot instance management to avoid circular imports
"""

from aiogram import Bot
from config.settings import BOT_TOKEN

# Global bot instance
bot = Bot(token=BOT_TOKEN)

def get_bot_instance():
    """Get the global bot instance"""
    return bot
