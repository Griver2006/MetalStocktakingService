from aiogram.types import InlineKeyboardButton, Message
import datetime

from utils.some_variable import metal_types, temp_operations
from keyboards.inline_kb_markup import inline_kb_markup
from api_sheets import record_plus_operation, record_minus_operation

from data import db_session
from data.users import User
from data.minus_operations import MinusOperations
from data.all_operations import AllOperations


async def do_plus_operation(message: Message):
    split_message = message.text.split()
    try:
        dbs = db_session.create_session()
        user = dbs.query(User).get(message.from_user.id)
        # Создаём и записываем значения в AllOperations
        all_operations = AllOperations()
        date_time = str(message.date).split()  # Берём дату и время
        all_operations.date = datetime.datetime.strptime(date_time[0], "%Y-%m-%d").date()  # Записываем дату
        all_operations.time = datetime.datetime.strptime(date_time[1], "%H:%M:%S").time()  # Записываем время
        all_operations.metal = user.metal  # Записываем выбранный пользователем металл
        all_operations.quantity = float(split_message[0].replace(',', '.'))  # Записываем колличество металла
        # Проверяем, указал ли пользователь цену и если не указал, записываем по цене из metal_types -
        # эту цену мы заранее передавали пользователю при выборе другого металла
        all_operations.price = float(split_message[1].replace(',', '.')) if ' ' in message.text\
            else float(user.price)
        all_operations.sum = all_operations.quantity * all_operations.price  # Записываем сумму
        all_operations.comment = ' '.join(split_message[2:])  # Записываем комментарий если он есть

        # Здесь мы проверяем, записывает ли пользователь операцию через функцию
        # 'Начать запись куша' из 'Меню кнопки Куш'
        # Если пользователь записывает не через эту функцию, то сразу добавляем операцию в базу данных
        # Если пользователь всё же записывает через эту функцию то,
        # операцию мы запишем позже по другой цене и в другой функции
        if not user.kush_recording:
            dbs.add(all_operations)
        # Сбрасываем значения у пользователя по умолчанию
        user.metal = 'Черный'
        user.price = float(metal_types['Черный'])
        # Также прибавляем получившуюся сумму к общей сумме клиента
        user.client_amount = user.client_amount + all_operations.sum
        # Костыль для изменения общей суммы клиента, если кнопка с общей суммой клиента уже есть то, удаляем её
        if len(inline_kb_markup.inline_keyboard) != 0:
            inline_kb_markup.inline_keyboard.clear()
        # Добавляем кнопку с общей суммой клиента, если кнопка вызывается не внутри состояния то,
        # при нажатии на неё сбрасывает общую сумму клиента
        inline_kb_markup.add(InlineKeyboardButton(f'Общая сумма: {user.client_amount}',
                                                  callback_data='reset_total_amount'))
        await message.bot.send_message(message.chat.id, f'Успешно добавлено - {all_operations.metal}: '
                                                        f'{all_operations.quantity},'
                                                        f' Цена: {all_operations.price},'
                                                        f' Сумма: {round(all_operations.sum)}',
                                       reply_markup=inline_kb_markup)
        # Собираем данные для записи операции в google sheets
        data = [date_time[0].replace('-', '.'), date_time[1][:5], all_operations.metal,
                all_operations.quantity, all_operations.price, all_operations.sum, all_operations.comment]
        dbs.commit()
        # Если пользователь записывает операцию через функцию 'Начать запись куша' из 'Меню кнопки Куш'
        # то добавляем операцию в temp_operations и не записываем операцию в google sheets
        if user.kush_recording:
            temp_operations[message.from_user.id].append(data)
            return
        # Если функция дошла до этого момента, передаём данные для записи операции в google sheets
        record_plus_operation(data)
    except:
        await message.bot.send_message(message.chat.id,
                                       f'Вы неправильно вписали данные, проверьте корректность в руководстве')
        return


