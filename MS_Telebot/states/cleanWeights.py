from aiogram.dispatcher.filters.state import State, StatesGroup


class CleanWeights(StatesGroup):
    waiting_for_request = State()
    waiting_for_new_clean_weights = State()
    waiting_for_remove_clean_weight = State()