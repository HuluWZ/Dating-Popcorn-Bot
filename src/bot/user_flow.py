"""
User flow handlers for Dating Popcorn Bot with database integration
"""

import logging
from typing import Optional, Dict, Any
from aiogram import Bot, Dispatcher
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters.callback_data import CallbackData

from config.settings import SUPPORTED_LANGUAGES, DEFAULT_LANGUAGE
from src.utils.localization import get_message
from src.models.user import User
from src.models.review import Review, ReviewStatus, SearchResult

logger = logging.getLogger(__name__)

# In-memory storage (replace with database later)
user_data: Dict[int, User] = {}
reviews: Dict[str, Review] = {}

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
class ActionCallback(CallbackData, prefix="action"):
    action: str

class LanguageCallback(CallbackData, prefix="lang"):
    language: str

class SearchCallback(CallbackData, prefix="search"):
    search_type: str

# In-memory storage interface (replace with database later)
class StorageInterface:
    """In-memory storage interface for user and review operations"""
    
    @staticmethod
    async def get_user_by_telegram_id(telegram_id: int) -> Optional[User]:
        """Get user by telegram ID from memory"""
        return user_data.get(telegram_id)
    
    @staticmethod
    async def create_user(user: User) -> User:
        """Create new user in memory"""
        user_data[user.telegram_id] = user
        return user
    
    @staticmethod
    async def update_user(user: User) -> User:
        """Update user in memory"""
        user_data[user.telegram_id] = user
        return user
    
    @staticmethod
    async def save_review(review: Review) -> Review:
        """Save review to memory"""
        review_id = f"review_{review.reviewer_telegram_id}_{len(reviews)}"
        review.id = review_id
        reviews[review_id] = review
        return review

# Helper functions
def get_user_language(user: Optional[User]) -> str:
    """Get user's preferred language"""
    return user.language if user else DEFAULT_LANGUAGE

