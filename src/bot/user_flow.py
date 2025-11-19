"""
User flow handlers for Dating Popcorn Bot - Simple flow without data storage
"""

import logging
from enum import Enum
from typing import Optional, Set, Dict
from aiogram import Bot, Dispatcher
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters.callback_data import CallbackData

from config.settings import SUPPORTED_LANGUAGES, DEFAULT_LANGUAGE
from src.utils.localization import get_message
from src.utils.review_display import ReviewDisplay, create_mock_image_reviews
from src.bot.bot_instance import get_bot_instance

logger = logging.getLogger(__name__)

# Simple language storage per user session
user_languages: dict[int, str] = {}

# FSM States
class ReviewStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_content = State()
    waiting_for_exact_address = State()
    waiting_for_photo = State()

class SearchStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_image = State()

# Callback data classes
class SearchCallback(CallbackData, prefix="search"):
    search_type: str

# Helper functions
def validate_image_content(file_content: bytes) -> Optional[str]:
    """
    Validate image file type by checking magic numbers (file signatures)
    
    Args:
        file_content: Raw file content as bytes
    
    Returns:
        File extension if valid image, None otherwise
    """
    if not file_content or len(file_content) < 4:
        return None
    
    # Check magic numbers for different image formats
    # JPEG: FF D8 FF
    if file_content[:3] == b'\xff\xd8\xff':
        return 'jpg'
    
    # PNG: 89 50 4E 47 0D 0A 1A 0A
    if file_content[:8] == b'\x89PNG\r\n\x1a\n':
        return 'png'
    
    # GIF: 47 49 46 38 (GIF8)
    if file_content[:4] == b'GIF8':
        return 'gif'
    
    # BMP: 42 4D
    if file_content[:2] == b'BM':
        return 'bmp'
    
    # WebP: Check for WebP signature
    if file_content[:4] == b'RIFF' and file_content[8:12] == b'WEBP':
        return 'webp'
    
    # TIFF: 49 49 2A 00 (little endian) or 4D 4D 00 2A (big endian)
    if file_content[:4] in [b'II*\x00', b'MM\x00*']:
        return 'tiff'
    
    return None

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

def _normalize_button_text(text: str) -> str:
    return text.strip().lower()

class MainMenuAction(str, Enum):
    WRITE_REVIEW = 'common.buttons.write_review'
    SEARCH_REVIEWS = 'common.buttons.search_reviews'

def _build_main_menu_button_map() -> Dict[str, MainMenuAction]:
    mapping: Dict[str, MainMenuAction] = {}
    for action in MainMenuAction:
        for locale in SUPPORTED_LANGUAGES:
            localized_text = get_message(locale, action.value)
            if localized_text:
                mapping[_normalize_button_text(localized_text)] = action
    return mapping

MAIN_MENU_BUTTON_MAP = _build_main_menu_button_map()

def get_main_menu_action_from_text(text: Optional[str]) -> Optional[MainMenuAction]:
    if not text:
        return None
    return MAIN_MENU_BUTTON_MAP.get(_normalize_button_text(text))

def is_write_review_button_text(text: Optional[str]) -> bool:
    return get_main_menu_action_from_text(text) == MainMenuAction.WRITE_REVIEW

def is_search_review_button_text(text: Optional[str]) -> bool:
    return get_main_menu_action_from_text(text) == MainMenuAction.SEARCH_REVIEWS

