from aiogram import types, executor, Dispatcher, Bot
from aiogram.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage

from api_sheets import call_metals_prices
from api_sheets import record, delete_last_row, record_minus_operation, get_report

import os
import datetime
from data import db_session
from data.users import User
from data.all_operations import AllOperations
from data.minus_operations import MinusOperations
from data.clean_weights import ButtonsCleanWeights

from config import TOKEN

db_session.global_init("db/Metals_with_data.db")


metal_types = dict(call_metals_prices())
kush_prices = dict(call_metals_prices(kush=True))
menu_buttons = ['Записать веса', 'Куш', 'Отчёты', 'Чистые веса', '📚Руководство']
information_buttons = ['Сводка весов за всё время', 'Сводка весов за сегодня',
                       'Цены металлов', 'Куш цены металлов']
kush_buttons = ['Начать запись куша', 'Указать процент для куша']
clean_weights_buttons = [name[0] for name in db_session.create_session().query(
    ButtonsCleanWeights.name_clean_weight).all()]
temp_weights = {}

bot = Bot(token=TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())
reply_kb_menu = ReplyKeyboardMarkup(resize_keyboard=True)
reply_kb_metals = ReplyKeyboardMarkup(resize_keyboard=True)
reply_kb_information = ReplyKeyboardMarkup(resize_keyboard=True)
reply_kb_kush = ReplyKeyboardMarkup(resize_keyboard=True)
reply_kb_clean_weights = ReplyKeyboardMarkup(resize_keyboard=True)
inline_kb_markup = InlineKeyboardMarkup()


class Recording(StatesGroup):
    waiting_for_data_record = State()


class Kush(StatesGroup):
    waiting_for_kush_request = State()
    waiting_for_kush_percent = State()


class Report(StatesGroup):
    waiting_for_report_request = State()


class CleanWeights(StatesGroup):
    waiting_for_request = State()
    waiting_for_new_clean_weights = State()
    waiting_for_remove_clean_weight = State()


def load_buttons(keyboard, ls_buttons, btn_back=True):
    new_row = True
    for btn in ls_buttons:
        if new_row:
            keyboard.add(types.KeyboardButton(btn))
            new_row = False
        else:
            keyboard.insert(types.KeyboardButton(btn))
            new_row = True
    if btn_back:
        keyboard.add(types.KeyboardButton('Вернуться в меню'))


load_buttons(reply_kb_menu, menu_buttons, btn_back=False)

reply_kb_metals.add(types.KeyboardButton('Сбросить общую сумма'))
load_buttons(reply_kb_metals, [*list(metal_types.keys()), 'Удалить последную запись'])

load_buttons(reply_kb_kush, kush_buttons)
load_buttons(reply_kb_information, information_buttons)

reply_kb_clean_weights.add(types.KeyboardButton('Добавить новый чистый вес'))
reply_kb_clean_weights.add(types.KeyboardButton('Удалить вес'))
load_buttons(reply_kb_clean_weights, [*clean_weights_buttons])


def is_float_int(digits):
    true_symbols = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '.', '-']
    if '-' in digits and digits.index('-') > 0:
        return False
    for symb in digits.replace(',', '.'):
        if symb not in true_symbols:
            return False
    return True


async def swap_metal(message):
    dbs = db_session.create_session()
    user = dbs.query(User).get(message.from_user.id)
    user.metal = message.text
    user.price = float(metal_types[message.text])
    dbs.commit()
    await bot.send_message(message.chat.id,
                           f'Выбранный тип металла: {user.metal},'
                           f' Цена: {user.price}',
                           reply_markup=reply_kb_metals)


async def reset_total_amount(message: types.Message):
    dbs = db_session.create_session()
    user = dbs.query(User).get(message.from_user.id)
    user.client_amount = 0
    dbs.commit()
    inline_kb_markup.inline_keyboard.clear()
    await message.answer('Ждём нового клиента')


