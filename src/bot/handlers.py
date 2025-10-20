"""
Bot handlers for Dating Popcorn Bot
"""

import logging
from typing import Dict, Any
from aiogram import Bot, Dispatcher
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters.callback_data import CallbackData

from config.settings import SUPPORTED_LANGUAGES, DEFAULT_LANGUAGE
from src.utils.localization import get_message
from src.models import User, UserLocation, Review, ReviewStatus, SearchResult

logger = logging.getLogger(__name__)

# User data storage (in production, use a database)
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

class ReviewCallback(CallbackData, prefix="review"):
    review_id: str
    action: str

# Helper functions
def get_user_language(user_id: int) -> str:
    """Get user's preferred language"""
    user = user_data.get(user_id)
    return user.language if user else DEFAULT_LANGUAGE

def get_or_create_user(user_id: int, username: str = None, first_name: str = None, last_name: str = None) -> User:
    """Get or create user"""
    if user_id not in user_data:
        user_data[user_id] = User(
            user_id=user_id,
            username=username,
            first_name=first_name,
            last_name=last_name
        )
    return user_data[user_id]

def get_main_menu_keyboard(language: str) -> ReplyKeyboardMarkup:
    """Get main menu keyboard with side-by-side buttons"""
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
    """Get language selection keyboard with flags"""
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

# Command handlers
async def handle_start_command(message: Message, state: FSMContext):
    """Handle /start command"""
    user_id = message.from_user.id
    user = get_or_create_user(
        user_id=user_id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name
    )
    
    # Always show language selection first for new users
    if user.language == DEFAULT_LANGUAGE and not user.location:
        await message.answer(
            get_message('en', 'bot.language_selection.title'),
            reply_markup=get_language_keyboard()
        )
        return
    
    language = user.language
    
    # Check if user has shared location
    if not user.location:
        # Get user's display name
        display_name = user.first_name or user.username or f"User {user_id}"
        
        await message.answer(
            get_message(language, 'bot.welcome.message', name=display_name),
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text="📍 Share Location", request_location=True)]],
                resize_keyboard=True,
                one_time_keyboard=True
            )
        )
    else:
        await message.answer(
            get_message(language, 'bot.location.received'),
            reply_markup=get_main_menu_keyboard(language)
        )

async def handle_search_command(message: Message, state: FSMContext):
    """Handle /search command"""
    user_id = message.from_user.id
    user = get_or_create_user(user_id)
    language = user.language
    
    if not user.location:
        await message.answer(get_message(language, 'invalid_location'))
        return
    
    await message.answer(
        get_message(language, 'choose_action'),
        reply_markup=get_search_type_keyboard(language)
    )

async def handle_write_command(message: Message, state: FSMContext):
    """Handle /write command"""
    user_id = message.from_user.id
    user = get_or_create_user(user_id)
    language = user.language
    
    if not user.location:
        await message.answer(get_message(language, 'invalid_location'))
        return
    
    await state.set_state(ReviewStates.waiting_for_name)
    await message.answer(
        get_message(language, 'enter_review_name'),
        reply_markup=get_cancel_keyboard(language)
    )

# Location handler
async def handle_location(message: Message, state: FSMContext):
    """Handle location sharing"""
    user_id = message.from_user.id
    user = get_or_create_user(user_id)
    language = user.language
    
    location = message.location
    user.location = UserLocation(
        user_id=user_id,
        latitude=location.latitude,
        longitude=location.longitude,
        timestamp=message.date
    )
    user.update_activity()
    
    await message.answer(
        get_message(language, 'location_received'),
        reply_markup=get_main_menu_keyboard(language)
    )

# Callback query handlers
async def handle_action_callback(callback: CallbackQuery, callback_data: ActionCallback, state: FSMContext):
    """Handle action callbacks"""
    user_id = callback.from_user.id
    user = get_or_create_user(user_id)
    language = user.language
    
    if callback_data.action == "back_to_menu":
        await callback.message.edit_text(
            get_message(language, 'choose_action'),
            reply_markup=get_search_type_keyboard(language)
        )
    
    await callback.answer()

async def handle_language_callback(callback: CallbackQuery, callback_data: LanguageCallback, state: FSMContext):
    """Handle language selection"""
    user_id = callback.from_user.id
    user = get_or_create_user(user_id)
    language = callback_data.language
    
    # Update user language
    user.language = language
    user.update_activity()
    
    await callback.message.edit_text(
        get_message(language, 'choose_action'),
        reply_markup=get_main_menu_keyboard(language)
    )
    await callback.answer(get_message(language, 'language_changed', language=language))

