from aiogram.types import ReplyKeyboardMarkup
from features.load_buttons import load_buttons
from utils.some_variable import call_metals_prices


reply_kb_kush_recording = ReplyKeyboardMarkup(resize_keyboard=True)

metal_types = dict(call_metals_prices())
load_buttons(reply_kb_kush_recording, initial_buttons=['Веса вписаны', 'Сбросить общую сумму'],
             two_buttons_row=list(metal_types.keys()), end_buttons=['Удалить последную запись',
                                                                    'Вернуться в меню куша'], btn_back=False)