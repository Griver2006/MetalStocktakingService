from keyboards.reply_kb_menu import reply_kb_menu
from data import db_session
from data.users import User


async def for_startup(dp):
    # При запуске бота возвращяем всех пользователей в меню
    for user_id in db_session.create_session().query(User.id).all():
        await dp.bot.send_message(user_id[0], 'Бот запущен!', reply_markup=reply_kb_menu)