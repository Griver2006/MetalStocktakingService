from aiogram.dispatcher.filters.state import State, StatesGroup


class Recording(StatesGroup):
    waiting_for_data_record = State()