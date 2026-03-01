import asyncio
import sys
import logging
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parents[2]))


from apps.telegram_bot.config import settings

#from apps.telegram_bot.db_handler import PostgresHandler
from apps.telegram_bot.handlers.start import start_router

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

#postgres_db = PostgresHandler(settings.POSTGRES_LINK)

bot = Bot(token=settings.TELEGRAM_BOT_API_KEY, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
storage = MemoryStorage()
dp = Dispatcher(bot=bot, storage=storage)

# Start Bot
async def main():
    if bot.token == settings.TELEGRAM_BOT_API_KEY:
        print("Starting Personal Intelligence Node – Telegram Bot...")
    dp.include_router(start_router)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
