import os
from aiogram import types
from aiogram.dispatcher import FSMContext

from loader import dp

from states.cleanWeights import CleanWeights

from keyboards.reply_kb_menu import reply_kb_menu
from keyboards.reply_kb_clean_weights import reply_kb_clean_weights

from utils.some_variable import clean_weights_buttons

from data import db_session
from data.clean_weights import ButtonsCleanWeights


@dp.message_handler(state=CleanWeights.waiting_for_request)
async def clean_weights(message: types.Message, state: FSMContext):
    dbs = db_session.create_session()
    if message.text == 'Вернуться в меню':
        await message.bot.send_message(message.chat.id, 'Вы в меню',
                                       reply_markup=reply_kb_menu)
        await state.finish()
        return
    if message.text == 'Добавить новый предмет с его чистым весом':
        await message.bot.send_message(message.chat.id, 'Добавьте фото предмета с его названием и описанием',
                                       reply_markup=reply_kb_clean_weights)
        # Переходим в состояния(функцию) для добавления нового чистого веса
        await CleanWeights.waiting_for_new_clean_weights.set()
        return
    if message.text == 'Удалить предмет':
        await message.bot.send_message(message.chat.id, 'Нажмите на копку с названием предмета',
                                       reply_markup=reply_kb_clean_weights)
        # Переходим в состояния(функцию) для удаления чистого веса
        await CleanWeights.waiting_for_remove_clean_weight.set()
    if message.text in clean_weights_buttons:
        # Отправляем пользователю фото предмета с его чистым весом
        clean_weight = dbs.query(ButtonsCleanWeights).filter(ButtonsCleanWeights.name_clean_weight
                                                             == message.text).first()
        await message.bot.send_photo(message.from_user.id, types.InputFile(clean_weight.path),
                                     caption=clean_weight.description_clean_w,
                                     reply_to_message_id=message.message_id)


# Состояние(функция из Меню кнопки 'Чистые веса') для добавления чистого веса
@dp.message_handler(content_types=['photo', 'text'], state=CleanWeights.waiting_for_new_clean_weights)
async def add_new_clean_weight(message: types.Message, state: FSMContext):
    dbs = db_session.create_session()
    # Делаем проверку отправил ли пользователь текст с картинкой
    if not message.caption:
        await message.bot.send_message(message.chat.id, "Запрос отклонён, пожалуйста сделайте запрос"
                                                        " как показано в руководстве и повторите комманду",
                                       reply_markup=reply_kb_clean_weights)
        # Возвращаемся в состояния(Меню кнопки 'Чистые веса')
        await CleanWeights.waiting_for_request.set()
        return
    if message.md_text in 'Вернуться в меню':
        await message.bot.send_message(message.chat.id, 'Вы в меню',
                                       reply_markup=reply_kb_menu)
        await state.finish()
        return
    # Делаем проверку отправил ли пользователь текст с '-'
    if not message.md_text or '-' not in message.md_text and message.md_text.count('-') == 1 or not message.photo or\
            '-' not in message.caption:
        await message.bot.send_message(message.chat.id, "Запрос отклонён, пожалуйста сделайте запрос"
                                                        " как показано в руководстве и повторите комманду",
                                       reply_markup=reply_kb_clean_weights)
        # Возвращаемся в состояния(Меню кнопки 'Чистые веса')
        await CleanWeights.waiting_for_request.set()
        return
    # Делаем проверку есть ли чистый вес уже в списке чистых весов
    if message.md_text.split('-')[0][:-1].strip() in clean_weights_buttons:
        await message.bot.send_message(message.chat.id, 'Предмет с таким названием, уже есть в базе.'
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
    await message.bot.send_message(message.chat.id, 'Новый чистый вес добавлен!',
                                   reply_markup=reply_kb_clean_weights)
    dbs.commit()
    # Возвращаемся в состояния(Меню кнопки 'Чистые веса')
    await CleanWeights.waiting_for_request.set()


# Состояние(функция из Меню кнопки 'Чистые веса') для удаления чистого веса
@dp.message_handler(content_types=['photo', 'text'], state=CleanWeights.waiting_for_remove_clean_weight)
async def remove_clean_weight(message: types.Message, state: FSMContext):
    dbs = db_session.create_session()
    if message.md_text in 'Вернуться в меню':
        await message.bot.send_message(message.chat.id, 'Вы в меню',
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
        await message.bot.send_message(message.chat.id, 'Чистый вес успешно удалён!',
                                       reply_markup=reply_kb_clean_weights)
        # Возвращаемся в состояния(Меню кнопки 'Чистые веса')
        await CleanWeights.waiting_for_request.set()
    else:
        await message.bot.send_message(message.chat.id, 'Такого предмета нету в базе данных!',
                                       reply_markup=reply_kb_clean_weights)