import datetime
from aiogram import types
from aiogram.dispatcher import FSMContext
from api_sheets import record_plus_operation, delete_last_row

from loader import dp

from states.recording import Recording
from states.kush import Kush

from keyboards.reply_kb_menu import reply_kb_menu
from keyboards.reply_kb_kush import reply_kb_kush
from keyboards.reply_kb_metals import reply_kb_metals
from keyboards.reply_kb_kush_recording import reply_kb_kush_recording

from utils.some_variable import temp_operations, metal_types, kush_prices
from features.is_float_int import is_float_int
from features.operations import do_minus_operation, do_plus_operation
from features.change_metal import change_metal
from features.reset_total_amount import reset_total_amount

from data import db_session
from data.users import User
from data.all_operations import AllOperations


@dp.message_handler(state=Recording.waiting_for_data_record)
async def do_record(message: types.Message, state: FSMContext):
    dbs = db_session.create_session()
    current_user = dbs.query(User).get(message.from_user.id)
    if message.text\
            == 'Вернуться в меню':
        await message.bot.send_message(message.chat.id, 'Записывание весов металла остановлено',
                                       reply_markup=reply_kb_menu)
        await state.finish()
        return
    # Здесь мы проверяем, записывает ли пользователь операцию через функцию
    # 'Начать запись куша' из 'Меню кнопки Куш'
    if message.text == 'Вернуться в меню куша':
        # При выходе из этой функции, сбрасываем или установливаем некоторые значение
        temp_operations[message.from_user.id] = []
        current_user.kush_recording = False
        current_user.client_amount = 0
        await message.bot.send_message(message.chat.id, 'Записывание куша прервано, веса сброшены',
                                       reply_markup=reply_kb_kush)
        await state.finish()
        dbs.commit()
        # Возвращаемся в состояния(Меню кнопки куш)
        await Kush.waiting_for_kush_request.set()
        return
    # Проверяем хочет пользователь записать минусовую операцию
    if '-' in message.text.split()[0] and is_float_int(message.text.split()[0]):
        # Делаем проверку не записывается ли сейчас куш
        if not current_user.kush_recording:
            # Передаём значение в функцию записи минусовых операций
            await do_minus_operation(message)
        else:
            await message.answer("Вы не можете добавиь минусовую операцию во время записи куша")
            return
    # Проверяем является ли данное пользователем первое значение числом
    elif is_float_int(message.text.split()[0]):
        # Передаём значение в функцию записи плюсовых операций
        await do_plus_operation(message)
    # Проверяем передал ли пользователь тип металла
    elif message.text in metal_types.keys():
        # Переходим в функцию и сменяем тип металла
        await change_metal(message)
    elif message.text == 'Сбросить общую сумму':
        await reset_total_amount(message)
    elif message.text in 'Веса вписаны':
        # Проверяем вписал ли пользователь хоть какой-то вес
        if not temp_operations[message.from_user.id]:
            await message.bot.send_message(message.chat.id, 'Вы не вписали не один вес',
                                           reply_markup=reply_kb_metals)
            return
        # Общая сумма сум по основным ценам 'Актуальный прайс'
        total_amount_tmp_s = round(sum(operation[5] for operation in temp_operations[message.from_user.id]))
        # Сумма рабочего который разобрал куш клиента
        worker_amount = round(total_amount_tmp_s / 100 * current_user.kush_percent)
        # Изменяем операции на новые цены, а также изменяем сумму под новую цену
        for operation in temp_operations[message.from_user.id]:
            operation[4] = float(kush_prices[operation[2]].replace(',', '.'))
            operation[5] = operation[3] * operation[4]
        employer_amount = sum(operation[3] * float(kush_prices['Черный'].replace(',', '.'))
                              for operation in temp_operations[message.from_user.id])
        # Сумма клиента чей куш был разобран
        client_amount = round(sum(operation[5] for operation in temp_operations[message.from_user.id])
                              - employer_amount - worker_amount)
        information = f'\n{"---" * 10}\n'.join([f'Сумма рабочего: {worker_amount}', f'Ваша Сумма: {client_amount}'])
        await message.bot.send_message(message.chat.id, information,
                                       reply_markup=reply_kb_kush)
        # Записываем все операции из temp_operations с изменёнными ценой и суммой в бд и google sheets
        for operation in temp_operations[message.from_user.id]:
            operation[4] = float(kush_prices[operation[2]].replace(',', '.'))  # Изменяем цену
            operation[5] = operation[3] * operation[4]  # Изменяем сумму
            all_operations = AllOperations()
            all_operations.date = datetime.datetime.strptime(operation[0], "%Y.%m.%d").date()
            all_operations.time = datetime.datetime.strptime(operation[1], "%H:%M").time()
            all_operations.metal = operation[2]
            all_operations.quantity = operation[3]
            all_operations.price = operation[4]
            all_operations.sum = operation[5]
            all_operations.comment = operation[6]
            dbs.add(all_operations)
            record_plus_operation(operation)
        temp_operations[message.from_user.id] = []  # Очищаем список временных операций
        current_user.kush_recording = False  # Сбрасываем записывание металла
        current_user.client_amount = 0  # Также сбрасываем общую сумму клиента
        dbs.commit()
        # Возвращаемся в состояния(Меню кнопки куш)
        await Kush.waiting_for_kush_request.set()
        return
    elif message.text == 'Удалить последную запись':
        # Проверяем записывает пользователь куш
        if current_user.kush_recording:
            # Если так то, удаляем операцию из временных операций
            temp_operations[message.from_user.id] = temp_operations[message.from_user.id][:-1]
        else:
            # Удаляем операцию из google sheets
            delete_last_row()
            # Берём последную операцию
            last_row = dbs.query(AllOperations).order_by(AllOperations.id.desc()).first()
            # Удаляем её из бд
            dbs.delete(last_row)
        dbs.commit()
        await message.bot.send_message(message.chat.id, f'Последняя запись успешно удалена',
                                       reply_markup=reply_kb_kush_recording if current_user.kush_recording
                                       else reply_kb_metals)
    else:
        await message.answer("Запрос отклонён, пожалуйста сделайте запрос как показано в руководстве")
        return
    dbs.commit()