def get_main_menu_keyboard(language: str) -> ReplyKeyboardMarkup:
    """Get main menu keyboard with Write Review and Search Someone buttons"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=get_message(language, MainMenuAction.WRITE_REVIEW.value)),
                KeyboardButton(text=get_message(language, MainMenuAction.SEARCH_REVIEWS.value))
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
        
        # Save location to database (will create user if they don't exist)
        username = message.from_user.username
        logger.info(f"Saving location for user {user_id}: lat={location.latitude}, lng={location.longitude}")
        success = await set_user_location(user_id, location.latitude, location.longitude, username=username)
        
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
    
    await state.clear()
    
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
    
    await state.clear()
    
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
        logger.info(f"User {user_id} cancelled review creation at name step")
        await state.clear()
        await message.answer(
            get_message(language, 'bot.main_menu.choose_action'),
            reply_markup=get_main_menu_keyboard(language)
        )
        return
    
    if not message.text or len(message.text.strip()) < 2:
        logger.warning(f"User {user_id} provided invalid name: '{message.text}' (too short)")
        await message.answer(get_message(language, 'review.flow.validation.name_too_short'))
        return
    
    full_name = message.text.strip()
    logger.info(f"User {user_id} provided review name: '{full_name}'")
    
    await state.update_data(full_name=full_name)
    await state.set_state(ReviewStates.waiting_for_exact_address)
    
    await message.answer(
        get_message(language, 'review.flow.enter_contact').format(name=full_name),
        reply_markup=get_skip_keyboard(language)
    )

async def handle_review_content(message: Message, state: FSMContext):
    """Handle review content input"""
    user_id = message.from_user.id
    language = get_user_language(user_id)
    
    if message.text == get_message(language, 'common.buttons.cancel'):
        logger.info(f"User {user_id} cancelled review creation at content step")
        await state.clear()
        await message.answer(
            get_message(language, 'bot.main_menu.choose_action'),
            reply_markup=get_main_menu_keyboard(language)
        )
        return
    
    if not message.text or len(message.text.strip()) < 10:
        logger.warning(f"User {user_id} provided invalid content: '{message.text}' (too short, length: {len(message.text) if message.text else 0})")
        await message.answer(get_message(language, 'review.flow.validation.content_too_short'))
        return
    
    content = message.text.strip()
    logger.info(f"User {user_id} provided review content: '{content[:100]}{'...' if len(content) > 100 else ''}' (length: {len(content)})")
    
    await state.update_data(content=content)
    await state.set_state(ReviewStates.waiting_for_photo)
    
    # Get full_name from state data for the message
    data = await state.get_data()
    full_name = data.get('full_name', 'this person')
    
    await message.answer(
        get_message(language, 'review.flow.upload_image').format(name=full_name),
        reply_markup=get_skip_keyboard(language)
    )

async def handle_review_exact_address(message: Message, state: FSMContext):
    """Handle review social handle input"""
    user_id = message.from_user.id
    language = get_user_language(user_id)
    data = await state.get_data()
    
    exact_address = None
    if message.text == get_message(language, 'common.buttons.skip_optional'):
        # Skip social handle
        logger.info(f"User {user_id} skipped social handle for review")
    else:
        # Normalize social handle
        from src.utils.social_utils import normalize_query
        original_input = message.text.strip()
        exact_address = normalize_query(original_input)
        logger.info(f"User {user_id} provided exact address: original='{original_input}' -> normalized='{exact_address}'")
    
    await state.update_data(exact_address=exact_address)
    await state.set_state(ReviewStates.waiting_for_content)
    
    # Get full_name from state data for the message
    full_name = data.get('full_name', 'this person')
    
    await message.answer(
        get_message(language, 'review.flow.enter_content'),
        reply_markup=get_cancel_keyboard(language)
    )

async def handle_review_photo(message: Message, state: FSMContext):
    """Handle review photo input and save review to database"""
    user_id = str(message.from_user.id)  # Convert to string for database
    language = get_user_language(int(user_id))
    data = await state.get_data()
    
    # Get review data
    full_name = data.get('full_name')
    content = data.get('content')
    exact_address = data.get('exact_address')
    
    logger.info(f"Processing review submission for user {user_id}: name='{full_name}', exact_address='{exact_address}', content_length={len(content) if content else 0}")
    
    # Handle photo upload
    image_url = None
    if message.text == get_message(language, 'common.buttons.skip_optional'):
        # Skip photo upload
        logger.info(f"User {user_id} skipped photo upload for review")
    else:
        # Handle photo upload
        if message.photo:
            try:
                # Get the largest photo
                photo = message.photo[-1]
                logger.info(f"User {user_id} uploaded photo: file_id={photo.file_id}, file_size={photo.file_size} bytes")
                
                # Validate file size (5MB max)
                max_size_bytes = 5 * 1024 * 1024  # 5MB
                if photo.file_size and photo.file_size > max_size_bytes:
                    logger.warning(f"User {user_id} uploaded photo too large: {photo.file_size} bytes (max: {max_size_bytes})")
                    await message.answer(get_message(language, 'review.flow.validation.photo_too_large'))
                    return
                
                # Download photo from Telegram
                bot = get_bot_instance()
                file = await bot.get_file(photo.file_id)
                logger.info(f"User {user_id} photo file info: file_path={file.file_path}")
                
                # Download file data for validation
                file_data = await bot.download_file(file.file_path)
                file_content = file_data.read()
                logger.info(f"User {user_id} downloaded photo data: {len(file_content)} bytes")
                
                # Validate file type by content (magic numbers)
                file_type = validate_image_content(file_content)
                if not file_type or file_type not in ['jpg', 'png']:
                    logger.warning(f"User {user_id} uploaded invalid photo format - detected: {file_type}, allowed: jpg, png")
                    await message.answer(get_message(language, 'review.flow.validation.invalid_photo_format'))
                    return
                
                logger.info(f"User {user_id} photo validation passed: type={file_type}, size={photo.file_size} bytes")
                
                # Upload to S3
                from src.utils.s3_utils import upload_to_s3
                from io import BytesIO
                
                file_buffer = BytesIO(file_content)
                logger.info(f"User {user_id} uploading photo to S3 with type: {file_type}")
                image_url = await upload_to_s3(file_buffer, file_type)
                
                logger.info(f"User {user_id} successfully uploaded photo to S3: {image_url}")
                
            except Exception as e:
                logger.error(f"Error uploading photo for user {user_id}: {e}")
                await message.answer(get_message(language, 'review.flow.errors.photo_upload_failed'))
                return
        else:
            logger.warning(f"User {user_id} sent message without photo when photo was expected")
            await message.answer(get_message(language, 'review.flow.validation.photo_required'))
            return
    
    try:
        # Import database functions
        from src.database.simple_db import create_review
        
        # Log all fields being inserted
        logger.info(f"=== REVIEW SUBMISSION SUMMARY FOR USER {user_id} ===")
        logger.info(f"Field: reviewer_id = '{user_id}' (type: {type(user_id).__name__})")
        logger.info(f"Field: full_name = '{full_name}' (type: {type(full_name).__name__}, length: {len(full_name) if full_name else 0})")
        logger.info(f"Field: content = '{content[:100]}{'...' if len(content) > 100 else ''}' (type: {type(content).__name__}, length: {len(content) if content else 0})")
        logger.info(f"Field: exact_address = '{exact_address}' (type: {type(exact_address).__name__})")
        logger.info(f"Field: image_url = '{image_url}' (type: {type(image_url).__name__})")
        logger.info(f"Field: status = 'PENDING' (auto-assigned)")
        logger.info(f"=== END REVIEW SUBMISSION SUMMARY ===")
        
        # Save review to database
        logger.info(f"🔄 Calling create_review() with parameters:")
        logger.info(f"   - reviewer_id: '{user_id}'")
        logger.info(f"   - full_name: '{full_name}'")
        logger.info(f"   - content: '{content[:50]}{'...' if len(content) > 50 else ''}'")
        logger.info(f"   - exact_address: '{exact_address}'")
        logger.info(f"   - image_url: '{image_url}'")
        
        review = await create_review(
            reviewer_id=user_id,
            full_name=full_name,
            content=content,
            exact_address=exact_address,
            image_url=image_url
        )
        
        if review:
            logger.info(f"✅ Review saved successfully to database:")
            logger.info(f"   - Review ID: {review.id}")
            logger.info(f"   - Reviewer ID: {review.reviewer_id}")
            logger.info(f"   - Full Name: {review.full_name}")
            logger.info(f"   - Content Length: {len(review.content)}")
            logger.info(f"   - Exact Address: {review.exact_address}")
            logger.info(f"   - Image URL: {review.image_url}")
            logger.info(f"   - Status: {review.status.value}")
            logger.info(f"   - Created At: {review.created_at}")
            logger.info(f"   - Updated At: {review.updated_at}")
            
            # Clear state and show success message
            await state.clear()
            
            success_message = get_message(language, 'review.flow.saved')
            
            await message.answer(
                success_message,
                reply_markup=get_main_menu_keyboard(language)
            )
        else:
            logger.error(f"❌ Failed to create review for user {user_id} - create_review returned None")
            logger.error(f"   Database function returned None - possible database error")
            raise Exception("Failed to create review - database returned None")
        
    except Exception as e:
        logger.error(f"❌ Error saving review for user {user_id}: {e}")
        logger.error(f"   - Full Name: {full_name}")
        logger.error(f"   - Content Length: {len(content) if content else 0}")
        logger.error(f"   - Exact Address: {exact_address}")
        logger.error(f"   - Image URL: {image_url}")
        await message.answer(
            get_message(language, 'errors.review_save_failed'),
            reply_markup=get_main_menu_keyboard(language)
        )

# Search flow handlers
async def handle_search_name(message: Message, state: FSMContext):
    """Handle name search input"""
    user_id = message.from_user.id
    telegram_id = str(user_id)  # Convert to string for database
    language = get_user_language(user_id)
    
    logger.info(f"🔍 User {user_id} ({telegram_id}) initiated name search")
    
    if not message.text or len(message.text.strip()) < 2:
        logger.warning(f"❌ User {user_id} provided invalid search query: '{message.text}'")
        await message.answer(get_message(language, 'common.validation.name_required'))
        return
    
    search_query = message.text.strip()
    logger.info(f"🔍 Search query: '{search_query}' (length: {len(search_query)})")
    
    try:
        # Show searching message
        logger.debug(f"📤 Sending searching message to user {user_id}")
        await message.answer(
            get_message(language, 'search.results.searching', name=search_query)
        )
        
        # Import search service
        from src.database.services import SearchService
        
        # Perform advanced search
        logger.info(f"🔍 Starting database search for user {user_id}")
        search_results = await SearchService.advanced_search_by_name_and_location(
            searcher_telegram_id=telegram_id,
            query=search_query,
            radius_km=50  # 50 km radius
        )
        
        logger.info(f"🔍 Database search completed for user {user_id}: {len(search_results)} results")
        
        if not search_results:
            logger.info(f"❌ No results found for user {user_id} query: '{search_query}'")
            await message.answer(get_message(language, 'search.results.none_found'))
            await state.clear()
            return
        
        # Extract reviews from results with distance calculation
        import math
        reviews = []
        for review_obj, match_count, distance_km in search_results:
            # Round up the distance using math.ceil
            rounded_distance = math.ceil(distance_km) if distance_km > 0 else 1
            
            # Log image URL for debugging
            image_url = review_obj.image_url
            if image_url:
                logger.info(f"Review '{review_obj.full_name}' has image URL: {image_url}")
            else:
                logger.debug(f"Review '{review_obj.full_name}' has no image URL")
            
            reviewer_username = None
            reviewer = getattr(review_obj, 'reviewer', None)
            if reviewer and reviewer.username:
                reviewer_username = reviewer.username
            
            review_dict = {
                'name': review_obj.full_name,
                'content': review_obj.content,
                'distance': rounded_distance,
                'image': image_url,  # Can be None or URL string
                'reviewer_username': reviewer_username,
                # 'exact_address': review_obj.exact_address  # intentionally hidden from users
            }
            reviews.append(review_dict)
            logger.debug(f"   Converted: '{review_obj.full_name}' -> dict format (distance: {rounded_distance}km, original: {distance_km:.2f}km, has_image: {bool(image_url)})")
        
        logger.info(f"📋 Displaying {len(reviews)} reviews to user {user_id}")
        
        # Use review display system
        from src.bot.bot_instance import get_bot_instance
        bot = get_bot_instance()
        review_display = ReviewDisplay(bot)
        
        logger.debug(f"📤 Displaying reviews to user {user_id}")
        await review_display.display_reviews(message, reviews, language)
        
        logger.info(f"✅ Successfully displayed search results to user {user_id}")
        
    except Exception as e:
        logger.error(f"❌ Error in name search for user {user_id}: {e}")
        logger.exception("Full traceback:")
        await message.answer("Sorry, there was an error searching. Please try again.")
    
    # Show main menu
    logger.debug(f"📤 Showing main menu to user {user_id}")
    await message.answer(
        get_message(language, 'bot.main_menu.choose_action'),
        reply_markup=get_main_menu_keyboard(language)
    )
    
    logger.info(f"✅ Name search flow completed for user {user_id}")
    await state.clear()

async def handle_search_image(message: Message, state: FSMContext):
    """Handle image search input with real face recognition"""
    user_id = message.from_user.id
    telegram_id = str(user_id)  # Convert to string for database
    language = get_user_language(user_id)
    
    logger.info(f"📷 User {user_id} ({telegram_id}) initiated image search")
    
    # Check rate limit
    from src.utils.rate_limiter import check_rate_limit
    is_allowed, rate_limit_error = check_rate_limit(telegram_id)
    if not is_allowed:
        logger.warning(f"❌ Rate limit exceeded for user {user_id}")
        await message.answer(rate_limit_error or get_message(language, 'errors.rate_limit'))
        await state.clear()
        return
    
    if not message.photo:
        await message.answer(get_message(language, 'search.flow.by_image.upload_required'))
        await state.clear()
        return
    
    # Get user location
    from src.database.simple_db import get_user_location
    user_location = await get_user_location(telegram_id)
    
    if not user_location:
        logger.warning(f"❌ User {user_id} has no location set")
        await message.answer(get_message(language, 'bot.location.required_for_search'))
        await state.clear()
        return
    
    user_latitude, user_longitude = user_location
    logger.info(f"📍 User location: {user_latitude}, {user_longitude}")
    
    # Image received - show confirmation
    await message.answer(get_message(language, 'search.flow.by_image.received'))
    
    # Show processing message
    await message.answer(get_message(language, 'search.flow.by_image.processing'))
    
    uploaded_image_bytes = None
    
    try:
        # Download photo from Telegram
        bot = get_bot_instance()
        photo = message.photo[-1]  # Get largest photo
        
        logger.info(f"📥 Downloading photo from Telegram: file_id={photo.file_id}")
        file = await bot.get_file(photo.file_id)
        file_data = await bot.download_file(file.file_path)
        file_content = file_data.read()
        uploaded_image_bytes = file_content
        
        logger.info(f"✅ Downloaded photo: {len(uploaded_image_bytes)} bytes")
        
        # Validate file type
        file_type = validate_image_content(uploaded_image_bytes)
        if not file_type or file_type not in ['jpg', 'png']:
            logger.warning(f"❌ Invalid photo format: {file_type}")
            await message.answer(get_message(language, 'review.flow.validation.invalid_photo_format'))
            await state.clear()
            return
        
        # Perform face recognition search (using bytes directly, no S3 upload needed)
        from src.utils.image_comparison import search_by_image
        from src.utils.rekognition_utils import FaceDetectionError, FaceComparisonError
        
        matches = await search_by_image(
            uploaded_image_bytes=uploaded_image_bytes,
            user_latitude=user_latitude,
            user_longitude=user_longitude,
            radius_km=50,
            similarity_threshold=90.0  # 90% match threshold
        )
        
        # Image bytes are automatically cleaned up after comparison (no S3 upload needed)
        logger.info("✅ Image comparison completed, image data cleaned up")
        
        # Format results for display
        if matches:
            # Convert to ReviewDisplay format
            review_dicts = []
            for match in matches:
                review = match.review
                
                # Use distance_km already calculated in image_comparison.py
                distance_km = match.distance_km or 0
                
                reviewer_username = None
                reviewer = getattr(review, 'reviewer', None)
                if reviewer and reviewer.username:
                    reviewer_username = reviewer.username
                
                review_dict = {
                    'name': review.full_name,
                    'content': review.content,
                    'distance': distance_km,
                    'exact_address': review.exact_address,  # Not displayed but kept for future use
                    'image': review.image_url,
                    'similarity': match.similarity,  # Similarity percentage for display
                    'reviewer_username': reviewer_username
                }
                review_dicts.append(review_dict)
            
            # Sort by match percentage (similarity) - highest first
            review_dicts.sort(key=lambda x: x.get('similarity', 0), reverse=True)
            
            # Limit to max 3 results
            review_dicts = review_dicts[:3]
            
            # Display results
            bot = get_bot_instance()
            review_display = ReviewDisplay(bot)
            await review_display.display_reviews(message, review_dicts, language)
        else:
            # No matches found
            await message.answer(get_message(language, 'search.results.none_found'))
        
        # Show main menu
        await message.answer(
            get_message(language, 'bot.main_menu.choose_action'),
            reply_markup=get_main_menu_keyboard(language)
        )
    
    except FaceDetectionError as e:
        error_code = getattr(e, 'error_code', 'UNKNOWN')
        logger.error(f"❌ Face detection error: {error_code} - {str(e)}")
        
        # Map error codes to localized messages
        if error_code == 'NO_FACE':
            await message.answer(get_message(language, 'search.flow.by_image.errors.no_face_detected'))
        elif error_code == 'FACE_TOO_SMALL_OR_LOW_QUALITY':
            await message.answer(get_message(language, 'search.flow.by_image.errors.face_too_small_or_low_quality'))
        elif error_code == 'INVALID_IMAGE':
            await message.answer(get_message(language, 'search.flow.by_image.errors.invalid_image'))
        elif error_code == 'IMAGE_TOO_LARGE':
            await message.answer(get_message(language, 'search.flow.by_image.errors.image_too_large'))
        else:
            await message.answer(get_message(language, 'search.flow.by_image.errors.detection_failed'))
    
    except FaceComparisonError as e:
        logger.error(f"❌ Face comparison error: {str(e)}")
        await message.answer(get_message(language, 'search.flow.by_image.errors.comparison_failed'))
    
    except Exception as e:
        logger.error(f"❌ Unexpected error in image search: {e}")
        logger.exception("Full traceback:")
        await message.answer(get_message(language, 'errors.general'))
    
    await state.clear()

# Error handler
async def handle_unknown_message(message: Message):
    """Handle unknown messages"""
    user_id = message.from_user.id
    language = get_user_language(user_id)
    
    await message.answer(
        get_message(language, 'errors.invalid_button'),
        reply_markup=get_main_menu_keyboard(language)
    )