async def do_plus_operation(message: types.Message):
    global temp_weights
    # Загружаем значения в базу данных
    try:
        dbs = db_session.create_session()
        user = dbs.query(User).get(message.from_user.id)
        all_operations = AllOperations()
        date_time = str(message.date).split()
        all_operations.date = datetime.datetime.strptime(date_time[0], "%Y-%m-%d").date()
        all_operations.time = datetime.datetime.strptime(date_time[1], "%H:%M:%S").time()
        all_operations.metal = user.metal
        all_operations.quantity = float(message.text.split()[0].replace(',', '.'))
        all_operations.price = float(message.text.split()[1].replace(',', '.')) if ' ' in message.text\
            else float(user.price)
        all_operations.sum = all_operations.quantity * all_operations.price
        all_operations.comment = ' '.join(message.text.split()[2:])
        if not user.kush_recording:
            dbs.add(all_operations)
        user.metal = 'Черный'
        user.price = float(metal_types['Черный'])
        user.client_amount = user.client_amount + all_operations.sum
        if len(inline_kb_markup.inline_keyboard) != 0:
            inline_kb_markup.inline_keyboard.clear()
        inline_kb_markup.add(InlineKeyboardButton(f'Общая сумма: {user.client_amount}',
                                                  callback_data='show_temp_amount'))
        await bot.send_message(message.chat.id, f'Успешно добавлено - {all_operations.metal}: '
                                                f'{all_operations.quantity},'
                                                f' Цена: {all_operations.price},'
                                                f' Сумма: {round(all_operations.sum)}',
                               reply_markup=inline_kb_markup)
        values = [date_time[0].replace('-', '.'), date_time[1][:5], all_operations.metal,
                  all_operations.quantity, all_operations.price, all_operations.sum, all_operations.comment]
        dbs.commit()
        if user.kush_recording:
            temp_weights[message.from_user.id].append(values)
            return
        record(values)
    except Exception as e:
        print(e)
        await bot.send_message(message.chat.id, f'Вы неправильно вписали данные, проверьте корректность в руководстве')
        return


async def do_minus_operation(message):
    global temp_weights
    # Загружаем значения в базу данных
    try:
        dbs = db_session.create_session()
        user = dbs.query(User).get(message.from_user.id)
        # Добавляем данные сначала в минусовые операции
        minus_operations = MinusOperations()
        minus_operations.metal = user.metal
        minus_operations.date = datetime.datetime.strptime(str(message.date).split()[0], "%Y-%m-%d").date()
        minus_operations.quantity = abs(float(message.text.split()[0].replace(',', '.')))
        minus_operations.task = ''
        minus_operations.where = ''
        if message.text.split()[-1] != 'Корректировка':
            minus_operations.price = float(message.text.split()[1].replace(',', '.')) if ' ' in message.text \
                else float(user.price)
            minus_operations.sum = minus_operations.quantity * minus_operations.price
            if len(message.text.split()[2:]) == 1:
                minus_operations.where = message.text.split()[2:3][0]
            if len(message.text.split()[2:]) == 2:
                minus_operations.task = message.text.split()[2:][-1]
                minus_operations.where = message.text.split()[2:][0]
        else:
            minus_operations.price = 0
            minus_operations.sum = 0
            minus_operations.task = message.text.split()[-1]
            minus_operations.where = message.text.split()[1]
        # Теперь добавляем в все операции
        all_operations = AllOperations()
        date_time = str(message.date).split()
        all_operations.date = datetime.datetime.strptime(date_time[0], "%Y-%m-%d").date()
        all_operations.time = datetime.datetime.strptime(date_time[1], "%H:%M:%S").time()
        all_operations.metal = user.metal
        all_operations.quantity = float(message.text.split()[0].replace(',', '.'))
        all_operations.price = float(message.text.split()[1].replace(',', '.')) if ' ' in message.text \
            else float(user.price)
        all_operations.sum = all_operations.quantity * all_operations.price
        all_operations.comment = message.text.split()[1]

        dbs.add(minus_operations)
        dbs.add(all_operations)
        user.client_amount = user.client_amount - minus_operations.sum
        user.metal = 'Черный'
        user.price = float(metal_types['Черный'])
        if len(inline_kb_markup.inline_keyboard) != 0:
            inline_kb_markup.inline_keyboard.clear()
        inline_kb_markup.add(InlineKeyboardButton(f'Общая сумма: {user.client_amount}',
                                                  callback_data='show_temp_amount'))
        await bot.send_message(message.chat.id, f'Успешно добавлено - {minus_operations.metal}: '
                                                f'{minus_operations.quantity},'
                                                f' Цена: {minus_operations.price}, Сумма: {round(minus_operations.sum)}',
                               reply_markup=inline_kb_markup)
        dbs.commit()
        record_minus_operation([minus_operations.metal, minus_operations.quantity, minus_operations.price, minus_operations.sum,
                                str(message.date).split()[0].replace('-', '.'), minus_operations.task,
                                minus_operations.where])
    except Exception as e:
        print(e)
        await bot.send_message(message.chat.id, f'Вы неправильно вписали данные, проверьте корректность в руководстве')
        return


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
        temp_weights[message.from_user.id] = []
        current_user.kush_recording = True
        # reply_kb_metals.keyboard.clear()
        reply_kb_metals.keyboard.insert(0, ['Веса вписаны'])
        reply_kb_metals.keyboard[-1] = ['Вернуться в меню куша']
        await bot.send_message(message.chat.id, 'Куш записывается, впишите веса',
                               reply_markup=reply_kb_metals)
        dbs.commit()
        await Recording.waiting_for_data_record.set()
        return
    elif message.text == 'Указать процент для куша':
        await message.answer("Укажите процент:")
        await Kush.next()
        return
    # user = dbs.query(User).get(message.from_user.id)
    # dbs.commit()
    await state.finish()


