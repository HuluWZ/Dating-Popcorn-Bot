"""
FSM state definitions used across bot flows.
"""

from aiogram.fsm.state import State, StatesGroup


class ReviewStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_content = State()
    waiting_for_exact_address = State()
    waiting_for_photo = State()


class SearchStates(StatesGroup):
    choosing_search_type = State()
    waiting_for_name = State()
    waiting_for_image = State()

