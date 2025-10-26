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
from src.utils.review_display import ReviewDisplay, create_mock_reviews, create_mock_image_reviews

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
            ]
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
    """Handle /start command - check user existence and location status"""
    user_id = str(message.from_user.id)  # Convert to string for database
    username = message.from_user.username
    
    # Automatically detect user's language from Telegram settings
    detected_language = detect_user_language(message)
    set_user_language(int(user_id), detected_language)
    
    logger.info(f"User {user_id} started bot with language: {detected_language}")
    
    try:
        # Import database functions
        from src.database.simple_db import get_user, create_or_get_user, has_user_location
        
        # Check if user exists in database
        logger.info(f"Checking if user {user_id} exists in database...")
        user = await get_user(user_id)
        
        if user is None:
            # User doesn't exist - register them
            logger.info(f"User {user_id} not found, creating new user...")
            user = await create_or_get_user(user_id, username)
            logger.info(f"Created new user: {user.id}")
            
            # Send welcome message and request location
            await message.answer(
                get_message(detected_language, 'bot.welcome.message', name=message.from_user.first_name or "User"),
                reply_markup=get_location_keyboard(detected_language)
            )
        else:
            # User exists - check if they have location
            logger.info(f"User {user_id} found in database")
            has_location = await has_user_location(user_id)
            
            if not has_location:
                # User exists but no location - request location
                logger.info(f"User {user_id} exists but has no location, requesting location...")
                await message.answer(
                    get_message(detected_language, 'bot.welcome.message', name=message.from_user.first_name or "User"),
                    reply_markup=get_location_keyboard(detected_language)
                )
            else:
                # User exists and has location - show main menu
                logger.info(f"User {user_id} exists and has location, showing main menu...")
                await message.answer(
                    get_message(detected_language, 'bot.main_menu.welcome_back', name=message.from_user.first_name or "User"),
                    reply_markup=get_main_menu_keyboard(detected_language)
                )
                
    except Exception as e:
        logger.error(f"Error in handle_start_command for user {user_id}: {e}")
        # Fallback to requesting location
        await message.answer(
            get_message(detected_language, 'bot.welcome.message', name=message.from_user.first_name or "User"),
            reply_markup=get_location_keyboard(detected_language)
        )

# Location handler
async def handle_location(message: Message, state: FSMContext):
    """Handle location sharing and save to database"""
    user_id = str(message.from_user.id)  # Convert to string for database
    language = get_user_language(int(user_id))
    
    # Log location data for monitoring
    location = message.location
    if location:
        logger.info(f"User {user_id} shared location: lat={location.latitude}, lng={location.longitude}, accuracy={location.horizontal_accuracy}")
    else:
        logger.warning(f"User {user_id} sent location message but location data is None")
        await message.answer(get_message(language, 'errors.location_not_received'))
        return
    
    try:
        # Import database functions
        from src.database.simple_db import set_user_location
        
        # Save location to database
        logger.info(f"Saving location for user {user_id}: lat={location.latitude}, lng={location.longitude}")
        success = await set_user_location(user_id, location.latitude, location.longitude)
        
        if success:
            logger.info(f"Location saved successfully for user {user_id}: lat={location.latitude}, lng={location.longitude}")
            await message.answer(
                get_message(language, 'bot.location.received'),
                reply_markup=get_main_menu_keyboard(language)
            )
        else:
            logger.warning(f"Failed to save location for user {user_id} - location may already be set (lat={location.latitude}, lng={location.longitude})")
            await message.answer(
                get_message(language, 'bot.location.already_set'),
                reply_markup=get_main_menu_keyboard(language)
            )
            
    except Exception as e:
        logger.error(f"Error saving location for user {user_id}: {e}")
        await message.answer(
            get_message(language, 'errors.location_save_failed'),
            reply_markup=get_main_menu_keyboard(language)
        )

# Main menu button handlers
async def handle_write_review_button(message: Message, state: FSMContext):
    """Handle Write Review button - check location first"""
    user_id = str(message.from_user.id)  # Convert to string for database
    language = get_user_language(int(user_id))
    
    try:
        # Import database functions
        from src.database.simple_db import has_user_location
        
        # Check if user has location
        logger.info(f"Checking location for user {user_id} before Write Review...")
        has_location = await has_user_location(user_id)
        
        if not has_location:
            logger.info(f"User {user_id} has no location, requesting location for Write Review...")
            await message.answer(
                get_message(language, 'bot.location.required_for_review'),
                reply_markup=get_location_keyboard(language)
            )
            return
        
        logger.info(f"User {user_id} has location, proceeding with Write Review...")
        await state.set_state(ReviewStates.waiting_for_name)
        await message.answer(
            get_message(language, 'review.flow.enter_name'),
            reply_markup=get_cancel_keyboard(language)
        )
        
    except Exception as e:
        logger.error(f"Error checking location for Write Review for user {user_id}: {e}")
        # Fallback to requesting location
        await message.answer(
            get_message(language, 'bot.location.required_for_review'),
            reply_markup=get_location_keyboard(language)
        )

