from aiogram.dispatcher.filters.state import State, StatesGroup


class Report(StatesGroup):
    waiting_for_report_request = State()