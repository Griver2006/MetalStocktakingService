from aiogram import types


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