import asyncio
import datetime as dt

from config import settings

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

bot = Bot(token=settings.TELEGRAM_BOT_API_KEY)
storage = MemoryStorage()
dp = Dispatcher(bot=bot, storage=storage)

### Start Bot
async def main():
    if bot.token == settings.TELEGRAM_BOT_API_KEY:
        print(f"{dt.datetime.now} – Starting Personal Intelligence Node – Telegram Bot...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
