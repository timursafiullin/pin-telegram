import logging

from apps.telegram_bot.config import settings

#from apps.telegram_bot.db_handler import PostgresHandler

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
