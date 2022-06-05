from aiogram import executor

from loader import dp
import handlers
from utils.notify_users import for_startup
import utils.set_default_commands


async def on_startup(dispatcher):
    await for_startup(dispatcher)


if __name__ == '__main__':
    executor.start_polling(dp, on_startup=on_startup)