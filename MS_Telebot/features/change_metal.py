from utils.some_variable import metal_types
from keyboards.reply_kb_kush_recording import reply_kb_kush_recording
from keyboards.reply_kb_metals import reply_kb_metals

from data import db_session
from data.users import User


async def change_metal(message):
    dbs = db_session.create_session()
    user = dbs.query(User).get(message.from_user.id)
    user.metal = message.text  # Меняем металл у пользователя
    user.price = float(metal_types[message.text])  # Также меняем цену, её собственно берём из словаря
    dbs.commit()
    await message.bot.send_message(message.chat.id,
                                   f'Выбранный тип металла: {user.metal},'
                                   f' Цена: {user.price}',
                                   reply_markup=reply_kb_kush_recording if user.kush_recording else reply_kb_metals)