async def handle_search_callback(callback: CallbackQuery, callback_data: SearchCallback, state: FSMContext):
    """Handle search type selection"""
    user_id = callback.from_user.id
    user = get_or_create_user(user_id)
    language = user.language
    
    if callback_data.search_type == "name":
        await state.set_state(SearchStates.waiting_for_name)
        await callback.message.edit_text(
            get_message(language, 'enter_name'),
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[
                    InlineKeyboardButton(
                        text=get_message(language, 'back_to_menu'),
                        callback_data=ActionCallback(action="back_to_menu").pack()
                    )
                ]]
            )
        )
    elif callback_data.search_type == "image":
        await state.set_state(SearchStates.waiting_for_image)
        await callback.message.edit_text(
            get_message(language, 'upload_image'),
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[
                    InlineKeyboardButton(
                        text=get_message(language, 'back_to_menu'),
                        callback_data=ActionCallback(action="back_to_menu").pack()
                    )
                ]]
            )
        )
    
    await callback.answer()

# Message handlers
async def handle_write_review_button(message: Message, state: FSMContext):
    """Handle write review button"""
    user_id = message.from_user.id
    user = get_or_create_user(user_id)
    language = user.language
    
    if not user.location:
        await message.answer(get_message(language, 'invalid_location'))
        return
    
    await state.set_state(ReviewStates.waiting_for_name)
    await message.answer(
        get_message(language, 'enter_review_name'),
        reply_markup=get_cancel_keyboard(language)
    )

async def handle_search_reviews_button(message: Message, state: FSMContext):
    """Handle search reviews button"""
    user_id = message.from_user.id
    user = get_or_create_user(user_id)
    language = user.language
    
    if not user.location:
        await message.answer(get_message(language, 'invalid_location'))
        return
    
    await message.answer(
        get_message(language, 'choose_action'),
        reply_markup=get_search_type_keyboard(language)
    )

async def handle_language_button(message: Message, state: FSMContext):
    """Handle language selection button"""
    await message.answer(
        get_message('en', 'language_selection'),
        reply_markup=get_language_keyboard()
    )

# Review flow handlers
async def handle_review_name(message: Message, state: FSMContext):
    """Handle review name input"""
    user_id = message.from_user.id
    user = get_or_create_user(user_id)
    language = user.language
    
    if message.text == get_message(language, 'cancel'):
        await state.clear()
        await message.answer(
            get_message(language, 'choose_action'),
            reply_markup=get_main_menu_keyboard(language)
        )
        return
    
    if not message.text or len(message.text.strip()) < 2:
        await message.answer(get_message(language, 'name_required'))
        return
    
    # Store the name and move to next step
    await state.update_data(subject_name=message.text.strip())
    await state.set_state(ReviewStates.waiting_for_contact)
    
    await message.answer(
        get_message(language, 'enter_contact', name=message.text.strip()),
        reply_markup=get_skip_keyboard(language)
    )

async def handle_review_contact(message: Message, state: FSMContext):
    """Handle review contact input"""
    user_id = message.from_user.id
    user = get_or_create_user(user_id)
    language = user.language
    data = await state.get_data()
    
    if message.text == get_message(language, 'skip_optional'):
        contact = None
    else:
        contact = message.text.strip()
    
    await state.update_data(subject_contact=contact)
    await state.set_state(ReviewStates.waiting_for_text)
    
    await message.answer(
        get_message(language, 'enter_review_text'),
        reply_markup=get_cancel_keyboard(language)
    )

async def handle_review_text(message: Message, state: FSMContext):
    """Handle review text input"""
    user_id = message.from_user.id
    user = get_or_create_user(user_id)
    language = user.language
    
    if message.text == get_message(language, 'cancel'):
        await state.clear()
        await message.answer(
            get_message(language, 'choose_action'),
            reply_markup=get_main_menu_keyboard(language)
        )
        return
    
    if not message.text or len(message.text.strip()) < 10:
        await message.answer(get_message(language, 'review_text_required'))
        return
    
    # Store the review text and move to image step
    await state.update_data(review_text=message.text.strip())
    await state.set_state(ReviewStates.waiting_for_image)
    
    data = await state.get_data()
    await message.answer(
        get_message(language, 'upload_review_image', name=data['subject_name']),
        reply_markup=get_skip_keyboard(language)
    )

