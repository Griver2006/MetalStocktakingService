from aiogram.types import ReplyKeyboardMarkup
from features.load_buttons import load_buttons
from utils.some_variable import metal_types


reply_kb_metals = ReplyKeyboardMarkup(resize_keyboard=True)


load_buttons(reply_kb_metals, initial_buttons=['Сбросить общую сумму'],
             two_buttons_row=list(metal_types.keys()), end_buttons=['Удалить последную запись'])