async def handle_search_someone_button(message: Message, state: FSMContext):
    """Handle Search Someone button - check location first"""
    user_id = str(message.from_user.id)  # Convert to string for database
    language = get_user_language(int(user_id))
    
    try:
        # Import database functions
        from src.database.simple_db import has_user_location
        
        # Check if user has location
        logger.info(f"Checking location for user {user_id} before Search Reviews...")
        has_location = await has_user_location(user_id)
        
        if not has_location:
            logger.info(f"User {user_id} has no location, requesting location for Search Reviews...")
            await message.answer(
                get_message(language, 'bot.location.required_for_search'),
                reply_markup=get_location_keyboard(language)
            )
            return
        
        logger.info(f"User {user_id} has location, proceeding with Search Reviews...")
        await message.answer(
            get_message(language, 'search.flow.choose_method'),
            reply_markup=get_search_type_keyboard(language)
        )
        
    except Exception as e:
        logger.error(f"Error checking location for Search Reviews for user {user_id}: {e}")
        # Fallback to requesting location
        await message.answer(
            get_message(language, 'bot.location.required_for_search'),
            reply_markup=get_location_keyboard(language)
        )



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
    """Handle review image input and save review to database"""
    user_id = str(message.from_user.id)  # Convert to string for database
    language = get_user_language(int(user_id))
    data = await state.get_data()
    
    # Get review data
    full_name = data.get('full_name')
    social_handle = data.get('exact_information')
    review_content = data.get('review_content')
    
    logger.info(f"Processing review submission for user {user_id}: name='{full_name}', social_handle='{social_handle}', content_length={len(review_content) if review_content else 0}")
    
    # Handle image upload
    image_file_id = None
    if message.text == get_message(language, 'common.buttons.skip_optional'):
        # Skip image upload
        logger.info(f"User {user_id} skipped image upload for review")
    else:
        # Handle image upload
        if message.photo:
            # In production, save image to S3 and get URL
            image_file_id = message.photo[-1].file_id
            logger.info(f"User {user_id} uploaded image for review: file_id={image_file_id}")
        else:
            await message.answer(get_message(language, 'review.flow.upload_image_required'))
            return
    
    try:
        # Import database functions
        from src.database.simple_db import create_review
        
        # Save review to database
        logger.info(f"Saving review to database for user {user_id}: name='{full_name}', social_handle='{social_handle}', content='{review_content[:100]}...'")
        
        review = await create_review(
            reviewer_id=user_id,
            full_name=full_name,
            content=review_content,
            social_handle=social_handle,
            images=[image_file_id] if image_file_id else None
        )
        
        logger.info(f"Review saved successfully: id={review.id}, reviewer_id={review.reviewer_id}, full_name='{review.full_name}', status='{review.status.value}'")
        
        # Clear state and show success message
        await state.clear()
        
        await message.answer(
            get_message(language, 'review.flow.saved'),
            reply_markup=get_main_menu_keyboard(language)
        )
        
    except Exception as e:
        logger.error(f"Error saving review for user {user_id}: {e}")
        await message.answer(
            get_message(language, 'errors.review_save_failed'),
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
    
    # Use new review display system
    # Use shared bot instance for efficiency
    from src.bot.bot import get_bot_instance
    bot = get_bot_instance()
    review_display = ReviewDisplay(bot)
    mock_reviews = create_mock_reviews()
    
    await review_display.display_reviews(message, mock_reviews, language)
    
    # Show main menu
    await message.answer(
        get_message(language, 'bot.main_menu.choose_action'),
        reply_markup=get_main_menu_keyboard(language)
    )
    
    await state.clear()

async def handle_search_image(message: Message, state: FSMContext):
    """Handle image search input"""
    user_id = message.from_user.id
    language = get_user_language(user_id)
    logger.info(f"Image search input: {message.photo} \n Message: {message}") 
    if message.photo:
        # Image received - show confirmation and processing message
        await message.answer(get_message(language, 'search.flow.by_image.received'))
        
        # Show processing message
        await message.answer(get_message(language, 'search.flow.by_image.processing'))
        
        # Simulate image processing delay
        import asyncio
        await asyncio.sleep(2)
        
        # Use new review display system for image results
        # Use shared bot instance for efficiency
        from src.bot.bot import get_bot_instance
        bot = get_bot_instance()
        review_display = ReviewDisplay(bot)
        mock_image_reviews = create_mock_image_reviews()
        
        await review_display.display_reviews(message, mock_image_reviews, language)
        
        # Show main menu
        await message.answer(
            get_message(language, 'bot.main_menu.choose_action'),
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
