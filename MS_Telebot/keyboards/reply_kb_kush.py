from aiogram.types import ReplyKeyboardMarkup
from features.load_buttons import load_buttons


reply_kb_kush = ReplyKeyboardMarkup(resize_keyboard=True)

kush_buttons = ['Начать запись куша', 'Указать процент для куша']
load_buttons(reply_kb_kush, two_buttons_row=kush_buttons)