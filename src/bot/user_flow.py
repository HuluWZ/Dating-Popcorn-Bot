"""
User flow handlers for Dating Popcorn Bot - Simple flow without data storage
"""

import logging
from typing import Optional
from aiogram import Bot, Dispatcher
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters.callback_data import CallbackData

from config.settings import SUPPORTED_LANGUAGES, DEFAULT_LANGUAGE
from src.utils.localization import get_message

logger = logging.getLogger(__name__)

# Simple language storage per user session
user_languages: dict[int, str] = {}

# FSM States
class ReviewStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_contact = State()
    waiting_for_text = State()
    waiting_for_image = State()

class SearchStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_image = State()

# Callback data classes
class LanguageCallback(CallbackData, prefix="lang"):
    language: str

class SearchCallback(CallbackData, prefix="search"):
    search_type: str

# Helper functions
def detect_user_language(message: Message) -> str:
    """
    Detect user's language from Telegram settings
    Returns user's language if supported, 'en' as default
    """
    # Get user's language code from Telegram
    user_lang_code = message.from_user.language_code
    
    # Log the detected language for debugging
    logger.info(f"User {message.from_user.id} language_code: {user_lang_code}")
    
    # Check if user's language code exists in our supported languages
    if user_lang_code and user_lang_code in SUPPORTED_LANGUAGES:
        logger.info(f"Using user's language: {user_lang_code}")
        return user_lang_code
    else:
        logger.info(f"User language '{user_lang_code}' not supported, defaulting to {DEFAULT_LANGUAGE}")
        return DEFAULT_LANGUAGE  # Default to English for unsupported languages

def get_user_language(user_id: int) -> str:
    """Get user's preferred language"""
    return user_languages.get(user_id, DEFAULT_LANGUAGE)

def set_user_language(user_id: int, language: str):
    """Set user's preferred language"""
    user_languages[user_id] = language

def get_main_menu_keyboard(language: str) -> ReplyKeyboardMarkup:
    """Get main menu keyboard with Write Review and Search Someone buttons"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=get_message(language, 'common.buttons.write_review')),
                KeyboardButton(text=get_message(language, 'common.buttons.search_reviews'))
            ],
            [KeyboardButton(text=get_message(language, 'common.buttons.language_button'))]
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )
    return keyboard

def get_location_keyboard(language: str) -> ReplyKeyboardMarkup:
    """Get location sharing keyboard"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=get_message(language, 'common.buttons.share_location'), request_location=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    return keyboard

def get_search_type_keyboard(language: str) -> InlineKeyboardMarkup:
    """Get search type selection keyboard"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text=get_message(language, 'search.flow.by_name.button'),
                callback_data=SearchCallback(search_type="name").pack()
            )],
            [InlineKeyboardButton(
                text=get_message(language, 'search.flow.by_image.button'),
                callback_data=SearchCallback(search_type="image").pack()
            )]
        ]
    )
    return keyboard

def get_language_keyboard() -> InlineKeyboardMarkup:
    """Get language selection keyboard"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🇺🇸 English", callback_data=LanguageCallback(language="en").pack())],
            [InlineKeyboardButton(text="🇪🇸 Español", callback_data=LanguageCallback(language="es").pack())]
        ]
    )
    return keyboard

def get_cancel_keyboard(language: str) -> ReplyKeyboardMarkup:
    """Get cancel keyboard"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=get_message(language, 'common.buttons.cancel'))]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    return keyboard

def get_skip_keyboard(language: str) -> ReplyKeyboardMarkup:
    """Get skip keyboard"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=get_message(language, 'common.buttons.skip_optional'))]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    return keyboard

# Main user flow handler
async def handle_start_command(message: Message, state: FSMContext):
    """Handle /start command - automatically detect language and request location"""
    user_id = message.from_user.id
    
    # Automatically detect user's language from Telegram settings
    detected_language = detect_user_language(message)
    set_user_language(user_id, detected_language)
    
    logger.info(f"User {user_id} started bot with language: {detected_language}")
    
    # Send welcome message in detected language and request location
    await message.answer(
        get_message(detected_language, 'bot.welcome.message', name=message.from_user.first_name or "User"),
        reply_markup=get_location_keyboard(detected_language)
    )

# Location handler
async def handle_location(message: Message, state: FSMContext):
    """Handle location sharing"""
    user_id = message.from_user.id
    language = get_user_language(user_id)
    
    # Remove the location button and show main menu
    await message.answer(
        get_message(language, 'bot.location.received'),
        reply_markup=get_main_menu_keyboard(language)
    )

# Main menu button handlers
async def handle_write_review_button(message: Message, state: FSMContext):
    """Handle Write Review button"""
    user_id = message.from_user.id
    language = get_user_language(user_id)
    
    await state.set_state(ReviewStates.waiting_for_name)
    await message.answer(
        get_message(language, 'review.flow.enter_name'),
        reply_markup=get_cancel_keyboard(language)
    )

async def handle_search_someone_button(message: Message, state: FSMContext):
    """Handle Search Someone button"""
    user_id = message.from_user.id
    language = get_user_language(user_id)
    
    await message.answer(
        get_message(language, 'search.flow.choose_method'),
        reply_markup=get_search_type_keyboard(language)
    )

async def handle_language_button(message: Message, state: FSMContext):
    """Handle language selection button"""
    user_id = message.from_user.id
    current_language = get_user_language(user_id)
    
    await message.answer(
        get_message(current_language, 'bot.language_selection.title'),
        reply_markup=get_language_keyboard()
    )

