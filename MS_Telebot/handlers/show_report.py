from aiogram import types
from aiogram.dispatcher import FSMContext
from api_sheets import get_report, call_metals_prices

from loader import dp

from states.report import Report

from keyboards.reply_kb_menu import reply_kb_menu
from keyboards.reply_kb_information import reply_kb_information


@dp.message_handler(state=Report.waiting_for_report_request)
async def show_report(message: types.Message, state: FSMContext):
    if message.text == 'Вернуться в меню':
        await message.bot.send_message(message.chat.id, 'Записывание весов металла остановлено',
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
        await message.bot.send_message(message.chat.id, data,
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
        await message.bot.send_message(message.chat.id, data,
                                       reply_markup=reply_kb_information)
        return
    elif message.text == 'Цены металлов':
        # Вызываем функцию которая возвращяет цены металлов
        request = call_metals_prices()
        if not request:
            request = call_metals_prices()
        data = f'\n{"---" * 10}\n'.join([' '.join(cort) for cort in request])
        await message.bot.send_message(message.chat.id, data,
                                       reply_markup=reply_kb_information)
        return
    elif message.text == 'Куш цены металлов':
        # Вызываем функцию которая возвращяет цены металлов, передаём значение чтобы цены вернули из другой таблицы
        request = call_metals_prices(kush=True)
        if not request:
            request = call_metals_prices(kush=True)
        data = f'\n{"---" * 10}\n'.join([' '.join(cort) for cort in request])
        await message.bot.send_message(message.chat.id, data,
                                       reply_markup=reply_kb_information)