@dp.message_handler(state=Kush.waiting_for_kush_percent)
async def kush_set_percent(message: types.Message, state: FSMContext):
    dbs = db_session.create_session()
    if message.text in 'Вернуться в меню':
        await bot.send_message(message.chat.id, 'Вы в меню',
                               reply_markup=reply_kb_menu)
        await state.finish()
    elif not is_float_int(message.text) or float(message.text) < 0 or float(message.text.lower()) > 100:
        await message.answer("Запрос отклонён, пожалуйста впишите процент как показано в руководстве")
        return
    user = dbs.query(User).get(message.from_user.id)
    user.kush_percent = float(message.text)
    dbs.commit()
    await message.answer("Процент успешно установлен")
    await Kush.waiting_for_kush_request.set()


@dp.message_handler(state=Recording.waiting_for_data_record)
async def do_record(message: types.Message, state: FSMContext):
    dbs = db_session.create_session()
    current_user = dbs.query(User).get(message.from_user.id)
    if message.text == 'Вернуться в меню':
        await bot.send_message(message.chat.id, 'Записывание весов металла остановлено',
                               reply_markup=reply_kb_menu)
        await state.finish()
        return
    if message.text == 'Вернуться в меню куша':
        reply_kb_metals.keyboard.pop(0)
        temp_weights[message.from_user.id] = []
        current_user.kush_recording = False
        current_user.client_amount = 0
        reply_kb_metals.keyboard[-1] = ['Вернуться в меню']
        await bot.send_message(message.chat.id, 'Записывание куша прервано, веса сброшены',
                               reply_markup=reply_kb_kush)
        await state.finish()
        await Kush.waiting_for_kush_request.set()
        return
    if '-' in message.text.split()[0] and is_float_int(message.text.split()[0]):
        await do_minus_operation(message)
    elif is_float_int(message.text.split()[0]):
        await do_plus_operation(message)
    elif message.text in metal_types.keys():
        await swap_metal(message)
    elif message.text == 'Сбросить общую сумма':
        await reset_total_amount(message)
    elif message.text in 'Веса вписаны':
        if not temp_weights[message.from_user.id]:
            await bot.send_message(message.chat.id, 'Вы не вписали не один вес',
                                   reply_markup=reply_kb_metals)
            return
        # Общая сумма сум по основным ценам 'Актуальный прайс'
        total_amount_tmp_s = round(sum(operation[5] for operation in temp_weights[message.from_user.id]))
        # Сумма рабочего который разобрал куш клиента
        worker_amount = round(total_amount_tmp_s / 100 * current_user.kush_percent)
        # Изменяем записи на новые цены, а также изменяем сумму под новую цену
        for operation in temp_weights[message.from_user.id]:
            operation[4] = float(kush_prices[operation[2]].replace(',', '.'))  # Изменяем цену
            operation[5] = operation[3] * operation[4]  # Изменяем сумму
        # Сумма работадателя которую нужно отнять от суммы клиента
        employer_amount = sum(operation[3] * float(kush_prices['Черный'].replace(',', '.'))
                              for operation in temp_weights[message.from_user.id])
        # Сумма клиента чей куш был разобран
        client_amount = round(sum(operation[5] for operation in temp_weights[message.from_user.id])
                              - employer_amount - worker_amount)
        information = f'\n{"---" * 10}\n'.join([f'Сумма рабочего: {worker_amount}', f'Ваша Сумма: {client_amount}'])
        await bot.send_message(message.chat.id, information,
                               reply_markup=reply_kb_kush)
        for operation in temp_weights[message.from_user.id]:
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
            record(operation)
        temp_weights[message.from_user.id] = []
        current_user.kush_recording = False
        current_user.client_amount = 0
        reply_kb_metals.keyboard.pop(0)
        dbs.commit()
        return
    elif message.text == 'Удалить последную запись':
        delete_last_row()
        last_row = dbs.query(AllOperations).order_by(AllOperations.id.desc()).first()
        dbs.delete(last_row)
        await bot.send_message(message.chat.id, f'Последняя запись успешно удалена',
                               reply_markup=reply_kb_metals)
    else:
        await message.answer("Запрос отклонён, пожалуйста сделайте запрос как показано в руководстве")
        return
    dbs.commit()


