from aiogram.dispatcher.filters.state import State, StatesGroup


class Kush(StatesGroup):
    waiting_for_kush_request = State()
    waiting_for_kush_percent = State()