async def handle_review_image(message: Message, state: FSMContext):
    """Handle review image input"""
    user_id = message.from_user.id
    user = get_or_create_user(user_id)
    language = user.language
    data = await state.get_data()
    
    if message.text == get_message(language, 'skip_optional'):
        # Save review without image
        await save_review(user_id, data, [])
        await state.clear()
        await message.answer(
            get_message(language, 'review_saved'),
            reply_markup=get_main_menu_keyboard(language)
        )
        return
    
    # Handle image upload
    if message.photo:
        # In a real implementation, you would save the image to S3
        # For now, we'll just store the file_id
        image_file_id = message.photo[-1].file_id
        await save_review(user_id, data, [image_file_id])
        await state.clear()
        await message.answer(
            get_message(language, 'review_saved'),
            reply_markup=get_main_menu_keyboard(language)
        )
    else:
        await message.answer("Please upload an image or click 'Skip / Omitir'")

# Search flow handlers
async def handle_search_name(message: Message, state: FSMContext):
    """Handle name search input"""
    user_id = message.from_user.id
    user = get_or_create_user(user_id)
    language = user.language
    
    if not message.text or len(message.text.strip()) < 2:
        await message.answer(get_message(language, 'name_required'))
        return
    
    # Simulate search results (in production, search the database)
    search_results = simulate_name_search(message.text.strip(), user_id)
    
    if not search_results:
        await message.answer(
            get_message(language, 'no_results'),
            reply_markup=get_main_menu_keyboard(language)
        )
    else:
        response = get_message(language, 'results_found', count=len(search_results))
        for i, result in enumerate(search_results[:3]):  # Show first 3 results
            response += f"\n\n{i+1}. {result.review.subject_name}"
            response += f"\n{result.review.review_text[:100]}..."
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
    user = get_or_create_user(user_id)
    language = user.language
    
    if message.photo:
        await message.answer(get_message(language, 'image_processing'))
        
        # Simulate image search results (in production, use AWS Rekognition)
        search_results = simulate_image_search(user_id)
        
        if not search_results:
            await message.answer(
                get_message(language, 'no_results'),
                reply_markup=get_main_menu_keyboard(language)
            )
        else:
            response = get_message(language, 'results_found', count=len(search_results))
            for i, result in enumerate(search_results[:3]):  # Show first 3 results
                response += f"\n\n{i+1}. {result.review.subject_name}"
                response += f"\n{result.review.review_text[:100]}..."
                if result.distance_km:
                    response += f"\n📍 {result.distance_km:.1f}km away"
            
            await message.answer(
                response,
                reply_markup=get_main_menu_keyboard(language)
            )
    else:
        await message.answer("Please upload an image for search")
    
    await state.clear()

# Helper functions
async def save_review(user_id: int, data: dict, images: list):
    """Save review to storage (in production, save to database)"""
    review_id = f"review_{user_id}_{len(reviews)}"
    
    user = get_or_create_user(user_id)
    review = Review(
        id=review_id,
        reviewer_user_id=user_id,
        reviewer_location=user.location.__dict__ if user.location else None,
        subject_name=data['subject_name'],
        subject_phone=data.get('subject_contact'),
        review_text=data['review_text'],
        images=images
    )
    
    reviews[review_id] = review
    logger.info(f"Saved review {review_id} by user {user_id}")

def simulate_name_search(name: str, user_id: int) -> list:
    """Simulate name search results (in production, search database)"""
    results = []
    user = get_or_create_user(user_id)
    
    if not user.location:
        return results
    
    # Search through existing reviews
    for review in reviews.values():
        if review.is_approved() and name.lower() in review.subject_name.lower():
            # Calculate distance (mock calculation)
            distance = 5.0  # Mock distance
            results.append(SearchResult(review=review, distance_km=distance))
    
    return results

def simulate_image_search(user_id: int) -> list:
    """Simulate image search results (in production, use AWS Rekognition)"""
    results = []
    user = get_or_create_user(user_id)
    
    if not user.location:
        return results
    
    # Search through existing reviews with images
    for review in reviews.values():
        if review.is_approved() and review.images:
            # Mock face matching score
            match_score = 0.85
            distance = 3.0  # Mock distance
            results.append(SearchResult(review=review, distance_km=distance, match_score=match_score))
    
    return results

# Error handler
async def handle_unknown_message(message: Message):
    """Handle unknown messages"""
    user_id = message.from_user.id
    user = get_or_create_user(user_id)
    language = user.language
    
    await message.answer(
        get_message(language, 'error_occurred'),
        reply_markup=get_main_menu_keyboard(language)
    )
