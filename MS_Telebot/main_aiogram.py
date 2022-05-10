from aiogram import types, executor, Dispatcher, Bot
from aiogram.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage

# Импортируем функии из модуля api_sheets
from api_sheets import call_metals_prices
from api_sheets import record_plus_operation, delete_last_row, record_minus_operation, get_report

import os
import datetime
# Импортируем базу данных
from data import db_session
from data.users import User
from data.all_operations import AllOperations
from data.minus_operations import MinusOperations
from data.clean_weights import ButtonsCleanWeights

# Также импортируем api token
from config import TOKEN

# Подключаем базу данных
db_session.global_init("db/Metals_with_data.db")

# Загружаем руководство
with open('usage guide', 'r', encoding='UTF-8') as guide:
    GUIDE = ''.join(guide.readlines())

# Здесь мы берём список кортежей и преобразуем его в словарь
metal_types = dict(call_metals_prices())
kush_prices = dict(call_metals_prices(kush=True))

# Создаём списки кнопок
menu_buttons = ['Записать веса', 'Куш', 'Отчёты', 'Чистые веса']
information_buttons = ['Сводка весов за всё время', 'Сводка весов за сегодня',
                       'Цены металлов', 'Куш цены металлов']
kush_buttons = ['Начать запись куша', 'Указать процент для куша']
clean_weights_buttons = [name[0] for name in db_session.create_session().query(
    ButtonsCleanWeights.name_clean_weight).all()]

# Этот словарь нужен для do_kush, он сохраняет веса которые нужно перепистаь по другим ценам
temp_operations = {}


# Создаём бота
bot = Bot(token=TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())
# Создаём клавиатуры
reply_kb_menu = ReplyKeyboardMarkup(resize_keyboard=True)
reply_kb_metals = ReplyKeyboardMarkup(resize_keyboard=True)
reply_kb_kush = ReplyKeyboardMarkup(resize_keyboard=True)
reply_kb_kush_recording = ReplyKeyboardMarkup(resize_keyboard=True)
reply_kb_information = ReplyKeyboardMarkup(resize_keyboard=True)
reply_kb_clean_weights = ReplyKeyboardMarkup(resize_keyboard=True)
inline_kb_markup = InlineKeyboardMarkup()


# Создаём состояния которые будут вызывать функции по данным им запросам:
# Состояние (Меню кнопки 'Записать веса')
class Recording(StatesGroup):
    waiting_for_data_record = State()


# Состояние (Меню кнопки 'Куш')
class Kush(StatesGroup):
    waiting_for_kush_request = State()
    waiting_for_kush_percent = State()


# Состояние (Меню кнопки 'Отчёты')
class Report(StatesGroup):
    waiting_for_report_request = State()


# Состояние (Меню кнопки 'Чистые веса')
class CleanWeights(StatesGroup):
    waiting_for_request = State()
    waiting_for_new_clean_weights = State()
    waiting_for_remove_clean_weight = State()


# Функия для удобной загрузки кнопок в клавиатуры
def load_buttons(keyboard, initial_buttons=[], two_buttons_row=[], end_buttons=[], btn_back=True):
    new_row = True
    # В начале клавиатуры добавляет кнопки, каждую в новый ряд
    for btn in initial_buttons:
        keyboard.add(types.KeyboardButton(btn))
    # Добавляет кнопки после начальных кнопок, по две ряд
    for btn in two_buttons_row:
        if new_row:
            keyboard.add(types.KeyboardButton(btn))
            new_row = False
        else:
            keyboard.insert(types.KeyboardButton(btn))
            new_row = True
    # Добавляет кнопки в конце
    for btn in end_buttons:
        keyboard.add(types.KeyboardButton(btn))
    # Проверка нужно ли добавлять кнопку возвращения в меню
    if btn_back:
        keyboard.add(types.KeyboardButton('Вернуться в меню'))


# Загружаем кнопки в клавиатуры
load_buttons(reply_kb_menu, two_buttons_row=menu_buttons, end_buttons=['📚Руководство'], btn_back=False)
load_buttons(reply_kb_metals, initial_buttons=['Сбросить общую сумму'],
             two_buttons_row=list(metal_types.keys()), end_buttons=['Удалить последную запись'])
load_buttons(reply_kb_kush_recording, initial_buttons=['Веса вписаны', 'Сбросить общую сумму'],
             two_buttons_row=list(metal_types.keys()), end_buttons=['Удалить последную запись',
                                                                    'Вернуться в меню куша'], btn_back=False)