def get_main_menu_keyboard(language: str) -> ReplyKeyboardMarkup:
    """Get main menu keyboard with Write Review and Search Someone buttons"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=get_message(language, 'common.buttons.write_review')),
                KeyboardButton(text=get_message(language, 'common.buttons.search_someone'))
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
                text=get_message(language, 'search.flow.by_name.prompt'),
                callback_data=SearchCallback(search_type="name").pack()
            )],
            [InlineKeyboardButton(
                text=get_message(language, 'search.flow.by_image.prompt'),
                callback_data=SearchCallback(search_type="image").pack()
            )],
            [InlineKeyboardButton(
                text=get_message(language, 'common.buttons.back_to_menu'),
                callback_data=ActionCallback(action="back_to_menu").pack()
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
    """Handle /start command - always ask for language preference first"""
    user_id = message.from_user.id
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name
    
    # Check if user exists in memory
    user = await StorageInterface.get_user_by_telegram_id(user_id)
    
    if user is None:
        # User doesn't exist in memory, create new user
        user = User(
            telegram_id=user_id,
            first_name=first_name or "Unknown",
            last_name=last_name
        )
        user = await StorageInterface.create_user(user)
        logger.info(f"Created new user: {user_id}")
    else:
        # User exists, update their info if needed
        if user.first_name != first_name or user.last_name != last_name:
            user.first_name = first_name or user.first_name
            user.last_name = last_name or user.last_name
            user = await StorageInterface.update_user(user)
            logger.info(f"Updated user info: {user_id}")
    
    # Always ask for language preference first
    await message.answer(
        get_message('en', 'bot.language_selection.title'),
        reply_markup=get_language_keyboard()
    )

# Location handler
async def handle_location(message: Message, state: FSMContext):
    """Handle location sharing"""
    user_id = message.from_user.id
    user = await StorageInterface.get_user_by_telegram_id(user_id)
    
    if user is None:
        await message.answer("Error: User not found. Please use /start command.")
        return
    
    language = get_user_language(user)
    location = message.location
    
    # Update user location
    user.set_location(location.latitude, location.longitude)
    user = await StorageInterface.update_user(user)
    
    await message.answer(
        get_message(language, 'bot.location.received'),
        reply_markup=get_main_menu_keyboard(language)
    )

# Main menu button handlers
async def handle_write_review_button(message: Message, state: FSMContext):
    """Handle Write Review button"""
    user_id = message.from_user.id
    user = await StorageInterface.get_user_by_telegram_id(user_id)
    
    if user is None:
        await message.answer("Error: User not found. Please use /start command.")
        return
    
    language = get_user_language(user)
    
    if user.location is None:
        await message.answer(
            get_message(language, 'bot.location.required'),
            reply_markup=get_location_keyboard(language)
        )
        return
    
    await state.set_state(ReviewStates.waiting_for_name)
    await message.answer(
        get_message(language, 'review.flow.enter_name'),
        reply_markup=get_cancel_keyboard(language)
    )

async def handle_search_someone_button(message: Message, state: FSMContext):
    """Handle Search Someone button"""
    user_id = message.from_user.id
    user = await StorageInterface.get_user_by_telegram_id(user_id)
    
    if user is None:
        await message.answer("Error: User not found. Please use /start command.")
        return
    
    language = get_user_language(user)
    
    if user.location is None:
        await message.answer(
            get_message(language, 'bot.location.required'),
            reply_markup=get_location_keyboard(language)
        )
        return
    
    await message.answer(
        get_message(language, 'search.flow.choose_method'),
        reply_markup=get_search_type_keyboard(language)
    )

async def handle_language_button(message: Message, state: FSMContext):
    """Handle language selection button"""
    await message.answer(
        get_message('en', 'bot.language_selection.title'),
        reply_markup=get_language_keyboard()
    )

# Language selection
async def handle_language_callback(callback: CallbackQuery, callback_data: LanguageCallback, state: FSMContext):
    """Handle language selection"""
    user_id = callback.from_user.id
    user = await StorageInterface.get_user_by_telegram_id(user_id)
    
    if user is None:
        await callback.answer("Error: User not found.")
        return
    
    language = callback_data.language
    user.language = language
    user = await StorageInterface.update_user(user)
    
    # Check if user has location after language selection
    if user.location is None:
        # User has no location, ask for location
        await callback.message.edit_text(
            get_message(language, 'bot.welcome.message', name=user.first_name),
            reply_markup=get_location_keyboard(language)
        )
    else:
        # User has location, show main menu
        await callback.message.edit_text(
            get_message(language, 'bot.main_menu.choose_action'),
            reply_markup=get_main_menu_keyboard(language)
        )
    
    await callback.answer(get_message(language, 'bot.main_menu.language_changed'))

# Search callbacks
async def handle_search_callback(callback: CallbackQuery, callback_data: SearchCallback, state: FSMContext):
    """Handle search type selection"""
    user_id = callback.from_user.id
    user = await StorageInterface.get_user_by_telegram_id(user_id)
    
    if user is None:
        await callback.answer("Error: User not found.")
        return
    
    language = get_user_language(user)
    
    if callback_data.search_type == "name":
        await state.set_state(SearchStates.waiting_for_name)
        await callback.message.edit_text(
            get_message(language, 'search.flow.by_name.prompt'),
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[
                    InlineKeyboardButton(
                        text=get_message(language, 'common.buttons.back_to_menu'),
                        callback_data=ActionCallback(action="back_to_menu").pack()
                    )
                ]]
            )
        )
    elif callback_data.search_type == "image":
        await state.set_state(SearchStates.waiting_for_image)
        await callback.message.edit_text(
            get_message(language, 'search.flow.by_image.prompt'),
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[
                    InlineKeyboardButton(
                        text=get_message(language, 'common.buttons.back_to_menu'),
                        callback_data=ActionCallback(action="back_to_menu").pack()
                    )
                ]]
            )
        )
    
    await callback.answer()

# Review flow handlers
async def handle_review_name(message: Message, state: FSMContext):
    """Handle review name input"""
    user_id = message.from_user.id
    user = await StorageInterface.get_user_by_telegram_id(user_id)
    language = get_user_language(user)
    
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
    user = await StorageInterface.get_user_by_telegram_id(user_id)
    language = get_user_language(user)
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
    user = await StorageInterface.get_user_by_telegram_id(user_id)
    language = get_user_language(user)
    
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
    user = await StorageInterface.get_user_by_telegram_id(user_id)
    language = get_user_language(user)
    data = await state.get_data()
    
    if message.text == get_message(language, 'common.buttons.skip_optional'):
        # Save review without image
        images = []
    else:
        # Handle image upload
        if message.photo:
            # In production, save image to S3 and get URL
            image_file_id = message.photo[-1].file_id
            images = [image_file_id]  # TODO: Convert to actual URLs
        else:
            await message.answer(get_message(language, 'review.flow.upload_image_required'))
            return
    
    # Create and save review
    review = Review(
        reviewer_telegram_id=user_id,
        full_name=data['full_name'],
        exact_information=data.get('exact_information'),
        review_content=data['review_content'],
        images=images,
        status=ReviewStatus.PENDING
    )
    
    await StorageInterface.save_review(review)
    await state.clear()
    
    await message.answer(
        get_message(language, 'review.flow.saved'),
        reply_markup=get_main_menu_keyboard(language)
    )

# Search flow handlers
async def handle_search_name(message: Message, state: FSMContext):
    """Handle name search input"""
    user_id = message.from_user.id
    user = await StorageInterface.get_user_by_telegram_id(user_id)
    language = get_user_language(user)
    
    if not message.text or len(message.text.strip()) < 2:
        await message.answer(get_message(language, 'common.validation.name_required'))
        return
    
    # Search reviews by name (in-memory search)
    search_results = []
    for review in reviews.values():
        if (review.status == ReviewStatus.APPROVED and 
            message.text.strip().lower() in review.full_name.lower()):
            # Mock distance calculation
            distance_km = 5.0  # Mock distance
            search_results.append(SearchResult(review=review, distance_km=distance_km))
    
    if not search_results:
        await message.answer(
            get_message(language, 'search.results.none_found'),
            reply_markup=get_main_menu_keyboard(language)
        )
    else:
        response = get_message(language, 'search.results.found', count=len(search_results))
        for i, result in enumerate(search_results[:3]):  # Show first 3 results
            response += f"\n\n{i+1}. {result.review.full_name}"
            response += f"\n{result.review.review_content[:100]}..."
            if result.distance_km:
                response += f"\n📍 {result.distance_km:.1f}km away"
        
        await message.answer(
            response,
            reply_markup=get_main_menu_keyboard(language)
        )
    
    await state.clear()

async def handle_search_image(message: Message, state: FSMContext):
    """Handle image search input"""
    user_id = message.from_user.id
    user = await StorageInterface.get_user_by_telegram_id(user_id)
    language = get_user_language(user)
    
    if message.photo:
        await message.answer(get_message(language, 'search.flow.by_image.processing'))
        
        # Search reviews by image (in-memory search - placeholder for AWS Rekognition)
        search_results = []
        for review in reviews.values():
            if (review.status == ReviewStatus.APPROVED and 
                review.images and len(review.images) > 0):
                # Mock image matching
                match_score = 0.85  # Mock match score
                distance_km = 3.0  # Mock distance
                search_results.append(SearchResult(
                    review=review, 
                    distance_km=distance_km, 
                    match_score=match_score
                ))
        
        if not search_results:
            await message.answer(
                get_message(language, 'search.results.none_found'),
                reply_markup=get_main_menu_keyboard(language)
            )
        else:
            response = get_message(language, 'search.results.found', count=len(search_results))
            for i, result in enumerate(search_results[:3]):  # Show first 3 results
                response += f"\n\n{i+1}. {result.review.full_name}"
                response += f"\n{result.review.review_content[:100]}..."
                if result.distance_km:
                    response += f"\n📍 {result.distance_km:.1f}km away"
                if result.match_score:
                    response += f"\n🎯 Match: {result.match_score:.1%}"
            
            await message.answer(
                response,
                reply_markup=get_main_menu_keyboard(language)
            )
    else:
        await message.answer(get_message(language, 'search.flow.by_image.upload_required'))
    
    await state.clear()

# Error handler
async def handle_unknown_message(message: Message):
    """Handle unknown messages"""
    user_id = message.from_user.id
    user = await StorageInterface.get_user_by_telegram_id(user_id)
    language = get_user_language(user)
    
    await message.answer(
        get_message(language, 'errors.general'),
        reply_markup=get_main_menu_keyboard(language)
    )
