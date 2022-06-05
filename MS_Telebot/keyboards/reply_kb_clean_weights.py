from aiogram.types import ReplyKeyboardMarkup
from features.load_buttons import load_buttons
from utils.some_variable import clean_weights_buttons


reply_kb_clean_weights = ReplyKeyboardMarkup(resize_keyboard=True)


load_buttons(reply_kb_clean_weights, initial_buttons=['Добавить новый предмет с его чистым весом', 'Удалить предмет'],
             two_buttons_row=clean_weights_buttons)