load_buttons(reply_kb_kush, two_buttons_row=kush_buttons)
load_buttons(reply_kb_information, two_buttons_row=information_buttons)
load_buttons(reply_kb_clean_weights, initial_buttons=['Добавить новый предмет с его чистым весом', 'Удалить предмет'],
             two_buttons_row=clean_weights_buttons)


# Функия для проверки является ли переденанное ему значение просто числом или числом с плавающей точкой
def is_float_int(digits):
    true_symbols = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '.', '-']
    # Если он есть '-' и он стоит не вначале, возвращяет False
    if '-' in digits and digits.index('-') > 0:
        return False
    for symb in digits.replace(',', '.'):
        if symb not in true_symbols:
            return False
    return True


# Функия для изменения выбранного металла пользователем
async def change_metal(message):
    dbs = db_session.create_session()
    user = dbs.query(User).get(message.from_user.id)
    user.metal = message.text  # Меняем металл у пользователя
    user.price = float(metal_types[message.text])  # Также меняем цену, её собственно берём из словаря
    dbs.commit()
    await bot.send_message(message.chat.id,
                           f'Выбранный тип металла: {user.metal},'
                           f' Цена: {user.price}',
                           reply_markup=reply_kb_kush_recording if user.kush_recording else reply_kb_metals)


# Функия сбрасывает накопившуюся общую сумму клиента
async def reset_total_amount(message: types.Message):
    # Сбрасываем общую сумму клиента в базе
    dbs = db_session.create_session()
    user = dbs.query(User).get(message.from_user.id)
    user.client_amount = 0
    dbs.commit()
    # И также сбрасываем это значение у кнопки (Здесь на самом деле я удаляю кнопку)
    inline_kb_markup.inline_keyboard.clear()
    await message.answer('Ждём нового клиента')