async def do_minus_operation(message):
    split_message = message.text.split()
    try:
        dbs = db_session.create_session()
        user = dbs.query(User).get(message.from_user.id)
        # Создаём и записываем значения в MinusOperations
        minus_operations = MinusOperations()
        minus_operations.metal = user.metal  # Записываем выбранный пользователем металл
        # Записываем дату
        minus_operations.date = datetime.datetime.strptime(str(message.date).split()[0], "%Y-%m-%d").date()
        minus_operations.quantity = abs(float(split_message[0].replace(',', '.')))  # Записываем колличество
        minus_operations.task = ''  # Записываем почему был продан металл
        minus_operations.where = ''  # Записываем где был продан металл
        # Это проверка, если пользователь просто хочет сделать Корректировку
        # Это проверка нужна для того, чтобы записать минусовую операцию без цены и суммы
        if split_message[-1] != 'Корректировка':
            # Если 'Корректировки' нету то
            minus_operations.price = float(split_message[1].replace(',', '.')) if ' ' in message.text \
                else float(user.price)  # Записываем цену металла которую передал пользователь
            minus_operations.sum = minus_operations.quantity * minus_operations.price  # Записываем сумму
            # Делаем проверку вписал ли пользователь что-то после колличества и суммы
            if len(split_message[2:]) == 1:
                # Если вписал только одно значение,
                # то записываем это значение туда где нужно указать 'где был продан металл'
                minus_operations.where = split_message[-1]
            if len(split_message[2:]) >= 2:
                # Если вписал несколько значений, то
                # Последнее значение записываем туда где нужно указать 'почему был продан металл'
                minus_operations.task = split_message[2:][-1]
                # А первое значение записываем туда где нужно указать 'где был продан металл'
                minus_operations.where = split_message[2:][0]
        else:
            # Если 'Корректировка' было передано то
            minus_operations.price = 0  # Записываем цену нулём
            minus_operations.sum = 0  # Также записываем сумму нулём
            minus_operations.task = split_message[-1]  # Записываем почему был продан металл
            minus_operations.where = split_message[1]  # Записываем где был продан металл
        # Теперь записываем в 'AllOperations'
        all_operations = AllOperations()
        date_time = str(message.date).split()  # Берём дату и время
        all_operations.date = datetime.datetime.strptime(date_time[0], "%Y-%m-%d").date()  # Записываем дату
        all_operations.time = datetime.datetime.strptime(date_time[1], "%H:%M:%S").time()  # Записываем время
        all_operations.metal = user.metal  # Записываем выбранный пользователем металл
        all_operations.quantity = float(split_message[0].replace(',', '.'))  # Записываем колличество
        all_operations.price = minus_operations.price  # Записываем цену
        all_operations.sum = all_operations.quantity * all_operations.price  # Записываем сумму
        all_operations.comment = minus_operations.where  # Записываем комментарий
        # Добавляем всё это в базу данных
        dbs.add(minus_operations)
        dbs.add(all_operations)
        # Сбрасываем значения у пользователя по умолчанию
        user.metal = 'Черный'
        user.price = float(metal_types['Черный'])
        # Также прибавляем получившуюся сумму к общей сумме клиента
        user.client_amount = user.client_amount - minus_operations.sum
        # Костыль для изменения общей суммы клиента, если кнопка с общей суммой клиента уже есть то, удаляем её
        if len(inline_kb_markup.inline_keyboard) != 0:
            inline_kb_markup.inline_keyboard.clear()
        # Добавляем кнопку с общей суммой клиента, если кнопка вызывается не внутри состояния то,
        # при нажатии на неё сбрасывает общую сумму клиента
        inline_kb_markup.add(InlineKeyboardButton(f'Общая сумма: {user.client_amount}',
                                                  callback_data='show_temp_amount'))
        await message.bot.send_message(message.chat.id, f'Успешно добавлено - {minus_operations.metal}: '
                                                        f'{minus_operations.quantity},'
                                                        f' Цена: {minus_operations.price},'
                                                        f' Сумма: {round(minus_operations.sum)}',
                                       reply_markup=inline_kb_markup)
        dbs.commit()
        # Если функция дошла до этого момента, передаём данные для записи операции в google sheets
        record_minus_operation([minus_operations.metal, minus_operations.quantity, minus_operations.price,
                                minus_operations.sum,
                                str(message.date).split()[0].replace('-', '.'), minus_operations.task,
                                minus_operations.where])
    except:
        await message.bot.send_message(message.chat.id,
                                       f'Вы неправильно вписали данные, проверьте корректность в руководстве')
        return