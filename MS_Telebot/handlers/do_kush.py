from aiogram import types
from aiogram.dispatcher import FSMContext

from loader import dp

from states.recording import Recording
from states.kush import Kush

from keyboards.reply_kb_menu import reply_kb_menu
from keyboards.reply_kb_kush_recording import reply_kb_kush_recording

from utils.some_variable import temp_operations
from features.is_float_int import is_float_int

from data import db_session
from data.users import User


@dp.message_handler(state=Kush.waiting_for_kush_request)
async def do_kush(message: types.Message, state: FSMContext):
    dbs = db_session.create_session()
    current_user = dbs.query(User).get(message.from_user.id)
    if message.text in 'Вернуться в меню':
        await message.bot.send_message(message.chat.id, 'Вы в меню',
                                       reply_markup=reply_kb_menu)
        await state.finish()
        return
    elif message.text == 'Начать запись куша':
        # При запуске этой функции, сбрасываем или установливаем некоторые значение
        temp_operations[message.from_user.id] = []  # Сбрасываем список операций который пользователь забыл записать
        current_user.kush_recording = True  # Устанавливаем то, что пользователь в данный момент записывает куш
        current_user.client_amount = 0  # Сбрасываем общую сумму клиента
        await message.bot.send_message(message.chat.id, 'Куш записывается, впишите веса',
                                       reply_markup=reply_kb_kush_recording)
        dbs.commit()
        # Переходим в состояния 'Записать веса'
        await Recording.waiting_for_data_record.set()
        return
    elif message.text == 'Указать процент для куша':
        await message.answer("Укажите процент:")
        # Переходим в состояния(функцию) выставления процента
        await Kush.next()
        return


# Состояние(функция из Меню кнопки 'Куш') для выставления процента денег рабочего
@dp.message_handler(state=Kush.waiting_for_kush_percent)
async def kush_set_percent(message: types.Message, state: FSMContext):
    dbs = db_session.create_session()
    if message.text in 'Вернуться в меню':
        await message.bot.send_message(message.chat.id, 'Вы в меню',
                                       reply_markup=reply_kb_menu)
        await state.finish()
    # Проверяем указал ли пользователь именно число, также проверяем число на то что оно находится между 0 и 100
    elif not is_float_int(message.text) or float(message.text) < 0 or float(message.text.lower()) > 100:
        await message.answer("Запрос отклонён, пожалуйста впишите процент как показано в руководстве")
        return
    user = dbs.query(User).get(message.from_user.id)
    # Выставляем процент
    user.kush_percent = float(message.text)
    dbs.commit()
    await message.answer("Процент успешно установлен")
    # Возвращаемся в состояния(Меню кнопки куш)
    await Kush.waiting_for_kush_request.set()