# Language selection
async def handle_language_callback(callback: CallbackQuery, callback_data: LanguageCallback, state: FSMContext):
    """Handle language selection"""
    user_id = callback.from_user.id
    language = callback_data.language
    
    # Store user's language preference
    set_user_language(user_id, language)
    
    logger.info(f"User {user_id} manually changed language to: {language}")
    
    # Update the message to show language change confirmation
    await callback.message.edit_text(
        get_message(language, 'bot.main_menu.language_changed', language=language.upper())
    )
    
    # Send main menu in the new language
    await callback.message.answer(
        get_message(language, 'bot.main_menu.choose_action'),
        reply_markup=get_main_menu_keyboard(language)
    )
    
    await callback.answer()

# Search callbacks
async def handle_search_callback(callback: CallbackQuery, callback_data: SearchCallback, state: FSMContext):
    """Handle search type selection"""
    user_id = callback.from_user.id
    language = get_user_language(user_id)
    
    if callback_data.search_type == "name":
        await state.set_state(SearchStates.waiting_for_name)
        await callback.message.edit_text(
            get_message(language, 'search.flow.by_name.prompt')
        )
    elif callback_data.search_type == "image":
        await state.set_state(SearchStates.waiting_for_image)
        await callback.message.edit_text(
            get_message(language, 'search.flow.by_image.prompt')
        )
    
    await callback.answer()

# Review flow handlers
async def handle_review_name(message: Message, state: FSMContext):
    """Handle review name input"""
    user_id = message.from_user.id
    language = get_user_language(user_id)
    
    if message.text == get_message(language, 'common.buttons.cancel'):
        await state.clear()
        await message.answer(
            get_message(language, 'bot.main_menu.choose_action'),
            reply_markup=get_main_menu_keyboard(language)
        )
        return
    
    if not message.text or len(message.text.strip()) < 2:
        await message.answer(get_message(language, 'review.flow.validation.name_too_short'))
        return
    
    await state.update_data(full_name=message.text.strip())
    await state.set_state(ReviewStates.waiting_for_contact)
    
    await message.answer(
        get_message(language, 'review.flow.enter_contact', name=message.text.strip()),
        reply_markup=get_skip_keyboard(language)
    )

async def handle_review_contact(message: Message, state: FSMContext):
    """Handle review contact input"""
    user_id = message.from_user.id
    language = get_user_language(user_id)
    data = await state.get_data()
    
    if message.text == get_message(language, 'common.buttons.skip_optional'):
        exact_information = None
    else:
        exact_information = message.text.strip()
    
    await state.update_data(exact_information=exact_information)
    await state.set_state(ReviewStates.waiting_for_text)
    
    await message.answer(
        get_message(language, 'review.flow.enter_text'),
        reply_markup=get_cancel_keyboard(language)
    )

async def handle_review_text(message: Message, state: FSMContext):
    """Handle review text input"""
    user_id = message.from_user.id
    language = get_user_language(user_id)
    
    if message.text == get_message(language, 'common.buttons.cancel'):
        await state.clear()
        await message.answer(
            get_message(language, 'bot.main_menu.choose_action'),
            reply_markup=get_main_menu_keyboard(language)
        )
        return
    
    if not message.text or len(message.text.strip()) < 10:
        await message.answer(get_message(language, 'review.flow.validation.text_too_short'))
        return
    
    await state.update_data(review_content=message.text.strip())
    await state.set_state(ReviewStates.waiting_for_image)
    
    data = await state.get_data()
    await message.answer(
        get_message(language, 'review.flow.upload_image', name=data['full_name']),
        reply_markup=get_skip_keyboard(language)
    )

async def handle_review_image(message: Message, state: FSMContext):
    """Handle review image input"""
    user_id = message.from_user.id
    language = get_user_language(user_id)
    data = await state.get_data()
    
    if message.text == get_message(language, 'common.buttons.skip_optional'):
        # Skip image upload
        pass
    else:
        # Handle image upload
        if message.photo:
            # In production, save image to S3 and get URL
            image_file_id = message.photo[-1].file_id
            # Just acknowledge the image was received
            pass
        else:
            await message.answer(get_message(language, 'review.flow.upload_image_required'))
            return
    
    # Show completion message (no actual storage)
    await state.clear()
    
    await message.answer(
        get_message(language, 'review.flow.saved'),
        reply_markup=get_main_menu_keyboard(language)
    )

# Search flow handlers
async def handle_search_name(message: Message, state: FSMContext):
    """Handle name search input"""
    user_id = message.from_user.id
    language = get_user_language(user_id)
    
    if not message.text or len(message.text.strip()) < 2:
        await message.answer(get_message(language, 'common.validation.name_required'))
        return
    
    # Mock search results (no actual storage)
    search_name = message.text.strip()
    await message.answer(
        get_message(language, 'search.results.searching', name=search_name)
    )
    
    # Simulate search delay
    import asyncio
    await asyncio.sleep(1)
    
    # Show mock results
    await message.answer(
        get_message(language, 'search.results.mock_results'),
        reply_markup=get_main_menu_keyboard(language)
    )
    
    await state.clear()

async def handle_search_image(message: Message, state: FSMContext):
    """Handle image search input"""
    user_id = message.from_user.id
    language = get_user_language(user_id)
    
    if message.photo:
        await message.answer(get_message(language, 'search.flow.by_image.processing'))
        
        # Simulate image processing delay
        import asyncio
        await asyncio.sleep(2)
        
        # Show mock results
        await message.answer(
            get_message(language, 'search.results.mock_image_results'),
            reply_markup=get_main_menu_keyboard(language)
        )
    else:
        await message.answer(get_message(language, 'search.flow.by_image.upload_required'))
    
    await state.clear()

# Error handler
async def handle_unknown_message(message: Message):
    """Handle unknown messages"""
    user_id = message.from_user.id
    language = get_user_language(user_id)
    
    await message.answer(
        get_message(language, 'errors.general'),
        reply_markup=get_main_menu_keyboard(language)
    )
