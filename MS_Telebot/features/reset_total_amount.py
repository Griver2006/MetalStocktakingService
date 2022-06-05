from aiogram.types import Message

from keyboards.inline_kb_markup import inline_kb_markup

from data import db_session
from data.users import User


async def reset_total_amount(message: Message):
    # Сбрасываем общую сумму клиента в базе
    dbs = db_session.create_session()
    user = dbs.query(User).get(message.from_user.id)
    user.client_amount = 0
    dbs.commit()
    # И также сбрасываем это значение у кнопки (Здесь на самом деле я удаляю кнопку)
    inline_kb_markup.inline_keyboard.clear()
    await message.answer('Ждём нового клиента')