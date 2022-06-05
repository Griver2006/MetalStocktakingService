from aiogram.types import ReplyKeyboardMarkup
from features.load_buttons import load_buttons


reply_kb_menu = ReplyKeyboardMarkup(resize_keyboard=True)

menu_buttons = ['Записать веса', 'Куш', 'Отчёты', 'Чистые веса']
load_buttons(reply_kb_menu, two_buttons_row=menu_buttons, end_buttons=['📚Руководство'], btn_back=False)