# Функия для записи плюсовых весов металла в базу данных
async def do_plus_operation(message: types.Message):
    global temp_operations
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
        await bot.send_message(message.chat.id, f'Успешно добавлено - {all_operations.metal}: '
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
        await bot.send_message(message.chat.id, f'Вы неправильно вписали данные, проверьте корректность в руководстве')
        return


# Функия для записи минусовых весов металла в базу данных
async def do_minus_operation(message):
    global temp_operations
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
        await bot.send_message(message.chat.id, f'Успешно добавлено - {minus_operations.metal}: '
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
    except Exception:
        await bot.send_message(message.chat.id, f'Вы неправильно вписали данные, проверьте корректность в руководстве')
        return


# Состояние(Меню кнопки 'Куш') для обработки передаваемых ему запросов
@dp.message_handler(state=Kush.waiting_for_kush_request)
async def do_kush(message: types.Message, state: FSMContext):
    dbs = db_session.create_session()
    current_user = dbs.query(User).get(message.from_user.id)
    if message.text in 'Вернуться в меню':
        await bot.send_message(message.chat.id, 'Вы в меню',
                               reply_markup=reply_kb_menu)
        await state.finish()
        return
    elif message.text == 'Начать запись куша':
        # При запуске этой функции, сбрасываем или установливаем некоторые значение
        temp_operations[message.from_user.id] = []  # Сбрасываем список операций который пользователь забыл записать
        current_user.kush_recording = True  # Устанавливаем то, что пользователь в данный момент записывает куш
        current_user.client_amount = 0  # Сбрасываем общую сумму клиента
        await bot.send_message(message.chat.id, 'Куш записывается, впишите веса',
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
        await bot.send_message(message.chat.id, 'Вы в меню',
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


# Состояние (Меню кнопки 'Записать веса') для обработки передаваемых ему запросов
@dp.message_handler(state=Recording.waiting_for_data_record)
async def do_record(message: types.Message, state: FSMContext):
    dbs = db_session.create_session()
    current_user = dbs.query(User).get(message.from_user.id)
    if message.text == 'Вернуться в меню':
        await bot.send_message(message.chat.id, 'Записывание весов металла остановлено',
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
        await bot.send_message(message.chat.id, 'Записывание куша прервано, веса сброшены',
                               reply_markup=reply_kb_kush)
        await state.finish()
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
            await bot.send_message(message.chat.id, 'Вы не вписали не один вес',
                                   reply_markup=reply_kb_metals)
            return
        # Общая сумма сум по основным ценам 'Актуальный прайс'
        total_amount_tmp_s = round(sum(operation[5] for operation in temp_operations[message.from_user.id]))
        # Сумма рабочего который разобрал куш клиента
        worker_amount = round(total_amount_tmp_s / 100 * current_user.kush_percent)
        # Изменяем операции на новые цены, а также изменяем сумму под новую цену
        for operation in temp_operations[message.from_user.id]:
            operation[4] = float(kush_prices[operation[2]].replace(',', '.'))  # Изменяем цену
            operation[5] = operation[3] * operation[4]  # Изменяем сумму
        # Сумма работадателя которую нужно отнять от суммы клиента
        employer_amount = sum(operation[3] * float(kush_prices['Черный'].replace(',', '.'))
                              for operation in temp_operations[message.from_user.id])
        # Сумма клиента чей куш был разобран
        client_amount = round(sum(operation[5] for operation in temp_operations[message.from_user.id])
                              - employer_amount - worker_amount)
        information = f'\n{"---" * 10}\n'.join([f'Сумма рабочего: {worker_amount}', f'Ваша Сумма: {client_amount}'])
        await bot.send_message(message.chat.id, information,
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
        await bot.send_message(message.chat.id, f'Последняя запись успешно удалена',
                               reply_markup=reply_kb_kush_recording if current_user.kush_recording
                               else reply_kb_metals)
    else:
        await message.answer("Запрос отклонён, пожалуйста сделайте запрос как показано в руководстве")
        return
    dbs.commit()


# Состояние (Меню кнопки 'Отчёты') для обработки передаваемых ему запросов
@dp.message_handler(state=Report.waiting_for_report_request)
async def show_report(message: types.Message, state: FSMContext):
    if message.text == 'Вернуться в меню':
        await bot.send_message(message.chat.id, 'Записывание весов металла остановлено',
                               reply_markup=reply_kb_menu)
        await state.finish()
        return
    elif message.text == 'Сводка весов за всё время':
        # Вызываем функцию которая возвращяет информацию(сколько металла было принято) и передаём ей значение
        request = get_report('all_time')
        # Если request нечего не вернул, повторяем функцию
        if not request:
            request = get_report('all_time')
        # Данную нам информацию для более читабельной
        data = f'\n{"---" * 10}\n'.join([' '.join(cort) for cort in request])
        await bot.send_message(message.chat.id, data,
                               reply_markup=reply_kb_information)
        return
    elif message.text == 'Сводка весов за сегодня':
        # Вызываем функцию которая возвращяет информацию(сколько металла было принято) и передаём ей значение
        request = get_report('today')
        # Если request нечего не вернул, повторяем функцию
        if not request:
            request = get_report('today')
        # Данную нам информацию для более читабельной
        data = f'\n{"---" * 10}\n'.join([' '.join(cort) for cort in request])
        await bot.send_message(message.chat.id, data,
                               reply_markup=reply_kb_information)
        return
    elif message.text == 'Цены металлов':
        # Вызываем функцию которая возвращяет цены металлов
        request = call_metals_prices()
        if not request:
            request = call_metals_prices()
        data = f'\n{"---" * 10}\n'.join([' '.join(cort) for cort in request])
        await bot.send_message(message.chat.id, data,
                               reply_markup=reply_kb_information)
        return
    elif message.text == 'Куш цены металлов':
        # Вызываем функцию которая возвращяет цены металлов, передаём значение чтобы цены вернули из другой таблицы
        request = call_metals_prices(kush=True)
        if not request:
            request = call_metals_prices(kush=True)
        data = f'\n{"---" * 10}\n'.join([' '.join(cort) for cort in request])
        await bot.send_message(message.chat.id, data,
                               reply_markup=reply_kb_information)
        return


# Состояние (Меню кнопки 'Чистые веса') для обработки передаваемых ему запросов
@dp.message_handler(state=CleanWeights.waiting_for_request)
async def clean_weights(message: types.Message, state: FSMContext):
    dbs = db_session.create_session()
    if message.text == 'Вернуться в меню':
        await bot.send_message(message.chat.id, 'Вы в меню',
                               reply_markup=reply_kb_menu)
        await state.finish()
        return
    if message.text == 'Добавить новый предмет с его чистым весом':
        await bot.send_message(message.chat.id, 'Добавьте фото предмета с его названием и описанием',
                               reply_markup=reply_kb_clean_weights)
        # Переходим в состояния(функцию) для добавления нового чистого веса
        await CleanWeights.waiting_for_new_clean_weights.set()
        return
    if message.text == 'Удалить предмет':
        await bot.send_message(message.chat.id, 'Нажмите на копку с названием предмета',
                               reply_markup=reply_kb_clean_weights)
        # Переходим в состояния(функцию) для удаления чистого веса
        await CleanWeights.waiting_for_remove_clean_weight.set()
    if message.text in clean_weights_buttons:
        # Отправляем пользователю фото предмета с его чистым весом
        clean_weight = dbs.query(ButtonsCleanWeights).filter(ButtonsCleanWeights.name_clean_weight
                                                             == message.text).first()
        await bot.send_photo(message.from_user.id, types.InputFile(clean_weight.path),
                             caption=clean_weight.description_clean_w,
                             reply_to_message_id=message.message_id)


# Состояние(функция из Меню кнопки 'Чистые веса') для добавления чистого веса
@dp.message_handler(content_types=['photo', 'text'], state=CleanWeights.waiting_for_new_clean_weights)
async def add_new_clean_weight(message: types.Message, state: FSMContext):
    dbs = db_session.create_session()
    # Делаем проверку отправил ли пользователь текст с картинкой
    if not message.caption:
        await bot.send_message(message.chat.id, "Запрос отклонён, пожалуйста сделайте запрос"
                                                " как показано в руководстве и повторите комманду",
                               reply_markup=reply_kb_clean_weights)
        # Возвращаемся в состояния(Меню кнопки 'Чистые веса')
        await CleanWeights.waiting_for_request.set()
        return
    if message.md_text in 'Вернуться в меню':
        await bot.send_message(message.chat.id, 'Вы в меню',
                               reply_markup=reply_kb_menu)
        await state.finish()
        return
    # Делаем проверку отправил ли пользователь текст с '-'
    if not message.md_text or '-' not in message.md_text and message.md_text.count('-') == 1 or not message.photo or\
            '-' not in message.caption:
        await bot.send_message(message.chat.id, "Запрос отклонён, пожалуйста сделайте запрос"
                                                " как показано в руководстве и повторите комманду",
                               reply_markup=reply_kb_clean_weights)
        # Возвращаемся в состояния(Меню кнопки 'Чистые веса')
        await CleanWeights.waiting_for_request.set()
        return
    # Делаем проверку есть ли чистый вес уже в списке чистых весов
    if message.md_text.split('-')[0][:-1].strip() in clean_weights_buttons:
        await bot.send_message(message.chat.id, 'Предмет с таким названием, уже есть в базе.'
                                                ' Пожалуйста придумайте другое название и повторите попытку',
                               reply_markup=reply_kb_clean_weights)
        return
    # Создаём и добавляем значение в ButtonsCleanWeights
    new_clean_weight = ButtonsCleanWeights()
    new_clean_weight.name_clean_weight = message.md_text.split('-')[0][:-1].strip()  # Записываем название предмета
    new_clean_weight.description_clean_w = message.md_text.split('-')[1].strip()  # Записываем чистый вес предмета
    # Берём последний чистый вес из 'ButtonsCleanWeights'
    last_row = dbs.query(ButtonsCleanWeights).order_by(ButtonsCleanWeights.id.desc()).first()
    # Проверяем есть ли вообще хоть что-то в 'ButtonsCleanWeights'
    if last_row:
        # Если есть то, берём индекс последнего чистого веса и прибавляем 1, делаем это название фотографии
        # И создаём путь к новой фотографии
        path = f'photos_of_clean_weights/{last_row.id + 1}.jpg'
    else:
        # Если нету то, просто ставим 1 в название новой фотографии
        # И создаём путь к новой фотографии
        path = f'photos_of_clean_weights/1.jpg'
    new_clean_weight.path = path  # Записываем путь к фотографии чистого веса
    dbs.add(new_clean_weight)  # Добавляем чистый вес в бд
    clean_weights_buttons.append(new_clean_weight.name_clean_weight)  # Также добавляем чистый вес в список кнопок
    await message.photo[-1].download(path)  # Скачиваем фотографии и передаём ей путь который мы составили ранее
    reply_kb_clean_weights.keyboard = reply_kb_clean_weights.keyboard[:-1]  # Удаляем из клавиатуры последную кнопку
    if len(dbs.query(ButtonsCleanWeights).all()) % 2 != 0:  # Если в бд количество чистых весов не чётное
        # То добавляем кнопку на новую строку
        reply_kb_clean_weights.add(types.KeyboardButton(new_clean_weight.name_clean_weight))
    else:
        # Если чётное то, добавляем чистый вес на строку с последним чистым весов
        reply_kb_clean_weights.insert(types.KeyboardButton(new_clean_weight.name_clean_weight))
    reply_kb_clean_weights.add(types.KeyboardButton('Вернуться в меню'))  # Теперь возвращяем кнопку
    await bot.send_message(message.chat.id, 'Новый чистый вес добавлен!',
                           reply_markup=reply_kb_clean_weights)
    dbs.commit()
    # Возвращаемся в состояния(Меню кнопки 'Чистые веса')
    await CleanWeights.waiting_for_request.set()


# Состояние(функция из Меню кнопки 'Чистые веса') для удаления чистого веса
@dp.message_handler(content_types=['photo', 'text'], state=CleanWeights.waiting_for_remove_clean_weight)
async def remove_clean_weight(message: types.Message, state: FSMContext):
    dbs = db_session.create_session()
    if message.md_text in 'Вернуться в меню':
        await bot.send_message(message.chat.id, 'Вы в меню',
                               reply_markup=reply_kb_menu)
        await state.finish()
        return
    # Проверяем есть данное название чистого веса в списке чистых весов
    elif message.text in clean_weights_buttons:
        # Берём чистый вес из бд по данному нам названию
        clean_weight = dbs.query(ButtonsCleanWeights).filter(ButtonsCleanWeights.name_clean_weight
                                                             == message.text).first()
        os.remove(clean_weight.path)  # Удаляем фотографию чистого веса
        clean_weights_buttons.remove(clean_weight.name_clean_weight)  # Также удаляем из списка чистый вес
        # Удаляем из клавиатуры
        reply_kb_clean_weights.keyboard.remove([types.KeyboardButton(clean_weight.name_clean_weight)])
        dbs.delete(clean_weight)  # И наконец-то удаляем из бд
        dbs.commit()
        await bot.send_message(message.chat.id, 'Чистый вес успешно удалён!',
                               reply_markup=reply_kb_clean_weights)
        # Возвращаемся в состояния(Меню кнопки 'Чистые веса')
        await CleanWeights.waiting_for_request.set()
    else:
        await bot.send_message(message.chat.id, 'Такого предмета нету в базе данных!',
                               reply_markup=reply_kb_clean_weights)


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
    await bot.send_message(message.chat.id, 'Бот включён, приятного пользования!', reply_markup=reply_kb_menu)


# Функия для обновления цен
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
    await bot.send_message(message.chat.id, 'Цены обновлены!', reply_markup=reply_kb_menu)


@dp.message_handler(content_types=['text'])
async def set_text(message):
    global temp_operations
    if message.chat.type == 'private':
        if message.text == 'Записать веса':
            await bot.send_message(message.chat.id, 'Типы металлов загружены',
                                   reply_markup=reply_kb_metals)
            await Recording.waiting_for_data_record.set()
            return
        elif message.text == 'Куш':
            await bot.send_message(message.chat.id, 'Кнопки куша загружены',
                                   reply_markup=reply_kb_kush)
            await Kush.waiting_for_kush_request.set()
        elif message.text == 'Отчёты':
            await bot.send_message(message.chat.id, 'Кнопки отчётов загружены',
                                   reply_markup=reply_kb_information)
            await Report.waiting_for_report_request.set()
        elif message.text == 'Чистые веса':
            await bot.send_message(message.chat.id, 'Кнопки чистых весов загружены',
                                   reply_markup=reply_kb_clean_weights)
            await CleanWeights.waiting_for_request.set()
        elif message.text == '📚Руководство':
            await bot.send_message(message.chat.id, GUIDE,
                                   reply_markup=reply_kb_menu)
        else:
            await bot.send_message(message.chat.id, 'В этом боте нету такой котегории',
                                   reply_markup=reply_kb_menu)


async def for_startup(empty):
    # При запуске бота возвращяем всех пользователей в меню
    for user_id in db_session.create_session().query(User.id).all():
        await bot.send_message(user_id[0], 'Бот запущен!', reply_markup=reply_kb_menu)


if __name__ == '__main__':
    while True:
        try:
            executor.start_polling(dp, skip_updates=True, on_startup=for_startup)
        except Exception as e:
            print(e)
            executor.start_polling(dp, skip_updates=True, on_startup=for_startup)