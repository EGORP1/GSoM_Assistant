# This file defines callback functions that handle user interactions with the bot, such as button presses.

from aiogram import types
from aiogram.dispatcher import Dispatcher

async def start_handler(message: types.Message):
    # Implementation of the start command handler
    pass

async def callback_handler(callback: types.CallbackQuery):
    # Implementation of the callback query handler
    pass

def register_handlers(dp: Dispatcher):
    dp.register_message_handler(start_handler, commands=["start"])
    dp.register_callback_query_handler(callback_handler)