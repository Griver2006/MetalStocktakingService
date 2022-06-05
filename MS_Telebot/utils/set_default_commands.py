from aiogram import types

from loader import dp
from utils.some_variable import metal_types, kush_prices, temp_operations
from keyboards.reply_kb_menu import reply_kb_menu
from keyboards.reply_kb_metals import reply_kb_metals
from keyboards.reply_kb_kush import reply_kb_kush
from keyboards.reply_kb_information import reply_kb_information
from keyboards.reply_kb_clean_weights import reply_kb_clean_weights

from states.recording import Recording
from states.kush import Kush
from states.report import Report
from states.cleanWeights import CleanWeights
from api_sheets import call_metals_prices

from data import db_session
from data.users import User


with open('utils/usage guide', 'r', encoding='UTF-8') as guide:
    GUIDE = ''.join(guide.readlines())


@dp.message_handler(commands=['start'])
async def begin(message: types.Message):
    dbs = db_session.create_session()
    current_user = dbs.query(User).get(message.from_user.id)
    # Проверяем есть ли пользователь в базе данных
    if not current_user:
        # Если нет, то добавляем его
        user = User()
        user.id = message.from_user.id
        user.metal = 'Черный'
        user.price = float(metal_types['Черный'])
        dbs.add(user)
    else:
        # Если нет, то сбрасываем его значение
        current_user.metal = 'Черный'
        current_user.price = float(metal_types['Черный'])
        current_user.client_amount = 0
        current_user.kush_recording = False
        current_user.operation_ended = False
        current_user.kush_percent = 0
    dbs.commit()
    await message.bot.send_message(message.chat.id, 'Бот включён, приятного пользования!', reply_markup=reply_kb_menu)


@dp.message_handler(commands=['update_prices'])
async def update_prices(message: types.Message):
    global metal_types, kush_prices
    request_metals_types = call_metals_prices()
    if not request_metals_types:
        request_metals_types = call_metals_prices()
    request_kush_prices = call_metals_prices(kush=True)
    if not request_kush_prices:
        request_kush_prices = call_metals_prices(kush=True)
    metal_types = dict(request_metals_types)
    kush_prices = dict(request_kush_prices)
    await message.bot.send_message(message.chat.id, 'Цены обновлены!', reply_markup=reply_kb_menu)


@dp.message_handler(content_types=['text'])
async def set_text(message):
    global temp_operations
    if message.chat.type == 'private':
        if message.text == 'Записать веса':
            await message.bot.send_message(message.chat.id, 'Типы металлов загружены',
                                           reply_markup=reply_kb_metals)
            await Recording.waiting_for_data_record.set()
            return
        elif message.text == 'Куш':
            await message.bot.send_message(message.chat.id, 'Кнопки куша загружены',
                                           reply_markup=reply_kb_kush)
            await Kush.waiting_for_kush_request.set()
        elif message.text == 'Отчёты':
            await message.bot.send_message(message.chat.id, 'Кнопки отчётов загружены',
                                           reply_markup=reply_kb_information)
            await Report.waiting_for_report_request.set()
        elif message.text == 'Чистые веса':
            await message.bot.send_message(message.chat.id, 'Кнопки чистых весов загружены',
                                           reply_markup=reply_kb_clean_weights)
            await CleanWeights.waiting_for_request.set()
        elif message.text == '📚Руководство':
            await message.bot.send_message(message.chat.id, GUIDE,
                                           reply_markup=reply_kb_menu)
        else:
            await message.bot.send_message(message.chat.id, 'В этом боте нету такой котегории',
                                           reply_markup=reply_kb_menu)