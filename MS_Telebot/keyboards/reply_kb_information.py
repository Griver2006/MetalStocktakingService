from aiogram.types import ReplyKeyboardMarkup
from features.load_buttons import load_buttons


reply_kb_information = ReplyKeyboardMarkup(resize_keyboard=True)

information_buttons = ['Сводка весов за всё время', 'Сводка весов за сегодня',
                       'Цены металлов', 'Куш цены металлов']
load_buttons(reply_kb_information, two_buttons_row=information_buttons)