@dp.message_handler(state=Report.waiting_for_report_request)
async def show_report(message: types.Message, state: FSMContext):
    if message.text == 'Вернуться в меню':
        await bot.send_message(message.chat.id, 'Записывание весов металла остановлено',
                               reply_markup=reply_kb_menu)
        await state.finish()
        return
    elif message.text == 'Сводка весов за всё время':
        request = get_report('all_time')
        if not request:
            request = get_report('all_time')
        data = f'\n{"---" * 10}\n'.join([' '.join(cort) for cort in request])
        await bot.send_message(message.chat.id, data,
                               reply_markup=reply_kb_information)
        return
    elif message.text == 'Сводка весов за сегодня':
        request = get_report('today')
        if not request:
            request = get_report('today')
        data = f'\n{"---" * 10}\n'.join([' '.join(cort) for cort in request])
        await bot.send_message(message.chat.id, data,
                               reply_markup=reply_kb_information)
        return
    elif message.text == 'Цены металлов':
        request = call_metals_prices()
        if not request:
            request = call_metals_prices()
        data = f'\n{"---" * 10}\n'.join([' '.join(cort) for cort in request])
        await bot.send_message(message.chat.id, data,
                               reply_markup=reply_kb_information)
        return
    elif message.text == 'Куш цены металлов':
        request = call_metals_prices(kush=True)
        if not request:
            request = call_metals_prices(kush=True)
        data = f'\n{"---" * 10}\n'.join([' '.join(cort) for cort in request])
        await bot.send_message(message.chat.id, data,
                               reply_markup=reply_kb_information)
        return


@dp.message_handler(state=CleanWeights.waiting_for_request)
async def clean_weights(message: types.Message, state: FSMContext):
    dbs = db_session.create_session()
    if message.text == 'Вернуться в меню':
        await bot.send_message(message.chat.id, 'Вы в меню',
                               reply_markup=reply_kb_menu)
        await state.finish()
        return
    if message.text == 'Добавить новый чистый вес':
        await bot.send_message(message.chat.id, 'Добавьте фото предмета, его название и описание',
                               reply_markup=reply_kb_clean_weights)
        await CleanWeights.waiting_for_new_clean_weights.set()
        return
    if message.text == 'Удалить вес':
        await bot.send_message(message.chat.id, 'Нажмите на копку с названием предмета',
                               reply_markup=reply_kb_clean_weights)
        await CleanWeights.waiting_for_remove_clean_weight.set()
    if message.text in clean_weights_buttons:
        clean_weight = dbs.query(ButtonsCleanWeights).filter(ButtonsCleanWeights.name_clean_weight
                                                             == message.text).first()
        await bot.send_photo(message.from_user.id, types.InputFile(clean_weight.path),
                             caption=clean_weight.description_clean_w,
                             reply_to_message_id=message.message_id)


@dp.message_handler(content_types=['photo', 'text'], state=CleanWeights.waiting_for_new_clean_weights)
async def add_new_clean_weight(message: types.Message, state: FSMContext):
    dbs = db_session.create_session()
    if message.md_text in 'Вернуться в меню':
        await bot.send_message(message.chat.id, 'Вы в меню',
                               reply_markup=reply_kb_menu)
        await state.finish()
        return
    if not message.md_text or '-' not in message.md_text and message.md_text.count('-') == 1 or not message.photo:
        await bot.send_message(message.chat.id, "Запрос отклонён, пожалуйста сделайте запрос"
                                                " как показано в руководстве",
                               reply_markup=reply_kb_clean_weights)
        return
    if message.md_text.split('-')[0][:-1].strip() in clean_weights_buttons:
        await bot.send_message(message.chat.id, 'Предмет с таким названием, уже есть в базе.'
                                                ' Пожалуйста придумайте другое название и повторите попытку',
                               reply_markup=reply_kb_clean_weights)
        return
    new_clean_weight = ButtonsCleanWeights()
    new_clean_weight.name_clean_weight = message.md_text.split('-')[0][:-1].strip()
    new_clean_weight.description_clean_w = message.md_text.split('-')[1].strip()
    last_row = dbs.query(ButtonsCleanWeights).order_by(ButtonsCleanWeights.id.desc()).first()
    if last_row:
        path = f'photos_of_clean_weights/{last_row.id + 1}.jpg'
    else:
        path = f'photos_of_clean_weights/1.jpg'
    new_clean_weight.path = path
    dbs.add(new_clean_weight)
    clean_weights_buttons.append(new_clean_weight.name_clean_weight)
    await message.photo[-1].download(path)
    reply_kb_clean_weights.keyboard = reply_kb_clean_weights.keyboard[:-1]
    if len(dbs.query(ButtonsCleanWeights).all()) % 2 != 0:
        reply_kb_clean_weights.add(types.KeyboardButton(new_clean_weight.name_clean_weight))
    else:
        reply_kb_clean_weights.insert(types.KeyboardButton(new_clean_weight.name_clean_weight))
    reply_kb_clean_weights.add(types.KeyboardButton('Вернуться в меню'))
    await bot.send_message(message.chat.id, 'Новый чистый вес добавлен!',
                           reply_markup=reply_kb_clean_weights)
    dbs.commit()
    await CleanWeights.waiting_for_request.set()


