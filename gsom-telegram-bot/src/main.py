# filepath: /gsom-telegram-bot/gsom-telegram-bot/src/main.py
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.types import Message
from config import TOKEN
from handlers import register_handlers

bot = Bot(token=TOKEN)
dp = Dispatcher()

async def start_handler(message: Message):
    await message.answer("Привет! Я твой ассистент в СПбГУ.")

async def main():
    register_handlers(dp)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())