@dp.message_handler(content_types=['photo', 'text'], state=CleanWeights.waiting_for_remove_clean_weight)
async def remove_clean_weight(message: types.Message, state: FSMContext):
    dbs = db_session.create_session()
    if message.md_text in 'Вернуться в меню':
        await bot.send_message(message.chat.id, 'Вы в меню',
                               reply_markup=reply_kb_menu)
        await state.finish()
        return
    elif message.text in clean_weights_buttons:
        clean_weight = dbs.query(ButtonsCleanWeights).filter(ButtonsCleanWeights.name_clean_weight
                                                             == message.text).first()
        os.remove(clean_weight.path)
        dbs.delete(clean_weight)
        clean_weights_buttons.remove(clean_weight.name_clean_weight)

        reply_kb_clean_weights.keyboard.clear()
        reply_kb_clean_weights.add(types.KeyboardButton('Добавить новый чистый вес'))
        reply_kb_clean_weights.add(types.KeyboardButton('Удалить вес'))
        load_buttons(reply_kb_clean_weights, [*clean_weights_buttons])
        await bot.send_message(message.chat.id, 'Чистый вес успешно удалён!',
                               reply_markup=reply_kb_clean_weights)
        dbs.commit()
        await CleanWeights.waiting_for_request.set()
    else:
        await bot.send_message(message.chat.id, 'Такого предмета нету в базе данных!',
                               reply_markup=reply_kb_clean_weights)


@dp.message_handler(commands=['start'])
async def begin(message: types.Message):
    dbs = db_session.create_session()
    current_user = dbs.query(User).get(message.from_user.id)
    if not current_user:
        user = User()
        user.id = message.from_user.id
        user.metal = 'Черный'
        user.price = float(metal_types['Черный'])
        dbs.add(user)
    else:
        current_user.metal = 'Черный'
        current_user.price = float(metal_types['Черный'])
        current_user.client_amount = 0
        current_user.kush_recording = False
        current_user.operation_ended = False
        current_user.kush_percent = 0
    dbs.commit()
    print(type(message.chat.id))
    await bot.send_message(message.chat.id, 'Бот включён, приятного пользования!', reply_markup=reply_kb_menu)


@dp.message_handler(content_types=['text', 'photo'])
async def set_text(message):
    global temp_weights
    if message.chat.type == 'private':
        if message.text == 'Записать веса':
            await bot.send_message(message.chat.id, 'Типы металлов загружены',
                                   reply_markup=reply_kb_metals)
            await Recording.waiting_for_data_record.set()
            return
        if message.text == 'Куш':
            await bot.send_message(message.chat.id, 'Кнопки куша загружены',
                                   reply_markup=reply_kb_kush)
            await Kush.waiting_for_kush_request.set()
        if message.text == 'Отчёты':
            await bot.send_message(message.chat.id, 'Кнопки отчётов загружены',
                                   reply_markup=reply_kb_information)
            await Report.waiting_for_report_request.set()
        if message.text == 'Чистые веса':
            await bot.send_message(message.chat.id, 'Кнопки чистых весов загружены',
                                   reply_markup=reply_kb_clean_weights)
            await CleanWeights.waiting_for_request.set()
        if message.text == '📚Руководство':
            pass


async def for_startup(empty):
    for user_id in db_session.create_session().query(User.id).all():
        await bot.send_message(user_id[0], 'Бот перезапущен', reply_markup=reply_kb_menu)


if __name__ == '__main__':
    while True:
        try:
            executor.start_polling(dp, skip_updates=True, on_startup=for_startup)
        except Exception as e:
            print(e)